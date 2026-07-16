"""Tests for full catalog imports — Kronospan and Swiss Krono.

These tests validate that the generated YAML files (from markdown analysis)
import correctly into the SQLite catalog database.

Each test:
    1. Loads the YAML file
    2. Runs CatalogImporter.import_all()
    3. Asserts row counts match expectations
    4. Runs real discovery queries to prove the data is usable

Sources:
    - kronospan_full.yaml  ← generate_kronospan_yaml.py
    - kronoswiss_full.yaml ← generate_kronoswiss_yaml.py
"""

import json
from pathlib import Path

import pytest

from scripts.importer import CatalogImporter, load_yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

KRONOSPAN_YAML = DATA_DIR / "kronospan_full.yaml"
KRONOSWISS_YAML = DATA_DIR / "kronoswiss_full.yaml"


# ──────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────


@pytest.fixture
def kronospan_data() -> dict:
    return load_yaml(KRONOSPAN_YAML)


@pytest.fixture
def kronoswiss_data() -> dict:
    return load_yaml(KRONOSWISS_YAML)


# ══════════════════════════════════════════════════════════════════
# 1. Kronospan — full import
# ══════════════════════════════════════════════════════════════════


class TestKronospanImport:
    """Import kronospan_full.yaml and verify."""

    @pytest.fixture(autouse=True)
    def do_import(self, db, kronospan_data):
        self.db = db
        self.importer = CatalogImporter(db)
        self.stats = self.importer.import_all(kronospan_data)

    # ── Row counts ───────────────────────────────────────────────

    def test_producer_count(self):
        assert self.db.execute("SELECT COUNT(*) FROM producers").fetchone()[0] == 1

    def test_structure_count(self):
        assert self.db.execute("SELECT COUNT(*) FROM structures").fetchone()[0] >= 20

    def test_collection_count(self):
        assert self.db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 4

    def test_material_count(self):
        assert self.db.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 4

    def test_decor_count(self):
        n = self.db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
        assert n >= 60, f"Expected >=60 decors, got {n}"

    def test_variant_count(self):
        n = self.db.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
        assert n >= 10

    def test_worktop_spec_count(self):
        n = self.db.execute("SELECT COUNT(*) FROM worktop_specs").fetchone()[0]
        assert n >= 5

    def test_decor_structure_count(self):
        n = self.db.execute(
            "SELECT COUNT(*) FROM decor_structures"
        ).fetchone()[0]
        assert n >= 60

    def test_pairing_count(self):
        n = self.db.execute("SELECT COUNT(*) FROM pairings").fetchone()[0]
        assert n >= 4

    # ── Key data points ──────────────────────────────────────────

    def test_k8685_exists(self):
        row = self.db.execute(
            "SELECT name, name_en FROM decors WHERE business_id = 'K8685'"
        ).fetchone()
        assert row["name"] == "Biel Alpejska"
        assert row["name_en"] == "Alpine White"

    def test_k8685_four_structures(self):
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

    def test_k190_three_structures(self):
        rows = self.db.execute(
            "SELECT s.code FROM decor_structures ds "
            "JOIN decors d ON d.id = ds.decor_id "
            "JOIN structures s ON s.id = ds.structure_id "
            "WHERE d.business_id = 'K190'"
        ).fetchall()
        codes = {r["code"] for r in rows}
        assert codes == {"PE", "PD", "PW"}

    def test_postformed_worktop_868S(self):
        row = self.db.execute(
            "SELECT wf.construction, wf.profile_code, wf.edge_material, "
            "       wf.available_widths_mm "
            "FROM v_worktops_full wf WHERE wf.decor_id = '868S'"
        ).fetchone()
        assert row is not None
        assert row["construction"] == "postformed"
        assert row["profile_code"] == "U"
        assert row["edge_material"] == "Unoflex"
        assert json.loads(row["available_widths_mm"]) == [600]

    def test_postformed_worktop_7045_uu(self):
        row = self.db.execute(
            "SELECT wf.construction, wf.profile_code, wf.available_widths_mm "
            "FROM v_worktops_full wf WHERE wf.decor_id = '7045'"
        ).fetchone()
        assert row["profile_code"] == "U"
        assert json.loads(row["available_widths_mm"]) == [600]

    def test_slim_line_worktop_k749(self):
        row = self.db.execute(
            "SELECT wf.construction, wf.profile_code, wf.core_color "
            "FROM v_worktops_full wf WHERE wf.decor_id = 'K749'"
        ).fetchone()
        assert row["construction"] == "slim_line"
        assert row["profile_code"] == "NATURAL"
        assert row["core_color"] == "Beżowy"

    def test_abs_square_edge_worktop(self):
        row = self.db.execute(
            "SELECT wf.construction, wf.profile_code, wf.edge_material "
            "FROM v_worktops_full wf WHERE wf.decor_id = 'K349'"
        ).fetchone()
        assert row["construction"] == "abs_square_edge"
        assert row["profile_code"] == "SQUARE"
        assert row["edge_material"] == "ABS 1.5mm"

    def test_pairing_k8685_to_868S_worktop(self):
        rows = self.db.execute(
            "SELECT vp.target_decor_id, vp.pairing_type, vp.match_type "
            "FROM v_pairings_full vp "
            "WHERE vp.front_decor_id = 'K8685' AND vp.pairing_type = 'worktop'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["target_decor_id"] == "868S"
        assert rows[0]["match_type"] == "exact"

    def test_pairing_k8685_acrylic(self):
        rows = self.db.execute(
            "SELECT vp.target_decor_id, vp.match_type "
            "FROM v_pairings_full vp "
            "WHERE vp.front_decor_id = 'K8685' AND vp.pairing_type = 'acrylic'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["target_decor_id"] == "K523"

    def test_hpl_available_variants(self):
        rows = self.db.execute(
            "SELECT business_id FROM variants WHERE hpl_available = 1"
        ).fetchall()
        ids = {r["business_id"] for r in rows}
        assert "K8685-CH-18-SM" in ids
        assert "868S-PF-U-600" in ids

    def test_multi_structures_preserved_on_variant(self):
        row = self.db.execute(
            "SELECT multi_structures FROM variants "
            "WHERE business_id = 'K8685-CH-18-SM'"
        ).fetchone()
        assert row["multi_structures"] == "BS, PD, PW"

    # ── Idempotency ──────────────────────────────────────────────

    def test_import_idempotent(self, db, kronospan_data):
        """Second import of same YAML must not duplicate rows."""
        before = db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
        self.importer.import_all(kronospan_data)
        after = db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
        assert before == after


# ══════════════════════════════════════════════════════════════════
# 2. Swiss Krono — full import
# ══════════════════════════════════════════════════════════════════


class TestKronoSwissImport:
    """Import kronoswiss_full.yaml and verify."""

    @pytest.fixture(autouse=True)
    def do_import(self, db, kronoswiss_data):
        self.db = db
        self.importer = CatalogImporter(db)
        self.stats = self.importer.import_all(kronoswiss_data)

    # ── Row counts ───────────────────────────────────────────────

    def test_producer_count(self):
        assert self.db.execute("SELECT COUNT(*) FROM producers").fetchone()[0] == 1

    def test_structure_count(self):
        n = self.db.execute("SELECT COUNT(*) FROM structures").fetchone()[0]
        assert n >= 20, f"Expected >=20 structures, got {n}"

    def test_collection_count(self):
        assert self.db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 3

    def test_material_count(self):
        assert self.db.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 3

    def test_decor_count(self):
        n = self.db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
        assert n >= 35, f"Expected >=35 decors, got {n}"

    def test_variant_count(self):
        n = self.db.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
        assert n >= 8

    def test_worktop_spec_count(self):
        n = self.db.execute("SELECT COUNT(*) FROM worktop_specs").fetchone()[0]
        assert n >= 5

    def test_decor_structure_count(self):
        n = self.db.execute(
            "SELECT COUNT(*) FROM decor_structures"
        ).fetchone()[0]
        assert n >= 35

    # ── Key data points ──────────────────────────────────────────

    def test_u190_black_wood_worktop(self):
        row = self.db.execute(
            "SELECT wf.construction, wf.profile_code, wf.edge_material "
            "FROM v_worktops_full wf WHERE wf.decor_id = 'U190' "
            "AND wf.construction = 'black_wood'"
        ).fetchone()
        assert row is not None
        assert row["construction"] == "black_wood"
        assert row["profile_code"] == "NATURAL"
        assert row["edge_material"] == "naturalna"

    def test_d3274_black_wood_worktop(self):
        row = self.db.execute(
            "SELECT wf.construction FROM v_worktops_full wf "
            "WHERE wf.decor_id = 'D3274'"
        ).fetchone()
        assert row["construction"] == "black_wood"

    def test_d3314_synchro_structure(self):
        """D3314 Dąb Giovanni should have SD (Synchro Dąb) structure."""
        row = self.db.execute(
            "SELECT v.business_id, s.code, s.synchronized_texture "
            "FROM variants v "
            "JOIN structures s ON s.id = v.structure_id "
            "WHERE v.business_id = 'D3314-CH-18-SD'"
        ).fetchone()
        assert row["code"] == "SD"
        assert row["synchronized_texture"] == 1

    def test_synchro_variants_view(self):
        rows = self.db.execute(
            "SELECT variant_id FROM v_synchro_variants"
        ).fetchall()
        ids = {r["variant_id"] for r in rows}
        assert "D3314-CH-18-SD" in ids
        assert "D3801-CH-18-CL" in ids

    def test_postformed_r3_worktop(self):
        row = self.db.execute(
            "SELECT wf.construction, wf.profile_code, wf.edge_material "
            "FROM v_worktops_full wf WHERE wf.decor_id = 'K101'"
        ).fetchone()
        assert row["construction"] == "postformed"
        assert row["profile_code"] == "R3"
        assert row["edge_material"] == "HPL"

    def test_one_global_flag(self):
        rows = self.db.execute(
            "SELECT d.business_id FROM decors d "
            "JOIN decor_tags dt ON dt.decor_id = d.id "
            "JOIN tags t ON t.id = dt.tag_id WHERE t.slug = 'one-global'"
        ).fetchall()
        ids = {r["business_id"] for r in rows}
        assert "U164" in ids  # Antracyt
        assert "U190" in ids  # Czarny
        assert "D4225" in ids  # Dąb Artisan
        assert "D3823" in ids  # Dąb Nowy Jork

    def test_discontinued_decors(self):
        rows = self.db.execute(
            "SELECT business_id FROM decors WHERE discontinued = 1"
        ).fetchall()
        ids = {r["business_id"] for r in rows}
        assert "D3193" in ids  # Wiąz Amsterdam
        assert "D3194" in ids  # Wiąz Allegro

    def test_new_2024_decors(self):
        rows = self.db.execute(
            "SELECT d.business_id FROM decors d "
            "JOIN decor_tags dt ON dt.decor_id = d.id "
            "JOIN tags t ON t.id = dt.tag_id WHERE t.slug = 'new-2024'"
        ).fetchall()
        ids = {r["business_id"] for r in rows}
        assert "D70060" in ids  # Terrazzo Fresco
        assert "D70601" in ids  # Calacatta Oro

    def test_pairing_black_wood(self):
        rows = self.db.execute(
            "SELECT vp.target_decor_id, vp.pairing_type "
            "FROM v_pairings_full vp "
            "WHERE vp.front_decor_id = 'U190' "
            "AND vp.pairing_type = 'black_wood'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["target_decor_id"] == "U190"

    def test_pairing_hpl_laminate(self):
        rows = self.db.execute(
            "SELECT vp.pairing_type FROM v_pairings_full vp "
            "WHERE vp.front_decor_id = 'U190' "
            "AND vp.pairing_type = 'hpl_laminate'"
        ).fetchall()
        assert len(rows) == 1

    # ── Idempotency ──────────────────────────────────────────────

    def test_import_idempotent(self, db, kronoswiss_data):
        before = db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
        self.importer.import_all(kronoswiss_data)
        after = db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
        assert before == after


# ══════════════════════════════════════════════════════════════════
# 3. Cross-catalog — same DB, different producers
# ══════════════════════════════════════════════════════════════════


class TestCrossCatalogImport:
    """Both catalogs into the same DB — producers must not clash."""

    @pytest.fixture(autouse=True)
    def do_both_imports(self, db, kronospan_data, kronoswiss_data):
        self.db = db
        importer = CatalogImporter(db)
        self.kp_stats = importer.import_all(kronospan_data)
        self.ks_stats = importer.import_all(kronoswiss_data)

    def test_two_producers_coexist(self):
        rows = self.db.execute(
            "SELECT slug FROM producers ORDER BY slug"
        ).fetchall()
        slugs = {r["slug"] for r in rows}
        assert slugs == {"kronospan", "swiss_krono"}

    def test_structures_scoped_by_producer(self):
        """Kronospan SM and KronoSwiss SM should be different rows."""
        rows = self.db.execute(
            "SELECT s.code, p.slug AS producer "
            "FROM structures s "
            "JOIN producers p ON p.id = s.producer_id "
            "WHERE s.code = 'SM'"
        ).fetchall()
        producers = {r["producer"] for r in rows}
        assert "kronospan" in producers
        assert "swiss_krono" in producers

    def test_total_decors_from_both(self):
        n = self.db.execute("SELECT COUNT(*) FROM decors").fetchone()[0]
        assert n >= 100, f"Expected >=100 total decors, got {n}"

    def test_no_variant_id_clashes(self):
        """Both catalogs should produce unique variant business_ids."""
        rows = self.db.execute(
            "SELECT business_id, COUNT(*) AS cnt "
            "FROM variants GROUP BY business_id HAVING cnt > 1"
        ).fetchall()
        assert len(rows) == 0, f"Duplicate variant IDs: {rows}"

    def test_total_worktop_specs(self):
        n = self.db.execute("SELECT COUNT(*) FROM worktop_specs").fetchone()[0]
        assert n >= 10
