"""Tests for Phase 2 migration: Decor-Structure Junction + Pairing Types.

Covers:
    1. Schema integrity — decor_structures table, expanded pairings CHECK
    2. Junction table correctness — M2M CRUD, composite PK, indexes
    3. Pairings expanded types — acrylic, mirror, hpl_laminate, etc.
    4. Kronospan real-world — K8685 SM/BS/PD/PW, K190 PE/PD/PW
    5. KronoSwiss real-world — synchronized texture structures
    6. End-to-end — full discovery flow: decor → structures → variants → pairings
    7. Backward compatibility — deprecated multi_structures column still works
"""

import sqlite3

import pytest


# ══════════════════════════════════════════════════════════════════
# 1. Schema integrity
# ══════════════════════════════════════════════════════════════════


class TestSchemaIntegrity:
    """Phase 2 additions must exist in the schema."""

    def test_decor_structures_table_exists(self, db: sqlite3.Connection):
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "decor_structures" in tables

    def test_decor_structures_has_composite_pk(self, db: sqlite3.Connection):
        """PK must be (decor_id, structure_id) — no surrogate id column."""
        cols = db.execute("PRAGMA table_info(decor_structures)").fetchall()
        col_names = [c[1] for c in cols]
        # Should NOT have a standalone 'id' column
        assert "id" not in col_names
        # Should have both FK columns
        assert "decor_id" in col_names
        assert "structure_id" in col_names
        assert "is_primary" in col_names

    def test_decor_structures_has_indexes(self, db: sqlite3.Connection):
        indexes = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='decor_structures'"
            ).fetchall()
        }
        assert "idx_decor_structures_structure" in indexes
        assert "idx_decor_structures_primary" in indexes

    def test_pairings_table_still_exists_after_swap(self, db: sqlite3.Connection):
        """The table swap (drop old + rename new) must leave pairings in place."""
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "pairings" in tables
        # pairings_new should NOT exist (was renamed)
        assert "pairings_new" not in tables

    def test_pairings_check_expanded(self, db: sqlite3.Connection):
        """New pairing types must be accepted by the CHECK constraint."""
        cur = db.cursor()
        # Two test decors needed for pairings FK
        cur.execute(
            "INSERT INTO producers (slug, name) VALUES ('test_prov', 'Test')"
        )
        pid = cur.lastrowid
        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) VALUES "
            "('D-A', ?, 'A'), ('D-B', ?, 'B')",
            (pid, pid),
        )
        a_id, b_id = cur.execute(
            "SELECT id FROM decors WHERE business_id IN ('D-A', 'D-B') "
            "ORDER BY business_id"
        ).fetchall()
        a_id, b_id = a_id[0], b_id[0]

        new_types = [
            "acrylic",
            "mirror",
            "compact",
            "hpl_laminate",
            "kronoart",
            "black_wood",
        ]
        for ptype in new_types:
            cur.execute(
                "INSERT INTO pairings "
                "(front_decor_id, target_decor_id, pairing_type, match_type) "
                "VALUES (?, ?, ?, 'exact')",
                (a_id, b_id, ptype),
            )
        db.commit()

        stored = {
            r[0]
            for r in cur.execute(
                "SELECT pairing_type FROM pairings "
                "WHERE front_decor_id = ?", (a_id,)
            ).fetchall()
        }
        assert set(new_types).issubset(stored)

    def test_pairings_rejects_unknown_type(self, db: sqlite3.Connection):
        cur = db.cursor()
        cur.execute(
            "INSERT INTO producers (slug, name) VALUES ('tp', 'T')"
        )
        pid = cur.lastrowid
        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) VALUES "
            "('X', ?, 'X'), ('Y', ?, 'Y')", (pid, pid)
        )
        ids = cur.execute(
            "SELECT id FROM decors WHERE business_id IN ('X','Y') ORDER BY business_id"
        ).fetchall()
        x_id, y_id = ids[0][0], ids[1][0]

        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                "INSERT INTO pairings "
                "(front_decor_id, target_decor_id, pairing_type, match_type) "
                "VALUES (?, ?, 'foobar_invalid', 'exact')",
                (x_id, y_id),
            )

    def test_pairings_indexes_survived_swap(self, db: sqlite3.Connection):
        indexes = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='pairings'"
            ).fetchall()
        }
        assert "idx_pairings_front" in indexes
        assert "idx_pairings_target" in indexes
        assert "idx_pairings_type" in indexes

    def test_v_decor_structures_full_view_exists(self, db: sqlite3.Connection):
        views = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()
        }
        assert "v_decor_structures_full" in views

    def test_v_pairings_full_view_exists(self, db: sqlite3.Connection):
        views = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()
        }
        assert "v_pairings_full" in views


