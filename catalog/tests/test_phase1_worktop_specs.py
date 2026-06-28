"""Tests for Phase 1 migration: Worktop Specifications.

Covers:
    1. Schema integrity — new tables exist, ALTER TABLE additions applied
    2. Seed data — worktop_constructions, worktop_profiles, sheet_formats
    3. Constraints — CHECKs, FKs, UNIQUEs
    4. Real-world inserts — Kronospan postformed, KronoSwiss BLACK WOOD,
       Slim Line subcollections
    5. Views — v_worktops_full, v_synchro_variants
"""

import json
import sqlite3

import pytest


# ══════════════════════════════════════════════════════════════════
# 1. Schema integrity
# ══════════════════════════════════════════════════════════════════


class TestSchemaIntegrity:
    """The 5 new tables and ALTER TABLE columns must exist."""

    NEW_TABLES = [
        "sheet_formats",
        "subcollections",
        "worktop_constructions",
        "worktop_profiles",
        "worktop_specs",
    ]

    def test_all_new_tables_exist(self, db: sqlite3.Connection):
        existing = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table in self.NEW_TABLES:
            assert table in existing, f"Phase 1 table missing: {table}"

    def test_structures_has_synchronized_texture_column(self, db: sqlite3.Connection):
        cols = {row[1] for row in db.execute("PRAGMA table_info(structures)")}
        assert "synchronized_texture" in cols

    def test_materials_has_subcollection_fk_column(self, db: sqlite3.Connection):
        cols = {row[1] for row in db.execute("PRAGMA table_info(materials)")}
        assert "subcollection_id" in cols

    def test_variants_has_sheet_format_fk_column(self, db: sqlite3.Connection):
        cols = {row[1] for row in db.execute("PRAGMA table_info(variants)")}
        assert "sheet_format_id" in cols

    def test_decors_has_bilingual_and_flag_columns(self, db: sqlite3.Connection):
        cols = {row[1] for row in db.execute("PRAGMA table_info(decors)")}
        for col in ("name_en", "one_global", "new_2024", "discontinued"):
            assert col in cols, f"Phase 1 decor column missing: {col}"

    def test_views_exist(self, db: sqlite3.Connection):
        views = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()
        }
        assert "v_worktops_full" in views
        assert "v_synchro_variants" in views


# ══════════════════════════════════════════════════════════════════
# 2. Seed data
# ══════════════════════════════════════════════════════════════════


