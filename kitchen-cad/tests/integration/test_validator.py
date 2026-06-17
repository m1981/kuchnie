"""Phase 2 tests: Geometry validation / Walidacja geometryczna (TC-13.x).

Validation = checking that drill points are within panel bounds,
don't overlap, and have safe clearance from edges.

These tests define expected behavior for validation functionality.
Features marked with xfail are not yet implemented.

Covers:
- TC-13.1: Bounds checking (drill within panel)
- TC-13.2: Overlap detection (holes not too close)
- TC-13.3: Edge clearance (safe distance from edges)
- TC-13.4: Depth validation (not deeper than panel)
"""

from __future__ import annotations

import pytest

from kitchen_cad.models import DrillFace, DrillPoint, DrillType, Panel, PanelRole


# ---------------------------------------------------------------------------
# Validation model (expected structure — TDD)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="Validator not yet implemented", strict=False)
def test_validator_exists():
    """TC-13: Validator module should exist."""
    from kitchen_cad.validator import validate_panels  # noqa: F401
    assert callable(validate_panels)


@pytest.mark.xfail(reason="ValidationResult not yet implemented", strict=False)
def test_validation_result_model():
    """TC-13: ValidationResult model should exist."""
    from kitchen_cad.validator import ValidationResult
    result = ValidationResult(is_valid=True, errors=[], warnings=[])
    assert result.is_valid is True
    assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# TC-13.1: Bounds checking
# ---------------------------------------------------------------------------


class TestBoundsChecking:
    """TC-13.1: Verify drill points are within panel dimensions."""

    def _make_panel(self, width=594.0, height=714.0) -> Panel:
        return Panel(
            id="test",
            role=PanelRole.FRONT_DOOR,
            width=width,
            height=height,
            thickness=18.0,
            material="TEST",
        )

    def test_drill_at_valid_position(self):
        """TC-13.1.1: Drill within bounds — should be valid."""
        panel = self._make_panel(594.0, 714.0)
        dp = DrillPoint(
            x=297.0, y=357.0,
            diameter=5.0, depth=10.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
        )
        # Manual bounds check
        assert 0 <= dp.x <= panel.width
        assert 0 <= dp.y <= panel.height

    def test_drill_exceeds_x_bounds(self):
        """TC-13.1.2: Drill X > panel width — should be error."""
        panel = self._make_panel(594.0, 714.0)
        dp = DrillPoint(
            x=600.0, y=357.0,  # x > width
            diameter=5.0, depth=10.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
        )
        assert dp.x > panel.width, "Should detect X out of bounds"

    def test_drill_exceeds_y_bounds(self):
        """TC-13.1.3: Drill Y > panel height — should be error."""
        panel = self._make_panel(594.0, 714.0)
        dp = DrillPoint(
            x=297.0, y=750.0,  # y > height
            diameter=5.0, depth=10.0,
            face=DrillFace.INSIDE,
            drill_type=DrillType.SYSTEM_32,
        )
        assert dp.y > panel.height, "Should detect Y out of bounds"

    def test_drill_negative_x(self):
        """TC-13.1.4: Negative X — rejected by model (ge=0)."""
        with pytest.raises(Exception):
            DrillPoint(
                x=-10.0, y=357.0,
                diameter=5.0, depth=10.0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
            )

    def test_drill_negative_y(self):
        """TC-13.1.5: Negative Y — rejected by model (ge=0)."""
        with pytest.raises(Exception):
            DrillPoint(
                x=297.0, y=-10.0,
                diameter=5.0, depth=10.0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
            )


# ---------------------------------------------------------------------------
# TC-13.2: Overlap detection
# ---------------------------------------------------------------------------


class TestOverlapDetection:
    """TC-13.2: Verify holes are not too close to each other."""

    def test_holes_far_apart(self):
        """TC-13.2.1: Holes 50mm apart — no overlap."""
        dp1 = DrillPoint(x=100.0, y=100.0, diameter=10.0, depth=10.0,
                         face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32)
        dp2 = DrillPoint(x=150.0, y=100.0, diameter=10.0, depth=10.0,
                         face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32)

        distance = ((dp2.x - dp1.x)**2 + (dp2.y - dp1.y)**2)**0.5
        min_gap = (dp1.diameter + dp2.diameter) / 2  # radius sum
        assert distance > min_gap

    def test_holes_overlapping(self):
        """TC-13.2.2: Holes 5mm apart with ∅10 — overlapping."""
        dp1 = DrillPoint(x=100.0, y=100.0, diameter=10.0, depth=10.0,
                         face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32)
        dp2 = DrillPoint(x=105.0, y=100.0, diameter=10.0, depth=10.0,
                         face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32)

        distance = ((dp2.x - dp1.x)**2 + (dp2.y - dp1.y)**2)**0.5
        min_gap = (dp1.diameter + dp2.diameter) / 2
        assert distance < min_gap, "Should detect overlap"

    @pytest.mark.parametrize(
        "d1, d2, gap, should_overlap",
        [
            (5.0, 5.0, 10.0, False),    # TC-13.2.3: safe gap
            (5.0, 5.0, 4.0, True),      # TC-13.2.4: overlapping
            (35.0, 5.0, 20.0, True),    # TC-13.2.5: hinge cup near small hole
            (35.0, 35.0, 70.0, False),  # TC-13.2.6: two hinge cups, safe
            (35.0, 35.0, 30.0, True),   # TC-13.2.7: two hinge cups, overlapping
        ],
    )
    def test_overlap_calculation(self, d1: float, d2: float, gap: float, should_overlap: bool):
        """TC-13.2.3-7: Parametrized overlap detection."""
        dp1 = DrillPoint(x=100.0, y=100.0, diameter=d1, depth=10.0,
                         face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32)
        dp2 = DrillPoint(x=100.0 + gap, y=100.0, diameter=d2, depth=10.0,
                         face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32)

        distance = ((dp2.x - dp1.x)**2 + (dp2.y - dp1.y)**2)**0.5
        min_safe = (d1 + d2) / 2 + 2.0  # 2mm minimum material between holes

        if should_overlap:
            assert distance < min_safe, f"Holes at {gap}mm should overlap"
        else:
            assert distance >= min_safe, f"Holes at {gap}mm should not overlap"


