"""Seed worktop_compatibility table.

Rule-based approach:
- designer_pick: front and worktop share same color_family
- safe: neutral worktops (bialy, szary, bezowy, kremowy) go with anything
- bold: contrasting color families
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "catalog.db"

# Neutral worktop color families — universally compatible
NEUTRAL_COLORS = {"bialy", "szary", "bezowy", "kremowy"}


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def seed_worktop_compatibility(db: sqlite3.Connection) -> int:
    """Seed worktop_compatibility from color family rules."""
    # Get all front decors with color family
    fronts = db.execute(
        "SELECT d.id, d.business_id, COALESCE(cf.slug, '') AS color "
        "FROM decors d "
        "JOIN variants v ON v.decor_id = d.id "
        "LEFT JOIN color_families cf ON cf.id = d.color_family_id "
        "WHERE v.roles LIKE '%front%' "
        "GROUP BY d.id "
        "ORDER BY d.business_id"
    ).fetchall()

    # Get all worktop decors with color family
    worktops = db.execute(
        "SELECT d.id, d.business_id, COALESCE(cf.slug, '') AS color "
        "FROM decors d "
        "JOIN variants v ON v.decor_id = d.id "
        "LEFT JOIN color_families cf ON cf.id = d.color_family_id "
        "WHERE v.roles LIKE '%worktop%' "
        "GROUP BY d.id "
        "ORDER BY d.business_id"
    ).fetchall()

    if not fronts or not worktops:
        print("  ⚠ No fronts or worktops found — skipping")
        return 0

    added = 0
    for front in fronts:
        for worktop in worktops:
            # Skip self-pairing (same decor as both front and worktop)
            if front["id"] == worktop["id"]:
                continue

            # Determine match quality
            if front["color"] and front["color"] == worktop["color"]:
                quality = "designer_pick"
                note = f"Ten sam kolor: {front['color']}"
            elif worktop["color"] in NEUTRAL_COLORS:
                quality = "safe"
                note = f"Neutralny blat ({worktop['color']})"
            else:
                quality = "bold"
                note = f"Kontrast: {front['color']} + {worktop['color']}"

            # Priority: designer_pick=1, safe=2, bold=3
            priority = {"designer_pick": 1, "safe": 2, "bold": 3}[quality]

            db.execute(
                "INSERT OR IGNORE INTO worktop_compatibility "
                "(front_decor_id, worktop_decor_id, match_quality, style_note, priority) "
                "VALUES (?, ?, ?, ?, ?)",
                (front["id"], worktop["id"], quality, note, priority),
            )
            added += 1

    db.commit()
    return added


def main() -> None:
    db = get_db()

    print("Seeding worktop_compatibility...")
    added = seed_worktop_compatibility(db)
    print(f"  → {added} compatibility rows added")

    # Summary
    total = db.execute("SELECT COUNT(*) FROM worktop_compatibility").fetchone()[0]
    by_quality = db.execute(
        "SELECT match_quality, COUNT(*) as cnt "
        "FROM worktop_compatibility GROUP BY match_quality"
    ).fetchall()
    print(f"\nDatabase totals:")
    print(f"  Total: {total}")
    for row in by_quality:
        print(f"    {row['match_quality']}: {row['cnt']}")

    db.close()


if __name__ == "__main__":
    main()
