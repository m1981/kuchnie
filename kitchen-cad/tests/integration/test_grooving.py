"""Phase 2 tests: Grooving / Wręgowanie (TC-4.2, TC-7.x).

Wręgowanie = routing a groove (slot) in a panel for back panel (HDF) insertion.

These tests define expected behavior for grooving functionality.
Features marked with xfail are not yet implemented.

Covers:
- TC-4.2: Groove + drill template
- TC-7.1: Groove parameters (depth, width)
- TC-7.2: Groove type (through / non-through)
- TC-7.3: Groove edge selection
- TC-7.4: Groove offset from edge
"""

from __future__ import annotations

import pytest

from kitchen_cad.models import (
    CorpusSpec,
    EdgeSide,
    Panel,
    PanelRole,
)


# ---------------------------------------------------------------------------
# Groove model (expected structure — TDD)
# ---------------------------------------------------------------------------


class TestGrooveModel:
    """TC-7.x: Groove specification model.

    These tests document the expected GrooveSpec model structure.
    Once implemented, the model should have these fields.
    """

    @pytest.mark.xfail(reason="GrooveSpec not yet implemented", strict=False)
    def test_groove_spec_exists(self):
        """TC-7.1.1: GrooveSpec model should exist."""
        from kitchen_cad.models import GrooveSpec
        groove = GrooveSpec(
            edge=EdgeSide.LEFT,
            depth=9.0,
            width=3.2,
            offset=8.0,
            groove_type="through",
        )
        assert groove.depth == 9.0
        assert groove.width == 3.2


# ---------------------------------------------------------------------------
# TC-7.1: Groove parameters
# ---------------------------------------------------------------------------


class TestGrooveParameters:
    """TC-7.1: Verify groove depth and width parameters."""

    @pytest.mark.parametrize(
        "depth, width, label",
        [
            (6.0, 3.2, "TC-7.1.1_shallow_6mm"),
            (8.0, 3.0, "TC-7.1.2_standard_8mm"),
            (9.0, 3.2, "TC-7.1.3_typical_9mm"),
            (10.0, 3.2, "TC-7.1.4_deep_10mm"),
            (12.0, 4.0, "TC-7.1.5_very_deep_12mm"),
        ],
    )
    @pytest.mark.xfail(reason="GrooveSpec not yet implemented", strict=False)
    def test_groove_depth_width(self, depth: float, width: float, label: str):
        """TC-7.1.1-5: Different groove depth × width combinations."""
        from kitchen_cad.models import GrooveSpec

        groove = GrooveSpec(
            edge=EdgeSide.LEFT,
            depth=depth,
            width=width,
            offset=8.0,
            groove_type="through",
        )
        assert groove.depth == depth
        assert groove.width == width

    @pytest.mark.parametrize(
        "width, back_thickness, label",
        [
            (3.2, 3.0, "TC-7.1.6_HDF_3mm_groove_3.2"),
            (2.8, 2.5, "TC-7.1.7_thin_HDF_2.5mm"),
            (4.0, 3.5, "TC-7.1.8_thick_back_3.5mm"),
        ],
    )
    @pytest.mark.xfail(reason="Groove-back compatibility check not implemented", strict=False)
    def test_groove_matches_back_thickness(self, width: float, back_thickness: float, label: str):
        """Groove width should be ≥ back panel thickness + 0.2mm clearance."""
        assert width >= back_thickness + 0.2, \
            f"Groove width {width}mm too narrow for back thickness {back_thickness}mm"


# ---------------------------------------------------------------------------
# TC-7.2: Groove types
# ---------------------------------------------------------------------------


class TestGrooveTypes:
    """TC-7.2: Through vs non-through grooves."""

    @pytest.mark.xfail(reason="GrooveSpec not yet implemented", strict=False)
    def test_through_groove(self):
        """TC-7.2.1: Through groove — runs full length of edge."""
        from kitchen_cad.models import GrooveSpec

        groove = GrooveSpec(
            edge=EdgeSide.LEFT,
            depth=9.0,
            width=3.2,
            offset=8.0,
            groove_type="through",
        )
        assert groove.groove_type == "through"

    @pytest.mark.xfail(reason="GrooveSpec not yet implemented", strict=False)
    def test_non_through_groove(self):
        """TC-7.2.2: Non-through groove — stops before edges (e.g. glass back)."""
        from kitchen_cad.models import GrooveSpec

        groove = GrooveSpec(
            edge=EdgeSide.LEFT,
            depth=9.0,
            width=3.2,
            offset=8.0,
            groove_type="non_through",
            stop_offset_start=50.0,  # 50mm from start
            stop_offset_end=50.0,    # 50mm from end
        )
        assert groove.groove_type == "non_through"


# ---------------------------------------------------------------------------
# TC-7.3: Groove edge selection
# ---------------------------------------------------------------------------


