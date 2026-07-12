"""Execution-path (seam) tests — YAML → decompose → serialize → export.

Every defect found in the 2026-07 cold review sat at a seam between two
modules that no test crossed. These tests apply CAD/CAM testing doctrine
to those seams:

  1. Round-trip contract — a Kitchen that survives JSON serialization must
     be BEHAVIOURALLY identical: ``decompose()`` of the round-tripped
     kitchen produces the same panels and machining ops as the original.
     Field-level equality is not enough; the consumer is the decomposer.

  2. Physical invariants — assert what the physics demands, not magic
     numbers: every drilling lies inside the panel bounds, an edging strip
     is exactly as long as the edge it covers, left/right side panels carry
     independent (non-aliased) op objects.

  3. Vendor reference data — Blum values are asserted straight from the
     catalogue sheet (LEGRABOX NL500 screw chart, CLIP top cup geometry).
     The test must never re-derive them with the formulas under test.
"""

from dataclasses import asdict
from pathlib import Path

import pytest

from kuchnie_core.decomposer import decompose
from kuchnie_core.export.edging_csv import collect_edging_rows
from kuchnie_core.loader import load_cabinet
from kuchnie_core.model import Kitchen, PanelRole, Row
from kuchnie_core.serialize import kitchen_from_json_str, kitchen_to_json_str

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

CABINET_FIXTURES = ["K01.yaml", "G01.yaml", "K02_legrabox.yaml"]


def _wrap(cab) -> Kitchen:
    """Minimal valid Kitchen around a single cabinet."""
    return Kitchen(rows=[Row(
        id="r1", label="seam-test", wall_width_mm=4000, wall_height_mm=2600,
        cabinets=[cab],
    )])


# ═════════════════════════════════════════════════════════════════
# F1 — JSON round-trip must preserve decompose() behaviour
# ═════════════════════════════════════════════════════════════════

class TestRoundTripContract:
    """serialize → deserialize is THE inter-component contract (ADR-004).

    home-builder-adapter writes this JSON; kitchen-cam and kitchen-erp
    read it. If nested specs come back as plain dicts, every attribute
    access downstream explodes.
    """

    @pytest.mark.parametrize("fixture", CABINET_FIXTURES)
    def test_nested_specs_are_rehydrated(self, fixture):
        cab = load_cabinet(FIXTURES / fixture)
        cab2 = kitchen_from_json_str(
            kitchen_to_json_str(_wrap(cab))
        ).rows[0].cabinets[0]

        # Same types in and out — never a bare dict.
        assert type(cab2.shelf_pins) is type(cab.shelf_pins)
        assert type(cab2.handles) is type(cab.handles)
        assert type(cab2.hinges) is type(cab.hinges)
        assert type(cab2.config) is type(cab.config)

    @pytest.mark.parametrize("fixture", CABINET_FIXTURES)
    def test_roundtripped_cabinet_decomposes_identically(self, fixture):
        cab = load_cabinet(FIXTURES / fixture)
        cab2 = kitchen_from_json_str(
            kitchen_to_json_str(_wrap(cab))
        ).rows[0].cabinets[0]

        original = decompose(cab)
        roundtripped = decompose(cab2)  # cold review: AttributeError here

        assert [asdict(p) for p in roundtripped.panels] == \
               [asdict(p) for p in original.panels]
        assert [asdict(a) for a in roundtripped.accessories] == \
               [asdict(a) for a in original.accessories]


# ═════════════════════════════════════════════════════════════════
# F2 — edging worklist length must equal the physical edge
# ═════════════════════════════════════════════════════════════════