# ══════════════════════════════════════════════════════════════════
# 2. Junction table — M2M CRUD
# ══════════════════════════════════════════════════════════════════


class TestDecorStructuresJunction:
    """Core M2M behaviour: insert, query, delete cascade."""

    def test_insert_and_query(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        decor_id = lookup("decors", "business_id", "K8685")
        sm_id = lookup("structures", "code", "SM")

        db.execute(
            "INSERT INTO decor_structures (decor_id, structure_id, is_primary) "
            "VALUES (?, ?, 1)",
            (decor_id, sm_id),
        )
        db.commit()

        row = db.execute(
            "SELECT is_primary FROM decor_structures "
            "WHERE decor_id = ? AND structure_id = ?",
            (decor_id, sm_id),
        ).fetchone()
        assert row["is_primary"] == 1

    def test_composite_pk_blocks_duplicate(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        decor_id = lookup("decors", "business_id", "K8685")
        sm_id = lookup("structures", "code", "SM")

        db.execute(
            "INSERT INTO decor_structures (decor_id, structure_id) "
            "VALUES (?, ?)",
            (decor_id, sm_id),
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO decor_structures (decor_id, structure_id) "
                "VALUES (?, ?)",
                (decor_id, sm_id),
            )

    def test_cascade_delete_when_decor_deleted(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        decor_id = lookup("decors", "business_id", "K8685")
        sm_id = lookup("structures", "code", "SM")

        db.execute(
            "INSERT INTO decor_structures (decor_id, structure_id) "
            "VALUES (?, ?)",
            (decor_id, sm_id),
        )
        db.commit()
        db.execute("DELETE FROM decors WHERE id = ?", (decor_id,))
        db.commit()

        count = db.execute(
            "SELECT COUNT(*) FROM decor_structures WHERE decor_id = ?",
            (decor_id,),
        ).fetchone()[0]
        assert count == 0

    def test_cascade_delete_when_structure_deleted(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        decor_id = lookup("decors", "business_id", "K8685")
        sm_id = lookup("structures", "code", "SM")

        db.execute(
            "INSERT INTO decor_structures (decor_id, structure_id) "
            "VALUES (?, ?)",
            (decor_id, sm_id),
        )
        db.commit()
        db.execute("DELETE FROM structures WHERE id = ?", (sm_id,))
        db.commit()

        count = db.execute(
            "SELECT COUNT(*) FROM decor_structures "
            "WHERE decor_id = ? AND structure_id = ?",
            (decor_id, sm_id),
        ).fetchone()[0]
        assert count == 0

    def test_fk_rejects_nonexistent_decor(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        sm_id = lookup("structures", "code", "SM")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO decor_structures (decor_id, structure_id) "
                "VALUES (99999, ?)",
                (sm_id,),
            )

    def test_fk_rejects_nonexistent_structure(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        decor_id = lookup("decors", "business_id", "K8685")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO decor_structures (decor_id, structure_id) "
                "VALUES (?, 99999)",
                (decor_id,),
            )

    def test_one_primary_per_decor(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        """Not a DB constraint — enforced at application level.
        But we verify that the is_primary flag CAN be set on only one row
        and queried cleanly."""
        db = db_with_kronospan
        decor_id = lookup("decors", "business_id", "K8685")
        sm_id = lookup("structures", "code", "SM")
        bs_id = lookup("structures", "code", "BS")

        db.execute(
            "INSERT INTO decor_structures "
            "(decor_id, structure_id, is_primary) VALUES (?, ?, 1)",
            (decor_id, sm_id),
        )
        db.execute(
            "INSERT INTO decor_structures "
            "(decor_id, structure_id, is_primary) VALUES (?, ?, 0)",
            (decor_id, bs_id),
        )
        db.commit()

        primary = db.execute(
            "SELECT structure_id FROM decor_structures "
            "WHERE decor_id = ? AND is_primary = 1",
            (decor_id,),
        ).fetchall()
        assert len(primary) == 1
        assert primary[0]["structure_id"] == sm_id


# ══════════════════════════════════════════════════════════════════
# 3. Kronospan real-world — K8685 (SM, BS, PD, PW), K190 (PE, PD, PW)
# ══════════════════════════════════════════════════════════════════


class TestKronospanGlobalMultiStructures:
    """Kronospan Global Collection K8685 Biel Alpejska.

    Catalog str. 6-31:
      K8685 primary structure = SM (Super Mat)
      K8685 multi_structures  = BS, PD, PW
      Total = 4 structures for one decor.

    K190 Czarny:
      K190 primary structure = PE (Pearl Effect)
      K190 multi_structures  = PD, PW
      Total = 3 structures for one decor.
    """

    def _insert_structure(self, db, producer_id, code, name):
        cur = db.cursor()
        cur.execute(
            "INSERT INTO structures "
            "(code, name, type, finish, producer_id) "
            "VALUES (?, ?, 'structured', 'matt', ?)",
            (code, name, producer_id),
        )
        return cur.lastrowid

    def test_k8685_four_structures(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")
        k8685_id = lookup("decors", "business_id", "K8685")

        # PD and PW not in fixture — add them
        pd_id = self._insert_structure(db, producer_id, "PD", "Pearl Dark")
        pw_id = self._insert_structure(db, producer_id, "PW", "Pearl Wood")
        sm_id = lookup("structures", "code", "SM")
        bs_id = lookup("structures", "code", "BS")

        cur.executemany(
            "INSERT INTO decor_structures "
            "(decor_id, structure_id, is_primary) VALUES (?, ?, ?)",
            [
                (k8685_id, sm_id, 1),   # primary ("Str." column)
                (k8685_id, bs_id, 0),   # from "multi_structures"
                (k8685_id, pd_id, 0),   # from "multi_structures"
                (k8685_id, pw_id, 0),   # from "multi_structures"
            ],
        )
        db.commit()

        rows = db.execute(
            "SELECT s.code, ds.is_primary FROM decor_structures ds "
            "JOIN structures s ON s.id = ds.structure_id "
            "WHERE ds.decor_id = ? ORDER BY ds.is_primary DESC",
            (k8685_id,),
        ).fetchall()

        assert len(rows) == 4
        assert rows[0]["code"] == "SM" and rows[0]["is_primary"] == 1
        codes = {r["code"] for r in rows}
        assert codes == {"SM", "BS", "PD", "PW"}

    def test_k190_three_structures(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")
        k190_id = lookup("decors", "business_id", "K190")

        pd_id = self._insert_structure(db, producer_id, "PD", "Pearl Dark")
        pw_id = self._insert_structure(db, producer_id, "PW", "Pearl Wood")
        pe_id = lookup("structures", "code", "PE")

        cur.executemany(
            "INSERT INTO decor_structures "
            "(decor_id, structure_id, is_primary) VALUES (?, ?, ?)",
            [
                (k190_id, pe_id, 1),   # primary
                (k190_id, pd_id, 0),   # multi
                (k190_id, pw_id, 0),   # multi
            ],
        )
        db.commit()

        rows = db.execute(
            "SELECT s.code FROM decor_structures ds "
            "JOIN structures s ON s.id = ds.structure_id "
            "WHERE ds.decor_id = ?",
            (k190_id,),
        ).fetchall()
        codes = {r["code"] for r in rows}
        assert codes == {"PE", "PD", "PW"}

    def test_view_decor_structures_full_k8685(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")
        k8685_id = lookup("decors", "business_id", "K8685")
        sm_id = lookup("structures", "code", "SM")
        bs_id = lookup("structures", "code", "BS")

        cur.executemany(
            "INSERT INTO decor_structures "
            "(decor_id, structure_id, is_primary) VALUES (?, ?, ?)",
            [(k8685_id, sm_id, 1), (k8685_id, bs_id, 0)],
        )
        db.commit()

        rows = db.execute(
            "SELECT decor_id, structure_code, structure_name, is_primary "
            "FROM v_decor_structures_full WHERE decor_id = 'K8685'"
        ).fetchall()
        assert len(rows) == 2
        primary = [r for r in rows if r["is_primary"] == 1]
        assert len(primary) == 1
        assert primary[0]["structure_code"] == "SM"


# ══════════════════════════════════════════════════════════════════
# 4. KronoSwiss synchronized texture + multi-structure
# ══════════════════════════════════════════════════════════════════


class TestKronoSwissSynchronizedStructures:
    """KronoSwiss Sensesation has synchro structures (SE, SD, SW, OV).

    Source: kronoswiss_spec.md str. 58-59.
    D3314 'Dąb Giovanni' has primary structure SD (Synchro Dąb).
    """

    def test_decor_with_synchro_structure_flagged(
        self, db: sqlite3.Connection
    ):
        cur = db.cursor()
        cur.execute(
            "INSERT INTO producers (slug, name) VALUES ('swiss_krono', 'Swiss Krono')"
        )
        pid = cur.lastrowid
        # SD = synchronized
        cur.execute(
            "INSERT INTO structures "
            "(code, name, type, finish, synchronized_texture, producer_id) "
            "VALUES ('SD', 'Synchro Dąb', 'wood_grain', 'matt', 1, ?)",
            (pid,),
        )
        sd_id = cur.lastrowid
        # MX = not synchronized
        cur.execute(
            "INSERT INTO structures "
            "(code, name, type, finish, synchronized_texture, producer_id) "
            "VALUES ('MX', 'Matrix', 'structured', 'matt', 0, ?)",
            (pid,),
        )
        mx_id = cur.lastrowid

        # Collection + material for the variant FK chain
        cur.execute(
            "INSERT INTO collections (slug, producer_id, name) "
            "VALUES ('sensesation', ?, 'Sensesation')", (pid,)
        )
        col_id = cur.lastrowid
        mt_id = db.execute(
            "SELECT id FROM material_types WHERE slug = 'chipboard'"
        ).fetchone()[0]
        cur.execute(
            "INSERT INTO materials "
            "(slug, material_type_id, collection_id, name) "
            "VALUES ('sw-chip', ?, ?, 'Swiss Chip')", (mt_id, col_id)
        )
        mat_id = cur.lastrowid

        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) "
            "VALUES ('D3314', ?, 'Dąb Giovanni')", (pid,)
        )
        d3314_id = cur.lastrowid

        # Both structures available for D3314
        cur.executemany(
            "INSERT INTO decor_structures "
            "(decor_id, structure_id, is_primary) VALUES (?, ?, ?)",
            [(d3314_id, sd_id, 1), (d3314_id, mx_id, 0)],
        )

        # Two variants (one per structure)
        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, thickness_mm) "
            "VALUES ('D3314-SD-18', ?, ?, ?, 18)",
            (d3314_id, mat_id, sd_id),
        )
        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, thickness_mm) "
            "VALUES ('D3314-MX-18', ?, ?, ?, 18)",
            (d3314_id, mat_id, mx_id),
        )
        db.commit()

        # Only the synchro variant should appear in v_synchro_variants
        rows = db.execute(
            "SELECT variant_id FROM v_synchro_variants "
            "WHERE decor_id = 'D3314'"
        ).fetchall()
        ids = {r["variant_id"] for r in rows}
        assert ids == {"D3314-SD-18"}

        # Both structures should appear in v_decor_structures_full
        rows = db.execute(
            "SELECT structure_code, is_primary FROM v_decor_structures_full "
            "WHERE decor_id = 'D3314'"
        ).fetchall()
        assert len(rows) == 2
        codes = {r["structure_code"] for r in rows}
        assert codes == {"SD", "MX"}


# ══════════════════════════════════════════════════════════════════
# 5. Pairings expanded types — real-world matching
# ══════════════════════════════════════════════════════════════════


class TestPairingsExpandedTypes:
    """Matching products from Kronospan Global Collection.

    K8685 'Biel Alpejska' board matches:
      - K8685_AG  (acrylic)     → pairing_type = 'acrylic'
      - K8685_MG  (mirror)      → pairing_type = 'mirror'
      - K8685_CI  (compact)     → pairing_type = 'compact'
      - K8685_HPL (HPL)         → pairing_type = 'hpl_laminate'
      - K190_KA   (kronoart)    → pairing_type = 'kronoart'
      - 868S      (worktop)     → pairing_type = 'worktop'

    U190 'Czarny' (KronoSwiss) matches:
      - U190_KM   (black_wood)  → pairing_type = 'black_wood'
    """

    def test_kronospan_acrylic_pairing(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")
        k8685_id = lookup("decors", "business_id", "K8685")

        # Create the acrylic variant decor (e.g. K8685_AG)
        cur.execute(
            "INSERT INTO decors "
            "(business_id, producer_id, name, group_name) "
            "VALUES ('K8685-AG', ?, 'Biel Alpejska AG', 'XXIII')",
            (producer_id,),
        )
        acrylic_id = cur.lastrowid

        cur.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type, priority) "
            "VALUES (?, ?, 'acrylic', 'exact', 1)",
            (k8685_id, acrylic_id),
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM v_pairings_full "
            "WHERE front_decor_id = 'K8685' AND pairing_type = 'acrylic'"
        ).fetchone()
        assert row is not None
        assert row["target_decor_id"] == "K8685-AG"
        assert row["match_type"] == "exact"

    def test_kronospan_mirror_pairing(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")
        k8685_id = lookup("decors", "business_id", "K8685")

        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) "
            "VALUES ('K8685-MG', ?, 'Biel Alpejska MG')", (producer_id,)
        )
        mg_id = cur.lastrowid

        cur.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type) "
            "VALUES (?, ?, 'mirror', 'exact')",
            (k8685_id, mg_id),
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM v_pairings_full "
            "WHERE front_decor_id = 'K8685' AND pairing_type = 'mirror'"
        ).fetchone()
        assert row["target_decor_id"] == "K8685-MG"

    def test_kronospan_hpl_laminate_pairing(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")
        k8685_id = lookup("decors", "business_id", "K8685")

        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) "
            "VALUES ('8685-HPL', ?, 'Biel Alpejska HPL')", (producer_id,)
        )
        hpl_id = cur.lastrowid

        cur.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type) "
            "VALUES (?, ?, 'hpl_laminate', 'exact')",
            (k8685_id, hpl_id),
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM v_pairings_full "
            "WHERE front_decor_id = 'K8685' AND pairing_type = 'hpl_laminate'"
        ).fetchone()
        assert row["target_decor_id"] == "8685-HPL"

    def test_krono_swiss_black_wood_pairing(self, db: sqlite3.Connection):
        """KronoSwiss U190 → U190_BLACKWOOD via black_wood pairing."""
        cur = db.cursor()
        cur.execute(
            "INSERT INTO producers (slug, name) "
            "VALUES ('swiss_krono', 'Swiss Krono')"
        )
        pid = cur.lastrowid
        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) VALUES "
            "('U190', ?, 'Czarny'), ('U190-BW', ?, 'Czarny BW')",
            (pid, pid),
        )
        ids = cur.execute(
            "SELECT id, business_id FROM decors "
            "WHERE business_id IN ('U190', 'U190-BW') ORDER BY business_id"
        ).fetchall()
        u190_id = ids[0][0]
        bw_id = ids[1][0]

        cur.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type) "
            "VALUES (?, ?, 'black_wood', 'exact')",
            (u190_id, bw_id),
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM v_pairings_full "
            "WHERE target_decor_id = 'U190-BW'"
        ).fetchone()
        assert row["pairing_type"] == "black_wood"

    def test_view_pairings_full_shows_new_types(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")
        k8685_id = lookup("decors", "business_id", "K8685")

        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) "
            "VALUES ('K8685-AG', ?, 'Biel Alpejska AG')", (producer_id,)
        )
        ag_id = cur.lastrowid

        cur.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type) "
            "VALUES (?, ?, 'acrylic', 'exact')",
            (k8685_id, ag_id),
        )
        db.commit()

        rows = db.execute(
            "SELECT pairing_type FROM v_pairings_full "
            "WHERE front_decor_id = 'K8685'"
        ).fetchall()
        types = {r["pairing_type"] for r in rows}
        assert "acrylic" in types


