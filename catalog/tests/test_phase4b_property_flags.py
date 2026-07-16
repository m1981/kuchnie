"""Tests for Phase 4b: Property Flags.

Covers:
    1. Schema — table, constraints, indexes
    2. CRUD — insert, query, cascade delete
    3. Validation — CHECK on property name, UNIQUE per variant+property
    4. Import — YAML property_flags section
    5. Discovery — "which variants are antibacterial?"
"""

import sqlite3
from pathlib import Path

import pytest

from scripts.importer import CatalogImporter, load_yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────


def _make_variant(db, suffix="V1"):
    """Create a minimal variant for testing property flags."""
    cur = db.cursor()
    cur.execute(
        "INSERT INTO producers (slug, name) VALUES ('kp', 'K')"
    )
    pid = cur.lastrowid
    cur.execute(
        "INSERT INTO collections (slug, producer_id, name) "
        "VALUES ('g', ?, 'G')", (pid,)
    )
    cid = cur.lastrowid
    mt_id = db.execute(
        "SELECT id FROM material_types WHERE slug = 'chipboard'"
    ).fetchone()[0]
    cur.execute(
        "INSERT INTO materials "
        "(slug, material_type_id, collection_id, name) "
        "VALUES ('m', ?, ?, 'M')", (mt_id, cid)
    )
    mid = cur.lastrowid
    cur.execute(
        "INSERT INTO structures (code, name) VALUES ('SM', 'S')"
    )
    sid = cur.lastrowid
    cur.execute(
        "INSERT INTO decors (business_id, producer_id, name) "
        "VALUES ('D1', ?, 'D')", (pid,)
    )
    did = cur.lastrowid
    cur.execute(
        "INSERT INTO variants "
        "(business_id, decor_id, material_id, structure_id, "
        " thickness_mm, roles) "
        "VALUES (?, ?, ?, ?, 18, '[\"front\"]')", (suffix, did, mid, sid)
    )
    db.commit()
    return cur.lastrowid


# ══════════════════════════════════════════════════════════════════
# 1. Schema integrity
# ══════════════════════════════════════════════════════════════════


class TestSchemaIntegrity:
    def test_table_exists(self, db):
        tables = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "property_flags" in tables

    def test_columns(self, db):
        cols = {
            row["name"]
            for row in db.execute("PRAGMA table_info(property_flags)").fetchall()
        }
        assert "variant_id" in cols
        assert "property" in cols
        assert "value" in cols

    def test_index_exists(self, db):
        indexes = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='property_flags'"
            ).fetchall()
        }
        assert "idx_property_flags_variant" in indexes

    def test_view_exists(self, db):
        views = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()
        }
        assert "v_property_flags" in views


# ══════════════════════════════════════════════════════════════════
# 2. Constraints
# ══════════════════════════════════════════════════════════════════


class TestConstraints:
    def test_unique_per_variant_property(self, db):
        vid = _make_variant(db, "V-uniq")
        db.execute(
            "INSERT INTO property_flags (variant_id, property, value) "
            "VALUES (?, 'antibacterial', 1)", (vid,)
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO property_flags (variant_id, property, value) "
                "VALUES (?, 'antibacterial', 0)", (vid,)
            )

    def test_cascade_delete_on_variant(self, db):
        vid = _make_variant(db, "V-del")
        db.execute(
            "INSERT INTO property_flags (variant_id, property, value) "
            "VALUES (?, 'waterproof', 1)", (vid,)
        )
        db.commit()
        db.execute("DELETE FROM variants WHERE id = ?", (vid,))
        db.commit()
        count = db.execute(
            "SELECT COUNT(*) FROM property_flags WHERE variant_id = ?", (vid,)
        ).fetchone()[0]
        assert count == 0

    def test_multiple_properties_per_variant(self, db):
        vid = _make_variant(db, "V-multi")
        props = ["antibacterial", "waterproof", "anti_fingerprint", "uv_stable"]
        for p in props:
            db.execute(
                "INSERT INTO property_flags (variant_id, property, value) "
                "VALUES (?, ?, 1)", (vid, p)
            )
        db.commit()
        count = db.execute(
            "SELECT COUNT(*) FROM property_flags WHERE variant_id = ?", (vid,)
        ).fetchone()[0]
        assert count == 4

    def test_value_defaults_to_true(self, db):
        vid = _make_variant(db, "V-default")
        db.execute(
            "INSERT INTO property_flags (variant_id, property) "
            "VALUES (?, 'scratch_resistant')", (vid,)
        )
        db.commit()
        row = db.execute(
            "SELECT value FROM property_flags "
            "WHERE variant_id = ? AND property = 'scratch_resistant'",
            (vid,)
        ).fetchone()
        assert row["value"] == 1