class TestSeedData:
    """Reference rows from Phase 1 migration must be present."""

    EXPECTED_CONSTRUCTIONS = {
        "postformed",
        "abs_square_edge",
        "slim_line",
        "fitline",
        "black_wood",
    }
    EXPECTED_PROFILES = {"U", "U-U", "R3", "SQUARE", "NATURAL"}

    def test_worktop_constructions_seeded(self, db: sqlite3.Connection):
        rows = db.execute("SELECT slug FROM worktop_constructions").fetchall()
        seeded = {row[0] for row in rows}
        assert self.EXPECTED_CONSTRUCTIONS.issubset(seeded), (
            f"Missing constructions: {self.EXPECTED_CONSTRUCTIONS - seeded}"
        )

    def test_worktop_profiles_seeded(self, db: sqlite3.Connection):
        rows = db.execute("SELECT code FROM worktop_profiles").fetchall()
        seeded = {row[0] for row in rows}
        assert self.EXPECTED_PROFILES.issubset(seeded)

    def test_profile_U_has_radius_3_3mm(self, db: sqlite3.Connection):
        row = db.execute(
            "SELECT edge_radius_mm, profiled_sides FROM worktop_profiles WHERE code = 'U'"
        ).fetchone()
        assert row["edge_radius_mm"] == 3.3
        assert row["profiled_sides"] == "front"

    def test_profile_U_U_has_two_profiled_sides(self, db: sqlite3.Connection):
        row = db.execute(
            "SELECT profiled_sides FROM worktop_profiles WHERE code = 'U-U'"
        ).fetchone()
        assert row["profiled_sides"] == "front,back"

    def test_profile_SQUARE_has_radius_1_5mm(self, db: sqlite3.Connection):
        row = db.execute(
            "SELECT edge_radius_mm FROM worktop_profiles WHERE code = 'SQUARE'"
        ).fetchone()
        # ABS Square Edge: R=1.5mm
        assert row["edge_radius_mm"] == 1.5

    def test_profile_NATURAL_has_zero_radius(self, db: sqlite3.Connection):
        row = db.execute(
            "SELECT edge_radius_mm, profiled_sides FROM worktop_profiles "
            "WHERE code = 'NATURAL'"
        ).fetchone()
        assert row["edge_radius_mm"] == 0
        assert row["profiled_sides"] == "none"

    def test_construction_black_wood_is_swiss_krono(self, db: sqlite3.Connection):
        row = db.execute(
            "SELECT producer_hint FROM worktop_constructions WHERE slug = 'black_wood'"
        ).fetchone()
        assert row["producer_hint"] == "swiss_krono"

    def test_sheet_format_4100x1315_for_black_wood(self, db: sqlite3.Connection):
        # BLACK WOOD physical format from KronoSwiss str. 60-61
        row = db.execute(
            "SELECT length_mm, width_mm FROM sheet_formats WHERE slug = '4100x1315'"
        ).fetchone()
        assert row["length_mm"] == 4100
        assert row["width_mm"] == 1315

    def test_sheet_format_4100x600_for_postformed(self, db: sqlite3.Connection):
        row = db.execute(
            "SELECT length_mm, width_mm, use_hint FROM sheet_formats "
            "WHERE slug = '4100x600'"
        ).fetchone()
        assert row["length_mm"] == 4100
        assert row["use_hint"] == "worktop"

    def test_seed_inserts_are_idempotent(self, db: sqlite3.Connection):
        """Re-applying INSERT OR IGNORE seed rows must not duplicate.

        NOTE: We do NOT re-run the full migration script here, because
        `ALTER TABLE ADD COLUMN` is not idempotent in SQLite (no
        ``IF NOT EXISTS`` variant). In production, migrations are
        version-tracked (e.g. via a `schema_migrations` table) and each
        file runs exactly once. What MUST be idempotent are the
        ``CREATE TABLE IF NOT EXISTS`` blocks and ``INSERT OR IGNORE``
        seed statements — and that's what we verify here.
        """
        before_c = db.execute(
            "SELECT COUNT(*) FROM worktop_constructions"
        ).fetchone()[0]
        before_p = db.execute(
            "SELECT COUNT(*) FROM worktop_profiles"
        ).fetchone()[0]
        before_f = db.execute("SELECT COUNT(*) FROM sheet_formats").fetchone()[0]

        # Re-run only the idempotent seed statements
        db.executescript(
            """
            INSERT OR IGNORE INTO worktop_constructions (slug, name) VALUES
                ('postformed', 'Post-formed'),
                ('black_wood', 'BLACK WOOD');
            INSERT OR IGNORE INTO worktop_profiles
                (code, name, edge_radius_mm, profiled_sides) VALUES
                ('U', 'Profil U', 3.3, 'front'),
                ('NATURAL', 'Krawędź naturalna', 0, 'none');
            INSERT OR IGNORE INTO sheet_formats (slug, length_mm, width_mm) VALUES
                ('4100x600', 4100, 600),
                ('4100x1315', 4100, 1315);
            """
        )

        after_c = db.execute(
            "SELECT COUNT(*) FROM worktop_constructions"
        ).fetchone()[0]
        after_p = db.execute(
            "SELECT COUNT(*) FROM worktop_profiles"
        ).fetchone()[0]
        after_f = db.execute("SELECT COUNT(*) FROM sheet_formats").fetchone()[0]

        assert before_c == after_c, "worktop_constructions seeds duplicated"
        assert before_p == after_p, "worktop_profiles seeds duplicated"
        assert before_f == after_f, "sheet_formats seeds duplicated"

    def test_create_table_if_not_exists_is_idempotent(
        self, db: sqlite3.Connection
    ):
        """Re-issuing CREATE TABLE IF NOT EXISTS on existing tables is a no-op."""
        # All 5 phase-1 tables can be re-issued without error
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sheet_formats (id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS subcollections (id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS worktop_constructions (id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS worktop_profiles (id INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS worktop_specs (id INTEGER PRIMARY KEY);
            """
        )
        # Original schema still intact — count of seeded constructions unchanged
        n = db.execute("SELECT COUNT(*) FROM worktop_constructions").fetchone()[0]
        assert n >= 5  # postformed, abs_square_edge, slim_line, fitline, black_wood


# ══════════════════════════════════════════════════════════════════
# 3. CHECK constraints
# ══════════════════════════════════════════════════════════════════


class TestConstraints:
    """Domain validation enforced at DB level."""

    def test_sheet_format_rejects_negative_dimensions(self, db: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO sheet_formats (slug, length_mm, width_mm) "
                "VALUES ('bad', -100, 500)"
            )

    def test_sheet_format_requires_length_ge_width(self, db: sqlite3.Connection):
        """Canonical orientation: longer side is `length_mm`."""
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO sheet_formats (slug, length_mm, width_mm) "
                "VALUES ('flipped', 500, 1000)"
            )

    def test_worktop_profile_rejects_negative_radius(self, db: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO worktop_profiles "
                "(code, name, edge_radius_mm, profiled_sides) "
                "VALUES ('BAD', 'Bad', -1, 'front')"
            )

    def test_worktop_profile_rejects_invalid_profiled_sides(
        self, db: sqlite3.Connection
    ):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO worktop_profiles "
                "(code, name, edge_radius_mm, profiled_sides) "
                "VALUES ('X', 'X', 1.0, 'left,right')"
            )

    def test_worktop_spec_unique_per_variant(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        """A variant can have AT MOST ONE worktop_spec (1:0..1)."""
        db = db_with_kronospan
        # Create a postformed worktop variant for decor 868S
        decor_id = lookup("decors", "business_id", "868S")
        material_id = lookup("materials", "slug", "kronospan-postformed-global")
        structure_id = db.execute(
            "SELECT id FROM structures WHERE code = 'RS'"
        ).fetchone()[0]

        cur = db.cursor()
        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, thickness_mm, roles) "
            "VALUES ('868S-PF-U', ?, ?, ?, 38, '[\"worktop\"]')",
            (decor_id, material_id, structure_id),
        )
        variant_id = cur.lastrowid

        construction_id = lookup("worktop_constructions", "slug", "postformed")
        profile_id = lookup("worktop_profiles", "code", "U")

        cur.execute(
            "INSERT INTO worktop_specs "
            "(variant_id, construction_id, profile_id, available_widths_mm) "
            "VALUES (?, ?, ?, '[600]')",
            (variant_id, construction_id, profile_id),
        )
        # Second insert with same variant_id must fail
        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                "INSERT INTO worktop_specs "
                "(variant_id, construction_id, profile_id, available_widths_mm) "
                "VALUES (?, ?, ?, '[900]')",
                (variant_id, construction_id, profile_id),
            )

    def test_worktop_spec_fk_to_variant_enforced(self, db: sqlite3.Connection):
        """Cannot insert worktop_spec referring to nonexistent variant."""
        construction_id = db.execute(
            "SELECT id FROM worktop_constructions WHERE slug = 'postformed'"
        ).fetchone()[0]
        profile_id = db.execute(
            "SELECT id FROM worktop_profiles WHERE code = 'U'"
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO worktop_specs "
                "(variant_id, construction_id, profile_id, available_widths_mm) "
                "VALUES (99999, ?, ?, '[600]')",
                (construction_id, profile_id),
            )

    def test_subcollection_unique_slug_per_collection(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        """The same subcollection slug cannot exist twice within one collection."""
        db = db_with_kronospan
        collection_id = lookup("collections", "slug", "global")
        db.execute(
            "INSERT INTO subcollections (collection_id, slug, name) "
            "VALUES (?, 'slim_global', 'Global Collection')",
            (collection_id,),
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO subcollections (collection_id, slug, name) "
                "VALUES (?, 'slim_global', 'Dup')",
                (collection_id,),
            )


# ══════════════════════════════════════════════════════════════════
# 4. Real-world inserts from analyzed catalogs
# ══════════════════════════════════════════════════════════════════


class TestKronospanPostformed:
    """Kronospan blat 7045 'Szampański' postformed U + U-U.

    Source: blaty.pdf str. 48 (Global Collection 2026 - blaty robocze).
    """

    def test_insert_postformed_worktop_variant_with_spec(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()

        # Decor 7045 'Szampański' (worktop pair)
        producer_id = lookup("producers", "slug", "kronospan")
        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name, group_name) "
            "VALUES ('7045', ?, 'Szampański', 'XIV MAT 1')",
            (producer_id,),
        )
        decor_id = cur.lastrowid

        # Variant: postformed, 38mm, structure RS
        material_id = lookup("materials", "slug", "kronospan-postformed-global")
        structure_id = db.execute(
            "SELECT id FROM structures WHERE code = 'RS' AND producer_id = ?",
            (producer_id,),
        ).fetchone()[0]
        sheet_format_id = lookup("sheet_formats", "slug", "4100x600")

        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, "
            " thickness_mm, sheet_format_id, roles) "
            "VALUES ('7045-PF-U-600', ?, ?, ?, 38, ?, '[\"worktop\"]')",
            (decor_id, material_id, structure_id, sheet_format_id),
        )
        variant_id = cur.lastrowid

        # Worktop spec: profile U (one side), 600mm wide
        construction_id = lookup("worktop_constructions", "slug", "postformed")
        profile_id = lookup("worktop_profiles", "code", "U")
        cur.execute(
            "INSERT INTO worktop_specs "
            "(variant_id, construction_id, profile_id, "
            " max_length_mm, available_widths_mm, edge_material, "
            " splashback_available, matching_board_available, "
            " pieces_per_pallet) "
            "VALUES (?, ?, ?, 4100, '[600]', 'Unoflex', 1, 1, 10)",
            (variant_id, construction_id, profile_id),
        )
        db.commit()

        # Verify via view
        row = db.execute(
            "SELECT * FROM v_worktops_full WHERE variant_id = '7045-PF-U-600'"
        ).fetchone()
        assert row is not None
        assert row["decor_id"] == "7045"
        assert row["decor_name_pl"] == "Szampański"
        assert row["construction"] == "postformed"
        assert row["profile_code"] == "U"
        assert row["edge_radius_mm"] == 3.3
        assert row["edge_material"] == "Unoflex"
        assert row["sheet_length_mm"] == 4100
        assert row["sheet_width_mm"] == 600
        assert json.loads(row["available_widths_mm"]) == [600]
        assert bool(row["splashback_available"]) is True


class TestKronoSwissBlackWood:
    """KronoSwiss BLACK WOOD U190 'Czarny' — ultracienki 12mm.

    Source: SWISSKRONO_PL...PDF str. 60-61, 88 (BLACK WOOD Worktops table).
    Key facts: 12mm thick, density 900 kg/m³, fire class D-s1,d0, NATURAL edge.
    """

    def test_insert_black_wood_variant_with_natural_edge(
        self, db: sqlite3.Connection, lookup
    ):
        cur = db.cursor()

        # Producer + collection + material
        cur.execute(
            "INSERT INTO producers (slug, name, country) "
            "VALUES ('swiss_krono', 'Swiss Krono', 'Szwajcaria')"
        )
        producer_id = cur.lastrowid

        cur.execute(
            "INSERT INTO collections (slug, producer_id, name, has_countertops) "
            "VALUES ('black_wood', ?, 'BLACK WOOD Worktops', 1)",
            (producer_id,),
        )
        collection_id = cur.lastrowid

        # Reuse compact material_type seeded in 01-schema
        # Or create a dedicated material type. Here we use generic 'compact'.
        material_type_id = lookup("material_types", "slug", "compact")
        cur.execute(
            "INSERT INTO materials (slug, material_type_id, collection_id, name) "
            "VALUES ('swiss-blackwood', ?, ?, 'BLACK WOOD 12mm Worktop')",
            (material_type_id, collection_id),
        )
        material_id = cur.lastrowid

        # Structure 'KM' (Kamienna) — shared across producers (producer_id=NULL)
        cur.execute(
            "INSERT INTO structures (code, name, type, finish) "
            "VALUES ('KM', 'Kamienna', 'stone', 'structured')"
        )
        structure_id = cur.lastrowid

        # Decor U190 'Czarny' / 'Black' — KronoSwiss bilingual
        cur.execute(
            "INSERT INTO decors "
            "(business_id, producer_id, name, name_en, group_name, one_global) "
            "VALUES ('U190', ?, 'Czarny', 'Black', 'Unikolory', 1)",
            (producer_id,),
        )
        decor_id = cur.lastrowid

        # Sheet format 4100x1315 (BLACK WOOD specific)
        sheet_format_id = lookup("sheet_formats", "slug", "4100x1315")

        # Variant — thickness 12mm, role worktop
        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, "
            " thickness_mm, sheet_format_id, roles) "
            "VALUES ('U190-BW-12', ?, ?, ?, 12, ?, '[\"worktop\"]')",
            (decor_id, material_id, structure_id, sheet_format_id),
        )
        variant_id = cur.lastrowid

        # Worktop spec — BLACK WOOD construction, NATURAL edge
        construction_id = lookup("worktop_constructions", "slug", "black_wood")
        profile_id = lookup("worktop_profiles", "code", "NATURAL")
        cur.execute(
            "INSERT INTO worktop_specs "
            "(variant_id, construction_id, profile_id, "
            " max_length_mm, available_widths_mm, edge_material, "
            " pieces_per_pallet, pallet_weight_kg) "
            "VALUES (?, ?, ?, 4100, '[1315]', 'naturalna', 20, 1200)",
            (variant_id, construction_id, profile_id),
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM v_worktops_full WHERE variant_id = 'U190-BW-12'"
        ).fetchone()
        assert row["decor_name_pl"] == "Czarny"
        assert row["decor_name_en"] == "Black"
        assert row["construction"] == "black_wood"
        assert row["profile_code"] == "NATURAL"
        assert row["edge_radius_mm"] == 0
        assert row["thickness_mm"] == 12
        assert row["sheet_width_mm"] == 1315

    def test_one_global_flag_persists(self, db: sqlite3.Connection):
        cur = db.cursor()
        cur.execute(
            "INSERT INTO producers (slug, name) VALUES ('swiss_krono', 'Swiss Krono')"
        )
        producer_id = cur.lastrowid
        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name, one_global) "
            "VALUES ('U164', ?, 'Antracyt', 1)",
            (producer_id,),
        )
        row = db.execute(
            "SELECT one_global FROM decors WHERE business_id = 'U164'"
        ).fetchone()
        assert row["one_global"] == 1


class TestKronospanSlimLineSubcollections:
    """Kronospan Slim Line splits into 'Global' (10) and 'Plus' (6) subcollections.

    Source: blaty.pdf str. 64-65.
    """

    def test_subcollection_global_and_plus_coexist(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()

        collection_id = lookup("collections", "slug", "global")

        cur.execute(
            "INSERT INTO subcollections (collection_id, slug, name) "
            "VALUES (?, 'slim_global', 'Slim Line Global Collection')",
            (collection_id,),
        )
        sc_global_id = cur.lastrowid
        cur.execute(
            "INSERT INTO subcollections (collection_id, slug, name) "
            "VALUES (?, 'slim_plus', 'SlimLine Plus')",
            (collection_id,),
        )
        sc_plus_id = cur.lastrowid

        assert sc_global_id != sc_plus_id
        count = db.execute(
            "SELECT COUNT(*) FROM subcollections WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()[0]
        assert count == 2

    def test_material_links_to_subcollection(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()

        collection_id = lookup("collections", "slug", "global")
        cur.execute(
            "INSERT INTO subcollections (collection_id, slug, name) "
            "VALUES (?, 'slim_plus', 'SlimLine Plus')",
            (collection_id,),
        )
        sc_id = cur.lastrowid

        # New material assigned to subcollection
        material_type_id = lookup("material_types", "slug", "worktop_slim")
        cur.execute(
            "INSERT INTO materials "
            "(slug, material_type_id, collection_id, subcollection_id, name) "
            "VALUES ('slim-plus-material', ?, ?, ?, 'Slim Line Plus 12mm')",
            (material_type_id, collection_id, sc_id),
        )
        row = db.execute(
            "SELECT subcollection_id FROM materials WHERE slug = 'slim-plus-material'"
        ).fetchone()
        assert row["subcollection_id"] == sc_id


# ══════════════════════════════════════════════════════════════════
# 5. Synchronized texture (KronoSwiss ♻)
# ══════════════════════════════════════════════════════════════════


class TestSynchronizedTexture:
    """KronoSwiss has synchronized-texture structures: SE, SD, SW, CL, OV.

    Source: SWISSKRONO_PL...PDF str. 58-59.
    """

    def test_synchronized_flag_persists_on_structure(self, db: sqlite3.Connection):
        db.execute(
            "INSERT INTO structures (code, name, type, synchronized_texture) "
            "VALUES ('SD', 'Synchro Dąb', 'wood_grain', 1)"
        )
        row = db.execute(
            "SELECT synchronized_texture FROM structures WHERE code = 'SD'"
        ).fetchone()
        assert row["synchronized_texture"] == 1

    def test_synchro_variants_view_filters_correctly(self, db: sqlite3.Connection):
        cur = db.cursor()
        cur.execute(
            "INSERT INTO producers (slug, name) VALUES ('swiss_krono', 'Swiss Krono')"
        )
        producer_id = cur.lastrowid

        cur.execute(
            "INSERT INTO collections (slug, producer_id, name) "
            "VALUES ('sensesation', ?, 'Sensesation')",
            (producer_id,),
        )
        collection_id = cur.lastrowid
        mt_id = db.execute(
            "SELECT id FROM material_types WHERE slug = 'chipboard'"
        ).fetchone()[0]
        cur.execute(
            "INSERT INTO materials (slug, material_type_id, collection_id, name) "
            "VALUES ('swiss-chip', ?, ?, 'Swiss Chipboard')",
            (mt_id, collection_id),
        )
        material_id = cur.lastrowid

        # Two structures: SD (synchro) and MX (not synchro)
        cur.execute(
            "INSERT INTO structures (code, name, synchronized_texture) "
            "VALUES ('SD', 'Synchro Dąb', 1)"
        )
        sd_id = cur.lastrowid
        cur.execute(
            "INSERT INTO structures (code, name, synchronized_texture) "
            "VALUES ('MX', 'Matrix', 0)"
        )
        mx_id = cur.lastrowid

        # Decor + 2 variants
        cur.execute(
            "INSERT INTO decors (business_id, producer_id, name) "
            "VALUES ('D3314', ?, 'Dąb Giovanni')",
            (producer_id,),
        )
        decor_id = cur.lastrowid

        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, thickness_mm) "
            "VALUES ('D3314-SD-18', ?, ?, ?, 18)",
            (decor_id, material_id, sd_id),
        )
        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, thickness_mm) "
            "VALUES ('D3314-MX-18', ?, ?, ?, 18)",
            (decor_id, material_id, mx_id),
        )
        db.commit()

        rows = db.execute(
            "SELECT variant_id FROM v_synchro_variants WHERE decor_id = 'D3314'"
        ).fetchall()
        ids = {r["variant_id"] for r in rows}
        # Only the SD variant should appear in the synchro view
        assert ids == {"D3314-SD-18"}


# ══════════════════════════════════════════════════════════════════
# 6. End-to-end smoke test
# ══════════════════════════════════════════════════════════════════


class TestEndToEnd:
    """Compose a full Kronospan postformed worktop flow and query it back."""

    def test_full_kronospan_postformed_flow(
        self, db_with_kronospan: sqlite3.Connection, lookup
    ):
        db = db_with_kronospan
        cur = db.cursor()
        producer_id = lookup("producers", "slug", "kronospan")

        # Pair: K8685 board ↔ 868S worktop (same color "Biel Alpejska")
        # K8685 already exists via fixture
        board_decor = lookup("decors", "business_id", "K8685")
        worktop_decor = lookup("decors", "business_id", "868S")

        # Add pairing K8685 → 868S (board → worktop)
        cur.execute(
            "INSERT INTO pairings "
            "(front_decor_id, target_decor_id, pairing_type, match_type, priority) "
            "VALUES (?, ?, 'worktop', 'exact', 1)",
            (board_decor, worktop_decor),
        )

        # Build the 868S postformed worktop variant + spec
        material_id = lookup("materials", "slug", "kronospan-postformed-global")
        structure_id = db.execute(
            "SELECT id FROM structures WHERE code = 'RS' AND producer_id = ?",
            (producer_id,),
        ).fetchone()[0]
        sheet_id = lookup("sheet_formats", "slug", "4100x900")

        cur.execute(
            "INSERT INTO variants "
            "(business_id, decor_id, material_id, structure_id, "
            " thickness_mm, sheet_format_id, roles) "
            "VALUES ('868S-PF-UU-900', ?, ?, ?, 38, ?, '[\"worktop\"]')",
            (worktop_decor, material_id, structure_id, sheet_id),
        )
        variant_id = cur.lastrowid

        construction_id = lookup("worktop_constructions", "slug", "postformed")
        profile_id = lookup("worktop_profiles", "code", "U-U")

        cur.execute(
            "INSERT INTO worktop_specs "
            "(variant_id, construction_id, profile_id, "
            " max_length_mm, available_widths_mm, edge_material, "
            " splashback_available, matching_board_available) "
            "VALUES (?, ?, ?, 4100, '[900, 1200]', 'Unoflex', 1, 1)",
            (variant_id, construction_id, profile_id),
        )
        db.commit()

        # Query: "Given board K8685, what worktops can I pair with it?"
        rows = db.execute(
            """
            SELECT wf.variant_id, wf.profile_code, wf.edge_radius_mm,
                   wf.available_widths_mm
            FROM v_pairings_full vp
            JOIN v_worktops_full wf ON wf.decor_id = vp.target_decor_id
            WHERE vp.front_decor_id = 'K8685' AND vp.pairing_type = 'worktop'
            """
        ).fetchall()

        assert len(rows) == 1
        row = rows[0]
        assert row["variant_id"] == "868S-PF-UU-900"
        assert row["profile_code"] == "U-U"
        assert row["edge_radius_mm"] == 3.3
        assert json.loads(row["available_widths_mm"]) == [900, 1200]
