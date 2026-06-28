"""Tests for Phase 3: Catalog Importer (YAML → SQLite).

Covers:
    1. ImportStats dataclass
    2. Individual import_*() methods — each entity type
    3. Full import_all() — end-to-end YAML → DB
    4. Idempotency — re-running import_all() on same data
    5. Validation — missing required fields raise ValueError
    6. FK resolution — nonexistent slugs raise ValueError
    7. Real-world queries — discovery queries against imported data
"""

import json
import sqlite3
from pathlib import Path

import pytest

# Import from scripts package (added to path in conftest or via sys.path)
from scripts.importer import CatalogImporter, ImportStats, load_yaml


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_YAML = DATA_DIR / "kronospan_sample.yaml"


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────


@pytest.fixture
def importer(db: sqlite3.Connection) -> CatalogImporter:
    return CatalogImporter(db)


@pytest.fixture
def sample_data() -> dict:
    return load_yaml(SAMPLE_YAML)


# ══════════════════════════════════════════════════════════════════
# 1. ImportStats
# ══════════════════════════════════════════════════════════════════


class TestImportStats:
    def test_total_sums_all_fields(self):
        stats = ImportStats(producers=1, structures=3, decors=5)
        assert stats.total() == 9

    def test_repr_shows_nonzero(self):
        stats = ImportStats(producers=1, decors=5)
        r = repr(stats)
        assert "producers=1" in r
        assert "decors=5" in r
        assert "structures=" not in r  # 0, should be omitted


# ══════════════════════════════════════════════════════════════════
# 2. Individual import methods
# ══════════════════════════════════════════════════════════════════


class TestImportProducers:
    def test_inserts_producer(self, importer, db):
        importer.import_producers([
            {"slug": "kp", "name": "Kronospan", "country": "PL"}
        ])
        db.commit()
        row = db.execute(
            "SELECT slug, name, country FROM producers WHERE slug = 'kp'"
        ).fetchone()
        assert row["slug"] == "kp"
        assert row["country"] == "PL"

    def test_idempotent(self, importer, db):
        importer.import_producers([{"slug": "x", "name": "X"}])
        importer.import_producers([{"slug": "x", "name": "X"}])
        db.commit()
        n = db.execute(
            "SELECT COUNT(*) FROM producers WHERE slug = 'x'"
        ).fetchone()[0]
        assert n == 1

    def test_missing_slug_raises(self, importer):
        with pytest.raises(ValueError, match="slug"):
            importer.import_producers([{"name": "X"}])


class TestImportStructures:
    def test_inserts_structure_with_producer(self, importer, db):
        importer.import_producers([
            {"slug": "kp", "name": "Kronospan"}
        ])
        importer.import_structures([{
            "code": "SM", "name": "Super Mat",
            "type": "smooth", "finish": "matt",
            "producer_slug": "kp",
        }])
        db.commit()
        row = db.execute(
            "SELECT code, producer_id FROM structures WHERE code = 'SM'"
        ).fetchone()
        assert row["code"] == "SM"
        assert row["producer_id"] is not None  # scoped to producer

    def test_inserts_structure_without_producer(self, importer, db):
        importer.import_structures([{
            "code": "MX", "name": "Matrix",
            "type": "structured", "finish": "matt"
        }])
        db.commit()
        row = db.execute(
            "SELECT code, producer_id FROM structures WHERE code = 'MX'"
        ).fetchone()
        assert row["producer_id"] is None  # shared


class TestImportCollections:
    def test_inserts_collection(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "Kronospan"}])
        importer.import_collections([{
            "slug": "global", "producer_slug": "kp",
            "name": "Global Collection 2026",
            "has_countertops": True, "has_express": True,
        }])
        db.commit()
        row = db.execute(
            "SELECT slug, has_countertops FROM collections "
            "WHERE slug = 'global'"
        ).fetchone()
        assert row["has_countertops"] == 1

    def test_missing_producer_raises(self, importer):
        with pytest.raises(ValueError, match="not found"):
            importer.import_collections([{
                "slug": "x", "producer_slug": "nonexistent",
                "name": "X"
            }])


