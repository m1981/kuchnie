"""Seed pairings and edges for the configurator.

1. Carcass pairings: every Kronospan front decor → K110 (default)
2. Edges: from obrzeze codes in global-collection-decory.yaml
3. Variant-edges: link front variants to their matching edges
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs" / "materials" / "Kronospan"
DB_PATH = Path(__file__).parent.parent / "db" / "catalog.db"


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def seed_carcass_pairings(db: sqlite3.Connection) -> int:
    """Add default carcass pairing for every front decor → K110."""
    # Find K110 decor id
    k110 = db.execute(
        "SELECT id FROM decors WHERE business_id = 'K110'"
    ).fetchone()
    if not k110:
        print("  ⚠ K110 not found in decors — skipping carcass pairings")
        return 0
    k110_id = k110["id"]

    # Find all front-capable decors
    fronts = db.execute(
        "SELECT DISTINCT d.id, d.business_id "
        "FROM decors d "
        "JOIN variants v ON v.decor_id = d.id "
        "WHERE v.roles LIKE '%front%' "
        "ORDER BY d.business_id"
    ).fetchall()

    added = 0
    for front in fronts:
        # Check if pairing already exists
        existing = db.execute(
            "SELECT 1 FROM pairings "
            "WHERE front_decor_id = ? AND target_decor_id = ? AND pairing_type = 'carcass'",
            (front["id"], k110_id),
        ).fetchone()
        if existing:
            continue

        db.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type, priority, notes) "
            "VALUES (?, ?, 'carcass', 'default', 99, 'biały korpusowy — uniwersalny default')",
            (front["id"], k110_id),
        )
        added += 1

    db.commit()
    return added


def seed_edges(db: sqlite3.Connection) -> tuple[int, int]:
    """Create edge records from obrzeze codes, link to variants."""
    with open(DOCS_DIR / "global-collection-decory.yaml", encoding="utf-8") as f:
        full_data = yaml.safe_load(f)
    full_map = {str(d["dekor"]): d for d in full_data["dekory"]}

    # Get Schilsner supplier id
    schilsner = db.execute(
        "SELECT id FROM edge_suppliers WHERE slug = 'schilsner'"
    ).fetchone()
    supplier_id = schilsner["id"] if schilsner else None

    edges_added = 0
    links_added = 0

    # Process all variants with front role
    variants = db.execute(
        "SELECT v.id AS variant_pk, v.business_id, v.structure_id, "
        "       d.business_id AS decor_code "
        "FROM variants v "
        "JOIN decors d ON d.id = v.decor_id "
        "WHERE v.roles LIKE '%front%'"
    ).fetchall()

    for var in variants:
        decor_code = var["decor_code"]
        full_decor = full_map.get(decor_code)
        if not full_decor:
            continue

        obrzeze = full_decor.get("obrzeze")
        if not obrzeze:
            continue

        # Check if edge exists
        edge = db.execute(
            "SELECT id FROM edges WHERE code = ?",
            (obrzeze,),
        ).fetchone()

        if not edge:
            # Create edge
            db.execute(
                "INSERT INTO edges (code, supplier_id, material, notes) "
                "VALUES (?, ?, 'ABS', ?)",
                (obrzeze, supplier_id, f"Obrzeże dla {decor_code}"),
            )
            edge_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            edges_added += 1
        else:
            edge_id = edge["id"]

        # Link variant → edge
        existing = db.execute(
            "SELECT 1 FROM variant_edges WHERE variant_id = ? AND edge_id = ?",
            (var["variant_pk"], edge_id),
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO variant_edges (variant_id, edge_id) VALUES (?, ?)",
                (var["variant_pk"], edge_id),
            )
            links_added += 1

    db.commit()
    return edges_added, links_added


def main() -> None:
    db = get_db()

    print("Seeding carcass pairings...")
    pairings = seed_carcass_pairings(db)
    print(f"  → {pairings} carcass pairings added")

    print("Seeding edges from obrzeze codes...")
    edges, links = seed_edges(db)
    print(f"  → {edges} edges created, {links} variant-edge links")

    # Summary
    total_pairings = db.execute("SELECT COUNT(*) FROM pairings").fetchone()[0]
    total_edges = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    total_links = db.execute("SELECT COUNT(*) FROM variant_edges").fetchone()[0]
    print(f"\nDatabase totals:")
    print(f"  Pairings:       {total_pairings}")
    print(f"  Edges:          {total_edges}")
    print(f"  Variant-edges:  {total_links}")

    db.close()


if __name__ == "__main__":
    main()