# ══════════════════════════════════════════════════════════════════
# 6. End-to-end discovery flow
# ══════════════════════════════════════════════════════════════════


class TestEndToEndDiscovery:
    """Full flow: given a decor, discover all structures and matched products.

    Simulates an importer or UI asking:
      "I want to use K8685 Biel Alpejska in my kitchen project.
       What structures are available?
       What matching worktop can I pair it with?
       What acrylic variants exist?"
    """

    def test_full_k8685_discovery(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")

        k8685_id = lookup("decors", "business_id", "K8685")
        sm_id = lookup("structures", "code", "SM")
        bs_id = lookup("structures", "code", "BS")
        pe_id = lookup("structures", "code", "PE")

        # ── 1. Register structures for K8685 ──────────────────────
        cur.executemany(
            "INSERT INTO decor_structures "
            "(decor_id, structure_id, is_primary) VALUES (?, ?, ?)",
            [
                (k8685_id, sm_id, 1),  # primary (catalog "Str." column)
                (k8685_id, bs_id, 0),  # from "multi_structures"
                (k8685_id, pe_id, 0),  # from "multi_structures"
            ],
        )

        # ── 2. Create matching acrylic variant ────────────────────
        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) "
            "VALUES ('K8685-AG', ?, 'Biel Alpejska AG')",
            (producer_id,),
        )
        ag_id = cur.lastrowid

        cur.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type, priority) "
            "VALUES (?, ?, 'acrylic', 'exact', 1)",
            (k8685_id, ag_id),
        )

        # ── 3. Create matching worktop variant + pairings ─────────
        worktop_decor_id = lookup("decors", "business_id", "868S")
        postformed_material = lookup(
            "materials", "slug", "kronospan-postformed-global"
        )
        rs_id = lookup("structures", "code", "RS")

        cur.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type, priority) "
            "VALUES (?, ?, 'worktop', 'exact', 1)",
            (k8685_id, worktop_decor_id),
        )

        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, "
            " thickness_mm, roles) "
            "VALUES ('868S-PF-U', ?, ?, ?, 38, '[\"worktop\"]')",
            (worktop_decor_id, postformed_material, rs_id),
        )
        wt_variant_id = cur.lastrowid

        construction_id = lookup(
            "worktop_constructions", "slug", "postformed"
        )
        profile_id = lookup("worktop_profiles", "code", "U")

        cur.execute(
            "INSERT INTO worktop_specs "
            "(variant_id, construction_id, profile_id, "
            " available_widths_mm, edge_material) "
            "VALUES (?, ?, ?, '[600, 900, 1200]', 'Unoflex')",
            (wt_variant_id, construction_id, profile_id),
        )
        db.commit()

        # ── ASSERT: What structures does K8685 come in? ───────────
        structures = db.execute(
            "SELECT structure_code, is_primary "
            "FROM v_decor_structures_full "
            "WHERE decor_id = 'K8685' "
            "ORDER BY is_primary DESC"
        ).fetchall()
        assert len(structures) == 3
        assert structures[0]["structure_code"] == "SM"
        assert structures[0]["is_primary"] == 1
        codes = {s["structure_code"] for s in structures}
        assert codes == {"SM", "BS", "PE"}

        # ── ASSERT: What acrylic variant does K8685 match? ────────
        acrylic_pair = db.execute(
            "SELECT target_decor_id FROM v_pairings_full "
            "WHERE front_decor_id = 'K8685' AND pairing_type = 'acrylic'"
        ).fetchone()
        assert acrylic_pair["target_decor_id"] == "K8685-AG"

        # ── ASSERT: What worktop does K8685 pair with? ────────────
        worktop_pair = db.execute(
            """
            SELECT wf.variant_id, wf.construction, wf.profile_code,
                   wf.edge_material, wf.available_widths_mm
            FROM v_pairings_full vp
            JOIN v_worktops_full wf
              ON wf.decor_id = vp.target_decor_id
            WHERE vp.front_decor_id = 'K8685'
              AND vp.pairing_type = 'worktop'
            """
        ).fetchone()
        assert worktop_pair is not None
        assert worktop_pair["variant_id"] == "868S-PF-U"
        assert worktop_pair["construction"] == "postformed"
        assert worktop_pair["profile_code"] == "U"
        assert worktop_pair["edge_material"] == "Unoflex"
        import json

        assert json.loads(worktop_pair["available_widths_mm"]) == [
            600,
            900,
            1200,
        ]

        # ── ASSERT: How many matched products total? ──────────────
        total = db.execute(
            "SELECT COUNT(*) AS n FROM v_pairings_full "
            "WHERE front_decor_id = 'K8685'"
        ).fetchone()["n"]
        assert total == 2  # acrylic + worktop


# ══════════════════════════════════════════════════════════════════
# 7. Backward compatibility — deprecated multi_structures column
# ══════════════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    """The old `multi_structures` column on variants is still present
    (not dropped). Tests verify it still works during the transition period.
    """

    def test_multi_structures_column_still_exists(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cols = {row[1] for row in db.execute("PRAGMA table_info(variants)")}
        assert "multi_structures" in cols, (
            "Column was dropped prematurely — keep it during transition"
        )

    def test_multi_structures_can_still_be_written(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        decor_id = lookup("decors", "business_id", "K8685")
        material_id = lookup("materials", "slug", "kronospan-chipboard-global")
        sm_id = lookup("structures", "code", "SM")

        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, "
            " thickness_mm, multi_structures, roles) "
            "VALUES ('K8685-CH-18', ?, ?, ?, 18, 'BS, PD, PW', '[\"front\"]')",
            (decor_id, material_id, sm_id),
        )
        db.commit()

        row = db.execute(
            "SELECT multi_structures FROM variants "
            "WHERE business_id = 'K8685-CH-18'"
        ).fetchone()
        assert row["multi_structures"] == "BS, PD, PW"