class TestImportMaterials:
    def test_inserts_material(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_collections([{
            "slug": "g", "producer_slug": "kp", "name": "G"
        }])
        importer.import_materials([{
            "slug": "mat-1",
            "collection_slug": "g",
            "material_type_slug": "chipboard",
            "name": "Chipboard Global",
        }])
        db.commit()
        row = db.execute(
            "SELECT slug, name FROM materials WHERE slug = 'mat-1'"
        ).fetchone()
        assert row["name"] == "Chipboard Global"


class TestImportDecors:
    def test_inserts_decor(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_decors([{
            "business_id": "K8685",
            "producer_slug": "kp",
            "name": "Biel Alpejska",
            "name_en": "Alpine White",
            "group_name": "WHITE FRONT",
        }])
        db.commit()
        row = db.execute(
            "SELECT business_id, name, name_en FROM decors "
            "WHERE business_id = 'K8685'"
        ).fetchone()
        assert row["name_en"] == "Alpine White"

    def test_inserts_decor_with_flags(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_decors([{
            "business_id": "X1",
            "producer_slug": "kp",
            "name": "Test",
            "one_global": True,
            "new_2024": True,
            "discontinued": True,
        }])
        db.commit()
        row = db.execute(
            "SELECT one_global, new_2024, discontinued FROM decors "
            "WHERE business_id = 'X1'"
        ).fetchone()
        assert row["one_global"] == 1
        assert row["new_2024"] == 1
        assert row["discontinued"] == 1


class TestImportVariants:
    def test_inserts_variant(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_collections([{
            "slug": "g", "producer_slug": "kp", "name": "G"
        }])
        importer.import_materials([{
            "slug": "mat", "collection_slug": "g",
            "material_type_slug": "chipboard", "name": "M"
        }])
        importer.import_structures([{
            "code": "SM", "name": "Super Mat"
        }])
        importer.import_decors([{
            "business_id": "K8685", "producer_slug": "kp", "name": "B"
        }])
        importer.import_variants([{
            "business_id": "K8685-CH-18",
            "decor_code": "K8685",
            "material_slug": "mat",
            "structure_code": "SM",
            "thickness_mm": 18.0,
            "roles": ["front", "carcass"],
        }])
        db.commit()
        row = db.execute(
            "SELECT business_id, thickness_mm, roles FROM variants "
            "WHERE business_id = 'K8685-CH-18'"
        ).fetchone()
        assert row["thickness_mm"] == 18.0
        assert "front" in row["roles"]

    def test_roles_stored_as_json_array(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_collections([{
            "slug": "g", "producer_slug": "kp", "name": "G"
        }])
        importer.import_materials([{
            "slug": "mat", "collection_slug": "g",
            "material_type_slug": "chipboard", "name": "M"
        }])
        importer.import_structures([{"code": "SM", "name": "S"}])
        importer.import_decors([{
            "business_id": "D1", "producer_slug": "kp", "name": "D"
        }])
        importer.import_variants([{
            "business_id": "V1", "decor_code": "D1",
            "material_slug": "mat", "structure_code": "SM",
            "thickness_mm": 18.0,
            "roles": ["worktop"],
        }])
        db.commit()
        row = db.execute(
            "SELECT roles FROM variants WHERE business_id = 'V1'"
        ).fetchone()
        roles = json.loads(row["roles"])
        assert roles == ["worktop"]


class TestImportWorktops:
    def test_inserts_worktop_spec(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_collections([{
            "slug": "g", "producer_slug": "kp", "name": "G"
        }])
        importer.import_materials([{
            "slug": "mat", "collection_slug": "g",
            "material_type_slug": "worktop_postformed", "name": "W"
        }])
        importer.import_structures([{"code": "RS", "name": "R"}])
        importer.import_decors([{
            "business_id": "868S", "producer_slug": "kp", "name": "W"
        }])
        importer.import_variants([{
            "business_id": "868S-PF", "decor_code": "868S",
            "material_slug": "mat", "structure_code": "RS",
            "thickness_mm": 38.0, "roles": ["worktop"]
        }])
        importer.import_worktops([{
            "variant_business_id": "868S-PF",
            "construction_slug": "postformed",
            "profile_code": "U",
            "available_widths_mm": [600, 900],
            "edge_material": "Unoflex",
        }])
        db.commit()
        row = db.execute(
            "SELECT ws.available_widths_mm, wp.code AS profile "
            "FROM worktop_specs ws "
            "JOIN worktop_profiles wp ON wp.id = ws.profile_id "
            "JOIN variants v ON v.id = ws.variant_id "
            "WHERE v.business_id = '868S-PF'"
        ).fetchone()
        assert row["profile"] == "U"
        assert json.loads(row["available_widths_mm"]) == [600, 900]


class TestImportDecorStructures:
    def test_inserts_junction(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_structures([
            {"code": "SM", "name": "SM", "producer_slug": "kp"},
            {"code": "BS", "name": "BS", "producer_slug": "kp"},
        ])
        importer.import_decors([{
            "business_id": "K8685", "producer_slug": "kp", "name": "B"
        }])
        importer.import_decor_structures([
            {"decor_code": "K8685", "structure_code": "SM", "is_primary": True},
            {"decor_code": "K8685", "structure_code": "BS", "is_primary": False},
        ])
        db.commit()
        rows = db.execute(
            "SELECT s.code, ds.is_primary FROM decor_structures ds "
            "JOIN structures s ON s.id = ds.structure_id "
            "JOIN decors d ON d.id = ds.decor_id "
            "WHERE d.business_id = 'K8685'"
        ).fetchall()
        assert len(rows) == 2
        codes = {r["code"] for r in rows}
        assert codes == {"SM", "BS"}


class TestImportPairings:
    def test_inserts_pairing(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_decors([
            {"business_id": "K8685", "producer_slug": "kp", "name": "A"},
            {"business_id": "868S", "producer_slug": "kp", "name": "B"},
        ])
        importer.import_pairings([{
            "front_decor_code": "K8685",
            "target_decor_code": "868S",
            "pairing_type": "worktop",
            "match_type": "exact",
        }])
        db.commit()
        row = db.execute(
            "SELECT pairing_type, match_type FROM pairings "
            "WHERE front_decor_id = (SELECT id FROM decors WHERE business_id = 'K8685')"
        ).fetchone()
        assert row["pairing_type"] == "worktop"


# ══════════════════════════════════════════════════════════════════
# 3. Full import — end-to-end from YAML
# ══════════════════════════════════════════════════════════════════


class TestFullImport:
    """Import the kronospan_sample.yaml and verify counts + queries."""

    def test_full_import_counts(self, importer, sample_data, db):
        stats = importer.import_all(sample_data)

        assert stats.producers == 1
        assert stats.collections == 3
        assert stats.structures == 8
        assert stats.materials == 3
        assert stats.decors == 7
        assert stats.variants == 5
        assert stats.worktop_specs == 3
        assert stats.decor_structures == 8
        assert stats.pairings == 3

        # Verify actual row counts in DB
        assert db.execute("SELECT COUNT(*) FROM producers").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM structures").fetchone()[0] == 8
        assert db.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM decors").fetchone()[0] == 7
        assert db.execute("SELECT COUNT(*) FROM variants").fetchone()[0] == 5
        assert db.execute("SELECT COUNT(*) FROM worktop_specs").fetchone()[0] == 3
        assert db.execute(
            "SELECT COUNT(*) FROM decor_structures"
        ).fetchone()[0] == 8
        assert db.execute("SELECT COUNT(*) FROM pairings").fetchone()[0] == 3

    def test_full_import_idempotent(self, importer, sample_data, db):
        """Running import_all() twice must not duplicate rows."""
        importer.import_all(sample_data)
        importer.import_all(sample_data)

        assert db.execute("SELECT COUNT(*) FROM producers").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM structures").fetchone()[0] == 8
        assert db.execute("SELECT COUNT(*) FROM decors").fetchone()[0] == 7
        assert db.execute("SELECT COUNT(*) FROM variants").fetchone()[0] == 5
        assert db.execute("SELECT COUNT(*) FROM worktop_specs").fetchone()[0] == 3


# ══════════════════════════════════════════════════════════════════
# 4. Validation — error cases
# ══════════════════════════════════════════════════════════════════


class TestValidation:
    def test_missing_business_id_in_decors(self, importer):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        with pytest.raises(ValueError, match="business_id"):
            importer.import_decors([{"producer_slug": "kp", "name": "X"}])

    def test_missing_structure_code(self, importer):
        with pytest.raises(ValueError, match="code"):
            importer.import_structures([{"name": "X"}])

    def test_missing_collection_slug(self, importer):
        with pytest.raises(ValueError, match="collection_slug"):
            importer.import_materials([{
                "slug": "x",
                "material_type_slug": "chipboard",
                "name": "X",
            }])

    def test_nonexistent_producer_in_collection(self, importer):
        with pytest.raises(ValueError, match="not found"):
            importer.import_collections([{
                "slug": "x",
                "producer_slug": "ghost",
                "name": "X",
            }])

    def test_nonexistent_decor_in_variant(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_collections([{
            "slug": "g", "producer_slug": "kp", "name": "G"
        }])
        importer.import_materials([{
            "slug": "mat", "collection_slug": "g",
            "material_type_slug": "chipboard", "name": "M"
        }])
        importer.import_structures([{"code": "SM", "name": "S"}])
        with pytest.raises(ValueError, match="not found"):
            importer.import_variants([{
                "business_id": "V1", "decor_code": "GHOST",
                "material_slug": "mat", "structure_code": "SM",
                "thickness_mm": 18.0,
            }])

    def test_nonexistent_worktop_construction(self, importer, db):
        importer.import_producers([{"slug": "kp", "name": "K"}])
        importer.import_collections([{
            "slug": "g", "producer_slug": "kp", "name": "G"
        }])
        importer.import_materials([{
            "slug": "mat", "collection_slug": "g",
            "material_type_slug": "worktop_postformed", "name": "W"
        }])
        importer.import_structures([{"code": "RS", "name": "R"}])
        importer.import_decors([{
            "business_id": "D1", "producer_slug": "kp", "name": "D"
        }])
        importer.import_variants([{
            "business_id": "V1", "decor_code": "D1",
            "material_slug": "mat", "structure_code": "RS",
            "thickness_mm": 38.0, "roles": ["worktop"]
        }])
        with pytest.raises(ValueError, match="not found"):
            importer.import_worktops([{
                "variant_business_id": "V1",
                "construction_slug": "nonexistent_method",
                "profile_code": "U",
                "available_widths_mm": [600],
            }])


# ══════════════════════════════════════════════════════════════════
# 5. Real-world discovery queries on imported data
# ══════════════════════════════════════════════════════════════════


class TestDiscoveryQueries:
    """After full import, run real business queries against the data."""

    @pytest.fixture(autouse=True)
    def do_full_import(self, importer, sample_data, db):
        importer.import_all(sample_data)
        self.db = db

    def test_query_k8685_structures(self):
        rows = self.db.execute(
            "SELECT s.code, ds.is_primary "
            "FROM decor_structures ds "
            "JOIN decors d ON d.id = ds.decor_id "
            "JOIN structures s ON s.id = ds.structure_id "
            "WHERE d.business_id = 'K8685' "
            "ORDER BY ds.is_primary DESC"
        ).fetchall()
        assert len(rows) == 4
        assert rows[0]["code"] == "SM"
        assert rows[0]["is_primary"] == 1
        codes = {r["code"] for r in rows}
        assert codes == {"SM", "BS", "PD", "PW"}

    def test_query_k190_structures(self):
        rows = self.db.execute(
            "SELECT s.code FROM decor_structures ds "
            "JOIN decors d ON d.id = ds.decor_id "
            "JOIN structures s ON s.id = ds.structure_id "
            "WHERE d.business_id = 'K190'"
        ).fetchall()
        codes = {r["code"] for r in rows}
        assert codes == {"PE", "PD", "PW"}

    def test_query_worktops_for_k8685(self):
        rows = self.db.execute(
            "SELECT wf.variant_id, wf.construction, wf.profile_code, "
            "       wf.edge_material, wf.available_widths_mm "
            "FROM v_pairings_full vp "
            "JOIN v_worktops_full wf ON wf.decor_id = vp.target_decor_id "
            "WHERE vp.front_decor_id = 'K8685' AND vp.pairing_type = 'worktop'"
        ).fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row["construction"] == "postformed"
        assert row["profile_code"] == "U"
        assert row["edge_material"] == "Unoflex"
        assert json.loads(row["available_widths_mm"]) == [600]

    def test_query_slim_line_worktop_k749(self):
        rows = self.db.execute(
            "SELECT wf.construction, wf.profile_code, wf.core_color, "
            "       wf.edge_material "
            "FROM v_worktops_full wf "
            "WHERE wf.decor_id = 'K749'"
        ).fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row["construction"] == "slim_line"
        assert row["profile_code"] == "NATURAL"
        assert row["core_color"] == "Beżowy"

    def test_query_k8685_acrylic_pairing(self):
        rows = self.db.execute(
            "SELECT vp.target_decor_id, vp.match_type "
            "FROM v_pairings_full vp "
            "WHERE vp.front_decor_id = 'K8685' "
            "  AND vp.pairing_type = 'acrylic'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["target_decor_id"] == "K523"
        assert rows[0]["match_type"] == "close"

    def test_query_postformed_worktops_all(self):
        rows = self.db.execute(
            "SELECT wf.decor_name_pl, wf.profile_code, wf.available_widths_mm "
            "FROM v_worktops_full wf "
            "WHERE wf.construction = 'postformed'"
        ).fetchall()
        assert len(rows) == 2
        decors = {r["decor_name_pl"] for r in rows}
        assert decors == {"Biel Alpejska", "Szampański"}

    def test_query_discontinued_decors(self):
        # K091 in sample is discontinued=false, but let's verify the column works
        rows = self.db.execute(
            "SELECT business_id FROM decors WHERE discontinued = 1"
        ).fetchall()
        # In our sample, no decors are discontinued
        assert len(rows) == 0

    def test_query_hpl_available_decors(self):
        rows = self.db.execute(
            "SELECT v.business_id FROM variants v "
            "WHERE v.hpl_available = 1"
        ).fetchall()
        ids = {r["business_id"] for r in rows}
        assert "K8685-CH-18-SM" in ids
        assert "868S-PF-U-600" in ids
