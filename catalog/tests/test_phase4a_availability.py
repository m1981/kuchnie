"""Tests for Phase 4a: Variant Availability.

Covers:
    1. Schema integrity — table, indexes, view
    2. Constraints — CHECK on channel, UNIQUE(variant_id, channel)
    3. Real-world inserts — Kronospan Express 24h, Konfekcja
    4. KronoSwiss standard delivery
    5. Import integration — YAML availability section
    6. Discovery queries — "which variants are Express?"
"""

import sqlite3

import pytest


class TestSchemaIntegrity:
    """Phase 4a additions must exist."""

    def test_variant_availability_table_exists(self, db):
        tables = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "variant_availability" in tables

    def test_indexes_exist(self, db):
        indexes = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='variant_availability'"
            ).fetchall()
        }
        assert "idx_variant_availability_variant" in indexes
        assert "idx_variant_availability_channel" in indexes

    def test_view_exists(self, db):
        views = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()
        }
        assert "v_variants_availability" in views


class TestConstraints:
    """Domain validation at DB level."""

    def _make_variant(self, db, suffix="V1"):
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
        return cur.lastrowid

    def test_check_rejects_invalid_channel(self, db):
        vid = self._make_variant(db)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO variant_availability "
                "(variant_id, channel) VALUES (?, 'overnight')",
                (vid,),
            )

    def test_check_accepts_all_valid_channels(self, db):
        vid = self._make_variant(db, "V-all")
        for ch in ("express_24h", "konfekcja", "standard", "on_request"):
            db.execute(
                "INSERT INTO variant_availability "
                "(variant_id, channel) VALUES (?, ?)",
                (vid, ch),
            )
        db.commit()
        count = db.execute(
            "SELECT COUNT(*) FROM variant_availability "
            "WHERE variant_id = ?", (vid,)
        ).fetchone()[0]
        assert count == 4

    def test_unique_per_variant_channel(self, db):
        vid = self._make_variant(db, "V-uniq")
        db.execute(
            "INSERT INTO variant_availability "
            "(variant_id, channel) VALUES (?, 'express_24h')",
            (vid,),
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO variant_availability "
                "(variant_id, channel) VALUES (?, 'express_24h')",
                (vid,),
            )

    def test_cascade_delete_on_variant(self, db):
        vid = self._make_variant(db, "V-del")
        db.execute(
            "INSERT INTO variant_availability "
            "(variant_id, channel) VALUES (?, 'standard')",
            (vid,),
        )
        db.commit()
        db.execute("DELETE FROM variants WHERE id = ?", (vid,))
        db.commit()
        count = db.execute(
            "SELECT COUNT(*) FROM variant_availability "
            "WHERE variant_id = ?", (vid,)
        ).fetchone()[0]
        assert count == 0


class TestKronospanExpress:
    """Kronospan Global Collection Express 24h availability.

    Source: global-collection.md — EX flag on most decors.
    Warehouse: Mielec (main Kronospan Poland plant).
    """

    @pytest.fixture(autouse=True)
    def do_import(self, db):
        from scripts.importer import CatalogImporter, load_yaml
        from pathlib import Path

        yaml_path = (
            Path(__file__).resolve().parent.parent / "data" / "kronospan_full.yaml"
        )
        data = load_yaml(yaml_path)
        self.db = db
        self.importer = CatalogImporter(db)
        self.stats = self.importer.import_all(data)

    def test_availability_count(self):
        n = self.db.execute(
            "SELECT COUNT(*) FROM variant_availability"
        ).fetchone()[0]
        assert n >= 10

    def test_express_variants_from_mielec(self):
        rows = self.db.execute(
            "SELECT v.business_id, va.warehouse, va.lead_time "
            "FROM variant_availability va "
            "JOIN variants v ON v.id = va.variant_id "
            "WHERE va.channel = 'express_24h'"
        ).fetchall()
        assert len(rows) >= 7
        warehouses = {r["warehouse"] for r in rows}
        assert "Mielec" in warehouses

    def test_k8685_has_express_and_konfekcja(self):
        rows = self.db.execute(
            "SELECT va.channel FROM variant_availability va "
            "JOIN variants v ON v.id = va.variant_id "
            "WHERE v.business_id = 'K8685-CH-18-SM'"
        ).fetchall()
        channels = {r["channel"] for r in rows}
        assert "express_24h" in channels
        assert "konfekcja" in channels

    def test_postformed_868s_has_express(self):
        row = self.db.execute(
            "SELECT va.channel, va.warehouse, va.lead_time "
            "FROM variant_availability va "
            "JOIN variants v ON v.id = va.variant_id "
            "WHERE v.business_id = '868S-PF-U-600' "
            "AND va.channel = 'express_24h'"
        ).fetchone()
        assert row is not None
        assert row["warehouse"] == "Mielec"
        assert row["lead_time"] == "24h"

    def test_view_shows_express_variants(self):
        rows = self.db.execute(
            "SELECT variant_id, warehouse, lead_time "
            "FROM v_variants_availability "
            "WHERE channel = 'express_24h'"
        ).fetchall()
        assert len(rows) >= 7


