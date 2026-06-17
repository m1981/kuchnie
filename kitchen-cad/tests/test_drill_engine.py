"""Tests for drill_engine — System 32 + hinge drill positions."""

from __future__ import annotations

import pytest

from kitchen_cad.models import (
    DrillFace,
    DrillPoint,
    DrillType,
    Panel,
    PanelRole,
)
from kitchen_cad.panel_calculator import calculate_panels
from kitchen_cad.drill_engine import (
    apply_handles,
    apply_hinges,
    apply_system32,
    system32_y_positions,
    _shelf_pin_offsets,
)


# ---------------------------------------------------------------------------
# System 32 — Y position calculator
# ---------------------------------------------------------------------------

class TestShelfPinOffsets:
    """Shelf pin offset algorithm from Corpus .cmk reference."""

    def test_three_per_row(self):
        """max_per_row=3 → offsets [0, +32, -32]."""
        offsets = _shelf_pin_offsets(3)
        assert offsets == [0.0, 32.0, -32.0]

    def test_five_per_row(self):
        """max_per_row=5 → offsets [0, +32, -32, +64, -64]."""
        offsets = _shelf_pin_offsets(5)
        assert offsets == [0.0, 32.0, -32.0, 64.0, -64.0]

    def test_one_per_row(self):
        """max_per_row=1 → just the anchor."""
        offsets = _shelf_pin_offsets(1)
        assert offsets == [0.0]


class TestSystem32Positions:
    """System 32 holes start at 37 mm from each end, spaced 32 mm apart."""

    def test_720mm_high_panel(self):
        """H=720: first at 37, last at 677, 21 holes."""
        positions = system32_y_positions(720)
        assert positions[0] == pytest.approx(37.0)
        assert positions[-1] == pytest.approx(677.0)
        assert len(positions) == 21

    def test_560mm_high_panel(self):
        """H=560: first at 37, last at 517, 16 holes."""
        positions = system32_y_positions(560)
        assert positions[0] == pytest.approx(37.0)
        assert positions[-1] == pytest.approx(517.0)
        assert len(positions) == 16

    def test_spacing_is_32mm(self):
        positions = system32_y_positions(720)
        for a, b in zip(positions, positions[1:]):
            assert b - a == pytest.approx(32.0)

    def test_small_panel_200mm(self):
        """H=200: holes at 37, 69, 101, 133, 165 — 5 holes."""
        positions = system32_y_positions(200)
        assert positions[0] == 37
        assert all(y <= 200 - 37 for y in positions)


# ---------------------------------------------------------------------------
# System 32 — application to side panels
# ---------------------------------------------------------------------------

