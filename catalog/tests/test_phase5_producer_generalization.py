"""Phase 5 — producer generalization (schema 1.5.0, ADR-004).

Verifies:
  1. pairing_types is seeded and enforced by FK (no more CHECK enum)
  2. A new producer-specific pairing type is an INSERT, not a rebuild
  3. decors no longer carries one_global / new_2024 columns
  4. v_decors_full recomputes both flags from decor_tags (API unchanged)
  5. variants.producer_sku is unique when present, NULLs unrestricted
"""

from __future__ import annotations

import sqlite3

import pytest


def _decor_id(db, business_id: str) -> int:
    return db.execute(
        "SELECT id FROM decors WHERE business_id = ?", (business_id,)
    ).fetchone()[0]


class TestPairingTypes:
    def test_seeded_types_present(self, db):
        slugs = {r["slug"] for r in db.execute("SELECT slug FROM pairing_types")}
        assert {"carcass", "worktop", "kronoart", "black_wood"} <= slugs
        assert len(slugs) == 11

    def test_branded_types_carry_producer_hint(self, db):
        row = db.execute(
            "SELECT producer_hint FROM pairing_types WHERE slug = 'kronoart'"
        ).fetchone()
        assert row["producer_hint"] == "kronospan"

    def test_unknown_pairing_type_rejected_by_fk(self, db_with_kronospan):
        db = db_with_kronospan
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO pairings "
                "(front_decor_id, target_decor_id, pairing_type, match_type) "
                "VALUES (?, ?, 'no_such_type', 'exact')",
                (_decor_id(db, "K8685"), _decor_id(db, "K190")),
            )

    def test_new_producer_type_is_an_insert(self, db_with_kronospan):
        """Adding an Egger-branded pairing type must not need a rebuild."""
        db = db_with_kronospan
        db.execute(
            "INSERT INTO pairing_types (slug, name, producer_hint) "
            "VALUES ('perfectsense', 'PerfectSense', 'egger')"
        )
        db.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type) "
            "VALUES (?, ?, 'perfectsense', 'exact')",
            (_decor_id(db, "K8685"), _decor_id(db, "K190")),
        )
        row = db.execute(
            "SELECT pairing_type FROM v_pairings_full "
            "WHERE front_decor_id = 'K8685'"
        ).fetchone()
        assert row["pairing_type"] == "perfectsense"


class TestCollectionFlagsAsTags:
    def test_decors_has_no_flag_columns(self, db):
        cols = {r["name"] for r in db.execute("PRAGMA table_info(decors)")}
        assert "one_global" not in cols
        assert "new_2024" not in cols
        assert "discontinued" in cols  # lifecycle fact, stays a column

    def test_view_computes_flags_from_tags(self, db_with_kronospan):
        db = db_with_kronospan
        material_id = db.execute(
            "SELECT id FROM materials WHERE slug = 'kronospan-chipboard-global'"
        ).fetchone()[0]
        db.execute(
            "INSERT INTO variants (business_id, decor_id, material_id) "
            "VALUES ('K8685-CH-18', ?, ?)",
            (_decor_id(db, "K8685"), material_id),
        )
        db.execute(
            "INSERT INTO decor_tags (decor_id, tag_id) "
            "SELECT ?, id FROM tags WHERE slug = 'one-global'",
            (_decor_id(db, "K8685"),),
        )
        row = db.execute(
            "SELECT one_global, new_2024 FROM v_decors_full "
            "WHERE decor_id = 'K8685'"
        ).fetchone()
        assert row["one_global"] == 1
        assert row["new_2024"] == 0


class TestProducerSku:
    def _insert_variant(self, db, business_id: str, sku):
        material_id = db.execute(
            "SELECT id FROM materials WHERE slug = 'kronospan-chipboard-global'"
        ).fetchone()[0]
        db.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, producer_sku) "
            "VALUES (?, ?, ?, ?)",
            (business_id, _decor_id(db, "K8685"), material_id, sku),
        )

    def test_duplicate_sku_rejected(self, db_with_kronospan):
        db = db_with_kronospan
        self._insert_variant(db, "V1", "EGG-123456")
        with pytest.raises(sqlite3.IntegrityError):
            self._insert_variant(db, "V2", "EGG-123456")

    def test_null_sku_unrestricted(self, db_with_kronospan):
        db = db_with_kronospan
        self._insert_variant(db, "V1", None)
        self._insert_variant(db, "V2", None)  # no unique violation
        n = db.execute(
            "SELECT COUNT(*) FROM variants WHERE producer_sku IS NULL"
        ).fetchone()[0]
        assert n == 2
