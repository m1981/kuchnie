"""Seed U-U (island) postformed worktop variants.

Global Collection 2026 postformed worktops (blaty-postformed-spec.md,
str. 43 + 48 of blaty.pdf):

1. U-U profile = BOTH long edges factory-postformed (Unoflex, R=3.3mm),
   widths 900mm and 1200mm, length 4100mm, thickness 38mm.
2. Eligibility: decor must be listed in the manufacturer's 2026 postformed
   table (columns "Profil 2U 900mm" / "Profil 2U 1200mm") — the table
   documents 2U availability for its 40 rows / 39 distinct decor codes.
   Decors with a PF-U-600 variant in the DB but absent from that table
   (currently 0190) are NOT seeded: no manufacturer evidence of a 2U offer.
3. Edge banding: the table's "Obrzeże HPL" column lists an HPL edge roll
   (42 x 4110 mm, w krążku) for its full decor list, and the edge code is
   identical to the decor code (verified row by row in the source doc).
   The seeder materialises that edge, links it to the source PF-U-600
   variant (establishing the spec's "U variant's edge"), then copies the
   link to both new U-U variants.

NOTE on representation: variant_edges has no per-edge-position column
(UNIQUE(variant_id, edge_id) only), so a single variant→edge link is the
correct representation of "the same edge program applies to this worktop".
The both-long-edges-finished fact of U-U is carried by the profile row
(worktop_profiles code 'U-U', profiled_sides = 'front,back'), not by
duplicated variant_edges rows.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "catalog.db"

# Distinct decor codes of the Global Collection 2026 postformed table
# (blaty-postformed-spec.md section 5.1; 40 rows, K023 appears twice with
# structures SU and SQ, hence 39 distinct codes). These are the decors with
# documented "Profil 2U" (U-U) availability at 900mm and 1200mm.
GLOBAL_2026_POSTFORMED_DECORS = {
    # XIV MAT 1
    "7045", "868S", "K091", "K092", "K203", "K204", "K206", "K212", "K215",
    # XV MAT 2
    "4298", "4299", "5527", "K002", "K003", "K013", "K016", "K023", "K028",
    "K029", "K030", "K095", "K201", "K205", "K207", "K209", "K210", "K213",
    "K214", "K367", "K368", "K369",
    # XVI HG 1: K023 (SQ) — same code as XV MAT 2 row
    # XVII HG 2
    "K217", "K218", "2738", "K698",
    # XVIII SPECIAL
    "K699", "K703", "K704", "K705",
}

# U-U sheet formats: (slug, length_mm, width_mm), per packing table str. 43
UU_FORMATS = (("4100x900", 4100, 900), ("4100x1200", 4100, 1200))


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def ensure_sheet_formats(db: sqlite3.Connection) -> int:
    """Create the U-U sheet formats if missing (idempotent)."""
    added = 0
    for slug, length_mm, width_mm in UU_FORMATS:
        cur = db.execute(
            "INSERT OR IGNORE INTO sheet_formats (slug, length_mm, width_mm, use_hint) "
            "VALUES (?, ?, ?, 'worktop')",
            (slug, length_mm, width_mm),
        )
        added += cur.rowcount
    db.commit()
    return added


def _eligible_u_variants(db: sqlite3.Connection) -> list[sqlite3.Row]:
    """PF-U-600 variants whose decor has documented 2U availability."""
    rows = db.execute(
        "SELECT v.id AS variant_pk, v.business_id, v.decor_id, v.material_id, "
        "       v.structure_id, d.business_id AS decor_code "
        "FROM variants v "
        "JOIN decors d ON d.id = v.decor_id "
        "WHERE v.business_id LIKE '%-PF-U-600' "
        "ORDER BY d.business_id"
    ).fetchall()
    return [r for r in rows if r["decor_code"] in GLOBAL_2026_POSTFORMED_DECORS]


def ensure_hpl_edges(db: sqlite3.Connection) -> tuple[int, int]:
    """Create HPL edge-roll records and link them to the source U variants.

    Source: 'Obrzeże HPL' column of the 2026 postformed table — an HPL edge
    roll 42 x 4110 mm whose code equals the decor code. Linking it to the
    PF-U-600 variant gives the U-U seeding an honest in-DB edge source.
    """
    edges_added = 0
    links_added = 0

    for var in _eligible_u_variants(db):
        decor_code = var["decor_code"]

        edge = db.execute(
            "SELECT id FROM edges WHERE code = ?", (decor_code,)
        ).fetchone()
        if not edge:
            db.execute(
                "INSERT INTO edges (code, material, width_mm, notes) "
                "VALUES (?, 'HPL', 42, ?)",
                (
                    decor_code,
                    f"Obrzeże HPL 42x4110mm (w krążku) dla blatu {decor_code} "
                    "— Global Collection 2026, blaty.pdf str. 48",
                ),
            )
            edge_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            edges_added += 1
        else:
            edge_id = edge["id"]

        cur = db.execute(
            "INSERT OR IGNORE INTO variant_edges (variant_id, edge_id) VALUES (?, ?)",
            (var["variant_pk"], edge_id),
        )
        links_added += cur.rowcount

    db.commit()
    return edges_added, links_added


def seed_uu_variants(db: sqlite3.Connection) -> tuple[int, int]:
    """Create {code}-PF-UU-900 / {code}-PF-UU-1200 variants + edge links.

    Structure is inherited from the source PF-U-600 variant; edge links are
    copied from it (see module docstring for the U-U representation note).
    """
    format_ids = {}
    for slug, _, _ in UU_FORMATS:
        format_ids[slug] = db.execute(
            "SELECT id FROM sheet_formats WHERE slug = ?", (slug,)
        ).fetchone()["id"]

    variants_added = 0
    links_added = 0

    for var in _eligible_u_variants(db):
        u_edge_ids = [
            r["edge_id"]
            for r in db.execute(
                "SELECT edge_id FROM variant_edges WHERE variant_id = ?",
                (var["variant_pk"],),
            ).fetchall()
        ]

        for slug, _, width_mm in UU_FORMATS:
            uu_business_id = f"{var['decor_code']}-PF-UU-{width_mm}"

            existing = db.execute(
                "SELECT id FROM variants WHERE business_id = ?",
                (uu_business_id,),
            ).fetchone()
            if existing:
                uu_pk = existing["id"]
            else:
                db.execute(
                    "INSERT INTO variants "
                    "(business_id, decor_id, material_id, structure_id, "
                    " sheet_format_id, roles, thickness_mm) "
                    "VALUES (?, ?, ?, ?, ?, '[\"worktop\"]', 38.0)",
                    (
                        uu_business_id,
                        var["decor_id"],
                        var["material_id"],
                        var["structure_id"],
                        format_ids[slug],
                    ),
                )
                uu_pk = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                variants_added += 1

            for edge_id in u_edge_ids:
                cur = db.execute(
                    "INSERT OR IGNORE INTO variant_edges (variant_id, edge_id) "
                    "VALUES (?, ?)",
                    (uu_pk, edge_id),
                )
                links_added += cur.rowcount

    db.commit()
    return variants_added, links_added


def main() -> None:
    db = get_db()

    before_v = db.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
    before_ve = db.execute("SELECT COUNT(*) FROM variant_edges").fetchone()[0]
    before_sf = db.execute("SELECT COUNT(*) FROM sheet_formats").fetchone()[0]

    print("Ensuring U-U sheet formats (4100x900, 4100x1200)...")
    formats = ensure_sheet_formats(db)
    print(f"  → {formats} sheet formats added")

    print("Ensuring HPL edge rolls on source U variants...")
    edges, u_links = ensure_hpl_edges(db)
    print(f"  → {edges} edges created, {u_links} U-variant edge links")

    print("Seeding U-U variants (900/1200)...")
    variants, uu_links = seed_uu_variants(db)
    print(f"  → {variants} U-U variants created, {uu_links} U-U edge links")

    after_v = db.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
    after_ve = db.execute("SELECT COUNT(*) FROM variant_edges").fetchone()[0]
    after_sf = db.execute("SELECT COUNT(*) FROM sheet_formats").fetchone()[0]
    total_uu = db.execute(
        "SELECT COUNT(*) FROM variants WHERE business_id LIKE '%-PF-UU-%'"
    ).fetchone()[0]

    print("\nDatabase totals (before → after):")
    print(f"  Variants:       {before_v} → {after_v}")
    print(f"  Variant-edges:  {before_ve} → {after_ve}")
    print(f"  Sheet formats:  {before_sf} → {after_sf}")
    print(f"  U-U variants:   {total_uu}")

    db.close()


if __name__ == "__main__":
    main()
