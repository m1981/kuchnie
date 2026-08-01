"""G13: dolna_legrabox emits the hardware accessories the cutlist/panels
already imply but the decomposer used to leave out (confirmat screws, euro
runner screws, plinth legs/clips, HDF back fasteners).

Every quantity is DERIVED, not hard-coded twice:
  * Konfirmat 7x50    -- counted from the confirmat through-drill ops the
                          decomposer actually emits (single source of
                          truth: catalog._count_confirmat_ops).
  * Wkret euro 6.3x13  -- 4 x runner cabinet-profiles (2 profiles per
                          drawer: left side + right side).
  * Nozka regulowana 100mm / Klips cokolu + zaczep -- x4 each, gated on
    plinth_height_mm > 0.
  * Zszywki/wkrety HDF -- 1 kpl, gated on an HDF back panel.

D60 fixture (600x820x560, plinth 100mm, drawers M/C/C @ NL500/40kg, HDF
back) is hand-built the same way
exercises/walking-skeleton-d60/run_production_leg.py's build_instance()
does on its hand-entered fallback path. Counts are pinned against the
owner-confirmed golden at
exercises/walking-skeleton-d60/reference/{bom,hardware-order}.csv:
Konfirmat=10, Wkret euro=24, Nozka=4, Klips=4, Zszywki HDF=1.

Gap: G13 (decomposer emits missing hardware accessories)
Spec: docs/specs/purchasing-variants.md (wk-593a317b)
"""
import pytest

from kuchnie_core.catalog import (
    _confirmat_accessory,
    _count_confirmat_ops,
    _euro_screw_accessory,
    _hdf_back_fastener_accessory,
    _plinth_hardware_accessories,
)
from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import load_cabinet
from kuchnie_core.model import CabinetInstance, MachiningOp
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def build_d60_cabinet() -> CabinetInstance:
    """Mirrors walking-skeleton-d60/run_production_leg.py's
    build_instance() hand-entered fallback exactly (no Blender leg
    output available)."""
    drawer_heights = [140, 287, 287]
    codes = ["M", "C", "C"]
    drawers = [
        {"id": f"S{i+1}", "height_code": c, "nl": 500, "capacity_kg": 40,
         "wysokosc": h}
        for i, (c, h) in enumerate(zip(codes, drawer_heights))
    ]
    fronts = [
        {"id": f"F{i+1}", "typ": "szufladowy", "powiazany": f"S{i+1}"}
        for i in range(3)
    ]
    return CabinetInstance(
        id="D60S3",
        type="dolna_legrabox",
        description="walking skeleton D60 (hand-entered)",
        width_mm=600,
        height_mm=820,
        depth_mm=560,
        body_material="PLYTA_BIALA_18",
        back_material="HDF_BIALA_3",
        front_material="K5307_18",
        thickness_back_mm=3,
        plinth_height_mm=100,
        drawers=drawers,
        fronts=fronts,
        edge_banding_type="abs",
    )


@pytest.fixture(scope="module")
def d60_result():
    return decompose(build_d60_cabinet())


def _accessory(result, name):
    return next(a for a in result.accessories if a.name == name)


# ── D60: confirmat count is DERIVED and equals 10 ───────────────

def test_d60_confirmat_op_count_is_10(d60_result):
    """Single source of truth check: count the confirmat ops the
    decomposer actually emitted (not a hard-coded expectation)."""
    ops = [
        op for p in d60_result.panels for op in p.machining_ops
        if op.drill_type == "confirmat"
    ]
    assert len(ops) == 10


def test_d60_konfirmat_accessory_matches_derived_op_count(d60_result):
    ops_count = sum(
        1 for p in d60_result.panels for op in p.machining_ops
        if op.drill_type == "confirmat"
    )
    konfirmat = _accessory(d60_result, "Konfirmat 7x50")
    assert konfirmat.quantity == ops_count == 10
    assert konfirmat.type == "fastener"


# ── D60: full accessory pin against the golden ──────────────────

def test_d60_wkret_euro_quantity_is_24(d60_result):
    """4 x runner cabinet-profiles; D60 has 3 drawers x 2 profiles = 6
    profiles -> 24 screws."""
    wkret = _accessory(d60_result, "Wkret euro 6.3x13")
    assert wkret.quantity == 24
    assert wkret.type == "fastener"


def test_d60_plinth_hardware_quantities_are_4_each(d60_result):
    nozka = _accessory(d60_result, "Nozka regulowana 100 mm")
    klips = _accessory(d60_result, "Klips cokolu + zaczep")
    assert nozka.quantity == 4
    assert nozka.type == "leg"
    assert klips.quantity == 4
    assert klips.type == "plinth_clip"


def test_d60_hdf_back_fastener_quantity_is_1_kpl(d60_result):
    hdf = _accessory(d60_result, "Zszywki/wkrety HDF")
    assert hdf.quantity == 1
    assert hdf.type == "fastener"


