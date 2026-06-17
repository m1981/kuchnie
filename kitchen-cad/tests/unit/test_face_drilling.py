"""Phase 1 tests: Face drilling / System 32 (TC-8.1, TC-8.2).

Covers:
- TC-8.1.x: Drill diameters (5, 8, 10, 15, 20, 25, 35mm)
- TC-8.2.x: Drill depths
- TC-8.3.x: Drill types (single, multi-step, counterbore)
- TC-8.5.x: Coordinate validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kitchen_cad.models import DrillFace, DrillPoint, DrillType


# ---------------------------------------------------------------------------
# TC-8.1: Drill diameters
# ---------------------------------------------------------------------------


class TestDrillDiameters:
    """TC-8.1: Verify all standard drill diameters."""

    @pytest.mark.parametrize(
        "diameter, drill_type, label",
        [
            (5.0, DrillType.SYSTEM_32, "TC-8.1.1_System32"),
            (8.0, DrillType.DOWEL_CONNECTOR, "TC-8.1.2_kolek"),
            (10.0, DrillType.SYSTEM_32, "TC-8.1.3_10mm"),
            (15.0, DrillType.MINIFIX, "TC-8.1.4_minifix"),
            (20.0, DrillType.SYSTEM_32, "TC-8.1.5_20mm"),
            (25.0, DrillType.SYSTEM_32, "TC-8.1.6_25mm"),
            (35.0, DrillType.HINGE_CUP, "TC-8.1.7_zawias"),
        ],
    )
    def test_valid_diameter(self, diameter: float, drill_type: DrillType, label: str):
        """Drill point accepts all standard diameters."""
        dp = DrillPoint(
            x=100.0,
            y=100.0,
            diameter=diameter,
            depth=10.0,
            face=DrillFace.INSIDE,
            drill_type=drill_type,
            label=label,
        )
        assert dp.diameter == diameter

    def test_zero_diameter_rejected(self):
        """Diameter 0 is rejected (gt=0 constraint)."""
        with pytest.raises(ValidationError, match="diameter"):
            DrillPoint(
                x=100.0,
                y=100.0,
                diameter=0.0,
                depth=10.0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
            )

    def test_negative_diameter_rejected(self):
        """Negative diameter is rejected."""
        with pytest.raises(ValidationError, match="diameter"):
            DrillPoint(
                x=100.0,
                y=100.0,
                diameter=-5.0,
                depth=10.0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
            )


# ---------------------------------------------------------------------------
# TC-8.2: Drill depths
# ---------------------------------------------------------------------------


class TestDrillDepths:
    """TC-8.2: Verify drill depth validation."""

    @pytest.mark.parametrize(
        "depth, label",
        [
            (5.0, "TC-8.2.1_5mm"),
            (8.0, "TC-8.2.2_8mm"),
            (10.0, "TC-8.2.3_10mm"),
            (12.0, "TC-8.2.4_12mm_minifix"),
            (13.5, "TC-8.2.5_13.5mm_zawias"),
            (15.0, "TC-8.2.6_15mm"),
            (20.0, "TC-8.2.7_20mm"),
        ],
    )
    def test_valid_depth(self, depth: float, label: str):
        """Drill point accepts all standard depths."""
        dp = DrillPoint(
            x=100.0,
            y=100.0,
            diameter=5.0,
            depth=depth,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
            label=label,
        )
        assert dp.depth == depth

    def test_through_hole_depth_zero(self):
        """TC-8.2.8: Through hole represented as depth=0."""
        dp = DrillPoint(
            x=100.0,
            y=100.0,
            diameter=5.0,
            depth=0,  # through hole
            face=DrillFace.INSIDE,
            drill_type=DrillType.HANDLE,
            label="TC-8.2.8_through",
        )
        assert dp.depth == 0

    def test_negative_depth_rejected(self):
        """Negative depth is rejected (ge=0 constraint)."""
        with pytest.raises(ValidationError, match="depth"):
            DrillPoint(
                x=100.0,
                y=100.0,
                diameter=5.0,
                depth=-1.0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
            )


# ---------------------------------------------------------------------------
# TC-8.3: Drill types
# ---------------------------------------------------------------------------


class TestDrillTypes:
    """TC-8.3: Verify all drill type variants."""

    def test_single_drill(self):
        """TC-8.3.1: Single drill — standard hole."""
        dp = DrillPoint(
            x=100.0,
            y=100.0,
            diameter=5.0,
            depth=10.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
        )
        assert dp.drill_type == DrillType.SYSTEM_32

    def test_hinge_cup_drill(self):
        """TC-8.3.2: Hinge cup drill — ∅35mm, depth 13mm."""
        dp = DrillPoint(
            x=5.0,
            y=356.0,
            diameter=35.0,
            depth=13.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.HINGE_CUP,
        )
        assert dp.drill_type == DrillType.HINGE_CUP
        assert dp.diameter == 35.0

    def test_minifix_drill(self):
        """TC-8.3.3: Minifix drill — ∅15mm."""
        dp = DrillPoint(
            x=37.0,
            y=100.0,
            diameter=15.0,
            depth=12.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.MINIFIX,
        )
        assert dp.drill_type == DrillType.MINIFIX
        assert dp.diameter == 15.0


# ---------------------------------------------------------------------------
# TC-8.5: Coordinate validation
# ---------------------------------------------------------------------------


class TestDrillCoordinates:
    """TC-8.5: Verify coordinate validation."""

    def test_origin_position(self):
        """TC-8.5.1: Drill at origin (0,0) is valid."""
        dp = DrillPoint(
            x=0.0,
            y=0.0,
            diameter=5.0,
            depth=10.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
        )
        assert dp.x == 0.0
        assert dp.y == 0.0

    def test_positive_coordinates(self):
        """TC-8.5.2: Positive coordinates are valid."""
        dp = DrillPoint(
            x=298.0,
            y=356.0,
            diameter=5.0,
            depth=10.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
        )
        assert dp.x == 298.0
        assert dp.y == 356.0

    def test_negative_x_rejected(self):
        """TC-8.5.3: Negative X is rejected."""
        with pytest.raises(ValidationError, match="x"):
            DrillPoint(
                x=-10.0,
                y=356.0,
                diameter=5.0,
                depth=10.0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
            )

    def test_negative_y_rejected(self):
        """TC-8.5.4: Negative Y is rejected."""
        with pytest.raises(ValidationError, match="y"):
            DrillPoint(
                x=298.0,
                y=-10.0,
                diameter=5.0,
                depth=10.0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
            )

    def test_large_coordinates(self):
        """TC-8.5.5: Large coordinates accepted (bounds check is pipeline's job)."""
        dp = DrillPoint(
            x=5000.0,
            y=5000.0,
            diameter=5.0,
            depth=10.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
        )
        assert dp.x == 5000.0  # Model doesn't validate against panel bounds


# ---------------------------------------------------------------------------
# TC-8.x: System 32 positions from drill_engine
# ---------------------------------------------------------------------------


class TestSystem32Positions:
    """Verify System 32 Y-position calculation."""

    def test_positions_for_720mm_panel(self):
        """Standard 720mm panel has correct System 32 positions."""
        from kitchen_cad.drill_engine import system32_y_positions

        positions = system32_y_positions(720.0)
        assert positions[0] == pytest.approx(37.0)
        # Every position should be 32mm apart
        for i in range(1, len(positions)):
            gap = positions[i] - positions[i - 1]
            assert gap == pytest.approx(32.0, abs=0.1)
        # Last position should be ≤ 720 - 37 = 683
        assert positions[-1] <= 683.0 + 0.1

    def test_positions_for_300mm_panel(self):
        """Short 300mm panel: fewer positions."""
        from kitchen_cad.drill_engine import system32_y_positions

        positions = system32_y_positions(300.0)
        assert positions[0] == pytest.approx(37.0)
        # 300 - 37 - 37 = 226mm usable → 226/32 = ~7 positions
        assert 7 <= len(positions) <= 8

    def test_positions_for_1000mm_panel(self):
        """Tall 1000mm panel: more positions."""
        from kitchen_cad.drill_engine import system32_y_positions

        positions = system32_y_positions(1000.0)
        assert positions[0] == pytest.approx(37.0)
        # 1000 - 37 - 37 = 926mm usable → 926/32 = ~29 positions
        assert 28 <= len(positions) <= 30

    def test_minimum_panel_height(self):
        """Panel shorter than 74mm has no positions."""
        from kitchen_cad.drill_engine import system32_y_positions

        positions = system32_y_positions(70.0)
        assert len(positions) == 0  # 70 < 37 + 37 = 74

    def test_exact_minimum_panel_height(self):
        """Panel exactly 74mm has one position at 37mm."""
        from kitchen_cad.drill_engine import system32_y_positions

        positions = system32_y_positions(74.0)
        assert len(positions) == 1
        assert positions[0] == pytest.approx(37.0)