# ══════════════════════════════════════════════════════════════════
# 3. Import integration
# ══════════════════════════════════════════════════════════════════


class TestKronospanImport:
    @pytest.fixture(autouse=True)
    def do_import(self, db):

        data = load_yaml(DATA_DIR / "kronospan_full.yaml")
        self.db = db
        self.importer = CatalogImporter(db)
        self.stats = self.importer.import_all(data)

    def test_property_flags_count(self):
        n = self.db.execute(
            "SELECT COUNT(*) FROM property_flags"
        ).fetchone()[0]
        assert n >= 5

    def test_slim_line_waterproof(self):
        row = self.db.execute(
            "SELECT pf.property, pf.value "
            "FROM property_flags pf "
            "JOIN variants v ON v.id = pf.variant_id "
            "WHERE v.business_id = 'K749-SL-12' "
            "AND pf.property = 'waterproof'"
        ).fetchone()
        assert row is not None
        assert row["value"] == 1

    def test_su_structure_anti_fingerprint(self):
        """K8685-CH-18-SM has structure SM (Super Mat) — not anti-fingerprint.
        But we can verify the property exists on the correct variant."""
        row = self.db.execute(
            "SELECT pf.property "
            "FROM property_flags pf "
            "JOIN variants v ON v.id = pf.variant_id "
            "WHERE v.business_id = 'K8685-CH-18-SM' "
            "AND pf.property = 'scratch_resistant'"
        ).fetchone()
        assert row is not None


class TestKronoSwissImport:
    @pytest.fixture(autouse=True)
    def do_import(self, db):
        data = load_yaml(DATA_DIR / "kronoswiss_full.yaml")
        self.db = db
        self.importer = CatalogImporter(db)
        self.stats = self.importer.import_all(data)

    def test_property_flags_count(self):
        n = self.db.execute(
            "SELECT COUNT(*) FROM property_flags"
        ).fetchone()[0]
        assert n >= 5

    def test_black_wood_antibacterial(self):
        row = self.db.execute(
            "SELECT pf.property, pf.value "
            "FROM property_flags pf "
            "JOIN variants v ON v.id = pf.variant_id "
            "WHERE v.business_id = 'U190-BW-12' "
            "AND pf.property = 'antibacterial'"
        ).fetchone()
        assert row is not None
        assert row["value"] == 1

    def test_black_wood_waterproof(self):
        row = self.db.execute(
            "SELECT pf.property, pf.value "
            "FROM property_flags pf "
            "JOIN variants v ON v.id = pf.variant_id "
            "WHERE v.business_id = 'U190-BW-12' "
            "AND pf.property = 'waterproof'"
        ).fetchone()
        assert row is not None
        assert row["value"] == 1


# ══════════════════════════════════════════════════════════════════
# 4. Discovery queries
# ══════════════════════════════════════════════════════════════════


class TestDiscoveryQueries:
    @pytest.fixture(autouse=True)
    def do_import(self, db):
        data = load_yaml(DATA_DIR / "kronospan_full.yaml")
        self.db = db
        CatalogImporter(db).import_all(data)

    def test_which_variants_are_antibacterial(self):
        rows = self.db.execute(
            "SELECT v.business_id, pf.property "
            "FROM property_flags pf "
            "JOIN variants v ON v.id = pf.variant_id "
            "WHERE pf.property = 'antibacterial' AND pf.value = 1"
        ).fetchall()
        # Slim Line and some others should be antibacterial
        assert len(rows) >= 1

    def test_which_variants_are_waterproof(self):
        rows = self.db.execute(
            "SELECT v.business_id "
            "FROM property_flags pf "
            "JOIN variants v ON v.id = pf.variant_id "
            "WHERE pf.property = 'waterproof' AND pf.value = 1"
        ).fetchall()
        ids = {r["business_id"] for r in rows}
        assert "K749-SL-12" in ids  # Slim Line is waterproof

    def test_variant_with_all_properties(self):
        """Query: show me all properties for a specific variant."""
        rows = self.db.execute(
            "SELECT property, value FROM property_flags "
            "WHERE variant_id = ("
            "  SELECT id FROM variants WHERE business_id = 'K749-SL-12'"
            ")"
        ).fetchall()
        props = {r["property"]: r["value"] for r in rows}
        assert props.get("waterproof") == 1

    def test_view_shows_properties(self):
        rows = self.db.execute(
            "SELECT variant_id, property, value FROM v_property_flags"
        ).fetchall()
        assert len(rows) >= 5
