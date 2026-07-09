# kitchen_erp/core/catalog_client.py
"""Thin read-only client for the catalog service (ADR-008 canonical source).

Consumes the paginated /catalog/decors endpoint, whose items are FLAT rows
(one per variant, v_decors_full shape) — decor identity and variant fields
in one dict. stdlib-only on purpose: two JSON GETs do not justify a
dependency.

Failure contract: anything that prevents reading the catalog (connection,
HTTP status, malformed JSON) raises CatalogUnavailable. Callers decide
whether that degrades (app boot) or aborts (explicit refresh).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterator, Protocol

DEFAULT_CATALOG_URL = "http://127.0.0.1:8000/catalog"
PAGE_SIZE = 200


class CatalogUnavailable(RuntimeError):
    """The catalog service could not be read."""


class CatalogClient(Protocol):
    def iter_rows(self) -> Iterator[dict]:
        """Yield flat decor-variant rows from the catalog."""
        ...


class HttpCatalogClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0):
        self.base_url = (base_url or os.environ.get("CATALOG_URL", DEFAULT_CATALOG_URL)).rstrip("/")
        self.timeout = timeout

    def _get_json(self, path: str, params: dict) -> dict:
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.load(resp)
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            raise CatalogUnavailable(f"GET {url}: {e}") from e

    def iter_rows(self) -> Iterator[dict]:
        page = 1
        while True:
            payload = self._get_json("/decors", {"page": page, "page_size": PAGE_SIZE})
            items = payload.get("items", [])
            yield from items
            if page * PAGE_SIZE >= payload.get("total", 0) or not items:
                return
            page += 1
