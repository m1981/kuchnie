"""Tests for the materials bridge module.

Covers:
    1. Models — frozen, equality, defaults
    2. Protocol — FakeCatalog conformance
    3. SqliteMaterialCatalog — reads from real DB
    4. MaterialResolver — caching, errors, worktops
    5. Integration — resolver → sqlite → imported data
"""

import json
import sqlite3
from pathlib import Path

import pytest

from kuchnie_core.materials import (
    CatalogUnavailableError,
    EdgeInfo,
    MaterialCatalog,
    MaterialNotFoundError,
    MaterialResolver,
    SqliteMaterialCatalog,
    VariantInfo,
    WorktopInfo,
)
from kuchnie_core.materials.protocol import MaterialCatalog as Protocol

# ── Paths ────────────────────────────────────────────────────────

CATALOG_DIR = Path(__file__).resolve().parent.parent / "catalog"
DATA_DIR = CATALOG_DIR / "data"
ARCH_DIR = CATALOG_DIR / "docs" / "architecture"

SCHEMA_FILES = [
    "01-schema.sql",
    "02-phase1-worktop-specs.sql",
    "03-phase2-decor-structures-and-pairings.sql",
    "04-phase4a-variant-availability.sql",
    "05-phase4b-property-flags.sql",
]


# ── Fixtures ─────────────────────────────────────────────────────


def _build_test_db() -> sqlite3.Connection:
    """Create an in-memory DB with schema + Kronospan sample data."""
    from catalog.scripts.importer import CatalogImporter, load_yaml

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    for sql_file in SCHEMA_FILES:
        sql = (ARCH_DIR / sql_file).read_text(encoding="utf-8")
        db.executescript(sql)

    data = load_yaml(DATA_DIR / "kronospan_sample.yaml")
    importer = CatalogImporter(db)
    importer.import_all(data)
    return db


@pytest.fixture
def test_db(tmp_path):
    """Build a real SQLite file from kronospan_sample.yaml."""
    db = _build_test_db()
    db_path = tmp_path / "test_catalog.db"
    # Dump to file so SqliteMaterialCatalog can open it
    file_db = sqlite3.connect(str(db_path))
    db.backup(file_db)
    file_db.close()
    db.close()
    return db_path


@pytest.fixture
def catalog(test_db):
    """SqliteMaterialCatalog backed by test DB."""
    repo = SqliteMaterialCatalog(test_db)
    yield repo
    repo.close()


@pytest.fixture
def resolver(catalog):
    """MaterialResolver wrapping the test catalog."""
    return MaterialResolver(catalog)


# ══════════════════════════════════════════════════════════════════
# 1. Models
# ══════════════════════════════════════════════════════════════════


class TestModels:
    def test_variant_info_frozen(self):
        v = VariantInfo(
            code="K8685-CH-18-SM", decor_code="K8685",
            decor_name="Biel Alpejska", producer="kronospan",
            material_type="chipboard", structure="SM", thickness_mm=18.0,
        )
        with pytest.raises(AttributeError):
            v.code = "other"  # type: ignore[misc]

    def test_variant_info_equality(self):
        v1 = VariantInfo(
            code="X", decor_code="D", decor_name="N", producer="P",
            material_type="M", structure="S", thickness_mm=18.0,
        )
        v2 = VariantInfo(
            code="X", decor_code="D", decor_name="N", producer="P",
            material_type="M", structure="S", thickness_mm=18.0,
        )
        assert v1 == v2

    def test_edge_info_defaults(self):
        e = EdgeInfo(
            code="WK-8685-RS", supplier="schilsner",
            material="ABS", thickness_mm=1.2, width_mm=42,
        )
        assert e.radius_mm == 0

    def test_worktop_info_tuple_fields(self):
        w = WorktopInfo(
            variant_code="868S-PF-U-600", decor_code="868S",
            decor_name="Biel Alpejska", construction="postformed",
            profile="U", edge_radius_mm=3.3,
            available_widths_mm=(600, 900, 1200),
        )
        assert w.available_widths_mm == (600, 900, 1200)
        assert w.max_length_mm == 4100


# ══════════════════════════════════════════════════════════════════
# 2. Protocol conformance
# ══════════════════════════════════════════════════════════════════


class FakeCatalog:
    """Minimal fake for protocol conformance testing."""

    def __init__(self):
        self._variants: dict[str, VariantInfo] = {}
        self._edges: dict[str, EdgeInfo] = {}

    def add_variant(self, v: VariantInfo):
        self._variants[v.code] = v

    def add_edge(self, e: EdgeInfo):
        self._edges[e.code] = e

    def get_variant(self, code: str):
        return self._variants.get(code)

    def get_edge(self, code: str):
        return self._edges.get(code)

    def find_worktops(self, decor_code: str):
        return []

    def find_edges_for_variant(self, variant_code: str):
        return []


class TestProtocolConformance:
    def test_fake_catalog_is_material_catalog(self):
        fake = FakeCatalog()
        assert isinstance(fake, Protocol)

    def test_sqlite_catalog_is_material_catalog(self, catalog):
        assert isinstance(catalog, Protocol)

    def test_resolver_accepts_fake(self):
        fake = FakeCatalog()
        fake.add_variant(VariantInfo(
            code="X", decor_code="D", decor_name="N", producer="P",
            material_type="M", structure="S", thickness_mm=18.0,
        ))
        resolver = MaterialResolver(fake)
        result = resolver.resolve("X")
        assert result.thickness_mm == 18.0


