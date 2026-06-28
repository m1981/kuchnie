"""Shared pytest fixtures for catalog schema tests.

Loads the SQLite schema from `catalog/docs/architecture/*.sql` into an
in-memory database. Each test gets a fresh DB — no test pollution.

Migration order:
    1. `01-schema.sql`              — Base schema (v1.0.0)
    2. `02-phase1-worktop-specs.sql` — Phase 1 additions (v1.1.0)
       (more phases will be added as 03-*, 04-*, etc.)
"""

import sqlite3
from pathlib import Path

import pytest

ARCHITECTURE_DIR = (
    Path(__file__).resolve().parent.parent / "docs" / "architecture"
)

SCHEMA_FILES = [
    "01-schema.sql",
    "02-phase1-worktop-specs.sql",
    "03-phase2-decor-structures-and-pairings.sql",
]


def _load_sql(name: str) -> str:
    """Read a SQL file from the architecture directory."""
    path = ARCHITECTURE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"SQL migration not found: {path}")
    return path.read_text(encoding="utf-8")


@pytest.fixture
def db() -> sqlite3.Connection:
    """Fresh in-memory SQLite DB with all migrations applied.

    Yields a connection with FK enforcement enabled.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Foreign keys are OFF by default in SQLite — turn them on.
    conn.execute("PRAGMA foreign_keys = ON")

    for sql_file in SCHEMA_FILES:
        conn.executescript(_load_sql(sql_file))

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def db_with_kronospan(db: sqlite3.Connection) -> sqlite3.Connection:
    """DB seeded with a minimal Kronospan dataset for downstream tests.

    Inserts:
      - producer 'kronospan'
      - collection 'global'
      - material 'kronospan-chipboard-global' (chipboard type)
      - material 'kronospan-postformed-global' (worktop_postformed type)
      - structure 'SM' (Super Mat), 'RS' (Rustykalna)
      - decor K8685 'Biel Alpejska' (board)
      - decor 868S 'Biel Alpejska' (worktop pair to K8685)
    """
    cur = db.cursor()

    # Producer
    cur.execute(
        "INSERT INTO producers (slug, name, country) "
        "VALUES ('kronospan', 'Kronospan', 'Polska')"
    )
    producer_id = cur.lastrowid

    # Collection
    cur.execute(
        "INSERT INTO collections (slug, producer_id, name, has_countertops) "
        "VALUES ('global', ?, 'Global Collection 2026', 1)",
        (producer_id,),
    )
    collection_id = cur.lastrowid

    # Materials
    chipboard_type_id = cur.execute(
        "SELECT id FROM material_types WHERE slug = 'chipboard'"
    ).fetchone()[0]
    postformed_type_id = cur.execute(
        "SELECT id FROM material_types WHERE slug = 'worktop_postformed'"
    ).fetchone()[0]

    cur.execute(
        "INSERT INTO materials (slug, material_type_id, collection_id, name) "
        "VALUES ('kronospan-chipboard-global', ?, ?, 'Global Chipboard')",
        (chipboard_type_id, collection_id),
    )
    cur.execute(
        "INSERT INTO materials (slug, material_type_id, collection_id, name) "
        "VALUES ('kronospan-postformed-global', ?, ?, 'Global Postformed Worktop')",
        (postformed_type_id, collection_id),
    )

    # Structures (producer-scoped to avoid clashes with KronoSwiss SM)
    # SM = Super Mat (primary for K8685), BS = Black Structure,
    # PE = Pearl Effect (primary for K190), RS = Rustykalna
    cur.execute(
        "INSERT INTO structures (code, name, type, finish, producer_id) "
        "VALUES ('SM', 'Super Mat', 'smooth', 'matt', ?)",
        (producer_id,),
    )
    cur.execute(
        "INSERT INTO structures (code, name, type, finish, producer_id) "
        "VALUES ('BS', 'Black Structure', 'structured', 'matt', ?)",
        (producer_id,),
    )
    cur.execute(
        "INSERT INTO structures (code, name, type, finish, producer_id) "
        "VALUES ('PE', 'Pearl Effect', 'structured', 'gloss', ?)",
        (producer_id,),
    )
    cur.execute(
        "INSERT INTO structures (code, name, type, finish, producer_id) "
        "VALUES ('RS', 'Rustykalna', 'wood_grain', 'structured', ?)",
        (producer_id,),
    )

    # Decors
    cur.execute(
        "INSERT INTO decors (business_id, producer_id, name, group_name) "
        "VALUES ('K8685', ?, 'Biel Alpejska', 'WHITE FRONT')",
        (producer_id,),
    )
    cur.execute(
        "INSERT INTO decors (business_id, producer_id, name, group_name) "
        "VALUES ('868S', ?, 'Biel Alpejska', 'XIV MAT 1')",
        (producer_id,),
    )
    cur.execute(
        "INSERT INTO decors (business_id, producer_id, name, group_name) "
        "VALUES ('K190', ?, 'Czarny', 'COLOR BASIC')",
        (producer_id,),
    )

    db.commit()
    return db


# ──────────────────────────────────────────────────────────────────
# Helpers used across multiple tests
# ──────────────────────────────────────────────────────────────────


def lookup_id(db: sqlite3.Connection, table: str, column: str, value: str) -> int:
    """Generic FK resolution helper: SELECT id FROM <table> WHERE <column>=?."""
    row = db.execute(
        f"SELECT id FROM {table} WHERE {column} = ?", (value,)
    ).fetchone()
    if row is None:
        raise LookupError(f"{table}.{column}='{value}' not found")
    return row[0]


@pytest.fixture
def lookup(db: sqlite3.Connection):
    """Convenience fixture: lookup('material_types', 'slug', 'chipboard') → 1."""

    def _lookup(table: str, column: str, value: str) -> int:
        return lookup_id(db, table, column, value)

    return _lookup
