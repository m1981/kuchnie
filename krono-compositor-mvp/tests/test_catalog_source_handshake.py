"""Compositor side of the catalog schema-version handshake — bead kuchnie-019.

CatalogSource is deliberately forgiving: a dead catalog service falls back to
the last on-disk snapshot, because sales visits happen away from the office.
That forgiveness must NOT extend to a catalog whose schema the compositor no
longer understands — serving a stale snapshot after a migration is exactly the
silent failure the bead is about.

Also pins the de-duplication: `catalog_source.HttpCatalogClient` must be the
ONE implementation published by the service, not a second copy.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from compositor.presentation.catalog_source import (
    DEFAULT_CATALOG_URL,
    PAGE_SIZE,
    CatalogSchemaMismatch,
    CatalogSource,
    CatalogUnavailable,
    HttpCatalogClient,
)

# Importing the compositor module puts the repo root on sys.path (see its
# bootstrap), so the published implementation is importable here.
import catalog.client as published  # noqa: E402

BASE_URL = "http://catalog.test/catalog"

DECOR_ROW = {
    "decor_id": "K190",
    "decor_name": "Czarny",
    "producer": "kronospan",
    "roles": '["front"]',
    "img": "k190.jpg",
}


def _install_transport(monkeypatch, schema_version, rows=(DECOR_ROW,)):
    def _urlopen(url, timeout=None):
        if "/admin/stats" in url:
            body = {"producers": 1, "decors": 1, "variants": 1, "pairings": 0, "worktops": 0}
            if schema_version is not None:
                body["schema_version"] = schema_version
        elif "/decors" in url:
            body = {"items": list(rows), "total": len(rows)}
        elif url.endswith("/full"):
            body = {"producers": {"kronospan": {"decors": [{"id": "K190", "color_hex": "#111111"}]}}}
        else:
            raise urllib.error.HTTPError(url, 404, "not found", None, None)
        return io.BytesIO(json.dumps(body).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)


class _MismatchingClient:
    """Stand-in for a client whose handshake already failed."""

    def iter_rows(self):
        raise CatalogSchemaMismatch("catalog schema mismatch: 9.9.9 vs 1.5.0")

    def decor_hex_map(self):
        raise CatalogSchemaMismatch("catalog schema mismatch: 9.9.9 vs 1.5.0")


class TestOneImplementation:
    def test_http_client_is_the_published_one(self):
        assert HttpCatalogClient is published.HttpCatalogClient

    def test_errors_are_the_published_ones(self):
        assert CatalogUnavailable is published.CatalogUnavailable
        assert CatalogSchemaMismatch is published.CatalogSchemaMismatch

    def test_public_surface_is_preserved(self):
        assert DEFAULT_CATALOG_URL == "http://127.0.0.1:8000/catalog"
        assert PAGE_SIZE == 200
        assert HttpCatalogClient(base_url=BASE_URL).origin == "http://catalog.test"


class TestHandshake:
    def test_compatible_catalog_proceeds(self, monkeypatch):
        _install_transport(monkeypatch, published.CLIENT_SCHEMA_VERSION)
        rows = list(HttpCatalogClient(base_url=BASE_URL).iter_rows())
        assert rows == [DECOR_ROW]

    def test_incompatible_catalog_fails_loudly(self, monkeypatch):
        _install_transport(monkeypatch, "9.9.9")
        with pytest.raises(CatalogSchemaMismatch) as exc:
            list(HttpCatalogClient(base_url=BASE_URL).iter_rows())
        message = str(exc.value)
        assert "9.9.9" in message
        assert published.CLIENT_SCHEMA_VERSION in message
        assert BASE_URL in message

    def test_hex_map_also_handshakes(self, monkeypatch):
        _install_transport(monkeypatch, "9.9.9")
        with pytest.raises(CatalogSchemaMismatch):
            HttpCatalogClient(base_url=BASE_URL).decor_hex_map()


class TestSourceDoesNotDegradeOnMismatch:
    def test_mismatch_propagates_instead_of_serving_a_snapshot(self, tmp_path):
        snapshot = tmp_path / "snapshot.json"
        snapshot.write_text(
            json.dumps({"price_groups": [], "materials": [{"id": "STALE"}], "scenes": []}),
            encoding="utf-8",
        )
        source = CatalogSource(_MismatchingClient(), snapshot_path=str(snapshot))
        with pytest.raises(CatalogSchemaMismatch):
            source.get_catalog()

    def test_unavailable_still_degrades_to_snapshot(self, tmp_path, monkeypatch):
        """The offline path is untouched — only mismatches are fatal."""
        snapshot = tmp_path / "snapshot.json"
        snapshot.write_text(
            json.dumps({"price_groups": [], "materials": [{"id": "CACHED"}], "scenes": []}),
            encoding="utf-8",
        )

        def _boom(url, timeout=None):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", _boom)
        source = CatalogSource(HttpCatalogClient(base_url=BASE_URL), snapshot_path=str(snapshot))
        assert source.get_catalog()["materials"] == [{"id": "CACHED"}]

    def test_compatible_catalog_builds_materials(self, monkeypatch, tmp_path):
        _install_transport(monkeypatch, published.CLIENT_SCHEMA_VERSION)
        source = CatalogSource(
            HttpCatalogClient(base_url=BASE_URL),
            snapshot_path=str(tmp_path / "snapshot.json"),
        )
        materials = source.get_catalog()["materials"]
        assert [m["id"] for m in materials] == ["K190"]
        assert materials[0]["hex_color"] == "#111111"
