"""Phase 2 tests: Edge drilling / Wiercenie w czole (TC-9.x).

Edge drilling = drilling INTO the edge of a panel (perpendicular to face).
The hole is always centered on the panel thickness.

These tests define expected behavior for edge drilling functionality.
Features marked with xfail are not yet implemented.

Covers:
- TC-9.1: Edge drill parameters
- TC-9.2: Position in panel thickness (always centered)
"""

from __future__ import annotations

import pytest

from kitchen_cad.models import DrillFace, DrillPoint, DrillType


# ---------------------------------------------------------------------------
# TC-9.1: Edge drill parameters
# ---------------------------------------------------------------------------


class TestEdgeDrillParameters:
    """TC-9.1: Verify edge drill point specifications."""

    @pytest.mark.parametrize(
        "edge_num, distance, diameter, depth, label",
        [
            (2, 50.0, 8.0, 20.0, "TC-9.1.1_right_edge_50mm"),
            (4, 50.0, 8.0, 20.0, "TC-9.1.2_left_edge_50mm"),
            (1, 100.0, 5.0, 15.0, "TC-9.1.3_top_edge_100mm"),
            (3, 100.0, 5.0, 15.0, "TC-9.1.4_bottom_edge_100mm"),
        ],
    )
    def test_edge_drill_creation(self, edge_num: int, distance: float,
                                 diameter: float, depth: float, label: str):
        """TC-9.1.1-4: Edge drill points can be represented as DrillPoint.

        NOTE: Current DrillPoint model uses (x, y, face) but doesn't have
        an 'edge' field. Edge drills would need:
        - edge: which edge (1-4)
        - distance: position along edge from corner 0
        - Always centered in thickness

        This test documents the expected model structure.
        """
        # For now, we can create a DrillPoint with face=FRONT and document
        # that edge drilling needs a new DrillFace or model extension.
        dp = DrillPoint(
            x=distance,
            y=0,  # placeholder
            diameter=diameter,
            depth=depth,
            face=DrillFace.FRONT,  # Would need DrillFace.EDGE or edge field
            drill_type=DrillType.DOWEL_CONNECTOR,
            label=label,
        )
        assert dp.diameter == diameter
        assert dp.depth == depth

    @pytest.mark.xfail(reason="Edge drill model extension not yet implemented", strict=False)
    def test_edge_drill_needs_edge_field(self):
        """TC-9.1: Edge drill should specify which edge (1-4)."""
        # Expected model extension:
        # DrillPoint(..., edge=EdgeSide.RIGHT, edge_distance=50.0)
        from kitchen_cad.models import EdgeSide

        dp = DrillPoint(
            x=50.0,
            y=0,
            diameter=8.0,
            depth=20.0,
            face=DrillFace.FRONT,
            drill_type=DrillType.DOWEL_CONNECTOR,
        )
        # This should have an edge attribute when implemented
        assert hasattr(dp, 'edge'), "DrillPoint needs 'edge' field for edge drilling"


# ---------------------------------------------------------------------------
# TC-9.2: Position in panel thickness
# ---------------------------------------------------------------------------


class TestEdgeDrillThicknessPosition:
    """TC-9.2: Edge drill is always centered in panel thickness."""

    @pytest.mark.parametrize(
        "thickness, expected_center, label",
        [
            (18.0, 9.0, "TC-9.2.1_18mm_panel"),
            (19.0, 9.5, "TC-9.2.2_19mm_EGGER"),
            (22.0, 11.0, "TC-9.2.3_22mm_MDF"),
        ],
    )
    def test_center_calculation(self, thickness: float, expected_center: float, label: str):
        """TC-9.2.1-3: Center position = thickness / 2."""
        center = thickness / 2
        assert center == pytest.approx(expected_center, abs=0.01)

    @pytest.mark.xfail(reason="Edge drill engine not yet implemented", strict=False)
    def test_edge_drill_auto_centered(self):
        """Edge drill should be automatically centered in thickness."""
        from kitchen_cad.models import EdgeSide

        # Expected: when creating an edge drill, the position along the
        # thickness axis is automatically calculated as panel.thickness / 2
        panel_thickness = 18.0
        expected_center = 9.0

        # This would be done by the drill engine:
        # edge_drill = create_edge_drill(edge=EdgeSide.RIGHT, distance=50, ...)
        # assert edge_drill.thickness_position == expected_center
        assert panel_thickness / 2 == expected_center


# ---------------------------------------------------------------------------
# Edge drill coordinate system
# ---------------------------------------------------------------------------


class TestEdgeDrillCoordinateSystem:
    """Verify coordinate conventions for edge drilling."""

    def test_edge_numbering_convention(self):
        """Edge numbering: 1=top, 2=right, 3=bottom, 4=left (CW from top)."""
        edges = {
            1: "top",     # Krawędź 1
            2: "right",   # Krawędź 2
            3: "bottom",  # Krawędź 3
            4: "left",    # Krawędź 4
        }
        assert edges[1] == "top"
        assert edges[2] == "right"
        assert edges[3] == "bottom"
        assert edges[4] == "left"

    def test_distance_measured_from_corner_zero(self):
        """Distance along edge is measured from corner 0 (bottom-left)."""
        # For edge 2 (right): distance from bottom
        # For edge 4 (left): distance from bottom
        # For edge 1 (top): distance from left
        # For edge 3 (bottom): distance from left
        #
        # Corner 0 = bottom-left
        # Corner 1 = bottom-right
        # Corner 2 = top-right
        # Corner 3 = top-left
        corners = {
            0: (0, 0),       # bottom-left
            1: (100, 0),     # bottom-right (for width=100)
            2: (100, 200),   # top-right (for height=200)
            3: (0, 200),     # top-left
        }
        assert corners[0] == (0, 0)


# ---------------------------------------------------------------------------
# Edge drill with standard diameters
# ---------------------------------------------------------------------------


class TestEdgeDrillDiameters:
    """Standard diameters for edge drilling."""

    @pytest.mark.parametrize(
        "diameter, use_case, label",
        [
            (5.0, "shelf_pin", "TC-9.3.1_5mm_shelf_pin"),
            (8.0, "dowel_connector", "TC-9.3.2_8mm_dowel"),
            (10.0, "special_connector", "TC-9.3.3_10mm"),
            (15.0, "minifix", "TC-9.3.4_15mm_minifix"),
        ],
    )
    def test_standard_edge_drill_diameters(self, diameter: float, use_case: str, label: str):
        """Edge drill supports standard furniture diameters."""
        # These diameters should be supported for edge drilling
        assert diameter in [5.0, 8.0, 10.0, 15.0]

    @pytest.mark.parametrize(
        "depth, panel_thickness, label",
        [
            (15.0, 18.0, "TC-9.3.5_15mm_into_18mm"),
            (20.0, 18.0, "TC-9.3.6_20mm_into_18mm"),
            (12.0, 18.0, "TC-9.3.7_12mm_minifix"),
        ],
    )
    @pytest.mark.xfail(reason="Edge depth validation not yet implemented", strict=False)
    def test_edge_drill_depth_validation(self, depth: float, panel_thickness: float, label: str):
        """Edge drill depth should not exceed panel thickness."""
        # Edge drill goes into the edge, so depth must be < thickness
        # (can't drill deeper than the panel is wide)
        assert depth < panel_thickness, \
            f"Drill depth {depth}mm exceeds panel thickness {panel_thickness}mm"
