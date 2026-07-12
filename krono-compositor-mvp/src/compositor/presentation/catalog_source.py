# src/compositor/presentation/catalog_source.py
"""Catalog-service-backed material source (docs/specs/catalog-routing.md).

Replaces the hardcoded CATALOG dict per ADR-008: decor identity comes from
the catalog service; presentation-only concerns stay local (scenes, price
grouping, texture tiling widths). Offline, the source degrades to the last
snapshot written to disk — sales visits happen away from the office and a
dead catalog service must never crash the app.

stdlib-only on purpose, same trade as kitchen-erp's catalog_client: a few
JSON GETs do not justify a dependency.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator, Optional, Protocol

logger = logging.getLogger("catalog_source")

DEFAULT_CATALOG_URL = "http://127.0.0.1:8000/catalog"
PAGE_SIZE = 200
DEFAULT_SNAPSHOT_PATH = "assets/catalog_snapshot.json"
DEFAULT_TEXTURE_DIR = "assets/textures"

# Kronospan board width; tiling scale used when a decor has no override
DEFAULT_TEXTURE_WIDTH_MM = 2070.0
DEFAULT_HEX = "#CCCCCC"

# ── Presentation-owned data (spec: field-mapping table) ──────────────────

SCENES = [
    {
        "scene_id": "kitchen_01",
        "name": "Nowoczesna Kuchnia (Modern)",
        "angles": [
            {"angle_id": "main", "name": "Widok Główny (Front View)"},
            {"angle_id": "detail", "name": "Zbliżenie (Detail View)"},
        ],
    }
]

PRICE_GROUPS = [
    {"id": 1, "name": "Grupa Cenowa 1"},
    {"id": 2, "name": "Grupa Cenowa 2"},
]

# The catalog does not model texture tiling metadata (tr-0ba0f782), so the
# decors that have a tileable JPG under assets/textures/ carry their
# physical repeat width here until the catalog grows a home for it.
TEXTURE_WIDTH_OVERRIDES_MM: dict[str, float] = {
    "K5307": 1200.0,  # Dąb Artisan
    "K9103": 1200.0,  # Dąb Jasny
    "K552": 2000.0,   # Biały Marmur Lodowy
    "K190": 2000.0,   # Czarny
    "K7031": 1000.0,  # Krem
    "K9561": 1000.0,  # Zielony Oxid
}

# Prices are ERP-owned; this grouping is a sales-UI presentation concern.
PRICE_GROUP_OVERRIDES: dict[str, int] = {
    "K9103": 2,
    "K7031": 2,
}
DEFAULT_PRICE_GROUP = 1


class CatalogUnavailable(RuntimeError):
    """The catalog service could not be read."""


class CatalogClient(Protocol):
    def iter_rows(self) -> Iterator[dict[str, Any]]:
        """Yield flat decor-variant rows from GET /catalog/decors."""
        ...

    def decor_hex_map(self) -> dict[str, str]:
        """Map decor business id -> color-family hex approximation."""
        ...


class HttpCatalogClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0):
        self.base_url = (base_url or os.environ.get("CATALOG_URL", DEFAULT_CATALOG_URL)).rstrip("/")
        self.timeout = timeout

    @property
    def origin(self) -> str:
        parts = urllib.parse.urlsplit(self.base_url)
        return f"{parts.scheme}://{parts.netloc}"

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            url += f"?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                data: dict[str, Any] = json.load(resp)
                return data
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            raise CatalogUnavailable(f"GET {url}: {e}") from e

    def iter_rows(self) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            payload = self._get_json("/decors", {"page": page, "page_size": PAGE_SIZE})
            items = payload.get("items", [])
            yield from items
            if page * PAGE_SIZE >= payload.get("total", 0) or not items:
                return
            page += 1

    def decor_hex_map(self) -> dict[str, str]:
        payload = self._get_json("/full", {})
        out: dict[str, str] = {}
        for producer in payload.get("producers", {}).values():
            for decor in producer.get("decors", []):
                if decor.get("id") and decor.get("color_hex"):
                    out[decor["id"]] = decor["color_hex"]
        return out


def _derive_allowed_zone(roles: set[str]) -> str:
    if "carcass" in roles or {"front", "worktop"} <= roles:
        return "ANY"
    if roles == {"worktop"}:
        return "COUNTERTOP_ONLY"
    if "front" in roles:
        return "FRONT_ONLY"
    return "ANY"


def build_materials(rows: list[dict[str, Any]], hex_map: dict[str, str], origin: str = "") -> list[dict[str, Any]]:
    """Fold flat decor-variant rows into one material per decor."""
    by_decor: dict[str, dict[str, Any]] = {}
    roles_by_decor: dict[str, set[str]] = {}
    for row in rows:
        decor_id = row.get("decor_id")
        if not decor_id or row.get("discontinued"):
            continue
        try:
            roles = set(json.loads(row.get("roles") or "[]"))
        except (TypeError, ValueError):
            roles = set()
        roles_by_decor.setdefault(decor_id, set()).update(roles)
        if decor_id in by_decor:
            if not by_decor[decor_id]["img_url"] and row.get("img"):
                by_decor[decor_id]["img_url"] = _img_url(row, origin)
            continue
        by_decor[decor_id] = {
            "id": decor_id,
            "name": row.get("decor_name") or decor_id,
            "price_group": PRICE_GROUP_OVERRIDES.get(decor_id, DEFAULT_PRICE_GROUP),
            "allowed_zone": "ANY",  # finalized below from the role union
            "texture_width_mm": TEXTURE_WIDTH_OVERRIDES_MM.get(decor_id, DEFAULT_TEXTURE_WIDTH_MM),
            "hex_color": hex_map.get(decor_id, DEFAULT_HEX),
            "img_url": _img_url(row, origin),
        }
    for decor_id, material in by_decor.items():
        material["allowed_zone"] = _derive_allowed_zone(roles_by_decor[decor_id])
    return sorted(by_decor.values(), key=lambda m: m["id"])


def _img_url(row: dict[str, Any], origin: str) -> Optional[str]:
    if not row.get("img"):
        return None
    return f"{origin}/producers/{row.get('producer', '')}/decors/{row['img']}"


class CatalogSource:
    """Serves the /api/v1/catalog payload; caches in memory + disk snapshot."""

    def __init__(self, client: CatalogClient, snapshot_path: Optional[str] = None,
                 texture_dir: str = DEFAULT_TEXTURE_DIR):
        self._client = client
        self._snapshot_path = snapshot_path or os.environ.get(
            "COMPOSITOR_CATALOG_SNAPSHOT", DEFAULT_SNAPSHOT_PATH
        )
        self._texture_dir = texture_dir
        self._payload: Optional[dict[str, Any]] = None

    def get_catalog(self, refresh: bool = False) -> dict[str, Any]:
        if self._payload is None or refresh:
            self._payload = self._load()
        return self._payload

    def find_material(self, material_id: str) -> Optional[dict[str, Any]]:
        return next(
            (m for m in self.get_catalog()["materials"] if m["id"] == material_id),
            None,
        )

    def _load(self) -> dict[str, Any]:
        try:
            rows = list(self._client.iter_rows())
        except CatalogUnavailable as e:
            logger.warning("catalog service unreachable (%s); falling back to snapshot", e)
            snapshot = self._read_snapshot()
            if snapshot is not None:
                return snapshot
            logger.warning("no catalog snapshot at %s; serving empty material list", self._snapshot_path)
            return {"price_groups": PRICE_GROUPS, "materials": [], "scenes": SCENES}

        try:
            hex_map = self._client.decor_hex_map()
        except CatalogUnavailable as e:
            logger.warning("hex map unavailable (%s); swatches fall back to %s", e, DEFAULT_HEX)
            hex_map = {}

        origin = getattr(self._client, "origin", "")
        materials = build_materials(rows, hex_map, origin)
        for material in materials:
            material["renderable"] = os.path.isfile(
                os.path.join(self._texture_dir, f"{material['id']}.jpg")
            )
        payload = {
            "price_groups": PRICE_GROUPS,
            "materials": materials,
            "scenes": SCENES,
        }
        self._write_snapshot(payload)
        return payload

    def _read_snapshot(self) -> Optional[dict[str, Any]]:
        try:
            with open(self._snapshot_path, encoding="utf-8") as f:
                snapshot: dict[str, Any] = json.load(f)
                return snapshot
        except (OSError, json.JSONDecodeError):
            return None

    def _write_snapshot(self, payload: dict[str, Any]) -> None:
        try:
            with open(self._snapshot_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except OSError as e:
            logger.warning("could not write catalog snapshot to %s: %s", self._snapshot_path, e)
