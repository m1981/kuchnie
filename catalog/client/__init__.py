"""The catalog service's own read-only HTTP client — one implementation.

Published from `catalog/` on purpose (bead kuchnie-019): consumers already
depend on the service, so shipping the client next to the thing it talks to
keeps the dependency direction one-way and stops the class being copied. It
previously existed twice, independently maintained, in kitchen-erp and in
krono-compositor; both now re-export from here.

stdlib-only, deliberately: a handful of JSON GETs does not justify a
dependency, and importing this module must never drag FastAPI or pydantic
into a consumer's process.

Two failure modes, kept distinct because consumers treat them differently:

  CatalogUnavailable    the service could not be read (down, timeout, bad
                        JSON). Consumers may degrade — krono falls back to
                        its on-disk snapshot so a sales visit survives a
                        dead office box.
  CatalogSchemaMismatch the service answered, but with a schema this client
                        does not understand. NEVER degrade on this: mirroring
                        wrong rows or serving a stale snapshot after a
                        migration is the silent failure this module exists to
                        prevent. It is intentionally NOT a subclass of
                        CatalogUnavailable so existing `except
                        CatalogUnavailable` degrade paths cannot swallow it.

The handshake itself is lazy — one GET /admin/stats before the first data
read, cached per client — so constructing a client stays free of I/O and
callers need no new startup step.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterator, Optional, Protocol, Tuple

from catalog.db.engine import SCHEMA_VERSION

DEFAULT_CATALOG_URL = "http://127.0.0.1:8000/catalog"
PAGE_SIZE = 200
STATS_PATH = "/admin/stats"

#: Schema version this client is written against. Sourced from the schema
#: itself (catalog/db/schema.sql's `-- Version:` header) so there is exactly
#: one number in the repo to bump.
CLIENT_SCHEMA_VERSION = SCHEMA_VERSION


class CatalogUnavailable(RuntimeError):
    """The catalog service could not be read."""


class CatalogSchemaMismatch(RuntimeError):
    """The catalog service speaks a schema version this client does not."""


class CatalogClient(Protocol):
    def iter_rows(self) -> Iterator[Dict[str, Any]]:
        """Yield flat decor-variant rows from GET /catalog/decors."""
        ...


class DecorHexCatalogClient(CatalogClient, Protocol):
    def decor_hex_map(self) -> Dict[str, str]:
        """Map decor business id -> color-family hex approximation."""
        ...


def _parse_version(value: str) -> Tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3:
        raise ValueError(value)
    return int(parts[0]), int(parts[1]), int(parts[2])


def check_schema_compatible(
    actual: Optional[str],
    expected: str = CLIENT_SCHEMA_VERSION,
    *,
    source: str = "the catalog service",
) -> None:
    """Raise CatalogSchemaMismatch unless `actual` is one this client can read.

    Compatible means the same MAJOR.MINOR; PATCH may differ. The catalog's
    minor bumps have historically moved columns (1.4 -> 1.5 relocated the
    collection flags into decor_tags), so treating a minor bump as additive
    would reintroduce exactly the silent breakage this guards against. A
    deliberate consumer bump is the point.
    """
    if not actual:
        raise CatalogSchemaMismatch(
            f"{source} did not report a schema_version (expected {expected}). "
            "It predates the schema-version handshake, so its row shape cannot "
            "be trusted — upgrade the catalog service, or point CATALOG_URL at "
            "one that publishes schema_version in GET /admin/stats."
        )
    try:
        actual_parts = _parse_version(actual)
        expected_parts = _parse_version(expected)
    except ValueError:
        raise CatalogSchemaMismatch(
            f"{source} reported an unparseable catalog schema version "
            f"{actual!r}; this client requires {expected} (expected X.Y.Z)."
        ) from None
    if actual_parts[:2] != expected_parts[:2]:
        raise CatalogSchemaMismatch(
            f"catalog schema mismatch: {source} reports schema {actual}, "
            f"but this client is written against {expected} "
            f"(major.minor must match; patch may differ). "
            "Refusing to read a catalog whose shape it does not know — mirrored "
            "rows would be wrong or empty. Fix: upgrade the consumer to the "
            "catalog revision that ships schema "
            f"{actual_parts[0]}.{actual_parts[1]}.x, or roll the service back to "
            f"{expected_parts[0]}.{expected_parts[1]}.x."
        )


class HttpCatalogClient:
    """Reads the catalog over HTTP; handshakes on the schema version first.

    Consumes the paginated /decors endpoint, whose items are FLAT rows (one
    per variant, v_decors_full shape) — decor identity and variant fields in
    one dict.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        expected_schema_version: Optional[str] = None,
    ):
        self.base_url = (
            base_url or os.environ.get("CATALOG_URL", DEFAULT_CATALOG_URL)
        ).rstrip("/")
        self.timeout = timeout
        self.expected_schema_version = expected_schema_version or CLIENT_SCHEMA_VERSION
        self._verified_schema_version: Optional[str] = None

    @property
    def origin(self) -> str:
        parts = urllib.parse.urlsplit(self.base_url)
        return f"{parts.scheme}://{parts.netloc}"

    def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            url += f"?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                data: Dict[str, Any] = json.load(resp)
                return data
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            raise CatalogUnavailable(f"GET {url}: {e}") from e

    # ── handshake ────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """GET /admin/stats — row counts plus the schema_version field."""
        return self._get_json(STATS_PATH, {})

    def assert_compatible(self, force: bool = False) -> str:
        """Verify the service's schema version; return it. Cached per client.

        Raises CatalogUnavailable if the service cannot be reached (callers
        may degrade) and CatalogSchemaMismatch if it can but speaks a schema
        this client does not (callers must not).
        """
        if self._verified_schema_version is not None and not force:
            return self._verified_schema_version
        version = self.stats().get("schema_version")
        check_schema_compatible(
            version, self.expected_schema_version, source=self.base_url
        )
        assert version is not None  # check_schema_compatible rejects falsy
        self._verified_schema_version = version
        return version

    # ── reads ────────────────────────────────────────────────────

    def iter_rows(self) -> Iterator[Dict[str, Any]]:
        self.assert_compatible()
        return self._iter_rows()

    def _iter_rows(self) -> Iterator[Dict[str, Any]]:
        page = 1
        while True:
            payload = self._get_json("/decors", {"page": page, "page_size": PAGE_SIZE})
            items = payload.get("items", [])
            yield from items
            if page * PAGE_SIZE >= payload.get("total", 0) or not items:
                return
            page += 1

    def decor_hex_map(self) -> Dict[str, str]:
        self.assert_compatible()
        payload = self._get_json("/full", {})
        out: Dict[str, str] = {}
        for producer in payload.get("producers", {}).values():
            for decor in producer.get("decors", []):
                if decor.get("id") and decor.get("color_hex"):
                    out[decor["id"]] = decor["color_hex"]
        return out


__all__ = [
    "CLIENT_SCHEMA_VERSION",
    "DEFAULT_CATALOG_URL",
    "PAGE_SIZE",
    "STATS_PATH",
    "CatalogClient",
    "CatalogSchemaMismatch",
    "CatalogUnavailable",
    "DecorHexCatalogClient",
    "HttpCatalogClient",
    "check_schema_compatible",
]
