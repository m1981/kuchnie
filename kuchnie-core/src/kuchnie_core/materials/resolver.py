"""Material resolver — cached facade over MaterialCatalog.

Used by catalog.py and bom.py during decomposition.
Caches lookups per-session (dict) to avoid repeated DB hits.

Usage:
    from kuchnie_core.materials import MaterialResolver, SqliteMaterialCatalog

    catalog = SqliteMaterialCatalog("catalog/db/catalog.db")
    resolver = MaterialResolver(catalog)

    variant = resolver.resolve("K8685-CH-18-SM")  # cached after first call
    edges = resolver.resolve_edges("K8685-CH-18-SM")
"""

from __future__ import annotations

from .exceptions import MaterialNotFoundError
from .models import EdgeInfo, VariantInfo, WorktopInfo
from .protocol import MaterialCatalog


class MaterialResolver:
    """High-level API for resolving material codes during decomposition.

    Wraps a MaterialCatalog with:
        - LRU-style caching (dict, bounded size)
        - raise-on-miss semantics (MaterialNotFoundError)
        - Edge resolution with fallback logic

    NOT thread-safe (dict is not). Use per-thread instances.
    """

    def __init__(
        self,
        catalog: MaterialCatalog,
        cache_size: int = 512,
    ):
        self._catalog = catalog
        self._variant_cache: dict[str, VariantInfo] = {}
        self._edge_cache: dict[str, EdgeInfo] = {}
        self._worktop_cache: dict[str, list[WorktopInfo]] = {}
        self._cache_size = cache_size

    # ── Variant resolution ───────────────────────────────────────

    def resolve(self, code: str) -> VariantInfo:
        """Resolve material code to full info. Raises MaterialNotFoundError."""
        if code not in self._variant_cache:
            variant = self._catalog.get_variant(code)
            if variant is None:
                raise MaterialNotFoundError(code)
            self._put_variant(code, variant)
        return self._variant_cache[code]

    def try_resolve(self, code: str) -> VariantInfo | None:
        """Resolve material code. Returns None if not found (no exception)."""
        if code in self._variant_cache:
            return self._variant_cache[code]
        variant = self._catalog.get_variant(code)
        if variant is not None:
            self._put_variant(code, variant)
        return variant

    def _put_variant(self, code: str, variant: VariantInfo) -> None:
        if len(self._variant_cache) < self._cache_size:
            self._variant_cache[code] = variant

    # ── Edge resolution ──────────────────────────────────────────

    def resolve_edge(self, code: str) -> EdgeInfo:
        """Resolve edge banding code. Raises MaterialNotFoundError."""
        if code not in self._edge_cache:
            edge = self._catalog.get_edge(code)
            if edge is None:
                raise MaterialNotFoundError(code)
            if len(self._edge_cache) < self._cache_size:
                self._edge_cache[code] = edge
        return self._edge_cache[code]

    def resolve_edges(self, variant_code: str) -> list[EdgeInfo]:
        """Find all compatible edge bandings for a variant."""
        return self._catalog.find_edges_for_variant(variant_code)

    # ── Worktop resolution ───────────────────────────────────────

    def resolve_worktops(self, decor_code: str) -> list[WorktopInfo]:
        """Find all worktop variants for a decor. Cached per decor."""
        if decor_code not in self._worktop_cache:
            worktops = self._catalog.find_worktops(decor_code)
            if len(self._worktop_cache) < self._cache_size:
                self._worktop_cache[decor_code] = worktops
        return self._worktop_cache[decor_code]

    # ── Introspection ────────────────────────────────────────────

    @property
    def cache_stats(self) -> dict[str, int]:
        """Return cache fill levels for debugging."""
        return {
            "variants": len(self._variant_cache),
            "edges": len(self._edge_cache),
            "worktops": len(self._worktop_cache),
        }

    def clear_cache(self) -> None:
        """Evict all cached entries."""
        self._variant_cache.clear()
        self._edge_cache.clear()
        self._worktop_cache.clear()
