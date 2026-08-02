# kitchen_erp/core/catalog_client.py
"""Thin read-only client for the catalog service (ADR-008 canonical source).

The implementation is NOT here any more. It lived here and, character for
character, in krono-compositor as well — two copies of the same class, drifting
independently. It now lives once, published by the service itself as
`catalog.client` (bead kuchnie-019); this module is the ERP-facing re-export so
every existing import site keeps working unchanged.

What the move buys: `HttpCatalogClient` performs a schema-version handshake
(GET /catalog/admin/stats) before the first row is read, and raises
`CatalogSchemaMismatch` if the service speaks a schema this code base was not
written against. Previously a catalog migration would let
`refresh_material_mirror` mirror wrong or empty rows in silence.

Failure contract (unchanged for callers):
  CatalogUnavailable    service unreadable — callers decide whether that
                        degrades (app boot) or aborts (explicit refresh).
  CatalogSchemaMismatch service readable but incompatible — never degrade.
                        Deliberately not a CatalogUnavailable subclass, so the
                        existing `except CatalogUnavailable` sites cannot
                        swallow it.
"""
from __future__ import annotations

try:  # normal case: the repo root (which holds catalog/) is importable
    from catalog.client import (
        CLIENT_SCHEMA_VERSION,
        DEFAULT_CATALOG_URL,
        PAGE_SIZE,
        CatalogClient,
        CatalogSchemaMismatch,
        CatalogUnavailable,
        HttpCatalogClient,
        check_schema_compatible,
    )
except ImportError:  # sibling-component checkout: put the repo root on the path
    import sys
    from pathlib import Path

    _REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    from catalog.client import (
        CLIENT_SCHEMA_VERSION,
        DEFAULT_CATALOG_URL,
        PAGE_SIZE,
        CatalogClient,
        CatalogSchemaMismatch,
        CatalogUnavailable,
        HttpCatalogClient,
        check_schema_compatible,
    )

__all__ = [
    "CLIENT_SCHEMA_VERSION",
    "DEFAULT_CATALOG_URL",
    "PAGE_SIZE",
    "CatalogClient",
    "CatalogSchemaMismatch",
    "CatalogUnavailable",
    "HttpCatalogClient",
    "check_schema_compatible",
]