class TestApplySystem32:
    def test_side_panel_gets_system32_holes(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        s32 = [dp for dp in left.drill_points if dp.drill_type == DrillType.SYSTEM_32]
        assert len(s32) == 21  # 720mm → 21 holes

    def test_system32_x_is_37mm(self, base_door_spec):
        """All System 32 holes on side panel at X=37 from front edge."""
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        for dp in left.drill_points:
            if dp.drill_type == DrillType.SYSTEM_32:
                assert dp.x == pytest.approx(37.0)

    def test_system32_diameter_is_5mm(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        for dp in left.drill_points:
            if dp.drill_type == DrillType.SYSTEM_32:
                assert dp.diameter == 5.0

    def test_shelf_pins_added_for_shelf(self, base_door_spec):
        """Each shelf adds shelf-pin holes: 2 rows × 3 holes = 6 total."""
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        shelf_pins = [
            dp for dp in left.drill_points
            if dp.drill_type == DrillType.SHELF_PIN
        ]
        assert len(shelf_pins) == 6  # 2 rows × 3 holes (max_per_row=3)

    def test_shelf_pins_two_rows_at_correct_x(self, base_door_spec):
        """Front row at 50mm from front, back row at 80mm from back."""
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        shelf_pins = [
            dp for dp in left.drill_points
            if dp.drill_type == DrillType.SHELF_PIN
        ]
        front_pins = [dp for dp in shelf_pins if "front" in dp.label]
        back_pins = [dp for dp in shelf_pins if "back" in dp.label]
        assert len(front_pins) == 3
        assert len(back_pins) == 3
        # All front pins at X=50
        assert all(dp.x == pytest.approx(50.0) for dp in front_pins)
        # All back pins at X = 510 - 80 = 430
        assert all(dp.x == pytest.approx(430.0) for dp in back_pins)

    def test_shelf_pins_symmetrical_offsets(self, base_door_spec):
        """Shelf pin Y offsets are symmetrical: [0, +32, -32]."""
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        front_pins = [
            dp for dp in left.drill_points
            if dp.drill_type == DrillType.SHELF_PIN and "front" in dp.label
        ]
        ys = sorted(dp.y for dp in front_pins)
        base_y = 18 + 352  # panel_thickness + shelf_pos
        assert ys[0] == pytest.approx(base_y - 32)
        assert ys[1] == pytest.approx(base_y)
        assert ys[2] == pytest.approx(base_y + 32)

    def test_shelf_pins_diameter_5mm(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        for dp in left.drill_points:
            if dp.drill_type == DrillType.SHELF_PIN:
                assert dp.diameter == 5.0

    def test_shelf_pins_depth_8mm(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        for dp in left.drill_points:
            if dp.drill_type == DrillType.SHELF_PIN:
                assert dp.depth == 8.0

    def test_both_sides_get_same_pattern(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        right = next(p for p in panels if p.role == PanelRole.RIGHT_SIDE)
        left_s32 = [dp for dp in left.drill_points if dp.drill_type == DrillType.SYSTEM_32]
        right_s32 = [dp for dp in right.drill_points if dp.drill_type == DrillType.SYSTEM_32]
        assert len(left_s32) == len(right_s32)

    def test_no_system32_on_non_side_panels(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_system32(panels, base_door_spec)
        for p in panels:
            if p.role not in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE):
                s32 = [dp for dp in p.drill_points if dp.drill_type == DrillType.SYSTEM_32]
                assert len(s32) == 0


# ---------------------------------------------------------------------------
# Hinge application (Blum CLIP top 35mm)
# ---------------------------------------------------------------------------

class TestApplyHinges:
    def test_front_gets_hinge_cup_holes(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_hinges(panels, base_door_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        cups = [dp for dp in front.drill_points if dp.drill_type == DrillType.HINGE_CUP]
        assert len(cups) == 2

    def test_cup_diameter_is_35mm(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_hinges(panels, base_door_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        for dp in front.drill_points:
            if dp.drill_type == DrillType.HINGE_CUP:
                assert dp.diameter == 35.0

    def test_cup_depth_is_13mm(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_hinges(panels, base_door_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        for dp in front.drill_points:
            if dp.drill_type == DrillType.HINGE_CUP:
                assert dp.depth == 13.0

    def test_cup_x_is_5mm_from_left_edge(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_hinges(panels, base_door_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        for dp in front.drill_points:
            if dp.drill_type == DrillType.HINGE_CUP:
                assert dp.x == pytest.approx(5.0)

    def test_screw_holes_per_hinge(self, base_door_spec):
        """Each hinge cup gets 2 screw holes (Blum 45mm spacing)."""
        panels = calculate_panels(base_door_spec)
        panels = apply_hinges(panels, base_door_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        screws = [dp for dp in front.drill_points if dp.drill_type == DrillType.HINGE_SCREW]
        assert len(screws) == 4  # 2 hinges × 2 screws

    def test_screw_spacing_blum_45mm(self, base_door_spec):
        """Blum screws are 45mm apart (±22.5 from cup centre Y)."""
        panels = calculate_panels(base_door_spec)
        panels = apply_hinges(panels, base_door_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)

        cups = sorted(
            [dp for dp in front.drill_points if dp.drill_type == DrillType.HINGE_CUP],
            key=lambda d: d.y,
        )
        screws = sorted(
            [dp for dp in front.drill_points if dp.drill_type == DrillType.HINGE_SCREW],
            key=lambda d: d.y,
        )

        # First hinge: screws should be at cup_y ± 22.5
        cup_y = cups[0].y
        assert screws[0].y == pytest.approx(cup_y - 22.5)
        assert screws[1].y == pytest.approx(cup_y + 22.5)

    def test_first_hinge_at_100mm_from_top(self, base_door_spec):
        """Default: one hinge at 100mm from top, one at 100mm from bottom."""
        panels = calculate_panels(base_door_spec)
        panels = apply_hinges(panels, base_door_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        cups = sorted(
            [dp for dp in front.drill_points if dp.drill_type == DrillType.HINGE_CUP],
            key=lambda d: d.y,
        )
        # Front height = 714; top hinge at y = 714 - 100 = 614
        assert cups[-1].y == pytest.approx(714 - 100)

    def test_second_hinge_at_100mm_from_bottom(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        panels = apply_hinges(panels, base_door_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        cups = sorted(
            [dp for dp in front.drill_points if dp.drill_type == DrillType.HINGE_CUP],
            key=lambda d: d.y,
        )
        # Bottom hinge at y = 100
        assert cups[0].y == pytest.approx(100)

    def test_no_hinges_when_spec_has_none(self):
        from kitchen_cad.models import CorpusSpec
        spec = CorpusSpec(
            id="X", name="X", corpus_type="wall_door",
            width=600, height=400, depth=300, doors=[0],
        )
        panels = calculate_panels(spec)
        panels = apply_hinges(panels, spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        assert len(front.drill_points) == 0


# ---------------------------------------------------------------------------
# Handle application
# ---------------------------------------------------------------------------

class TestApplyHandles:
    def test_drawer_front_gets_handle_holes(self, base_drawer_spec):
        panels = calculate_panels(base_drawer_spec)
        panels = apply_handles(panels, base_drawer_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        handles = [dp for dp in front.drill_points if dp.drill_type == DrillType.HANDLE]
        assert len(handles) == 2  # two holes for a bar handle

    def test_handle_diameter_is_5mm(self, base_drawer_spec):
        panels = calculate_panels(base_drawer_spec)
        panels = apply_handles(panels, base_drawer_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        for dp in front.drill_points:
            if dp.drill_type == DrillType.HANDLE:
                assert dp.diameter == 5.0

    def test_handle_spacing_256mm(self, base_drawer_spec):
        panels = calculate_panels(base_drawer_spec)
        panels = apply_handles(panels, base_drawer_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        handles = sorted(
            [dp for dp in front.drill_points if dp.drill_type == DrillType.HANDLE],
            key=lambda d: d.x,
        )
        spacing = handles[1].x - handles[0].x
        assert spacing == pytest.approx(256.0)

    def test_handle_centred_on_front(self, base_drawer_spec):
        """Handle holes should be symmetrically centred on the front."""
        panels = calculate_panels(base_drawer_spec)
        panels = apply_handles(panels, base_drawer_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        handles = sorted(
            [dp for dp in front.drill_points if dp.drill_type == DrillType.HANDLE],
            key=lambda d: d.x,
        )
        centre = front.width / 2
        midpoint = (handles[0].x + handles[1].x) / 2
        assert midpoint == pytest.approx(centre)

    def test_handle_y_centred_vertically(self, base_drawer_spec):
        panels = calculate_panels(base_drawer_spec)
        panels = apply_handles(panels, base_drawer_spec)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        handles = [
            dp for dp in front.drill_points if dp.drill_type == DrillType.HANDLE
        ]
        expected_y = front.height / 2
        for h in handles:
            assert h.y == pytest.approx(expected_y)