class TestGrooveEdgeSelection:
    """TC-7.3: Verify groove can be placed on any edge."""

    @pytest.mark.parametrize(
        "edge, label",
        [
            (EdgeSide.BOTTOM, "TC-7.3.1_bottom_bok"),
            (EdgeSide.TOP, "TC-7.3.2_top_dno"),
            (EdgeSide.RIGHT, "TC-7.3.3_right"),
            (EdgeSide.LEFT, "TC-7.3.4_left"),
        ],
    )
    @pytest.mark.xfail(reason="GrooveSpec not yet implemented", strict=False)
    def test_groove_on_each_edge(self, edge: EdgeSide, label: str):
        """TC-7.3.1-4: Groove can be specified on any edge."""
        from kitchen_cad.models import GrooveSpec

        groove = GrooveSpec(
            edge=edge,
            depth=9.0,
            width=3.2,
            offset=8.0,
            groove_type="through",
        )
        assert groove.edge == edge


# ---------------------------------------------------------------------------
# TC-7.4: Groove offset from edge
# ---------------------------------------------------------------------------


class TestGrooveOffset:
    """TC-7.4: Verify groove offset (distance from panel edge)."""

    @pytest.mark.parametrize(
        "offset, label",
        [
            (5.0, "TC-7.4.1_close_5mm"),
            (8.0, "TC-7.4.2_standard_8mm"),
            (10.0, "TC-7.4.3_deep_10mm"),
            (44.0, "TC-7.4.4_special_44mm"),
        ],
    )
    @pytest.mark.xfail(reason="GrooveSpec not yet implemented", strict=False)
    def test_groove_offset_values(self, offset: float, label: str):
        """TC-7.4.1-4: Different offset values from edge."""
        from kitchen_cad.models import GrooveSpec

        groove = GrooveSpec(
            edge=EdgeSide.LEFT,
            depth=9.0,
            width=3.2,
            offset=offset,
            groove_type="through",
        )
        assert groove.offset == offset


# ---------------------------------------------------------------------------
# TC-4.2: Groove + drill template
# ---------------------------------------------------------------------------


class TestGrooveDrillTemplate:
    """TC-4.2: Template combining grooving with drilling."""

    @pytest.mark.xfail(reason="Groove drill integration not yet implemented", strict=False)
    def test_bok_with_groove_and_system32(self):
        """TC-4.2.1: Side panel with groove for back + System 32 holes."""
        # Expected: side panel has groove on bottom edge (EdgeSide.BOTTOM)
        # AND System 32 holes on the face
        from kitchen_cad.models import GrooveSpec
        from kitchen_cad.drill_engine import apply_system32

        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_door",
            width=800,
            height=720,
            depth=510,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
        )

        # Create side panel
        panel = Panel(
            id="T-BOK-L",
            role=PanelRole.LEFT_SIDE,
            width=510.0,
            height=720.0,
            thickness=18.0,
            material="TEST",
        )

        # Apply System 32
        panels = apply_system32([panel], spec)
        assert len(panels[0].drill_points) > 0

        # TODO: Apply groove when implemented
        # groove = GrooveSpec(edge=EdgeSide.BOTTOM, depth=8.0, width=3.2, ...)
        # panels = apply_groove(panels, spec)
        # assert panel has groove annotation

    @pytest.mark.xfail(reason="Groove drill integration not yet implemented", strict=False)
    def test_groove_dimensions_match_spec(self):
        """TC-4.2.2: Groove depth matches back_groove_depth from CorpusSpec."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_door",
            width=800,
            height=720,
            depth=510,
            panel_thickness=18,
            back_thickness=3,
            back_groove_depth=8,
        )
        # Expected: groove depth = spec.back_groove_depth = 8mm
        assert spec.back_groove_depth == 8.0
        # Expected: groove width = spec.back_thickness + 0.2 = 3.2mm
        expected_width = spec.back_thickness + 0.2
        assert expected_width == pytest.approx(3.2, abs=0.1)


# ---------------------------------------------------------------------------
# Integration: Groove in panel_calculator
# ---------------------------------------------------------------------------


class TestGrooveInCalculator:
    """Verify panel_calculator accounts for groove in dimensions."""

    def test_horizontal_panel_height_accounts_for_groove(self):
        """Horizontal panels (top/bottom) have reduced height for groove."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_door",
            width=800,
            height=720,
            depth=510,
            panel_thickness=18,
            back_groove_depth=8,
        )
        from kitchen_cad.panel_calculator import _horizontal_panels

        panels = _horizontal_panels(spec)
        # Height = depth - back_groove_depth = 510 - 8 = 502
        for panel in panels:
            assert panel.height == pytest.approx(502.0, abs=0.1)

    def test_shelf_panel_height_accounts_for_groove_and_system32(self):
        """Shelf panels have reduced height for groove + System 32 offset."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_door",
            width=800,
            height=720,
            depth=510,
            panel_thickness=18,
            back_groove_depth=8,
            shelves=[352],
        )
        from kitchen_cad.panel_calculator import _shelf_panels

        panels = _shelf_panels(spec, spec.config.shelves)
        # Height = depth - back_groove_depth - 37 = 510 - 8 - 37 = 465
        for panel in panels:
            assert panel.height == pytest.approx(465.0, abs=0.1)