# ══════════════════════════════════════════════════════════════════
# 3. SqliteMaterialCatalog
# ══════════════════════════════════════════════════════════════════


class TestSqliteCatalog:
    def test_get_variant_k8685(self, catalog):
        v = catalog.get_variant("K8685-CH-18-SM")
        assert v is not None
        assert v.code == "K8685-CH-18-SM"
        assert v.decor_code == "K8685"
        assert v.decor_name == "Biel Alpejska"
        assert v.producer == "kronospan"
        assert v.material_type == "chipboard"
        assert v.structure == "SM"
        assert v.thickness_mm == 18.0

    def test_get_variant_roles(self, catalog):
        v = catalog.get_variant("K8685-CH-18-SM")
        assert v is not None
        assert "front" in v.roles
        assert "carcass" in v.roles

    def test_get_variant_not_found(self, catalog):
        assert catalog.get_variant("NONEXISTENT") is None

    def test_find_worktops_for_868s(self, catalog):
        worktops = catalog.find_worktops("868S")
        assert len(worktops) >= 1
        w = worktops[0]
        assert w.construction == "postformed"
        assert w.profile == "U"
        assert 600 in w.available_widths_mm

    def test_find_worktops_empty(self, catalog):
        assert catalog.find_worktops("NONEXISTENT") == []

    def test_nonexistent_db_raises(self, tmp_path):
        repo = SqliteMaterialCatalog(tmp_path / "ghost.db")
        with pytest.raises(CatalogUnavailableError):
            repo.get_variant("X")


# ══════════════════════════════════════════════════════════════════
# 4. MaterialResolver
# ══════════════════════════════════════════════════════════════════


class TestResolver:
    def test_resolve_returns_variant(self, resolver):
        v = resolver.resolve("K8685-CH-18-SM")
        assert v.thickness_mm == 18.0

    def test_resolve_raises_on_missing(self, resolver):
        with pytest.raises(MaterialNotFoundError) as exc_info:
            resolver.resolve("GHOST")
        assert "GHOST" in str(exc_info.value)

    def test_try_resolve_returns_none(self, resolver):
        assert resolver.try_resolve("GHOST") is None

    def test_cache_hit(self, resolver):
        resolver.resolve("K8685-CH-18-SM")
        resolver.resolve("K8685-CH-18-SM")  # second call — cache hit
        assert resolver.cache_stats["variants"] == 1

    def test_cache_multiple(self, resolver):
        resolver.resolve("K8685-CH-18-SM")
        resolver.resolve("K190-CH-18-PE")
        assert resolver.cache_stats["variants"] == 2

    def test_clear_cache(self, resolver):
        resolver.resolve("K8685-CH-18-SM")
        resolver.clear_cache()
        assert resolver.cache_stats["variants"] == 0

    def test_resolve_worktops(self, resolver):
        worktops = resolver.resolve_worktops("868S")
        assert len(worktops) >= 1

    def test_resolve_worktops_cached(self, resolver):
        resolver.resolve_worktops("868S")
        resolver.resolve_worktops("868S")
        assert resolver.cache_stats["worktops"] == 1


# ══════════════════════════════════════════════════════════════════
# 5. Integration — real data from YAML → SQLite → resolver
# ══════════════════════════════════════════════════════════════════


class TestIntegration:
    """End-to-end: YAML → import → SQLite → resolver → DTOs."""

    def test_k8685_full_resolution(self, resolver):
        v = resolver.resolve("K8685-CH-18-SM")
        assert v.decor_code == "K8685"
        assert v.decor_name == "Biel Alpejska"
        assert v.producer == "kronospan"
        assert v.material_type == "chipboard"
        assert v.structure == "SM"
        assert v.thickness_mm == 18.0
        assert "front" in v.roles
        assert "carcass" in v.roles
        assert v.hpl_available is True

    def test_k190_full_resolution(self, resolver):
        v = resolver.resolve("K190-CH-18-PE")
        assert v.decor_code == "K190"
        assert v.decor_name == "Czarny"
        assert v.structure == "PE"
        assert v.thickness_mm == 18.0

    def test_postformed_worktop_868s(self, resolver):
        worktops = resolver.resolve_worktops("868S")
        assert len(worktops) >= 1
        w = worktops[0]
        assert w.variant_code == "868S-PF-U-600"
        assert w.construction == "postformed"
        assert w.profile == "U"
        assert w.edge_radius_mm == 3.3
        assert w.edge_material == "Unoflex"
        assert 600 in w.available_widths_mm

    def test_slim_line_worktop_k749(self, resolver):
        worktops = resolver.resolve_worktops("K749")
        assert len(worktops) >= 1
        w = worktops[0]
        assert w.construction == "slim_line"
        assert w.profile == "NATURAL"
        assert w.edge_radius_mm == 0
        assert w.core_color == "Beżowy"

    def test_resolver_with_fake_catalog(self):
        """Engine tests can use FakeCatalog — no SQLite needed."""
        fake = FakeCatalog()
        fake.add_variant(VariantInfo(
            code="TEST-18", decor_code="TEST", decor_name="Test",
            producer="test", material_type="chipboard",
            structure="SM", thickness_mm=18.0,
            roles=("front", "carcass"),
        ))
        resolver = MaterialResolver(fake)
        v = resolver.resolve("TEST-18")
        assert v.thickness_mm == 18.0
        assert "front" in v.roles
