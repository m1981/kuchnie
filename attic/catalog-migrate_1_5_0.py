# TOMBSTONE (2026-07-16): atticized by owner dark-triage decision. One-shot
# generator/migration whose output is already committed (catalog/data/*.yaml,
# schema 1.5.0). The living data pipeline is documented in
# docs/specs/catalog-service.md; rebuild = catalog.scripts.seed + seed_* extras.
"""Migrate an existing catalog.db from schema 1.4.0 to 1.5.0 (ADR-004).

Changes:
  1. pairing_types lookup table; pairings.pairing_type CHECK → FK
  2. decors.one_global / decors.new_2024 columns → decor_tags rows
     (v_decors_full recomputes both, so the API shape is unchanged)
  3. variants.producer_sku column + partial unique index
  4. Views recreated from schema.sql (new v_decors_full definition)

Idempotent: detects an already-migrated DB and exits cleanly.

Usage:
    python -m catalog.scripts.migrate_1_5_0 [db_path]
    (default db_path: catalog/db/catalog.db)
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from catalog.db.engine import get_connection, init_schema

VIEWS = [
    # v_synchro_variants is only defined by the docs/architecture chain;
    # dropped defensively — that chain recreates it, schema.sql does not.
    "v_synchro_variants",
    "v_decors_full",
    "v_pairings_full",
    "v_worktops_full",
    "v_variants_availability",
    "v_decor_structures_full",
    "v_property_flags",
]

PAIRING_TYPES = [
    ("carcass", "Korpus", None),
    ("worktop", "Blat", None),
    ("splashback", "Panel ścienny", None),
    ("side_panel", "Bok widoczny", None),
    ("plinth", "Cokół", None),
    ("hpl_laminate", "Laminat HPL", None),
    ("acrylic", "Akryl", None),
    ("mirror", "Lustro", None),
    ("compact", "Compact", None),
    ("kronoart", "KronoArt", "kronospan"),
    ("black_wood", "BLACK WOOD", "swiss_krono"),
]


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in db.execute(f"PRAGMA table_info({table})")}


def migrate(db: sqlite3.Connection) -> bool:
    """Run the 1.4.0 → 1.5.0 migration. Returns False if already applied."""
    if "one_global" not in _columns(db, "decors"):
        return False

    db.commit()  # PRAGMA foreign_keys is a no-op inside a transaction
    db.execute("PRAGMA foreign_keys=OFF")
    try:
        db.execute("BEGIN")

        # Views must go first: ALTER TABLE RENAME (SQLite ≥3.25)
        # re-validates every view and fails on one that references
        # a just-dropped table. Recreated from schema.sql in step 4.
        for view in VIEWS:
            db.execute(f"DROP VIEW IF EXISTS {view}")

        # ── 1. pairing_types + pairings rebuild ──────────────────
        db.execute(
            "CREATE TABLE IF NOT EXISTS pairing_types ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " slug TEXT NOT NULL UNIQUE,"
            " name TEXT NOT NULL,"
            " producer_hint TEXT,"
            " description TEXT,"
            " created_at TEXT NOT NULL DEFAULT (datetime('now')))"
        )
        db.executemany(
            "INSERT OR IGNORE INTO pairing_types (slug, name, producer_hint)"
            " VALUES (?, ?, ?)",
            PAIRING_TYPES,
        )
        db.execute(
            "CREATE TABLE pairings_new ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " front_decor_id INTEGER NOT NULL REFERENCES decors(id),"
            " target_decor_id INTEGER NOT NULL REFERENCES decors(id),"
            " pairing_type TEXT NOT NULL REFERENCES pairing_types(slug),"
            " match_type TEXT NOT NULL CHECK (match_type IN"
            "   ('exact', 'close', 'default')),"
            " priority INTEGER NOT NULL DEFAULT 1,"
            " notes TEXT,"
            " created_at TEXT NOT NULL DEFAULT (datetime('now')),"
            " updated_at TEXT NOT NULL DEFAULT (datetime('now')),"
            " UNIQUE(front_decor_id, target_decor_id, pairing_type))"
        )
        db.execute(
            "INSERT INTO pairings_new (id, front_decor_id, target_decor_id,"
            " pairing_type, match_type, priority, notes, created_at, updated_at)"
            " SELECT id, front_decor_id, target_decor_id, pairing_type,"
            " match_type, priority, notes, created_at, updated_at FROM pairings"
        )
        db.execute("DROP TABLE pairings")
        db.execute("ALTER TABLE pairings_new RENAME TO pairings")

        # ── 2. flags → decor_tags, then decors rebuild ───────────
        db.execute("INSERT OR IGNORE INTO tags (slug) VALUES ('one-global'), ('new-2024')")
        db.execute(
            "INSERT OR IGNORE INTO decor_tags (decor_id, tag_id)"
            " SELECT d.id, t.id FROM decors d JOIN tags t ON t.slug = 'one-global'"
            " WHERE d.one_global = 1"
        )
        db.execute(
            "INSERT OR IGNORE INTO decor_tags (decor_id, tag_id)"
            " SELECT d.id, t.id FROM decors d JOIN tags t ON t.slug = 'new-2024'"
            " WHERE d.new_2024 = 1"
        )

        db.execute(
            "CREATE TABLE decors_new ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " business_id TEXT NOT NULL,"
            " producer_id INTEGER NOT NULL REFERENCES producers(id),"
            " name TEXT NOT NULL,"
            " name_en TEXT,"
            " group_name TEXT,"
            " color_family_id INTEGER REFERENCES color_families(id),"
            " ncs TEXT, ral TEXT, pantone TEXT, img TEXT,"
            " discontinued BOOLEAN NOT NULL DEFAULT 0,"
            " notes TEXT,"
            " created_at TEXT NOT NULL DEFAULT (datetime('now')),"
            " updated_at TEXT NOT NULL DEFAULT (datetime('now')),"
            " UNIQUE(business_id, producer_id))"
        )
        db.execute(
            "INSERT INTO decors_new (id, business_id, producer_id, name,"
            " name_en, group_name, color_family_id, ncs, ral, pantone, img,"
            " discontinued, notes, created_at, updated_at)"
            " SELECT id, business_id, producer_id, name, name_en, group_name,"
            " color_family_id, ncs, ral, pantone, img, discontinued, notes,"
            " created_at, updated_at FROM decors"
        )
        db.execute("DROP TABLE decors")
        db.execute("ALTER TABLE decors_new RENAME TO decors")

        # ── 3. variants.producer_sku ─────────────────────────────
        if "producer_sku" not in _columns(db, "variants"):
            db.execute("ALTER TABLE variants ADD COLUMN producer_sku TEXT")

        violations = db.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"FK violations after migration: {violations}")
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    finally:
        db.execute("PRAGMA foreign_keys=ON")

    return True


def main() -> None:
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).resolve().parents[1] / "db" / "catalog.db"
    )
    db = get_connection(db_path)
    try:
        if migrate(db):
            init_schema(db)  # recreate views + indexes + seeds at 1.5.0
            print(f"Migrated {db_path} to schema 1.5.0")
        else:
            print(f"{db_path} already at schema 1.5.0 — nothing to do")
    finally:
        db.close()


if __name__ == "__main__":
    main()
