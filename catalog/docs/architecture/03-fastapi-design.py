"""
KUCHNIE CATALOG — FastAPI API Design
Version: 1.0.0 (design)
Date: 2026-06-27

This is the API DESIGN (not implementation). It defines:
  1. All endpoints with their request/response schemas
  2. Query parameters and filters
  3. Error responses
  4. Business logic descriptions

Stack: FastAPI + SQLite (via aiosqlite) + Pydantic v2

Architecture:
  catalog/
  ├── api/
  │   ├── __init__.py
  │   ├── main.py              ← FastAPI app
  │   ├── deps.py              ← DB connection, auth
  │   ├── routers/
  │   │   ├── decors.py        ← /api/decors
  │   │   ├── variants.py      ← /api/variants
  │   │   ├── pairings.py      ← /api/pairings
  │   │   ├── materials.py     ← /api/materials
  │   │   └── admin.py         ← /api/admin (migration, rebuild)
  │   └── middleware.py         ← CORS, logging
  ├── db/
  │   ├── __init__.py
  │   ├── engine.py            ← SQLite connection
  │   ├── migrations/          ← Alembic
  │   └── seed.py              ← Reference data
  ├── models/                  ← Pydantic models (02-pydantic-models.py)
  ├── services/
  │   ├── decor_service.py     ← Business logic
  │   ├── pairing_service.py   ← Pairing resolution
  │   └── search_service.py    ← Full-text search
  └── tests/
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

# ══════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────────
# 1. DECORS
# ──────────────────────────────────────────────────────────────────

"""
GET  /api/decors
    Summary: List decors with filters
    Query params:
        - producer: str = None          # 'kronospan', 'egger'
        - color_family: str = None      # 'bialy', 'dab'
        - material_type: str = None     # 'chipboard', 'mdf_acrylic'
        - role: str = None              # 'front', 'carcass', 'worktop'
        - structure: str = None         # 'SM', 'AG', 'RS'
        - tag: str = None               # 'frontowy', 'drewno'
        - search: str = None            # full-text search
        - page: int = 1
        - page_size: int = 50
    Response: PaginatedResponse[DecorWithVariants]
    Example: GET /api/decors?color_family=bialy&material_type=chipboard&role=front

GET  /api/decors/{decor_id}
    Summary: Get single decor with all variants
    Path: decor_id = business_id ('K8685')
    Response: DecorWithVariants
    Example: GET /api/decors/K8685

GET  /api/decors/{decor_id}/variants
    Summary: Get variants for a decor, optionally filtered
    Path: decor_id = business_id
    Query params:
        - material_type: str = None
        - role: str = None
    Response: list[Variant]
    Example: GET /api/decors/K8685/variants?material_type=worktop_postformed

GET  /api/decors/{decor_id}/pairings
    Summary: Get all pairings for a decor
    Path: decor_id = business_id
    Query params:
        - pairing_type: str = None      # 'carcass', 'worktop', 'splashback'
        - match_type: str = None        # 'exact', 'close', 'default'
    Response: list[PairingWithDecors]
    Example: GET /api/decors/K8685/pairings?pairing_type=carcass

GET  /api/decors/{decor_id}/alternatives
    Summary: Find alternative decors (same color_family, different producer)
    Path: decor_id = business_id
    Response: list[DecorWithVariants]
    Example: GET /api/decors/K8685/alternatives
"""


# ──────────────────────────────────────────────────────────────────
# 2. VARIANTS
# ──────────────────────────────────────────────────────────────────

"""
GET  /api/variants
    Summary: List variants with filters
    Query params:
        - decor_id: str = None          # 'K8685'
        - material_type: str = None     # 'chipboard', 'worktop_postformed'
        - role: str = None              # 'front', 'worktop'
        - structure: str = None         # 'SM', 'RS'
        - thickness_mm: float = None    # exact match
        - min_thickness: float = None
        - max_thickness: float = None
        - width_mm: int = None          # worktop width
        - page: int = 1
        - page_size: int = 50
    Response: PaginatedResponse[VariantWithDecor]
    Example: GET /api/variants?material_type=worktop_postformed&width_mm=600

