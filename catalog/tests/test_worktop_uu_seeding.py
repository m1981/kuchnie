"""Tests for U-U (island) postformed worktop seeding.

Spec: catalog/docs/specs/worktop-uu-seeding.md (slug: wtuu).

Domain basis (blaty-postformed-spec.md, Global Collection 2026, str. 43/48):
U-U profile = both long edges factory-postformed, widths 900/1200mm,
length 4100mm, thickness 38mm. Eligible decors are those listed in the
manufacturer's 2026 postformed table AND already modeled as a PF-U-600
variant — 18 decors → 36 U-U variants. Decor 0190 has a PF-U-600 variant
but is absent from the 2026 table, so it gets NO U-U variants.

DB convention: fixture-built in-memory DB (schema migrations + full
Kronospan import), then the seeder functions run twice — idempotency is
part of the seeding contract.
"""

from __future__ import annotations

import json
import re
import sqlite3

import pytest

from catalog.scripts.importer import CatalogImporter, load_yaml
from catalog.scripts.seed_worktop_uu import (
    ensure_hpl_edges,
    ensure_sheet_formats,
    seed_uu_variants,
)
from catalog.tests.conftest import DATA_DIR, SCHEMA_FILES, _load_sql

EXPECTED_UU_DECORS = 18
EXPECTED_UU_VARIANTS = 36  # 18 decors × 2 widths (900, 1200)


@pytest.fixture(scope="module")
def uu_db() -> sqlite3.Connection:
    """In-memory DB: migrations + kronospan_full.yaml + U-U seeder (run twice)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    for sql_file in SCHEMA_FILES:
        conn.executescript(_load_sql(sql_file))
    conn.commit()

    data = load_yaml(DATA_DIR / "kronospan_full.yaml")
    importer = CatalogImporter(conn)
    importer.import_all(data)

    # Run twice: the second pass must be a no-op (idempotent seeding).
    for _ in range(2):
        ensure_sheet_formats(conn)
        ensure_hpl_edges(conn)
        seed_uu_variants(conn)

    yield conn
    conn.close()


def _uu_rows(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
        "SELECT v.*, d.business_id AS decor_code "
        "FROM variants v JOIN decors d ON d.id = v.decor_id "
        "WHERE v.business_id LIKE '%-PF-UU-%' "
        "ORDER BY v.business_id"
    ).fetchall()


def test_uu_variant_count(uu_db: sqlite3.Connection):
    """SC-wtuu-001"""
    rows = _uu_rows(uu_db)
    assert len(rows) == EXPECTED_UU_VARIANTS
    decors = {r["decor_code"] for r in rows}
    assert len(decors) == EXPECTED_UU_DECORS
    # 0190 has a PF-U-600 variant but is NOT in the Global Collection 2026
    # postformed table — no documented 2U availability, so no U-U variants.
    assert "0190" not in decors
    assert uu_db.execute(
        "SELECT COUNT(*) FROM variants WHERE business_id LIKE '0190-PF-UU-%'"
    ).fetchone()[0] == 0


def test_uu_format_900(uu_db: sqlite3.Connection):
    """SC-wtuu-002"""
    rows = uu_db.execute(
        "SELECT v.business_id, sf.slug, sf.length_mm, sf.width_mm "
        "FROM variants v JOIN sheet_formats sf ON sf.id = v.sheet_format_id "
        "WHERE v.business_id LIKE '%-PF-UU-900'"
    ).fetchall()
    assert len(rows) == EXPECTED_UU_DECORS
    for row in rows:
        assert row["slug"] == "4100x900", row["business_id"]
        assert row["length_mm"] == 4100
        assert row["width_mm"] == 900


def test_uu_format_1200(uu_db: sqlite3.Connection):
    """SC-wtuu-003"""
    rows = uu_db.execute(
        "SELECT v.business_id, sf.slug, sf.length_mm, sf.width_mm "
        "FROM variants v JOIN sheet_formats sf ON sf.id = v.sheet_format_id "
        "WHERE v.business_id LIKE '%-PF-UU-1200'"
    ).fetchall()
    assert len(rows) == EXPECTED_UU_DECORS
    for row in rows:
        assert row["slug"] == "4100x1200", row["business_id"]
        assert row["length_mm"] == 4100
        assert row["width_mm"] == 1200


def test_uu_thickness_38(uu_db: sqlite3.Connection):
    """SC-wtuu-004"""
    rows = _uu_rows(uu_db)
    assert rows, "no U-U variants seeded"
    for row in rows:
        # 38mm is the fixed postformed thickness (packing table, str. 43)
        assert row["thickness_mm"] == 38.0, row["business_id"]


def test_uu_edge_banding(uu_db: sqlite3.Connection):
    """SC-wtuu-005"""

    def edge_codes(variant_business_id: str) -> set[str]:
        return {
            r["code"]
            for r in uu_db.execute(
                "SELECT e.code FROM variant_edges ve "
                "JOIN edges e ON e.id = ve.edge_id "
                "JOIN variants v ON v.id = ve.variant_id "
                "WHERE v.business_id = ?",
                (variant_business_id,),
            ).fetchall()
        }

    for row in _uu_rows(uu_db):
        uu_codes = edge_codes(row["business_id"])
        u_codes = edge_codes(f"{row['decor_code']}-PF-U-600")
        # Every U-U variant carries edge banding...
        assert uu_codes, f"{row['business_id']} has no edge"
        # ...copied from its source U variant...
        assert uu_codes == u_codes, row["business_id"]
        # ...and the code is the manufacturer's HPL edge roll, whose code is
        # identical to the decor code ('Obrzeże HPL' column, str. 48).
        assert row["decor_code"] in uu_codes

    # "Both edges finished" is represented by the U-U profile row, since
    # variant_edges has no per-edge-position column (see seeder docstring).
    profile = uu_db.execute(
        "SELECT profiled_sides FROM worktop_profiles WHERE code = 'U-U'"
    ).fetchone()
    assert profile["profiled_sides"] == "front,back"


def test_uu_roles_worktop(uu_db: sqlite3.Connection):
    """SC-wtuu-006"""
    for row in _uu_rows(uu_db):
        assert json.loads(row["roles"]) == ["worktop"], row["business_id"]


def test_uu_business_id_pattern(uu_db: sqlite3.Connection):
    """SC-wtuu-007"""
    pattern = re.compile(r"^[A-Z0-9]+-PF-UU-(900|1200)$")
    for row in _uu_rows(uu_db):
        assert pattern.match(row["business_id"]), row["business_id"]
        # prefix is the decor's own business id (e.g. K201-PF-UU-900)
        assert row["business_id"].startswith(f"{row['decor_code']}-PF-UU-")
