"""Catalog schema-version handshake — bead kuchnie-019.

The catalog owns the schema; consumers read it over HTTP. Before this
module the version was written only in a comment header of
``db/schema.sql`` and no consumer ever asked for it, so a migration broke
consumers *silently*. Here the version becomes part of the wire contract:

  * ``GET /catalog/admin/stats`` reports ``schema_version``
  * ``catalog.client`` refuses to read a catalog whose version it does not
    understand, and says so loudly

Fixtures come from ``conftest.py`` (``db``, ``client``, ``db_seeded``).
"""

from __future__ import annotations

import io
import json
import re
import urllib.error
import urllib.request

import pytest

from catalog.client import (
    CLIENT_SCHEMA_VERSION,
    DEFAULT_CATALOG_URL,
    PAGE_SIZE,
    CatalogSchemaMismatch,
    CatalogUnavailable,
    HttpCatalogClient,
    check_schema_compatible,
)
from catalog.db.engine import SCHEMA_VERSION, _SCHEMA_PATH

TEST_BASE_URL = "http://testserver/catalog"


# ── The authoritative version ────────────────────────────────────


class TestAuthoritativeVersion:
    def test_schema_version_matches_the_schema_sql_header(self):
        """schema.sql's ``-- Version:`` header is the single source of truth."""
        header = _SCHEMA_PATH.read_text(encoding="utf-8")[:500]
        match = re.search(r"^--\s*Version:\s*(\S+)\s*$", header, re.MULTILINE)
        assert match is not None, "schema.sql lost its '-- Version:' header"
        assert SCHEMA_VERSION == match.group(1)

    def test_schema_version_is_a_dotted_triple(self):
        assert re.fullmatch(r"\d+\.\d+\.\d+", SCHEMA_VERSION)

    def test_client_expects_the_version_it_ships_with(self):
        """No second constant to drift: the client pins the schema it ships with."""
        assert CLIENT_SCHEMA_VERSION == SCHEMA_VERSION


# ── The wire contract ────────────────────────────────────────────


class TestStatsExposesSchemaVersion:
    def test_stats_reports_schema_version(self, client):
        resp = client.get("/catalog/admin/stats")
        assert resp.status_code == 200
        assert resp.json()["schema_version"] == SCHEMA_VERSION

    def test_stats_still_reports_counts(self, client):
        """The handshake field is additive — existing consumers keep working."""
        stats = client.get("/catalog/admin/stats").json()
        assert stats["producers"] == 1
        assert stats["decors"] == 7
        assert stats["variants"] == 5
        assert stats["pairings"] == 3
        assert stats["worktops"] == 3


# ── Compatibility rule ───────────────────────────────────────────


class TestCheckSchemaCompatible:
    def test_identical_version_is_compatible(self):
        check_schema_compatible("1.5.0", "1.5.0")

    def test_patch_drift_is_compatible(self):
        check_schema_compatible("1.5.9", "1.5.0")
        check_schema_compatible("1.5.0", "1.5.9")

    def test_minor_bump_is_incompatible(self):
        with pytest.raises(CatalogSchemaMismatch):
            check_schema_compatible("1.6.0", "1.5.0")

    def test_major_bump_is_incompatible(self):
        with pytest.raises(CatalogSchemaMismatch):
            check_schema_compatible("2.0.0", "1.5.0")

    def test_older_service_is_incompatible(self):
        with pytest.raises(CatalogSchemaMismatch):
            check_schema_compatible("1.4.0", "1.5.0")

    def test_error_names_expected_and_actual(self):
        with pytest.raises(CatalogSchemaMismatch) as exc:
            check_schema_compatible("2.0.0", "1.5.0", source="http://catalog:8000")
        message = str(exc.value)
        assert "2.0.0" in message  # what the service reports
        assert "1.5.0" in message  # what the client requires
        assert "http://catalog:8000" in message  # who to look at

    def test_unparseable_version_is_a_mismatch_not_a_crash(self):
        with pytest.raises(CatalogSchemaMismatch):
            check_schema_compatible("not-a-version", "1.5.0")

    def test_mismatch_is_not_an_availability_error(self):
        """Consumers degrade on CatalogUnavailable — a mismatch must NOT degrade."""
        assert not issubclass(CatalogSchemaMismatch, CatalogUnavailable)
        assert not issubclass(CatalogUnavailable, CatalogSchemaMismatch)