class TestKronoSwissStandard:
    """KronoSwiss standard delivery availability.

    Source: kronoswiss_spec.md — no EX flag, standard delivery from Żary.
    """

    @pytest.fixture(autouse=True)
    def do_import(self, db):
        from scripts.importer import CatalogImporter, load_yaml
        from pathlib import Path

        yaml_path = (
            Path(__file__).resolve().parent.parent / "data" / "kronoswiss_full.yaml"
        )
        data = load_yaml(yaml_path)
        self.db = db
        self.importer = CatalogImporter(db)
        self.stats = self.importer.import_all(data)

    def test_availability_count(self):
        n = self.db.execute(
            "SELECT COUNT(*) FROM variant_availability"
        ).fetchone()[0]
        assert n >= 4

    def test_standard_delivery_from_zary(self):
        rows = self.db.execute(
            "SELECT v.business_id, va.warehouse, va.lead_time "
            "FROM variant_availability va "
            "JOIN variants v ON v.id = va.variant_id "
            "WHERE va.channel = 'standard'"
        ).fetchall()
        assert len(rows) >= 4
        warehouses = {r["warehouse"] for r in rows}
        assert "Żary" in warehouses

    def test_u190_board_has_standard(self):
        row = self.db.execute(
            "SELECT va.channel, va.warehouse, va.lead_time "
            "FROM variant_availability va "
            "JOIN variants v ON v.id = va.variant_id "
            "WHERE v.business_id = 'U190-CH-18-VL' "
            "AND va.channel = 'standard'"
        ).fetchone()
        assert row is not None
        assert row["warehouse"] == "Żary"
        assert row["lead_time"] == "7d"

    def test_no_express_for_kronoswiss(self):
        """KronoSwiss catalog doesn't have Express 24h flag."""
        rows = self.db.execute(
            "SELECT COUNT(*) FROM variant_availability "
            "WHERE channel = 'express_24h'"
        ).fetchone()[0]
        assert rows == 0


class TestImportIntegration:
    """Availability section imported via CatalogImporter.import_all()."""

    def test_availability_in_stats(self, db):
        from scripts.importer import CatalogImporter, load_yaml
        from pathlib import Path

        yaml_path = (
            Path(__file__).resolve().parent.parent / "data" / "kronospan_full.yaml"
        )
        data = load_yaml(yaml_path)
        importer = CatalogImporter(db)
        stats = importer.import_all(data)
        assert stats.availability >= 10

    def test_availability_idempotent(self, db):
        from scripts.importer import CatalogImporter, load_yaml
        from pathlib import Path

        yaml_path = (
            Path(__file__).resolve().parent.parent / "data" / "kronospan_full.yaml"
        )
        data = load_yaml(yaml_path)
        importer = CatalogImporter(db)
        importer.import_all(data)
        before = db.execute(
            "SELECT COUNT(*) FROM variant_availability"
        ).fetchone()[0]
        importer.import_all(data)
        after = db.execute(
            "SELECT COUNT(*) FROM variant_availability"
        ).fetchone()[0]
        assert before == after


class TestDiscoveryQueries:
    """Business queries on availability data."""

    @pytest.fixture(autouse=True)
    def do_import(self, db):
        from scripts.importer import CatalogImporter, load_yaml
        from pathlib import Path

        yaml_path = (
            Path(__file__).resolve().parent.parent / "data" / "kronospan_full.yaml"
        )
        data = load_yaml(yaml_path)
        self.db = db
        CatalogImporter(db).import_all(data)

    def test_which_variants_are_express(self):
        """Query: show me all Express 24h variants."""
        rows = self.db.execute(
            "SELECT variant_id, decor_name, material_type, "
            "       thickness_mm, warehouse "
            "FROM v_variants_availability "
            "WHERE channel = 'express_24h' "
            "ORDER BY thickness_mm"
        ).fetchall()
        assert len(rows) >= 7
        # Should include both chipboard (12/16/18mm) and worktop (38mm) and slim (12mm)
        thicknesses = {r["thickness_mm"] for r in rows}
        assert 18.0 in thicknesses  # chipboard
        assert 38.0 in thicknesses  # postformed
        assert 12.0 in thicknesses  # slim

    def test_which_variants_have_konfekcja(self):
        """Query: show me all variants with konfekcja (small quantities)."""
        rows = self.db.execute(
            "SELECT variant_id, decor_id "
            "FROM v_variants_availability "
            "WHERE channel = 'konfekcja'"
        ).fetchall()
        assert len(rows) >= 2

    def test_variant_with_multiple_channels(self):
        """Query: which variants have both Express and Konfekcja?"""
        rows = self.db.execute(
            "SELECT v.business_id, COUNT(*) AS channels "
            "FROM variant_availability va "
            "JOIN variants v ON v.id = va.variant_id "
            "GROUP BY v.business_id "
            "HAVING channels >= 2"
        ).fetchall()
        ids = {r["business_id"] for r in rows}
        assert "K8685-CH-18-SM" in ids  # has express + konfekcja
