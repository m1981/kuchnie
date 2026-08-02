"""ERP side of the catalog schema-version handshake — bead kuchnie-019.

`refresh_material_mirror` used to mirror whatever the catalog returned. If a
catalog migration changed the row shape the mirror went wrong or empty and
nobody found out. Now the client refuses to read an incompatible catalog and
says which versions are involved.

Also pins the de-duplication: `kitchen_erp.core.catalog_client` must be a
re-export of the ONE implementation published by the service, not a second
copy.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from kitchen_erp.core.catalog_client import (
    DEFAULT_CATALOG_URL,
    PAGE_SIZE,
    CatalogClient,
    CatalogSchemaMismatch,
    CatalogUnavailable,
    HttpCatalogClient,
)
from kitchen_erp.core.material_mirror import refresh_material_mirror

# Importing the ERP module puts the repo root on sys.path (see its bootstrap),
# so the published implementation is importable for the identity assertions.
import catalog.client as published  # noqa: E402

BASE_URL = "http://catalog.test/catalog"

DECOR_ROW = {
    "decor_id": "K8685",
    "decor_name": "Biel Alpejska",
    "producer": "kronospan",
    "variant_id": "K8685-SM-18",
    "thickness_mm": 18,
    "roles": '["front"]',
}


def _install_transport(monkeypatch, schema_version, rows=(DECOR_ROW,)):
    """Serve a fake catalog service over the stdlib client's urlopen."""
    seen = []

    def _urlopen(url, timeout=None):
        seen.append(url)
        if "/admin/stats" in url:
            body = {"producers": 1, "decors": 1, "variants": 1, "pairings": 0, "worktops": 0}
            if schema_version is not None:
                body["schema_version"] = schema_version
        elif "/decors" in url:
            body = {"items": list(rows), "total": len(rows)}
        else:
            raise urllib.error.HTTPError(url, 404, "not found", None, None)
        return io.BytesIO(json.dumps(body).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    return seen


class TestOneImplementation:
    def test_http_client_is_the_published_one(self):
        assert HttpCatalogClient is published.HttpCatalogClient

    def test_errors_are_the_published_ones(self):
        assert CatalogUnavailable is published.CatalogUnavailable
        assert CatalogSchemaMismatch is published.CatalogSchemaMismatch

    def test_public_surface_is_preserved(self):
        """Existing ERP imports must keep resolving."""
        assert CatalogClient is not None
        assert DEFAULT_CATALOG_URL == "http://127.0.0.1:8000/catalog"
        assert PAGE_SIZE == 200


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

    def test_handshake_runs_before_any_row_is_read(self, monkeypatch):
        seen = _install_transport(monkeypatch, "9.9.9")
        with pytest.raises(CatalogSchemaMismatch):
            list(HttpCatalogClient(base_url=BASE_URL).iter_rows())
        assert seen and "/admin/stats" in seen[0]
        assert not any("/decors" in url for url in seen)

    def test_mismatch_is_not_swallowed_by_the_degrade_path(self, monkeypatch):
        """`except CatalogUnavailable` must not hide a schema mismatch."""
        _install_transport(monkeypatch, "9.9.9")
        with pytest.raises(CatalogSchemaMismatch):
            try:
                list(HttpCatalogClient(base_url=BASE_URL).iter_rows())
            except CatalogUnavailable:  # pragma: no cover - would be the bug
                pytest.fail("schema mismatch degraded silently")

    def test_mirror_refresh_aborts_on_mismatch(self, session, monkeypatch):
        """The bead's concrete symptom: mirroring wrong/empty rows."""
        _install_transport(monkeypatch, "9.9.9")
        with pytest.raises(CatalogSchemaMismatch):
            refresh_material_mirror(session, HttpCatalogClient(base_url=BASE_URL))