GET  /api/variants/{variant_id}
    Summary: Get single variant with decor and edges
    Path: variant_id = business_id ('K8685-CH')
    Response: VariantWithDecor
    Example: GET /api/variants/K8685-CH
"""


# ──────────────────────────────────────────────────────────────────
# 3. PAIRINGS
# ──────────────────────────────────────────────────────────────────

"""
GET  /api/pairings
    Summary: List all pairings with filters
    Query params:
        - front_decor_id: str = None
        - target_decor_id: str = None
        - pairing_type: str = None
        - match_type: str = None
        - page: int = 1
        - page_size: int = 50
    Response: PaginatedResponse[PairingWithDecors]

GET  /api/pairings/resolve
    Summary: Resolve pairings for a front decor (with fallback)
    Query params:
        - front_decor_id: str (required)
        - pairing_type: str (required)  # 'carcass', 'worktop', 'splashback'
    Response: list[PairingWithDecors]
    Logic:
        1. Find exact match (front_decor_id = K8685, match_type = exact)
        2. Find close matches (match_type = close)
        3. Find defaults (front_decor_id = '*', match_type = default)
        4. Sort by priority
        5. For each target decor, find available variants
    Example: GET /api/pairings/resolve?front_decor_id=K8685&pairing_type=carcass

GET  /api/pairings/suggest
    Summary: Suggest full kitchen configuration
    Query params:
        - front_decor_id: str (required)
    Response:
        {
            "front": DecorWithVariants,
            "carcass": { "pairing": PairingWithDecors, "variants": [Variant] },
            "worktop": { "pairing": PairingWithDecors, "variants": [Variant] },
            "splashback": { "pairing": PairingWithDecors, "variants": [Variant] }
        }
    Example: GET /api/pairings/suggest?front_decor_id=K8685
"""


# ──────────────────────────────────────────────────────────────────
# 4. MATERIALS
# ──────────────────────────────────────────────────────────────────

"""
GET  /api/materials
    Summary: List all materials
    Query params:
        - material_type: str = None
        - producer: str = None
        - collection: str = None
    Response: list[Material]

GET  /api/material-types
    Summary: List all material types
    Response: list[MaterialType]

GET  /api/collections
    Summary: List all collections
    Query params:
        - producer: str = None
    Response: list[Collection]

GET  /api/structures
    Summary: List all structures
    Query params:
        - producer: str = None
        - type: str = None              # 'smooth', 'wood_grain', 'stone'
    Response: list[Structure]
"""


# ──────────────────────────────────────────────────────────────────
# 5. PRODUCERS
# ──────────────────────────────────────────────────────────────────

"""
GET  /api/producers
    Summary: List all producers
    Response: list[Producer]

GET  /api/producers/{slug}
    Summary: Get producer with collections and stats
    Path: slug = 'kronospan'
    Response: Producer with nested collections, decor count, variant count
"""


# ──────────────────────────────────────────────────────────────────
# 6. SEARCH
# ──────────────────────────────────────────────────────────────────

"""
GET  /api/search
    Summary: Full-text search across decors, variants, edges
    Query params:
        - q: str (required)             # search term
        - type: str = None              # 'decor', 'variant', 'edge'
    Response:
        {
            "decors": [DecorWithVariants],
            "variants": [VariantWithDecor],
            "edges": [Edge]
        }
    Example: GET /api/search?q=Biel+Alpejska
"""


# ──────────────────────────────────────────────────────────────────
# 7. ADMIN (migration, rebuild, stats)
# ──────────────────────────────────────────────────────────────────

"""
POST /api/admin/migrate
    Summary: Run YAML → SQLite migration
    Body: { "source": "decors.yaml", "dry_run": true }
    Response: { "decors": 177, "variants": 180, "errors": [] }

POST /api/admin/rebuild-fts
    Summary: Rebuild full-text search index
    Response: { "status": "ok" }

GET  /api/admin/stats
    Summary: Database statistics
    Response:
        {
            "decors": { "total": 177, "by_producer": { "kronospan": 177 } },
            "variants": { "total": 180, "by_material_type": { ... } },
            "pairings": { "total": 0, "by_type": { ... } },
            "edges": { "total": 0 }
        }