# ── The one HTTP client, against the real app ────────────────────


def _install_transport(monkeypatch, test_client, stats_override=None):
    """Route the stdlib client's urlopen through the FastAPI TestClient."""

    def _urlopen(url, timeout=None):
        path = url[len("http://testserver") :]
        resp = test_client.get(path)
        if resp.status_code != 200:
            raise urllib.error.HTTPError(url, resp.status_code, "error", None, None)
        if stats_override is None or not path.startswith("/catalog/admin/stats"):
            return io.BytesIO(resp.content)
        payload = {**resp.json(), **stats_override}
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)


class TestHttpCatalogClient:
    def test_defaults_are_the_published_ones(self):
        assert DEFAULT_CATALOG_URL == "http://127.0.0.1:8000/catalog"
        assert PAGE_SIZE == 200

    def test_base_url_from_environment(self, monkeypatch):
        monkeypatch.setenv("CATALOG_URL", "http://elsewhere:9000/catalog/")
        assert HttpCatalogClient().base_url == "http://elsewhere:9000/catalog"

    def test_origin_strips_the_path(self):
        assert HttpCatalogClient(base_url=TEST_BASE_URL).origin == "http://testserver"

    def test_compatible_service_lets_rows_through(self, client, monkeypatch):
        _install_transport(monkeypatch, client)
        rows = list(HttpCatalogClient(base_url=TEST_BASE_URL).iter_rows())
        assert rows, "seeded catalog should yield decor-variant rows"
        assert "decor_id" in rows[0]

    def test_compatible_service_lets_hex_map_through(self, client, monkeypatch):
        _install_transport(monkeypatch, client)
        assert isinstance(HttpCatalogClient(base_url=TEST_BASE_URL).decor_hex_map(), dict)

    def test_assert_compatible_returns_the_service_version(self, client, monkeypatch):
        _install_transport(monkeypatch, client)
        got = HttpCatalogClient(base_url=TEST_BASE_URL).assert_compatible()
        assert got == SCHEMA_VERSION

    def test_incompatible_service_blocks_rows(self, client, monkeypatch):
        _install_transport(monkeypatch, client, stats_override={"schema_version": "9.0.0"})
        http = HttpCatalogClient(base_url=TEST_BASE_URL)
        with pytest.raises(CatalogSchemaMismatch) as exc:
            list(http.iter_rows())
        assert "9.0.0" in str(exc.value)
        assert SCHEMA_VERSION in str(exc.value)

    def test_incompatible_service_blocks_hex_map(self, client, monkeypatch):
        _install_transport(monkeypatch, client, stats_override={"schema_version": "9.0.0"})
        with pytest.raises(CatalogSchemaMismatch):
            HttpCatalogClient(base_url=TEST_BASE_URL).decor_hex_map()

    def test_service_without_the_handshake_field_is_a_mismatch(self, client, monkeypatch):
        """A service too old to publish a version cannot be trusted either."""
        _install_transport(monkeypatch, client, stats_override={"schema_version": None})
        with pytest.raises(CatalogSchemaMismatch):
            list(HttpCatalogClient(base_url=TEST_BASE_URL).iter_rows())

    def test_handshake_is_performed_once_per_client(self, client, monkeypatch):
        _install_transport(monkeypatch, client)
        http = HttpCatalogClient(base_url=TEST_BASE_URL)
        calls = []
        original = http.stats

        def _counting_stats():
            calls.append(1)
            return original()

        monkeypatch.setattr(http, "stats", _counting_stats)
        list(http.iter_rows())
        http.decor_hex_map()
        assert len(calls) == 1

    def test_unreachable_service_is_unavailable_not_a_mismatch(self, monkeypatch):
        def _boom(url, timeout=None):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", _boom)
        with pytest.raises(CatalogUnavailable):
            list(HttpCatalogClient(base_url=TEST_BASE_URL).iter_rows())