def test_d60_g13_accessory_names_are_exactly_the_golden_set(d60_result):
    """No more, no fewer than the five G13 names (plus the pre-existing
    LEGRABOX runner accessories) -- catches accidental duplicates."""
    g13_names = {
        "Konfirmat 7x50", "Wkret euro 6.3x13", "Nozka regulowana 100 mm",
        "Klips cokolu + zaczep", "Zszywki/wkrety HDF",
    }
    present = {a.name for a in d60_result.accessories}
    assert g13_names <= present
    for name in g13_names:
        matches = [a for a in d60_result.accessories if a.name == name]
        assert len(matches) == 1, f"{name!r} should appear exactly once"


# ── Gating: plinth hardware off when plinth_height_mm == 0 ──────

def test_plinth_hardware_absent_when_no_plinth():
    cab = build_d60_cabinet()
    cab.plinth_height_mm = 0
    result = decompose(cab)
    names = {a.name for a in result.accessories}
    assert "Nozka regulowana 100 mm" not in names
    assert "Klips cokolu + zaczep" not in names
    # cokół panel itself is also gated on plinth_height_mm > 0
    assert not any(p.name == "Cokół" for p in result.panels)


def test_plinth_hardware_helper_returns_empty_for_zero_plinth():
    cab = build_d60_cabinet()
    cab.plinth_height_mm = 0
    assert _plinth_hardware_accessories(cab) == []


# ── Gating: HDF fastener off when back is not HDF ────────────────

def test_hdf_fastener_absent_when_back_is_not_hdf():
    cab = build_d60_cabinet()
    cab.back_material = "PLYTA_BIALA_3"  # plain board back, not HDF
    result = decompose(cab)
    names = {a.name for a in result.accessories}
    assert "Zszywki/wkrety HDF" not in names


def test_hdf_fastener_helper_returns_none_for_non_hdf_back():
    cab = build_d60_cabinet()
    cab.back_material = "PLYTA_BIALA_3"
    assert _hdf_back_fastener_accessory(cab) is None


def test_hdf_fastener_helper_is_case_insensitive():
    cab = build_d60_cabinet()
    cab.back_material = "hdf_biala_3"
    acc = _hdf_back_fastener_accessory(cab)
    assert acc is not None
    assert acc.name == "Zszywki/wkrety HDF"


# ── Shared helpers: direct unit coverage (reusable by other dolna_*) ──

def test_count_confirmat_ops_sums_across_lists():
    ops_a = [MachiningOp(type="drill", drill_type="confirmat"),
             MachiningOp(type="drill", drill_type="confirmat")]
    ops_b = [MachiningOp(type="drill", drill_type="confirmat"),
             MachiningOp(type="drill", drill_type="runner_screw")]
    assert _count_confirmat_ops([ops_a, ops_b]) == 3


def test_count_confirmat_ops_empty():
    assert _count_confirmat_ops([[], []]) == 0


def test_confirmat_accessory_quantity_matches_op_count():
    cab = build_d60_cabinet()
    ops = [MachiningOp(type="drill", drill_type="confirmat") for _ in range(7)]
    acc = _confirmat_accessory(cab, [ops])
    assert acc.quantity == 7
    assert acc.name == "Konfirmat 7x50"


def test_euro_screw_accessory_is_4x_profiles():
    cab = build_d60_cabinet()
    acc = _euro_screw_accessory(cab, n_profiles=6)
    assert acc.quantity == 24
    acc0 = _euro_screw_accessory(cab, n_profiles=0)
    assert acc0.quantity == 0


# ── K02 (2-drawer legrabox fixture): quantities scale correctly ─

def test_k02_wkret_euro_scales_to_drawer_count():
    """K02 has 2 LEGRABOX drawers -> 4 profiles -> 16 euro screws."""
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    wkret = next(a for a in result.accessories if a.name == "Wkret euro 6.3x13")
    assert wkret.quantity == 16


def test_k02_confirmat_accessory_matches_derived_op_count():
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    ops_count = sum(
        1 for p in result.panels for op in p.machining_ops
        if op.drill_type == "confirmat"
    )
    konfirmat = next(a for a in result.accessories if a.name == "Konfirmat 7x50")
    assert konfirmat.quantity == ops_count
    assert ops_count == 5 * 2  # per-side 5 confirmat ops (K02 test already
    # pins 5/side in test_legrabox.py::test_K02_has_machining_ops) x 2 sides


def test_k02_plinth_hardware_present_and_hdf_fastener_present():
    """K02 has nozki (plinth 100mm) and an HDF back -- both gated
    accessories should appear."""
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    names = {a.name for a in result.accessories}
    assert "Nozka regulowana 100 mm" in names
    assert "Klips cokolu + zaczep" in names
    assert "Zszywki/wkrety HDF" in names


def test_k02_accessory_counts_unaffected_for_pre_existing_types():
    """G13 must not disturb the pre-existing runner/handle accessories
    test_legrabox.py::test_K02_accessories already pins."""
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    runners = [a for a in result.accessories if a.type == "runner"]
    handles = [a for a in result.accessories if a.type == "handle"]
    assert len(runners) == 2
    assert len(handles) == 1
