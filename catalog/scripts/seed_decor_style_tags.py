"""Seed decor_style_tags — associate front decors with style tags.

Rule-based approach by color family:
  dab, orzech, jesion, buk, wiaz, brzoza → wood
  czarny → industrial, bold
  szary → modern, stone
  bialy → minimalist, modern
  zielony → bold, nature
  niebieski → bold
  czerwony → bold
  bezowy, kremowy → warm, classic
  marmur → stone, classic
  lupek → stone, industrial
  brazowy → warm, classic
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "catalog.db"

# color_family → list of (style_tag_slug, relevance)
COLOR_STYLE_MAP = {
    "dab":       [("wood", 3), ("warm", 2), ("classic", 1)],
    "orzech":    [("wood", 3), ("warm", 2), ("classic", 2)],
    "jesion":    [("wood", 3), ("warm", 1)],
    "buk":       [("wood", 3), ("warm", 1)],
    "wiaz":      [("wood", 3), ("warm", 1)],
    "brzoza":    [("wood", 2), ("warm", 1)],
    "czarny":    [("industrial", 2), ("bold", 2), ("modern", 1)],
    "szary":     [("modern", 2), ("stone", 1), ("matte", 1)],
    "bialy":     [("minimalist", 3), ("modern", 2)],
    "zielony":   [("bold", 3), ("modern", 1)],
    "niebieski": [("bold", 3), ("modern", 1)],
    "czerwony":  [("bold", 3)],
    "bezowy":    [("warm", 2), ("classic", 1)],
    "kremowy":   [("warm", 2), ("classic", 1)],
    "marmur":    [("stone", 3), ("classic", 1)],
    "lupek":     [("stone", 3), ("industrial", 2)],
    "brazowy":   [("warm", 2), ("classic", 2), ("wood", 1)],
}


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def seed_decor_style_tags(db: sqlite3.Connection) -> int:
    # Build style_tag slug → id map
    tag_map = {}
    for row in db.execute("SELECT id, slug FROM style_tags").fetchall():
        tag_map[row["slug"]] = row["id"]

    # Get all front decors with color family
    fronts = db.execute(
        "SELECT d.id, d.business_id, COALESCE(cf.slug, '') AS color "
        "FROM decors d "
        "JOIN variants v ON v.decor_id = d.id "
        "LEFT JOIN color_families cf ON cf.id = d.color_family_id "
        "WHERE v.roles LIKE '%front%' "
        "GROUP BY d.id"
    ).fetchall()

    added = 0
    for front in fronts:
        color = front["color"]
        if color not in COLOR_STYLE_MAP:
            continue

        for tag_slug, relevance in COLOR_STYLE_MAP[color]:
            tag_id = tag_map.get(tag_slug)
            if not tag_id:
                continue

            db.execute(
                "INSERT OR IGNORE INTO decor_style_tags "
                "(decor_id, style_tag_id, relevance) VALUES (?, ?, ?)",
                (front["id"], tag_id, relevance),
            )
            added += 1

    db.commit()
    return added


def main() -> None:
    db = get_db()

    print("Seeding decor_style_tags...")
    added = seed_decor_style_tags(db)
    print(f"  → {added} decor-style associations")

    total = db.execute("SELECT COUNT(*) FROM decor_style_tags").fetchone()[0]
    print(f"  → {total} associations total in table")
    by_tag = db.execute(
        "SELECT st.slug, COUNT(*) as cnt "
        "FROM decor_style_tags dst "
        "JOIN style_tags st ON st.id = dst.style_tag_id "
        "GROUP BY st.slug ORDER BY cnt DESC"
    ).fetchall()
    print("\nBy style tag:")
    for row in by_tag:
        print(f"  {row['slug']:15s} {row['cnt']} decors")

    db.close()


if __name__ == "__main__":
    main()