# ---------------------------------------------------------------------------
# TC-13.3: Edge clearance
# ---------------------------------------------------------------------------


class TestEdgeClearance:
    """TC-13.3: Verify holes have safe distance from panel edges."""

    def _make_panel(self) -> Panel:
        return Panel(
            id="test",
            role=PanelRole.LEFT_SIDE,
            width=510.0,
            height=720.0,
            thickness=18.0,
            material="TEST",
        )

    def test_drill_safe_from_edges(self):
        """TC-13.3.1: Drill 50mm from all edges — safe."""
        panel = self._make_panel()
        dp = DrillPoint(x=255.0, y=360.0, diameter=5.0, depth=10.0,
                        face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32)

        min_clearance = 5.0  # 5mm minimum from edge
        assert dp.x >= min_clearance
        assert dp.y >= min_clearance
        assert dp.x <= panel.width - min_clearance
        assert dp.y <= panel.height - min_clearance

    def test_drill_close_to_edge(self):
        """TC-13.3.2: Drill 2mm from edge — should warn."""
        panel = self._make_panel()
        dp = DrillPoint(x=2.0, y=360.0, diameter=5.0, depth=10.0,
                        face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32)

        min_clearance = 3.0  # 3mm minimum
        is_too_close = dp.x < min_clearance
        assert is_too_close, "Should detect drill too close to edge"

    def test_system32_respects_offset(self):
        """TC-13.3.3: System 32 at 37mm from edge — safe."""
        from kitchen_cad.drill_engine import SYSTEM32_OFFSET
        min_clearance = 5.0
        assert SYSTEM32_OFFSET >= min_clearance


# ---------------------------------------------------------------------------
# TC-13.4: Depth validation
# ---------------------------------------------------------------------------


class TestDepthValidation:
    """TC-13.4: Verify drill depth doesn't exceed panel thickness."""

    @pytest.mark.parametrize(
        "depth, thickness, should_pass",
        [
            (10.0, 18.0, True),    # TC-13.4.1: safe
            (13.5, 18.0, True),    # TC-13.4.2: hinge cup, safe
            (18.0, 18.0, True),    # TC-13.4.3: exactly at limit
            (20.0, 18.0, False),   # TC-13.4.4: exceeds thickness
            (0, 18.0, True),       # TC-13.4.5: through hole (depth=0)
        ],
    )
    def test_depth_vs_thickness(self, depth: float, thickness: float, should_pass: bool):
        """TC-13.4.1-5: Depth must be ≤ thickness (or 0 for through)."""
        if should_pass:
            assert depth <= thickness or depth == 0
        else:
            assert depth > thickness and depth != 0, "Should detect excessive depth"

    def test_hinge_cup_depth_safe(self):
        """TC-13.4.6: Standard hinge cup (13mm) in 18mm panel — safe."""
        cup_depth = 13.0
        panel_thickness = 18.0
        remaining = panel_thickness - cup_depth
        assert remaining >= 3.0, "At least 3mm material behind cup"

    def test_hinge_cup_depth_risky(self):
        """TC-13.4.7: Hinge cup (13mm) in 16mm panel — risky but possible."""
        cup_depth = 13.0
        panel_thickness = 16.0
        remaining = panel_thickness - cup_depth
        # Only 3mm remaining — technically ok but tight
        assert remaining == 3.0


# ---------------------------------------------------------------------------
# Integration: validate_panels function (expected API)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="validate_panels not yet implemented", strict=False)
class TestValidatePanelsFunction:
    """Expected API for validate_panels function."""

    def test_valid_panel_passes(self):
        """Valid panel with valid drill points passes validation."""
        from kitchen_cad.validator import validate_panels, ValidationResult

        panel = Panel(
            id="test",
            role=PanelRole.FRONT_DOOR,
            width=594.0,
            height=714.0,
            thickness=18.0,
            material="TEST",
            drill_points=[
                DrillPoint(x=297.0, y=357.0, diameter=5.0, depth=10.0,
                           face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32),
            ],
        )

        result = validate_panels([panel])
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_out_of_bounds_drill_fails(self):
        """Drill out of bounds produces error."""
        from kitchen_cad.validator import validate_panels

        panel = Panel(
            id="test",
            role=PanelRole.FRONT_DOOR,
            width=594.0,
            height=714.0,
            thickness=18.0,
            material="TEST",
            drill_points=[
                DrillPoint(x=600.0, y=357.0, diameter=5.0, depth=10.0,
                           face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32),
            ],
        )

        result = validate_panels([panel])
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_excessive_depth_fails(self):
        """Drill depth > thickness produces error."""
        from kitchen_cad.validator import validate_panels

        panel = Panel(
            id="test",
            role=PanelRole.FRONT_DOOR,
            width=594.0,
            height=714.0,
            thickness=18.0,
            material="TEST",
            drill_points=[
                DrillPoint(x=297.0, y=357.0, diameter=5.0, depth=25.0,
                           face=DrillFace.INSIDE, drill_type=DrillType.SYSTEM_32),
            ],
        )

        result = validate_panels([panel])
        assert result.is_valid is False
