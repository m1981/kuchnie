# TOMBSTONE (2026-07-16): atticized by owner dark-triage decision. One-shot
# generator/migration whose output is already committed (catalog/data/*.yaml,
# schema 1.5.0). The living data pipeline is documented in
# docs/specs/catalog-service.md; rebuild = catalog.scripts.seed + seed_* extras.
"""Generate catalog YAML files from markdown spec documents.

Reads the structured markdown tables (created in earlier analysis phases)
and produces YAML files consumable by CatalogImporter.

Usage:
    python -m scripts.generate_kronospan_yaml
    # → writes catalog/data/kronospan_full.yaml
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ══════════════════════════════════════════════════════════════════
# Kronospan Global Collection — 174 decors
# Source: docs/materials-boards/Kronospan/global-collection.md
# ══════════════════════════════════════════════════════════════════

KRONOSPAN_PRODUCER = {
    "slug": "kronospan",
    "name": "Kronospan",
    "country": "Polska",
    "website": "kronosfera.pl",
}

KRONOSPAN_STRUCTURES = [
    # From global-collection.md struktury section
    {"code": "SM", "name": "Super Mat", "type": "smooth", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "PE", "name": "Pearl Effect", "type": "structured", "finish": "gloss",
     "producer_slug": "kronospan"},
    {"code": "BS", "name": "Black Structure", "type": "structured", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "PD", "name": "Pearl Dark", "type": "structured", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "PW", "name": "Pearl Wood", "type": "wood_grain", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "RS", "name": "Rustykalna", "type": "wood_grain", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "SU", "name": "Super Ultra Mat", "type": "smooth", "finish": "matt",
     "fingerprint_resistant": True, "producer_slug": "kronospan"},
    {"code": "FP", "name": "Front Plain", "type": "smooth", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "SN", "name": "Struktura Naturalna", "type": "wood_grain",
     "finish": "structured", "producer_slug": "kronospan"},
    {"code": "RT", "name": "Rustykalna (kamień)", "type": "stone",
     "finish": "structured", "producer_slug": "kronospan"},
    {"code": "HU", "name": "Hudson", "type": "wood_grain", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "AD", "name": "Arvadonna", "type": "wood_grain", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "PV", "name": "Primavera", "type": "wood_grain", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "RW", "name": "Rustic Wood", "type": "wood_grain", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "SL", "name": "Slate", "type": "stone", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "GM", "name": "Glass Matte", "type": "smooth", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "SQ", "name": "Square", "type": "structured", "finish": "gloss",
     "producer_slug": "kronospan"},
    {"code": "GG", "name": "Glass Gloss", "type": "structured", "finish": "gloss",
     "producer_slug": "kronospan"},
    {"code": "PA", "name": "Pearl Antyczny", "type": "structured", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "PH", "name": "Photo", "type": "stone", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "LV", "name": "Lava", "type": "stone", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "UE", "name": "Urban Effect", "type": "structured", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "TO", "name": "Touch One", "type": "structured", "finish": "matt",
     "producer_slug": "kronospan"},
    {"code": "IS", "name": "Italian Stone", "type": "stone", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "PN", "name": "Pearl Nature", "type": "stone", "finish": "structured",
     "producer_slug": "kronospan"},
    {"code": "SE", "name": "Drewno Jesionu", "type": "wood_grain", "finish": "structured",
     "producer_slug": "kronospan"},
]


# ── Global Collection decors (subset representative + edge cases) ──
# Full list would be 174 — here we include ~30 key decors covering all groups
# plus all decors that have matching products, worktops, or special flags.

GLOBAL_DECORS = [
    # WHITE CORPUS (group I)
    {"business_id": "K110", "name": "Biały Korpusowy", "group_name": "WHITE CORPUS",
     "color_family_slug": "bialy", "producer_slug": "kronospan"},

    # WHITE FRONT (group II)
    {"business_id": "K101", "name": "Biały Frontowy", "name_en": "Front White",
     "group_name": "WHITE FRONT", "color_family_slug": "bialy",
     "producer_slug": "kronospan"},
    {"business_id": "K8685", "name": "Biel Alpejska", "name_en": "Alpine White",
     "group_name": "WHITE FRONT", "color_family_slug": "bialy",
     "ncs": "S 0500-N", "ral": "9016", "producer_slug": "kronospan"},

    # COLOR BASIC (group III) — 22 decors
    {"business_id": "K190", "name": "Czarny", "name_en": "Black",
     "group_name": "COLOR BASIC", "color_family_slug": "czarny",
     "ncs": "S 8502-B", "ral": "9004", "pantone": "Process Black C",
     "producer_slug": "kronospan"},
    {"business_id": "K164", "name": "Antracyt", "name_en": "Anthracite",
     "group_name": "COLOR BASIC", "color_family_slug": "szary",
     "ncs": "S 7502-G", "ral": "7043", "producer_slug": "kronospan"},
    {"business_id": "K7045", "name": "Szampański", "name_en": "Champagne",
     "group_name": "COLOR BASIC", "color_family_slug": "bezowy",
     "pantone": "7527 C", "producer_slug": "kronospan"},
    {"business_id": "K523", "name": "Galaxus", "group_name": "COLOR BASIC",
     "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K5981", "name": "Kaszmir", "name_en": "Cashmere",
     "group_name": "COLOR BASIC", "color_family_slug": "kremowy",
     "producer_slug": "kronospan"},
    {"business_id": "K0112", "name": "Jasny Szary", "name_en": "Light Grey",
     "group_name": "COLOR BASIC", "color_family_slug": "szary",
     "producer_slug": "kronospan"},

    # COLOR SPECIAL (group VI)
    {"business_id": "K553", "name": "Galaxus SU", "group_name": "COLOR SPECIAL",
     "color_family_slug": "szary", "producer_slug": "kronospan"},

    # WOOD BASIC (group VII)
    {"business_id": "K2738", "name": "Dąb Cremona Torro", "name_en": "Oak Cremona Torro",
     "group_name": "WOOD BASIC", "color_family_slug": "dab",
     "producer_slug": "kronospan"},
    {"business_id": "K9103", "name": "Dąb Jasny", "name_en": "Light Oak",
     "group_name": "WOOD BASIC", "color_family_slug": "dab",
     "producer_slug": "kronospan"},
    {"business_id": "K5307", "name": "Dąb Artisan", "name_en": "Artisan Oak",
     "group_name": "WOOD BASIC", "color_family_slug": "dab",
     "producer_slug": "kronospan"},
    {"business_id": "K3025", "name": "Dąb Vintage Jasny", "name_en": "Vintage Light Oak",
     "group_name": "WOOD BASIC", "color_family_slug": "dab",
     "producer_slug": "kronospan"},

    # WOOD FRONT (group VIII)
    {"business_id": "K365", "name": "Dąb Coast Evoke", "name_en": "Coast Evoke Oak",
     "group_name": "WOOD FRONT", "color_family_slug": "dab",
     "producer_slug": "kronospan"},
    {"business_id": "K003", "name": "Dąb Craft Złoty", "name_en": "Craft Golden Oak",
     "group_name": "WOOD FRONT", "color_family_slug": "dab",
     "producer_slug": "kronospan"},
    {"business_id": "K091", "name": "Dąb Porterhouse Jasny", "name_en": "Porterhouse Light Oak",
     "group_name": "WOOD FRONT", "color_family_slug": "dab",
     "producer_slug": "kronospan"},
    {"business_id": "K092", "name": "Dąb Porterhouse Ciemny", "name_en": "Porterhouse Dark Oak",
     "group_name": "WOOD FRONT", "color_family_slug": "dab",
     "producer_slug": "kronospan"},
    {"business_id": "K203", "name": "Granit Antracyt", "name_en": "Anthracite Granite",
     "group_name": "CONTEMPO 1", "color_family_slug": "szary",
     "producer_slug": "kronospan"},

    # CONTEMPO 1 (group IX)
    {"business_id": "K023", "name": "Venato", "name_en": "Venato",
     "group_name": "CONTEMPO 1", "color_family_slug": "bialy",
     "producer_slug": "kronospan"},
    {"business_id": "K212", "name": "Marmur Beżowy Royal", "name_en": "Royal Beige Marble",
     "group_name": "CONTEMPO 1", "color_family_slug": "bezowy",
     "producer_slug": "kronospan"},
    {"business_id": "K215", "name": "Białe Wydmy", "name_en": "White Dunes",
     "group_name": "CONTEMPO 1", "color_family_slug": "bialy",
     "producer_slug": "kronospan"},
    {"business_id": "K367", "name": "Navona Kremowa", "name_en": "Cream Navona",
     "group_name": "CONTEMPO 1", "color_family_slug": "kremowy",
     "producer_slug": "kronospan"},
    {"business_id": "K368", "name": "Marmur Atlantycki Szary", "name_en": "Atlantic Grey Marble",
     "group_name": "CONTEMPO 1", "color_family_slug": "szary",
     "producer_slug": "kronospan"},

    # Slim Line specific (from blaty_slim_line_spec.md str. 65)
    {"business_id": "K749", "name": "Babylon Slate", "name_en": "Babylon Slate",
     "group_name": "XVIII SPECIAL", "color_family_slug": "bezowy",
     "producer_slug": "kronospan"},
    {"business_id": "K750", "name": "Agra Travertine", "name_en": "Agra Travertine",
     "group_name": "XVIII SPECIAL", "color_family_slug": "bezowy",
     "producer_slug": "kronospan"},
    {"business_id": "K594", "name": "Breccia Vivaldo", "name_en": "Breccia Vivaldo",
     "group_name": "XVIII SPECIAL", "color_family_slug": "bialy",
     "producer_slug": "kronospan"},
    {"business_id": "K595", "name": "Pietra Belvedere", "name_en": "Pietra Belvedere",
     "group_name": "XVIII SPECIAL", "color_family_slug": "szary",
     "producer_slug": "kronospan"},
    {"business_id": "K551", "name": "Calacatta Olympus", "name_en": "Calacatta Olympus",
     "group_name": "XVIII SPECIAL", "color_family_slug": "bialy",
     "producer_slug": "kronospan"},
    {"business_id": "K552", "name": "Biały Marmur Lodowy", "name_en": "White Marble Icy",
     "group_name": "XVIII SPECIAL", "color_family_slug": "bialy",
     "producer_slug": "kronospan"},

    # Worktop pairs (from blaty_postformed_spec.md str. 48)
    {"business_id": "868S", "name": "Biel Alpejska", "name_en": "Alpine White",
     "group_name": "XIV MAT 1", "color_family_slug": "bialy",
     "producer_slug": "kronospan"},
    {"business_id": "0190", "name": "Czarny", "name_en": "Black",
     "group_name": "XIV MAT 1", "color_family_slug": "czarny",
     "producer_slug": "kronospan"},
    {"business_id": "5527", "name": "Dąb Kamienny", "name_en": "Stone Oak",
     "group_name": "XIV MAT 1", "color_family_slug": "dab",
     "producer_slug": "kronospan"},
]


# ── Postformed worktop decors (from blaty_postformed_spec.md str. 48) ──

POSTFORMED_WORKTOP_DECORS = [
    {"business_id": "7045", "name": "Szampański", "group_name": "XIV MAT 1",
     "color_family_slug": "bezowy", "producer_slug": "kronospan"},
    {"business_id": "868S", "name": "Biel Alpejska", "group_name": "XIV MAT 1",
     "color_family_slug": "bialy", "producer_slug": "kronospan"},
    {"business_id": "0190", "name": "Czarny", "group_name": "XIV MAT 1",
     "color_family_slug": "czarny", "producer_slug": "kronospan"},
    {"business_id": "4298", "name": "Jasny Atelier", "group_name": "XV MAT 2",
     "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "4299", "name": "Ciemny Atelier", "group_name": "XV MAT 2",
     "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K201", "name": "Beton Ciemnoszary", "group_name": "XV MAT 2",
     "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K205", "name": "Beton Czarny", "group_name": "XV MAT 2",
     "color_family_slug": "czarny", "producer_slug": "kronospan"},
    {"business_id": "K207", "name": "Galaxy Szary", "group_name": "XV MAT 2",
     "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K209", "name": "Wapiń Crema", "group_name": "XV MAT 2",
     "color_family_slug": "kremowy", "producer_slug": "kronospan"},
    {"business_id": "K210", "name": "Krzemień Czarny", "group_name": "XV MAT 2",
     "color_family_slug": "czarny", "producer_slug": "kronospan"},
    {"business_id": "K213", "name": "Tivoli Ciemne", "group_name": "XV MAT 2",
     "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K214", "name": "Tivoli Jasne", "group_name": "XV MAT 2",
     "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K217", "name": "Andromeda Biała", "group_name": "XVII HG 2",
     "color_family_slug": "bialy", "producer_slug": "kronospan"},
    {"business_id": "K218", "name": "Andromeda Czarna", "group_name": "XVII HG 2",
     "color_family_slug": "czarny", "producer_slug": "kronospan"},
    {"business_id": "K698", "name": "Ciemny Brąz", "group_name": "XVIII SPECIAL",
     "color_family_slug": "brazowy", "producer_slug": "kronospan"},
    {"business_id": "K699", "name": "Calacatta Ambrosio", "group_name": "XVIII SPECIAL",
     "color_family_slug": "bialy", "producer_slug": "kronospan"},
    {"business_id": "K703", "name": "Portobello", "group_name": "XVIII SPECIAL",
     "color_family_slug": "bezowy", "producer_slug": "kronospan"},
    {"business_id": "K704", "name": "Piasek Perlino", "group_name": "XVIII SPECIAL",
     "color_family_slug": "bezowy", "producer_slug": "kronospan"},
    {"business_id": "K705", "name": "Piasek Stonehaven", "group_name": "XVIII SPECIAL",
     "color_family_slug": "bezowy", "producer_slug": "kronospan"},
]


# ── ABS Square Edge decors (from blaty_abs_square_edge_spec.md) ──

ABS_EDGE_DECORS = [
    {"business_id": "K093", "name": "Marmur Szary Emperador",
     "group_name": "ABS", "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K105", "name": "Dąb Endgrain Surowy",
     "group_name": "ABS", "color_family_slug": "dab", "producer_slug": "kronospan"},
    {"business_id": "K200", "name": "Beton Jasnoszary",
     "group_name": "ABS", "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K349", "name": "Beton Jasny",
     "group_name": "ABS", "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K350", "name": "Beton",
     "group_name": "ABS", "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K351", "name": "Beton Rdzawy",
     "group_name": "ABS", "color_family_slug": "brazowy", "producer_slug": "kronospan"},
    {"business_id": "K352", "name": "Beton Ciemny",
     "group_name": "ABS", "color_family_slug": "szary", "producer_slug": "kronospan"},
    {"business_id": "K353", "name": "Beton Czarny",
     "group_name": "ABS", "color_family_slug": "czarny", "producer_slug": "kronospan"},
    {"business_id": "K535", "name": "Dąb Barokowy Złoty",
     "group_name": "ABS", "color_family_slug": "dab", "producer_slug": "kronospan"},
    {"business_id": "K538", "name": "Łupek Arosa Jasny",
     "group_name": "ABS", "color_family_slug": "lupek", "producer_slug": "kronospan"},
    {"business_id": "K539", "name": "Łupek Arosa Ciemny",
     "group_name": "ABS", "color_family_slug": "lupek", "producer_slug": "kronospan"},
    {"business_id": "K540", "name": "Albus Szary",
     "group_name": "ABS", "color_family_slug": "szary", "producer_slug": "kronospan"},
]


# ══════════════════════════════════════════════════════════════════
# YAML generation
# ══════════════════════════════════════════════════════════════════

# Mapping: decor_code → primary structure_code
PRIMARY = {
    "K8685": "SM", "K101": "PE", "K110": "SM",
    "K190": "PE", "K164": "SM", "K7045": "SM",
    "K523": "PE", "K5981": "SM", "K0112": "SM",
    "K2738": "FP", "K9103": "FP", "K5307": "FP",
    "K3025": "FP", "K365": "FP", "K003": "FP",
    "K091": "FP", "K092": "FP", "K203": "PE",
    "K023": "SU", "K212": "PA", "K215": "BS",
    "K367": "PH", "K368": "PH", "K553": "SU",
    "K749": "LV", "K750": "LV", "K594": "SU",
    "K595": "SU", "K551": "SU", "K552": "SU",
    # Worktops
    "868S": "RS", "0190": "RS", "7045": "RS",
    "4298": "UE", "4299": "UE",
    "5527": "FP", "K201": "RS", "K205": "RS",
    "K207": "RS", "K209": "RS", "K210": "PE",
    "K213": "RS", "K214": "RS",
    "K217": "GG", "K218": "GG",
    "K698": "PN", "K699": "PN", "K703": "PN",
    "K704": "PN", "K705": "PN",
    # ABS
    "K093": "SL", "K105": "FP", "K200": "RS",
    "K349": "RT", "K350": "RT", "K351": "RT",
    "K352": "RT", "K353": "RT",
    "K535": "RW", "K538": "PN", "K539": "PN", "K540": "PN",
}

def generate_kronospan_yaml() -> dict:
    """Build the complete Kronospan YAML dict."""

    # Merge all decors (deduplicated by business_id)
    seen = set()
    all_decors = []
    for d in GLOBAL_DECORS + POSTFORMED_WORKTOP_DECORS + ABS_EDGE_DECORS:
        if d["business_id"] not in seen:
            all_decors.append(d)
            seen.add(d["business_id"])

    return {
        "producers": [KRONOSPAN_PRODUCER],
        "structures": KRONOSPAN_STRUCTURES,
        "collections": [
            {
                "slug": "kronospan-global",
                "producer_slug": "kronospan",
                "name": "Global Collection 2026",
                "source_pdf": "plyty-wiorowe-global-collection.pdf",
                "has_edgebanding": True,
                "has_hdf": True,
                "has_countertops": True,
                "has_express": True,
            },
            {
                "slug": "kronospan-postformed",
                "producer_slug": "kronospan",
                "name": "Global Collection 2026 — Blaty Post-formed",
                "source_pdf": "blaty.pdf",
                "has_edgebanding": True,
                "has_countertops": True,
                "has_express": True,
            },
            {
                "slug": "kronospan-abs-edge",
                "producer_slug": "kronospan",
                "name": "ABS Square Edge",
                "source_pdf": "blaty.pdf",
                "has_edgebanding": True,
                "has_countertops": True,
                "has_express": True,
            },
            {
                "slug": "kronospan-slim-line",
                "producer_slug": "kronospan",
                "name": "Slim Line",
                "source_pdf": "blaty.pdf",
                "has_edgebanding": False,
                "has_countertops": True,
                "has_express": True,
            },
        ],
        "materials": [
            {
                "slug": "kronospan-chipboard-global",
                "collection_slug": "kronospan-global",
                "material_type_slug": "chipboard",
                "name": "Global Collection — Płyta wiórowa laminowana",
                "sidedness": "two_sided_same",
                "has_express": True,
            },
            {
                "slug": "kronospan-postformed-global",
                "collection_slug": "kronospan-postformed",
                "material_type_slug": "worktop_postformed",
                "name": "Global Collection — Blat Post-formed 38mm",
            },
            {
                "slug": "kronospan-abs-edge-board",
                "collection_slug": "kronospan-abs-edge",
                "material_type_slug": "worktop_abs_edge",
                "name": "ABS Square Edge — Blat 38mm",
            },
            {
                "slug": "kronospan-slim-line-board",
                "collection_slug": "kronospan-slim-line",
                "material_type_slug": "worktop_slim",
                "name": "Slim Line — Płyta kompaktowa 12mm",
            },
        ],
        "decors": all_decors,
        "variants": _build_variants(all_decors, PRIMARY),
                "multi_structures": "BS, PD, PW",
        "worktops": [
            {
                "variant_business_id": "868S-PF-U-600",
                "construction_slug": "postformed",
                "profile_code": "U",
                "max_length_mm": 4100,
                "available_widths_mm": [600],
                "edge_material": "Unoflex",
                "edge_material_thickness_mm": 1.0,
                "splashback_available": True,
                "matching_board_available": True,
                "pieces_per_pallet": 10,
                "pallet_weight_kg": 620,
            },
            {
                "variant_business_id": "7045-PF-U-600",
                "construction_slug": "postformed",
                "profile_code": "U",
                "max_length_mm": 4100,
                "available_widths_mm": [600],
                "edge_material": "Unoflex",
                "edge_material_thickness_mm": 1.0,
                "splashback_available": True,
                "matching_board_available": True,
                "pieces_per_pallet": 10,
                "pallet_weight_kg": 946,
            },
            {
                "variant_business_id": "K349-ABS-635",
                "construction_slug": "abs_square_edge",
                "profile_code": "SQUARE",
                "max_length_mm": 4100,
                "available_widths_mm": [635],
                "edge_material": "ABS 1.5mm",
                "edge_material_thickness_mm": 1.5,
                "pieces_per_pallet": 10,
            },
            {
                "variant_business_id": "K749-SL-12",
                "construction_slug": "slim_line",
                "profile_code": "NATURAL",
                "max_length_mm": 4100,
                "available_widths_mm": [650],
                "edge_material": "naturalna",
                "core_color": "Beżowy",
            },
            {
                "variant_business_id": "K551-SL-12",
                "construction_slug": "slim_line",
                "profile_code": "NATURAL",
                "max_length_mm": 4100,
                "available_widths_mm": [650],
                "edge_material": "naturalna",
                "core_color": "Biały",
            },
            {
                "variant_business_id": "0190-SL-12",
                "construction_slug": "slim_line",
                "profile_code": "NATURAL",
                "max_length_mm": 4100,
                "available_widths_mm": [650],
                "edge_material": "naturalna",
                "core_color": "Czarny",
            },
        ],
        "decor_structures": _build_decor_structures(all_decors),
        "pairings": [
            {
                "front_decor_code": "K8685",
                "target_decor_code": "868S",
                "pairing_type": "worktop",
                "match_type": "exact",
                "priority": 1,
            },
            {
                "front_decor_code": "K8685",
                "target_decor_code": "K523",
                "pairing_type": "acrylic",
                "match_type": "close",
                "priority": 2,
            },
            {
                "front_decor_code": "K190",
                "target_decor_code": "0190",
                "pairing_type": "worktop",
                "match_type": "exact",
                "priority": 1,
            },
            {
                "front_decor_code": "K190",
                "target_decor_code": "7045",
                "pairing_type": "worktop",
                "match_type": "close",
                "priority": 2,
            },
            {
                "front_decor_code": "K190",
                "target_decor_code": "K523",
                "pairing_type": "hpl_laminate",
                "match_type": "close",
                "priority": 2,
            },
        ],
        "availability": [
            # Kronospan Global Collection: Express 24h (Mielec)
            {
                "variant_business_id": "K8685-CH-18-SM",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            {
                "variant_business_id": "K190-CH-18-PE",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            {
                "variant_business_id": "K8685-CH-18-SM",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            {
                "variant_business_id": "K8685-CH-18-SM",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            # Postformed worktops: Express 24h (Mielec)
            {
                "variant_business_id": "868S-PF-U-600",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            {
                "variant_business_id": "7045-PF-U-600",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            # Slim Line: Express 24h (Mielec)
            {
                "variant_business_id": "K749-SL-12",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            # ABS Square Edge: Express 24h (Mielec)
            {
                "variant_business_id": "K349-ABS-635",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },

            # Chipboard Express 24h (all primary decors)
            {
                "variant_business_id": "K523-CH-18-PE",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            {
                "variant_business_id": "K0112-CH-18-SM",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            {
                "variant_business_id": "K5981-CH-18-SM",
                "channel": "express_24h",
                "available": True,
                "warehouse": "Mielec",
                "lead_time": "24h",
            },
            # Konfekcja (small quantities)
            {
                "variant_business_id": "K8685-CH-18-SM",
                "channel": "konfekcja",
                "available": True,
                "min_order_qty": 1,
            },
            {
                "variant_business_id": "K190-CH-18-PE",
                "channel": "konfekcja",
                "available": True,
                "min_order_qty": 1,
            },
        ],
        "property_flags": [
            # Slim Line — waterproof (all Slim Line variants)
            {
                "variant_business_id": "K749-SL-12",
                "property": "waterproof",
                "value": True,
                "source": "catalog_page",
            },
            {
                "variant_business_id": "K551-SL-12",
                "property": "waterproof",
                "value": True,
                "source": "catalog_page",
            },
            {
                "variant_business_id": "0190-SL-12",
                "property": "waterproof",
                "value": True,
                "source": "catalog_page",
            },
            # Chipboard — scratch resistant (HPL surface)
            {
                "variant_business_id": "K8685-CH-18-SM",
                "property": "scratch_resistant",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "K190-CH-18-PE",
                "property": "scratch_resistant",
                "value": True,
                "source": "datasheet",
            },
            # Chipboard — UV stable
            {
                "variant_business_id": "K8685-CH-18-SM",
                "property": "uv_stable",
                "value": True,
                "source": "datasheet",
            },
            # Postformed — scratch resistant (HPL surface)
            {
                "variant_business_id": "868S-PF-U-600",
                "property": "scratch_resistant",
                "value": True,
                "source": "datasheet",
            },
            # Antibacterial — all Slim Line (compact board)
            {
                "variant_business_id": "K749-SL-12",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "K551-SL-12",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
            {
                "variant_business_id": "0190-SL-12",
                "property": "antibacterial",
                "value": True,
                "source": "datasheet",
            },
        ],
    }


def _build_variants(decors: list[dict], primary_map: dict) -> list[dict]:
    """Auto-generate variants for ALL decors.

    For each decor:
      - If it's in POSTFORMED_WORKTOP_DECORS → worktop variant (38mm, postformed)
      - If it's in ABS_EDGE_DECORS → ABS edge variant (38mm)
      - If it's in SLIM_LINE_DECORS (from YAML) → slim line variant (12mm)
      - Otherwise → chipboard variant (18mm) with primary structure
    """
    # Build lookup sets
    postformed_ids = {d["business_id"] for d in POSTFORMED_WORKTOP_DECORS}
    abs_ids = {d["business_id"] for d in ABS_EDGE_DECORS}

    # Slim Line decors from the YAML data (K749, K750, K551, K552, etc.)
    slim_ids = {"K749", "K750", "K551", "K552", "K594", "K595", "0190"}

    # ABS Square Edge structures
    ABS_STRUCTURES = {
        "K093": "SL", "K105": "FP", "K200": "RS", "K349": "RT",
        "K350": "RT", "K351": "RT", "K352": "RT", "K353": "RT",
        "K535": "RW", "K538": "PN", "K539": "PN", "K540": "PN",
        "K023": "SQ", "K217": "GM", "K218": "GM",
        "K365": "FP", "K523": "PE",
        "K107": "FP", "K367": "PH", "K368": "PH",
        "K544": "RW", "K545": "RW",
        "K549": "SL", "K550": "SL",
        "K091": "FP", "K092": "FP",
        "K1090": "BT", "K1085": "SM", "K1093": "IS",
        "K1091": "SK", "K1101": "IS", "K1083": "BT",
        "K1078": "IS", "K4008": "PE",
        "K1097": "SM", "K4876": "SM", "K4871": "BS",
        "K1099": "SM", "K1087": "PE", "K1052": "BL",
        "K1082": "SM", "K1032": "SK", "K1100": "SM",
        "K1098": "SM", "K1088": "SA", "K1102": "VL",
        "K1104": "SM", "K1103": "SM",
    }

    # Multi-structures: decor → all structures (from Global Collection tables)
    MULTI = {
        "K8685": "BS, PD, PW",
        "K190": "PD, PW",
        "K101": "SE",
        "K7045": "PW",
    }

    variants = []

    for d in decors:
        code = d["business_id"]
        primary = primary_map.get(code)
        if not primary:
            continue

        # Chipboard variant (18mm) — always
        chipboard = {
            "business_id": f"{code}-CH-18-{primary}",
            "decor_code": code,
            "material_slug": "kronospan-chipboard-global",
            "structure_code": primary,
            "thickness_mm": 18.0,
            "sheet_format_slug": "2800x2070",
            "roles": ["front", "carcass"],
            "hpl_available": True,
        }
        if code in MULTI:
            chipboard["multi_structures"] = MULTI[code]
        variants.append(chipboard)

        # Postformed worktop variant — if in postformed collection
        if code in postformed_ids:
            variants.append({
                "business_id": f"{code}-PF-U-600",
                "decor_code": code,
                "material_slug": "kronospan-postformed-global",
                "structure_code": "RS",
                "thickness_mm": 38.0,
                "sheet_format_slug": "4100x600",
                "roles": ["worktop"],
                "splashback_available": True,
                "hpl_available": True,
            })

        # ABS Square Edge variant — if in ABS collection
        if code in abs_ids:
            struct = ABS_STRUCTURES.get(code, "RT")
            variants.append({
                "business_id": f"{code}-ABS-635",
                "decor_code": code,
                "material_slug": "kronospan-abs-edge-board",
                "structure_code": struct,
                "thickness_mm": 38.0,
                "sheet_format_slug": "4100x635",
                "roles": ["worktop"],
                "splashback_available": True,
            })

        # Slim Line variant — if in slim collection
        if code in slim_ids:
            variants.append({
                "business_id": f"{code}-SL-12",
                "decor_code": code,
                "material_slug": "kronospan-slim-line-board",
                "structure_code": primary,
                "thickness_mm": 12.0,
                "sheet_format_slug": "4100x650",
                "roles": ["worktop"],
            })

    return variants


def _build_decor_structures(decors: list[dict]) -> list[dict]:
    """Build decor_structures junction rows.

    For now, each decor gets one junction row (primary structure only).
    Multi-structure data is stored in variant.multi_structures CSV
    until the full 174-decor import fills the junction table.
    """
    # Mapping: decor_code → primary structure_code

    # Multi-structures: decor → all structures (from Global Collection tables)
    MULTI = {
        "K8685": ["SM", "BS", "PD", "PW"],
        "K190": ["PE", "PD", "PW"],
        "K101": ["PE", "SE"],
        "K7045": ["SM", "PW"],
    }

    result = []
    seen = set()
    for d in decors:
        code = d["business_id"]
        primary = PRIMARY.get(code)
        if not primary or code in seen:
            continue
        seen.add(code)

        # Primary
        result.append({
            "decor_code": code,
            "structure_code": primary,
            "is_primary": True,
        })

        # Multi-structures (non-primary)
        for s in MULTI.get(code, []):
            if s != primary:
                result.append({
                    "decor_code": code,
                    "structure_code": s,
                    "is_primary": False,
                })

    return result


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════


def write_yaml(data: dict, path: Path):
    """Write dict as YAML to file."""
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Written: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    kronospan = generate_kronospan_yaml()
    write_yaml(kronospan, DATA_DIR / "kronospan_full.yaml")
    print(f"Decors: {len(kronospan['decors'])}")
    print(f"Variants: {len(kronospan['variants'])}")
    print(f"Worktops: {len(kronospan['worktops'])}")
    print(f"Decor structures: {len(kronospan['decor_structures'])}")
    print(f"Pairings: {len(kronospan['pairings'])}")
