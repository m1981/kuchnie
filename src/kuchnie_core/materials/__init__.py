"""Material catalog bridge — connects kuchnie-core to catalog data.

Public API:
    - MaterialCatalog (Protocol) — what the engine depends on
    - SqliteMaterialCatalog — production implementation
    - MaterialResolver — cached facade for decomposition
    - VariantInfo, EdgeInfo, WorktopInfo — lightweight DTOs
    - MaterialNotFoundError, EdgeNotFoundError — domain exceptions

Usage (production):
    from kuchnie_core.materials import SqliteMaterialCatalog, MaterialResolver

    catalog = SqliteMaterialCatalog("catalog/db/catalog.db")
    resolver = MaterialResolver(catalog)
    variant = resolver.resolve("K8685-CH-18-SM")

Usage (tests — no SQLite needed):
    from kuchnie_core.materials import MaterialCatalog, VariantInfo, MaterialResolver

    class FakeCatalog:
        def get_variant(self, code):
            return VariantInfo(code=code, thickness_mm=18.0, ...)
        def get_edge(self, code): return None
        def find_worktops(self, decor): return []
        def find_edges_for_variant(self, variant): return []

    resolver = MaterialResolver(FakeCatalog())
"""

from .exceptions import (
    CatalogUnavailableError,
    EdgeNotFoundError,
    MaterialCatalogError,
    MaterialNotFoundError,
)
from .models import (
    AvailabilityInfo,
    EdgeInfo,
    PropertyFlag,
    VariantInfo,
    WorktopInfo,
)
from .protocol import MaterialCatalog
from .resolver import MaterialResolver
from .sqlite_repository import SqliteMaterialCatalog

__all__ = [
    # Protocol
    "MaterialCatalog",
    # Implementations
    "SqliteMaterialCatalog",
    "MaterialResolver",
    # DTOs
    "VariantInfo",
    "EdgeInfo",
    "WorktopInfo",
    "PropertyFlag",
    "AvailabilityInfo",
    # Exceptions
    "MaterialCatalogError",
    "MaterialNotFoundError",
    "EdgeNotFoundError",
    "CatalogUnavailableError",
]
