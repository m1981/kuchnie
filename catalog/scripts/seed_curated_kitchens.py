"""Seed curated_kitchens and style_tags tables.

Uses actual variant business_ids from the database.
See docs/curated-kitchens.md for the full design rationale.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "catalog.db"


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


STYLE_TAGS = [
    ("scandinavian", "Skandynawski", "Scandinavian", "aesthetic"),
    ("modern", "Nowoczesny", "Modern", "aesthetic"),
    ("minimalist", "Minimalistyczny", "Minimalist", "aesthetic"),
    ("industrial", "Industrialny", "Industrial", "aesthetic"),
    ("classic", "Klasyczny", "Classic", "era"),
    ("warm", "Ciepły", "Warm", "color_mood"),
    ("bold", "Odwazny", "Bold", "color_mood"),
    ("wood", "Drewno", "Wood", "material_feel"),
    ("stone", "Kamień", "Stone", "material_feel"),
    ("matte", "Matowy", "Matte", "material_feel"),
]


# Each kitchen: (slug, name, description, front, carcass, worktop, edge_code,
#                side_panel, plinth, style_tags, budget_tier, featured)
KITCHENS = [
    (
        "bialy-dab-naturalny",
        "Biały Dąb Naturalny",
        "Klasyczna kuchnia skandynawska — białe drewno dębowe z marmurowym blatem.",
        "K003-CH-18-FP",    # front: Dąb Craft Złoty
        "K110-CH-18-SM",    # carcass: Biały Korpusowy
        "K101-PF-R3-600",   # worktop: Biały Frontowy (white)
        None,                # edge (postformed = built-in)
        "K003-CH-18-FP",    # side panel: matching front
        "K110-CH-18-SM",    # plinth: matching carcass
        '["scandinavian", "warm", "wood"]',
        "standard",
        True,
    ),
    (
        "szampanski-minimalizm",
        "Szampański Minimalizm",
        "Ciepły neutralny front z dębowym blatem — kuchnia „kaszmirowa”.",
        "K5981-CH-18-SM",   # front: Kaszmir
        "K110-CH-18-SM",    # carcass
        "K003-CH-18-FP",    # worktop: Dąb Craft Złoty (as worktop via pairing)
        None,
        "K5981-CH-18-SM",   # side panel: matching front
        "K110-CH-18-SM",    # plinth
        '["scandinavian", "warm", "matte"]',
        "standard",
        True,
    ),
    (
        "biel-alpejska-ultra",
        "Biel Alpejska Ultra",
        "Premium biała kuchnia — monochromatyczna, antybakteryjna.",
        "K8685-CH-18-SM",   # front: Biel Alpejska
        "K110-CH-18-SM",    # carcass
        "868S-PF-U-600",    # worktop: Biel Alpejska (worktop variant)
        None,
        "K8685-CH-18-SM",   # side panel: matching front
        "K110-CH-18-SM",    # plinth
        '["modern", "minimalist", "matte"]',
        "premium",
        True,
    ),
    (
        "antracytowa-perfekcja",
        "Antracytowa Perfekcja",
        "Ciemny antracytowy front z betonowym blatem — nowoczesny industrial.",
        "K164-CH-18-SM",    # front: Antracyt
        "K110-CH-18-SM",    # carcass
        "K200-ABS-635",     # worktop: Beton Jasnoszary
        None,
        "K164-CH-18-SM",    # side panel
        "K110-CH-18-SM",    # plinth
        '["modern", "industrial", "matte"]',
        "standard",
        True,
    ),
    (
        "beton-czarny",
        "Beton & Czarny",
        "Czarne betonowe fronty z jasnoszarym betonowym blatem — klasyczny industrial.",
        "K353-CH-18-RT",    # front: Beton Czarny
        "K110-CH-18-SM",    # carcass
        "K200-ABS-635",     # worktop: Beton Jasnoszary
        None,
        "K353-CH-18-RT",    # side panel
        "K190-CH-18-PE",    # plinth: Czarny
        '["industrial", "stone", "matte"]',
        "standard",
        False,
    ),
    (
        "ciemny-szmaragd",
        "Ciemny Szmaragd",
        "Zielone fronty z białym marmurowym blatem — odważny kolor natury.",
        "K520-CH-18-SU",    # front: Ciemny Szmaragd
        "K110-CH-18-SM",    # carcass
        "K217-PF-U-600",    # worktop: Andromeda Biała (white marble)
        None,
        "K520-CH-18-SU",    # side panel
        "K520-CH-18-SU",    # plinth: matching front
        '["bold", "modern", "matte"]',
        "premium",
        True,
    ),
    (
        "granatowa-elegancja",
        "Granatowa Elegancja",
        "Głęboki granatowy front z szarym kamiennym blatem — „nowy czarny”.",
        "K8984-CH-18-BS",   # front: Granatowy
        "K110-CH-18-SM",    # carcass
        "K540-ABS-635",     # worktop: Albus Szary
        None,
        "K8984-CH-18-BS",   # side panel
        "K190-CH-18-PE",    # plinth: Czarny
        '["bold", "modern", "stone"]',
        "standard",
        False,
    ),
    (
        "dab-craft-zloty",
        "Dąb Craft Złoty",
        "Ciepła klasyczna kuchnia — złoty dąb z metalicznym blatem.",
        "K003-CH-18-FP",    # front: Dąb Craft Złoty
        "K110-CH-18-SM",    # carcass
        "K093-ABS-635",     # worktop: Marmur Szary Emperador
        None,
        "K003-CH-18-FP",    # side panel
        "K003-CH-18-FP",    # plinth: matching front (continuous wood)
        '["classic", "warm", "wood"]',
        "standard",
        True,
    ),
]


def seed_style_tags(db: sqlite3.Connection) -> int:
    added = 0
    for slug, name_pl, name_en, category in STYLE_TAGS:
        db.execute(
            "INSERT OR IGNORE INTO style_tags (slug, name_pl, name_en, category) "
            "VALUES (?, ?, ?, ?)",
            (slug, name_pl, name_en, category),
        )
        added += 1
    db.commit()
    return added


def seed_curated_kitchens(db: sqlite3.Connection) -> int:
    added = 0
    for kitchen in KITCHENS:
        (slug, name, desc, front, carcass, worktop, edge_code,
         side_panel, plinth, tags, tier, featured) = kitchen

        db.execute(
            "INSERT OR IGNORE INTO curated_kitchens "
            "(slug, name, description, front_variant_id, carcass_variant_id, "
            " worktop_variant_id, edge_code, side_panel_variant_id, "
            " plinth_variant_id, style_tag_slugs, budget_tier, featured) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (slug, name, desc, front, carcass, worktop, edge_code,
             side_panel, plinth, tags, tier, featured),
        )
        added += 1
    db.commit()
    return added


def main() -> None:
    db = get_db()

    print("Seeding style_tags...")
    tags = seed_style_tags(db)
    print(f"  → {tags} style tags")

    print("Seeding curated_kitchens...")
    kitchens = seed_curated_kitchens(db)
    print(f"  → {kitchens} curated kitchens")

    # Summary
    total = db.execute("SELECT COUNT(*) FROM curated_kitchens").fetchone()[0]
    featured = db.execute(
        "SELECT COUNT(*) FROM curated_kitchens WHERE featured = 1"
    ).fetchone()[0]
    print("\nDatabase totals:")
    print(f"  Curated kitchens: {total} ({featured} featured)")
    print(f"  Style tags: {db.execute('SELECT COUNT(*) FROM style_tags').fetchone()[0]}")

    db.close()


if __name__ == "__main__":
    main()