POST /api/admin/import-yaml
    Summary: Import a YAML file into the database
    Body: multipart/form-data with .yaml file
    Response: { "imported": 177, "errors": [] }
"""


# ══════════════════════════════════════════════════════════════════
# ERROR RESPONSES
# ══════════════════════════════════════════════════════════════════

"""
Standard error response (all endpoints):
{
    "detail": "Decor K9999 not found",
    "type": "not_found",
    "status": 404
}

Validation error (422):
{
    "detail": [
        {
            "loc": ["body", "color_family"],
            "msg": "Invalid color_family: invalid",
            "type": "value_error"
        }
    ]
}
"""


# ══════════════════════════════════════════════════════════════════
# BUSINESS LOGIC DESCRIPTIONS
# ══════════════════════════════════════════════════════════════════


class PairingResolutionLogic:
    """
    How pairing resolution works:

    1. User asks: "What carcass goes with front K8685?"

    2. Query pairings table:
       SELECT * FROM pairings
       WHERE front_decor_id = 'K8685'
         AND pairing_type = 'carcass'
       ORDER BY priority ASC

    3. If no exact match found, try wildcard:
       SELECT * FROM pairings
       WHERE front_decor_id = '*'
         AND pairing_type = 'carcass'
         AND match_type = 'default'
       ORDER BY priority ASC

    4. For each pairing result, find available variants:
       SELECT * FROM variants v
       JOIN decors d ON d.id = v.decor_id
       WHERE d.business_id = '{target_decor_id}'
         AND 'carcass' IN (v.roles)

    5. Return sorted list:
       [
         { "pairing": ..., "variants": [...] },  # exact match
         { "pairing": ..., "variants": [...] },  # close match
         { "pairing": ..., "variants": [...] },  # default
       ]
    """
    pass


class SearchLogic:
    """
    Full-text search strategy:

    1. DECOR search (name, business_id, ncs, ral):
       - SQLite FTS5 on decors table
       - Match: name LIKE '%query%' OR business_id LIKE '%query%'

    2. VARIANT search (business_id, structure):
       - Match: business_id LIKE '%query%' OR structure_code LIKE '%query%'

    3. EDGE search (code):
       - Match: code LIKE '%query%'

    4. Results merged and deduplicated
    """
    pass


class StatisticsLogic:
    """
    Statistics computation:

    Per producer:
      - Total decors, variants
      - Variants by material_type
      - Variants by role
      - Decors by color_family

    Per material_type:
      - Total variants
      - Average thickness
      - Available structures

    Global:
      - Total pairings by type
      - Coverage: which decors have pairings
    """
    pass


# ══════════════════════════════════════════════════════════════════
# SAMPLE API CALLS (for documentation)
# ══════════════════════════════════════════════════════════════════

SAMPLE_REQUESTS = """
# 1. Get all white fronts in chipboard
curl "http://localhost:8000/api/decors?color_family=bialy&material_type=chipboard&role=front"

# 2. Get K8685 with all variants (board, worktop, HPL, splashback)
curl "http://localhost:8000/api/decors/K8685"

# 3. Get worktop variants for Biel Alpejska
curl "http://localhost:8000/api/decors/K8685/variants?material_type=worktop_postformed"

# 4. Resolve carcass pairing for front K8685
curl "http://localhost:8000/api/pairings/resolve?front_decor_id=K8685&pairing_type=carcass"

# 5. Full kitchen suggestion for front K8685
curl "http://localhost:8000/api/pairings/suggest?front_decor_id=K8685"

# 6. Search for "Biel Alpejska"
curl "http://localhost:8000/api/search?q=Biel+Alpejska"

# 7. Get all Post-formed worktops, 600mm wide
curl "http://localhost:8000/api/variants?material_type=worktop_postformed&width_mm=600"

# 8. Get all structures (for filter UI)
curl "http://localhost:8000/api/structures"

# 9. Database statistics
curl "http://localhost:8000/api/admin/stats"
"""
