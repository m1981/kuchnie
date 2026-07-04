"""Material catalog protocol — what the engine needs from a catalog.

The engine depends ONLY on this protocol, never on concrete implementations.
This allows:
    - SQLite repository (production)
    - Fake/mock repository (tests)
    - HTTP client (future, if needed)

Usage:
    from kuchnie_core.materials import MaterialCatalog, VariantInfo

    def decompose(cab, catalog: MaterialCatalog):
        variant = catalog.get_variant(cab.body_material)
        ...
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import EdgeInfo, VariantInfo, WorktopInfo


@runtime_checkable
class MaterialCatalog(Protocol):
    """Read-only interface to the material catalog.

    All methods return None or empty list for missing entries —
    the caller decides whether to raise or fallback.
    """

    def get_variant(self, code: str) -> VariantInfo | None:
        """Resolve a variant code (e.g. 'K8685-CH-18-SM') to full info.

        Returns None if code not found.
        """
        ...

    def get_edge(self, code: str) -> EdgeInfo | None:
        """Resolve an edge banding code (e.g. 'WK-8685-RS') to full info.

        Returns None if code not found.
        """
        ...

    def find_worktops(self, decor_code: str) -> list[WorktopInfo]:
        """Find all worktop variants for a given decor code.

        Returns empty list if no worktops found.
        """
        ...

    def find_edges_for_variant(self, variant_code: str) -> list[EdgeInfo]:
        """Find all compatible edge bandings for a variant.

        Returns empty list if no edges found.
        """
        ...