class TestEdgingLengthInvariant:
    """The decomposer stores the true strip length on each EdgeBand.

    The CSV export must trust it. The derive-from-dimensions rule
    ("front → width") is only a fallback for panels whose bands carry
    no length — it is WRONG for carcass side panels, where the cabinet
    front edge runs along the panel's height axis.
    """

    @pytest.mark.parametrize("fixture", CABINET_FIXTURES)
    def test_rows_use_stored_band_length(self, fixture):
        result = decompose(load_cabinet(FIXTURES / fixture))
        rows = collect_edging_rows(result.panels)
        bands = {
            (p.id, side): band
            for p in result.panels
            for side, band in p.banded_edges.items()
        }
        for row in rows:
            band = bands[(row.panel_id, row.side)]
            if band.length_mm:
                assert row.length_mm == band.length_mm, (
                    f"{row.panel_id}/{row.side}: CSV says {row.length_mm}, "
                    f"decomposer stored {band.length_mm}"
                )

    def test_side_panel_front_edge_runs_along_height(self):
        """K01 side panel: 510 deep × 620 high, front edge banded.

        The banded strip covers the vertical front edge → 620 mm.
        Deriving 510 (panel width) would cut every strip 110 mm short.
        """
        result = decompose(load_cabinet(FIXTURES / "K01.yaml"))
        side = next(p for p in result.panels if p.role == PanelRole.LEFT_SIDE)
        row = next(
            r for r in collect_edging_rows([side]) if r.side == "front"
        )
        assert row.length_mm == side.height_mm


# ═════════════════════════════════════════════════════════════════
# F4 — LEGRABOX runner ops: independent, positioned, in-bounds
# ═════════════════════════════════════════════════════════════════

class TestLegraboxRunnerOps:
    """K02 fixture: 2 × LEGRABOX C, NL500, carcass 800×720×510, plinth 100.

    Reference data (never derived from code under test):
      * Blum NL500 screw chart: 46, 78, 110, 398 mm from front edge.
      * Fixture geometry: bottom panel 18 mm, drawer front heights 177 mm,
        Blum axis offset 37 mm → runner axes at 18 + 37 = 55 mm (S1) and
        55 + 177 = 232 mm (S2) above the side panel's bottom edge.
      * Sides also carry confirmat drills + the HDF groove (wk-38c32190);
        runner assertions filter by drill_type per ADR-012 §2.
      * Side panel: width 510 (= cabinet depth), height 620 (720 − 100).

    Axis convention (kitchen-cam, the op consumer):
      x_mm = distance from FRONT edge, y_mm = distance from BOTTOM edge.
    """

    BLUM_NL500_SCREW_X = {46.0, 78.0, 110.0, 398.0}
    RUNNER_Y = {55.0, 232.0}

    @pytest.fixture()
    def sides(self):
        result = decompose(load_cabinet(FIXTURES / "K02_legrabox.yaml"))
        left = next(p for p in result.panels if p.role == PanelRole.LEFT_SIDE)
        right = next(p for p in result.panels if p.role == PanelRole.RIGHT_SIDE)
        return left, right

    def test_sides_do_not_share_op_objects(self, sides):
        """Mirrored ops must be independent instances — downstream CAM
        mutates per-side (mirroring, face flips); aliasing corrupts both."""
        left, right = sides
        left_ids = {id(op) for op in left.machining_ops}
        right_ids = {id(op) for op in right.machining_ops}
        assert not left_ids & right_ids

    def test_screw_x_positions_match_blum_nl500_chart(self, sides):
        left, _ = sides
        runners = [op for op in left.machining_ops
                   if op.drill_type == "runner_screw"]
        assert {op.x_mm for op in runners} == self.BLUM_NL500_SCREW_X

    def test_each_drawer_has_its_own_runner_height(self, sides):
        left, right = sides
        for side in (left, right):
            runners = [op for op in side.machining_ops
                       if op.drill_type == "runner_screw"]
            assert {op.y_mm for op in runners} == self.RUNNER_Y

    def test_op_count_is_drawers_times_screws(self, sides):
        left, right = sides
        n = lambda p: len([op for op in p.machining_ops
                           if op.drill_type == "runner_screw"])
        assert n(left) == n(right) == 2 * 4

    def test_all_ops_inside_panel_bounds(self, sides):
        """Physical invariant: a drilling outside the board is scrap."""
        for side in sides:
            for op in side.machining_ops:
                r = op.diameter_mm / 2
                assert r <= op.x_mm <= side.width_mm - r, asdict(op)
                assert r <= op.y_mm <= side.height_mm - r, asdict(op)

    def test_ops_are_routable_by_drill_type(self, sides):
        """ADR-012 §2: downstream CAM filters by drill_type, not note text."""
        left, _ = sides
        assert {op.drill_type for op in left.machining_ops
                if op.type == "drill"} == {"runner_screw", "confirmat"}
