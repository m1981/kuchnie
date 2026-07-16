# TOMBSTONE (2026-07-16): atticized by owner dark-triage decision. One-shot
# generator/migration whose output is already committed (catalog/data/*.yaml,
# schema 1.5.0). The living data pipeline is documented in
# docs/specs/catalog-service.md; rebuild = catalog.scripts.seed + seed_* extras.
"""Generate KronoSwiss catalog YAML from kronoswiss_spec.md.

Produces catalog/data/kronoswiss_full.yaml consumable by CatalogImporter.
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ══════════════════════════════════════════════════════════════════
# Swiss Krono — structures (str. 58-59)
# ══════════════════════════════════════════════════════════════════

SWISS_PRODUCER = {
    "slug": "swiss_krono",
    "name": "Swiss Krono",
    "country": "Szwajcaria",
    "website": "swisskrono.pl",
}

SWISS_STRUCTURES = [
    # From kronoswiss_spec.md str. 58-59 (boards)
    {"code": "SE", "name": "Drewno Jesionu", "name_en": "Ash Structure",
     "type": "wood_grain", "finish": "structured", "synchronized_texture": True,
     "producer_slug": "swiss_krono"},
    {"code": "OV", "name": "One Vision", "name_en": "One Vision",
     "type": "wood_grain", "finish": "structured", "synchronized_texture": True,
     "producer_slug": "swiss_krono"},
    {"code": "SD", "name": "Synchro Dąb", "name_en": "Synchro Oak",
     "type": "wood_grain", "finish": "structured", "synchronized_texture": True,
     "producer_slug": "swiss_krono"},
    {"code": "SW", "name": "Synchro Wiąz", "name_en": "Synchro Elm",
     "type": "wood_grain", "finish": "structured", "synchronized_texture": True,
     "producer_slug": "swiss_krono"},
    {"code": "CL", "name": "Synchro Lambrusco", "name_en": "Synchro Lambrusco",
     "type": "wood_grain", "finish": "structured", "synchronized_texture": True,
     "producer_slug": "swiss_krono"},
    {"code": "MX", "name": "Matrix", "name_en": "Matrix",
     "type": "structured", "finish": "matt",
     "producer_slug": "swiss_krono"},
    {"code": "SM", "name": "Gładka", "name_en": "Smooth",
     "type": "smooth", "finish": "matt",
     "producer_slug": "swiss_krono"},
    {"code": "VL", "name": "Mat", "name_en": "Mat",
     "type": "smooth", "finish": "matt",
     "producer_slug": "swiss_krono"},
    {"code": "BS", "name": "Biurowa", "name_en": "Office Surface",
     "type": "structured", "finish": "matt",
     "producer_slug": "swiss_krono"},
    {"code": "TO", "name": "Touch One", "name_en": "Touch One",
     "type": "structured", "finish": "matt",
     "fingerprint_resistant": True, "producer_slug": "swiss_krono"},
    {"code": "OW", "name": "One Wood", "name_en": "One Wood",
     "type": "wood_grain", "finish": "structured",
     "producer_slug": "swiss_krono"},
    {"code": "PE", "name": "Perlista", "name_en": "Pearl Like",
     "type": "structured", "finish": "gloss",
     "producer_slug": "swiss_krono"},
    # Worktop-specific (str. 94-95)
    {"code": "SQ", "name": "Połysk", "name_en": "Gloss",
     "type": "smooth", "finish": "gloss",
     "producer_slug": "swiss_krono"},
    {"code": "BL", "name": "Blacha", "name_en": "Plate",
     "type": "metal", "finish": "structured",
     "producer_slug": "swiss_krono"},
    {"code": "BT", "name": "Beton", "name_en": "Concrete",
     "type": "stone", "finish": "matt",
     "producer_slug": "swiss_krono"},
    {"code": "KM", "name": "Kamienna", "name_en": "Stone",
     "type": "stone", "finish": "structured",
     "producer_slug": "swiss_krono"},
    {"code": "LP", "name": "Łupek", "name_en": "Shale",
     "type": "stone", "finish": "structured",
     "producer_slug": "swiss_krono"},
    {"code": "SK", "name": "Skalna", "name_en": "Rock",
     "type": "stone", "finish": "structured",
     "producer_slug": "swiss_krono"},
    {"code": "IS", "name": "Italian Stone", "name_en": "Italian Stone",
     "type": "stone", "finish": "structured",
     "producer_slug": "swiss_krono"},
    {"code": "NA", "name": "Naturalne drewno", "name_en": "Natural Wood",
     "type": "wood_grain", "finish": "structured",
     "producer_slug": "swiss_krono"},
    {"code": "SA", "name": "Sandstone", "name_en": "Sandstone",
     "type": "stone", "finish": "structured",
     "producer_slug": "swiss_krono"},
    {"code": "BZ", "name": "Bazaltowa", "name_en": "Basalt",
     "type": "stone", "finish": "matt",
     "producer_slug": "swiss_krono"},
    {"code": "PR", "name": "Pory rustykalne", "name_en": "Rustic Pores",
     "type": "wood_grain", "finish": "structured",
     "producer_slug": "swiss_krono"},
]


# ══════════════════════════════════════════════════════════════════
# Decors — representative subset from kronoswiss_spec.md str. 96-99
# Covers all structure types, one_global flag, new_2024, discontinued.
# ══════════════════════════════════════════════════════════════════

SWISS_LAMINATED_DECORS = [
    # Unikolory (VL)
    {"business_id": "U164", "name": "Antracyt", "name_en": "Anthracite",
     "group_name": "Unikolory", "color_family_slug": "czarny",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "U190", "name": "Czarny", "name_en": "Black",
     "group_name": "Unikolory", "color_family_slug": "czarny",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "U112", "name": "Popiel", "name_en": "Grey",
     "group_name": "Unikolory", "color_family_slug": "szary",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "U570", "name": "Biała Porcelana", "name_en": "White Porcelain",
     "group_name": "Unikolory", "color_family_slug": "bialy",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "U8685", "name": "Biel Alpejska", "name_en": "Alpine White",
     "group_name": "Unikolory", "color_family_slug": "bialy",
     "producer_slug": "swiss_krono"},
    {"business_id": "U119", "name": "Beż Jasły", "name_en": "Light Beige",
     "group_name": "Unikolory", "color_family_slug": "bezowy",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "U6933", "name": "Kaszmirowy", "name_en": "Cashmere",
     "group_name": "Unikolory", "color_family_slug": "kremowy",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "U10030", "name": "Aloesowy", "name_en": "Aloe Green",
     "group_name": "Unikolory", "color_family_slug": "zielony",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "U4809", "name": "Morski", "name_en": "Granit Grey",
     "group_name": "Unikolory", "color_family_slug": "szary",
     "one_global": True, "producer_slug": "swiss_krono"},

    # Drewnopodobne (OW, OV, SE, SD, CL, SW, MX)
    {"business_id": "D9103", "name": "Dąb Jasny", "name_en": "Light Oak",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3025", "name": "Dąb Sonoma", "name_en": "Sonoma Oak",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},
    {"business_id": "D4225", "name": "Dąb Artisan", "name_en": "Artisan Oak Yellow",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D4428", "name": "Dąb Naturalny", "name_en": "Oak Natural",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D20110", "name": "Dąb Nostalgiczny", "name_en": "Soul Oak Natural",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D20230", "name": "Dąb Letni", "name_en": "Grace Oak Natural",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D3823", "name": "Dąb Nowy Jork", "name_en": "New York Oak",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D3314", "name": "Dąb Giovanni", "name_en": "Giovanni Oak",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3316", "name": "Dąb Helsinki", "name_en": "Helsinki Oak",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3801", "name": "Dąb Madryt", "name_en": "Madrid Oak",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3798", "name": "Dąb Londyn", "name_en": "London Oak",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3800", "name": "Dąb Rzym", "name_en": "Rome Oak",
     "group_name": "Drewnopodobne", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3806", "name": "Buk Bordeaux", "name_en": "Bordeaux Beech",
     "group_name": "Drewnopodobne", "color_family_slug": "buk",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3193", "name": "Wiąz Amsterdam", "name_en": "Amsterdam Elm",
     "group_name": "Drewnopodobne", "color_family_slug": "wiaz",
     "producer_slug": "swiss_krono", "discontinued": True},
    {"business_id": "D3194", "name": "Wiąz Allegro", "name_en": "Allegro Elm",
     "group_name": "Drewnopodobne", "color_family_slug": "wiaz",
     "producer_slug": "swiss_krono", "discontinued": True},
    {"business_id": "D722", "name": "Orzech", "name_en": "Walnut",
     "group_name": "Drewnopodobne", "color_family_slug": "orzech",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3813", "name": "Orzech Barcelona", "name_en": "Barcelona Walnut",
     "group_name": "Drewnopodobne", "color_family_slug": "orzech",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D4822", "name": "Orzech Ambasador", "name_en": "Walnut Ambassador",
     "group_name": "Drewnopodobne", "color_family_slug": "orzech",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D3158", "name": "Jesion Werona", "name_en": "Verona Ash",
     "group_name": "Drewnopodobne", "color_family_slug": "jesion",
     "producer_slug": "swiss_krono"},
    {"business_id": "D4426", "name": "Jesion Jasny", "name_en": "Ash White",
     "group_name": "Drewnopodobne", "color_family_slug": "jesion",
     "one_global": True, "producer_slug": "swiss_krono"},

    # Dekory fantazyjne (TO, BS, MX, PE)
    {"business_id": "D30090", "name": "Beton Szary", "name_en": "Cloudy Grey",
     "group_name": "Dekory fantazyjne", "color_family_slug": "szary",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D3274", "name": "Beton", "name_en": "Concrete",
     "group_name": "Dekory fantazyjne", "color_family_slug": "szary",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D1038", "name": "Beton Millennium", "name_en": "Millennium Concrete",
     "group_name": "Dekory fantazyjne", "color_family_slug": "szary",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D4448", "name": "Marmur Crema", "name_en": "Marmo Romeo White",
     "group_name": "Dekory fantazyjne", "color_family_slug": "marmur",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D1861", "name": "Akacja Księżycowa", "name_en": "Moon Acacia",
     "group_name": "Dekory fantazyjne", "color_family_slug": "brzoza",
     "producer_slug": "swiss_krono"},
    {"business_id": "D4878", "name": "Wytrawny Szary Kamień",
     "name_en": "Sophisticated Grey Rock",
     "group_name": "Dekory fantazyjne", "color_family_slug": "szary",
     "producer_slug": "swiss_krono"},

    # NEW 2024
    {"business_id": "D70060", "name": "Terrazzo Fresco", "name_en": "Terrazzo Fresh",
     "group_name": "Dekory fantazyjne", "color_family_slug": "kremowy",
     "one_global": True, "new_2024": True, "producer_slug": "swiss_krono"},
]


SWISS_WORKTOP_DECORS = [
    # BLACK WOOD (KM)
    {"business_id": "U190", "name": "Czarny", "name_en": "Black",
     "group_name": "BLACK WOOD", "color_family_slug": "czarny",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D3274", "name": "Beton", "name_en": "Concrete",
     "group_name": "BLACK WOOD", "color_family_slug": "szary",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D3806", "name": "Buk Bordeaux", "name_en": "Bordeaux Beech",
     "group_name": "BLACK WOOD", "color_family_slug": "buk",
     "producer_slug": "swiss_krono"},
    {"business_id": "D4033", "name": "Dąb Słoneczny", "name_en": "Solar Oak",
     "group_name": "BLACK WOOD", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},
    {"business_id": "D3158", "name": "Jesion Werona", "name_en": "Verona Ash",
     "group_name": "BLACK WOOD", "color_family_slug": "jesion",
     "producer_slug": "swiss_krono"},
    {"business_id": "D4878", "name": "Wytrawny Szary Kamień",
     "name_en": "Sophisticated Grey Rock",
     "group_name": "BLACK WOOD", "color_family_slug": "szary",
     "producer_slug": "swiss_krono"},

    # Postformed worktops
    {"business_id": "K101", "name": "Biały", "name_en": "White",
     "group_name": "Postformed", "color_family_slug": "bialy",
     "producer_slug": "swiss_krono"},
    {"business_id": "D4225", "name": "Dąb Artisan", "name_en": "Artisan Oak",
     "group_name": "Postformed", "color_family_slug": "dab",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D3823", "name": "Dąb Nowy Jork", "name_en": "New York Oak",
     "group_name": "Postformed", "color_family_slug": "dab",
     "one_global": True, "producer_slug": "swiss_krono"},
    {"business_id": "D3025", "name": "Dąb Sonoma", "name_en": "Sonoma Oak",
     "group_name": "Postformed", "color_family_slug": "dab",
     "producer_slug": "swiss_krono"},

    # NEW 2024 worktops
    {"business_id": "D70601", "name": "Calacatta Oro", "name_en": "Calacatta Oro",
     "group_name": "Postformed", "color_family_slug": "bialy",
     "new_2024": True, "producer_slug": "swiss_krono"},
    {"business_id": "D60664", "name": "Dąb Jesienny", "name_en": "Autumn Oak",
     "group_name": "Postformed", "color_family_slug": "dab",
     "new_2024": True, "producer_slug": "swiss_krono"},
]


# ══════════════════════════════════════════════════════════════════
# Build YAML dict
# ══════════════════════════════════════════════════════════════════

# Mapping: decor_code → primary structure_code (KronoSwiss)
SWISS_PRIMARY = {
    # Unikolory
    "U164": "VL", "U190": "VL", "U112": "PE", "U570": "SM",
    "U8685": "SM", "U119": "VL", "U6933": "VL", "U10030": "VL",
    "U4809": "VL",
    # Drewnopodobne
    "D9103": "OW", "D3025": "OW", "D4225": "OV", "D4428": "OV",
    "D20110": "OV", "D20230": "OV", "D3823": "OW", "D3314": "SD",
    "D3316": "SD", "D3801": "CL", "D3798": "CL", "D3800": "CL",
    "D3806": "OW", "D3193": "SW", "D3194": "SW",
    "D722": "SE", "D3813": "OW", "D4822": "OV",
    "D3158": "MX", "D4426": "OV",
    # Fantazyjne
    "D30090": "TO", "D3274": "BS", "D1038": "BS",
    "D4448": "VL", "D1861": "MX", "D4878": "VL",
    "D70060": "TO",
    # Worktops
    "K101": "PE", "D4033": "OW", "D70601": "SM", "D60664": "OW",
}


def _build_swiss_variants(decors: list[dict], primary_map: dict) -> list[dict]:
    """Auto-generate variants for ALL KronoSwiss decors.

    - BLACK WOOD decors → 12mm worktop variant
    - Postformed decors → 38mm worktop variant
    - Others → 18mm chipboard variant
    """
    blackwood_ids = {"U190", "D3274", "D3806", "D4033", "D3158", "D4878"}
    postformed_ids = {"K101", "D4225", "D3823", "D3025", "D70601", "D60664"}

    variants = []
    seen = set()
    for d in decors:
        code = d["business_id"]
        if code in seen:
            continue
        seen.add(code)
        primary = primary_map.get(code)
        if not primary:
            continue

        if code in blackwood_ids:
            variants.append({
                "business_id": f"{code}-BW-12",
                "decor_code": code,
                "material_slug": "swiss-blackwood-board",
                "structure_code": primary,
                "thickness_mm": 12.0,
                "sheet_format_slug": "4100x1315",
                "roles": ["worktop"],
            })
        elif code in postformed_ids:
            variants.append({
                "business_id": f"{code}-PF-R3-600",
                "decor_code": code,
                "material_slug": "swiss-postformed",
                "structure_code": primary,
                "thickness_mm": 38.0,
                "sheet_format_slug": "4100x600",
                "roles": ["worktop"],
            })
        else:
            variants.append({
                "business_id": f"{code}-CH-18-{primary}",
                "decor_code": code,
                "material_slug": "swiss-chipboard",
                "structure_code": primary,
                "thickness_mm": 18.0,
                "sheet_format_slug": "2800x2070",
                "roles": ["front", "carcass"],
            })
    return variants


def generate_kronoswiss_yaml() -> dict:
    # Merge decors (deduplicated)
    seen = set()
    all_decors = []
    for d in SWISS_LAMINATED_DECORS + SWISS_WORKTOP_DECORS:
        if d["business_id"] not in seen:
            all_decors.append(d)
            seen.add(d["business_id"])

    return {
        "producers": [SWISS_PRODUCER],
        "structures": SWISS_STRUCTURES,
        "collections": [
            {
                "slug": "swiss-laminated",
                "producer_slug": "swiss_krono",
                "name": "Płyty Laminowane 2025",
                "source_pdf": "SWISSKRONO_PL-Catalogue-Laminated-boards-and-Worktops-2025_PL_EN.pdf",
                "has_edgebanding": True,
                "has_express": True,
            },
            {
                "slug": "swiss-worktops",
                "producer_slug": "swiss_krono",
                "name": "Blaty Kuchenne 2025",
                "source_pdf": "SWISSKRONO_PL-Catalogue-Laminated-boards-and-Worktops-2025_PL_EN.pdf",
                "has_countertops": True,
                "has_express": True,
            },
            {
                "slug": "swiss-blackwood",
                "producer_slug": "swiss_krono",
                "name": "BLACK WOOD Worktops",
                "source_pdf": "SWISSKRONO_PL-Catalogue-Laminated-boards-and-Worktops-2025_PL_EN.pdf",
                "has_countertops": True,
            },
        ],
        "materials": [
            {
                "slug": "swiss-chipboard",
                "collection_slug": "swiss-laminated",
                "material_type_slug": "chipboard",
                "name": "Swiss Krono — Płyta wiórowa laminowana",
                "sidedness": "two_sided_same",
                "has_express": True,
            },
            {
                "slug": "swiss-postformed",
                "collection_slug": "swiss-worktops",
                "material_type_slug": "worktop_postformed",
                "name": "Swiss Krono — Blat Post-formed 38mm",
            },
            {
                "slug": "swiss-blackwood-board",
                "collection_slug": "swiss-blackwood",
                "material_type_slug": "worktop_slim",
                "name": "BLACK WOOD — HPL na rdzeniu 12mm",
            },
        ],
        "decors": all_decors,
        "variants": _build_swiss_variants(all_decors, SWISS_PRIMARY),
        "worktops": [
            # BLACK WOOD — U190 Czarny
            {
                "variant_business_id": "U190-BW-12",
                "construction_slug": "black_wood",
                "profile_code": "NATURAL",
                "max_length_mm": 4100,
                "available_widths_mm": [1315],
                "edge_material": "naturalna",
                "pieces_per_pallet": 20,
                "pallet_weight_kg": 1200,
            },
            # BLACK WOOD — D3274 Beton
            {
                "variant_business_id": "D3274-BW-12",
                "construction_slug": "black_wood",
                "profile_code": "NATURAL",
                "max_length_mm": 4100,
                "available_widths_mm": [1315],
                "edge_material": "naturalna",
                "pieces_per_pallet": 20,
            },
            # BLACK WOOD — D3806 Buk Bordeaux
            {
                "variant_business_id": "D3806-BW-12",
                "construction_slug": "black_wood",
                "profile_code": "NATURAL",
                "max_length_mm": 4100,
                "available_widths_mm": [1315],
                "edge_material": "naturalna",
                "pieces_per_pallet": 20,
            },
            # BLACK WOOD — D4878
            {
                "variant_business_id": "D4878-BW-12",
                "construction_slug": "black_wood",
                "profile_code": "NATURAL",
                "max_length_mm": 4100,
                "available_widths_mm": [1315],
                "edge_material": "naturalna",
                "pieces_per_pallet": 20,
            },
            # Postformed — K101 R3
            {
                "variant_business_id": "K101-PF-R3-600",
                "construction_slug": "postformed",
                "profile_code": "R3",
                "max_length_mm": 4100,
                "available_widths_mm": [600],
                "edge_material": "HPL",
                "pieces_per_pallet": 10,
            },
            # Postformed — D70601 Calacatta Oro
            {
                "variant_business_id": "D70601-PF-R3-600",
                "construction_slug": "postformed",
                "profile_code": "R3",
                "max_length_mm": 4100,
                "available_widths_mm": [600],
                "edge_material": "HPL",
                "pieces_per_pallet": 10,
            },
        ],
        "decor_structures": _build_swiss_decor_structures(all_decors),
        "pairings": [
            # U190 board → U190 BLACK WOOD
            {
                "front_decor_code": "U190",
                "target_decor_code": "U190",
                "pairing_type": "black_wood",
                "match_type": "exact",
                "priority": 1,
                "notes": "Same decor, different material (board → BLACK WOOD worktop)",
            },
            # D3274 board → D3274 BLACK WOOD
            {
                "front_decor_code": "D3274",
                "target_decor_code": "D3274",
                "pairing_type": "black_wood",
                "match_type": "exact",
                "priority": 1,
            },
            # U190 → U190 HPL laminate
            {
                "front_decor_code": "U190",
                "target_decor_code": "U190",
                "pairing_type": "hpl_laminate",
                "match_type": "exact",
                "priority": 1,
            },
            # U190 → K101 Biały worktop (close match)
            {
                "front_decor_code": "U190",
                "target_decor_code": "K101",
                "pairing_type": "worktop",
                "match_type": "close",
                "priority": 2,
                "notes": "Contrasting white worktop for black carcass",
            },
        ],
        "availability": [
            # KronoSwiss: standard delivery from Żary warehouse
            {
                "variant_business_id": "U190-BW-12",
                "channel": "standard",
                "available": True,
                "warehouse": "Żary",
                "lead_time": "7d",
            },
            {
                "variant_business_id": "U190-BW-12",
                "channel": "standard",
                "available": True,
                "warehouse": "Żary",
                "lead_time": "7d",
            },
            {
                "variant_business_id": "D3314-CH-18-SD",
                "channel": "standard",
                "available": True,
                "warehouse": "Żary",
                "lead_time": "7d",
            },
            {
                "variant_business_id": "D3801-CH-18-CL",
                "channel": "standard",
                "available": True,
                "warehouse": "Żary",
                "lead_time": "7d",
            },
            {
                "variant_business_id": "K101-PF-R3-600",
                "channel": "standard",
                "available": True,
                "warehouse": "Żary",
                "lead_time": "7d",
            },
        ],
        "property_flags": [
            # BLACK WOOD — all have antibacterial + waterproof
            {
                "variant_business_id": "U190-BW-12",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "U190-BW-12",
                "property": "waterproof",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "U190-BW-12",
                "property": "fire_resistant",
                "value": True,
                "source": "datasheet",
                "notes": "D-s1,d0 (trudnopalny)",
            },
            {
                "variant_business_id": "D3274-BW-12",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "D3274-BW-12",
                "property": "waterproof",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "D3806-BW-12",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "D4878-BW-12",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            # Laminated boards — antibacterial (all Swiss Krono products)
            {
                "variant_business_id": "U190-BW-12",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "D3314-CH-18-SD",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "D3801-CH-18-CL",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            # Postformed — antibacterial
            {
                "variant_business_id": "K101-PF-R3-600",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "D70601-PF-R3-600",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
        ],
    }


def _build_swiss_decor_structures(decors: list[dict]) -> list[dict]:
    """Each decor gets its primary structure in the junction table."""
    PRIMARY = {
        # Unikolory
        "U164": "VL", "U190": "VL", "U112": "PE", "U570": "SM",
        "U8685": "SM", "U119": "VL", "U6933": "VL", "U10030": "VL",
        "U4809": "VL",
        # Drewnopodobne
        "D9103": "OW", "D3025": "OW", "D4225": "OV", "D4428": "OV",
        "D20110": "OV", "D20230": "OV", "D3823": "OW", "D3314": "SD",
        "D3316": "SD", "D3801": "CL", "D3798": "CL", "D3800": "CL",
        "D3806": "OW", "D3193": "SW", "D3194": "SW",
        "D722": "SE", "D3813": "OW", "D4822": "OV",
        "D3158": "MX", "D4426": "OV",
        # Fantazyjne
        "D30090": "TO", "D3274": "BS", "D1038": "BS",
        "D4448": "VL", "D1861": "MX", "D4878": "VL",
        "D70060": "TO",
        # Worktops
        "K101": "PE", "D4033": "OW", "D70601": "SM", "D60664": "OW",
    }

    result = []
    seen = set()
    for d in decors:
        code = d["business_id"]
        primary = PRIMARY.get(code)
        if not primary or code in seen:
            continue
        seen.add(code)
        result.append({
            "decor_code": code,
            "structure_code": primary,
            "is_primary": True,
        })
    return result


if __name__ == "__main__":
    import yaml
    kronoswiss = generate_kronoswiss_yaml()
    path = DATA_DIR / "kronoswiss_full.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(kronoswiss, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Written: {path} ({path.stat().st_size} bytes)")
    print(f"Decors: {len(kronoswiss['decors'])}")
    print(f"Variants: {len(kronoswiss['variants'])}")
    print(f"Worktops: {len(kronoswiss['worktops'])}")
    print(f"Decor structures: {len(kronoswiss['decor_structures'])}")
    print(f"Pairings: {len(kronoswiss['pairings'])}")
