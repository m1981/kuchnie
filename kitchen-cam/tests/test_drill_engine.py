"""Tests for machining.py — System 32 + hinge + handle drill positions.

All tests use kuchnie_core.CabinetInstance and kuchnie_core.decomposer
directly (ADR-010 migration complete).
"""

from __future__ import annotations

import pytest

from kuchnie_core.model import CabinetInstance, HandleSpec, PanelRole
from kuchnie_core.decomposer import decompose
from kitchen_cam.machining import (
    SYSTEM32_OFFSET,
    SYSTEM32_SPACING,
    apply_handles,
    apply_hinges,
    apply_system32,
    apply_all_drilling,
    system32_y_positions,
    _shelf_pin_offsets,
    _hinge_positions,
)


# ---------------------------------------------------------------------------
# System 32 — Y position calculator
# ---------------------------------------------------------------------------

class TestShelfPinOffsets:
    """Shelf pin offset algorithm — symmetrical around anchor."""

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

    def test_620mm_high_panel(self):
        """H=620 (standard dolna_drzwiowa side): first at 37, 18 holes."""
        positions = system32_y_positions(620)
        assert positions[0] == pytest.approx(37.0)
        assert len(positions) == 18  # 620-37-37=546 → 546/32=17.06 → 18 holes


# ---------------------------------------------------------------------------
# System 32 — application to side panels
# ---------------------------------------------------------------------------

class TestApplySystem32:
    def test_side_panel_gets_system32_holes(self, base_door_cabinet):
        """Side panel should have System 32 drill ops."""
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        s32 = [op for op in left.machining_ops if op.drill_type == "system32"]
        # 620mm high → 18 System 32 positions
        assert len(s32) == 18

    def test_system32_x_is_37mm(self, base_door_cabinet):
        """All System 32 holes on side panel at X=37 from front edge."""
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        for op in left.machining_ops:
            if op.drill_type == "system32":
                assert op.x_mm == pytest.approx(37.0)

    def test_system32_diameter_is_5mm(self, base_door_cabinet):
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        for op in left.machining_ops:
            if op.drill_type == "system32":
                assert op.diameter_mm == 5.0

    def test_shelf_pins_added_for_shelf(self, base_door_cabinet):
        """Each shelf adds shelf-pin holes: 2 rows × 3 holes = 6 total."""
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        shelf_pins = [op for op in left.machining_ops if op.drill_type == "shelf_pin"]
        assert len(shelf_pins) == 6  # 2 rows × 3 holes (max_per_row=3)

    def test_shelf_pins_two_rows_at_correct_x(self, base_door_cabinet):
        """Front row at 50mm from front, back row at 80mm from back."""
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        shelf_pins = [op for op in left.machining_ops if op.drill_type == "shelf_pin"]
        front_pins = [op for op in shelf_pins if "front" in op.note]
        back_pins = [op for op in shelf_pins if "back" in op.note]
        assert len(front_pins) == 3
        assert len(back_pins) == 3
        # All front pins at X=50
        assert all(op.x_mm == pytest.approx(50.0) for op in front_pins)
        # All back pins at X = depth(510) - back_offset(80) = 430
        assert all(op.x_mm == pytest.approx(430.0) for op in back_pins)

    def test_shelf_pins_symmetrical_offsets(self, base_door_cabinet):
        """Shelf pin Y offsets are symmetrical: [0, +32, -32]."""
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        front_pins = [
            op for op in left.machining_ops
            if op.drill_type == "shelf_pin" and "front" in op.note
        ]
        ys = sorted(op.y_mm for op in front_pins)
        # shelf_pos = 352, thickness_side = 18 → base_y = 370
        base_y = 18 + 352
        assert ys[0] == pytest.approx(base_y - 32)
        assert ys[1] == pytest.approx(base_y)
        assert ys[2] == pytest.approx(base_y + 32)

    def test_shelf_pins_diameter_5mm(self, base_door_cabinet):
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        for op in left.machining_ops:
            if op.drill_type == "shelf_pin":
                assert op.diameter_mm == 5.0

    def test_shelf_pins_depth_8mm(self, base_door_cabinet):
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        for op in left.machining_ops:
            if op.drill_type == "shelf_pin":
                assert op.depth_mm == 8.0

    def test_both_sides_get_same_pattern(self, base_door_cabinet):
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        right = next(p for p in panels if p.role == PanelRole.RIGHT_SIDE)
        left_s32 = [op for op in left.machining_ops if op.drill_type == "system32"]
        right_s32 = [op for op in right.machining_ops if op.drill_type == "system32"]
        assert len(left_s32) == len(right_s32)

    def test_no_system32_on_non_side_panels(self, base_door_cabinet):
        result = decompose(base_door_cabinet)
        panels = apply_system32(result.panels, base_door_cabinet)
        for p in panels:
            if p.role not in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE):
                s32 = [op for op in p.machining_ops if op.drill_type == "system32"]
                assert len(s32) == 0


# ---------------------------------------------------------------------------
# Hinge application (Blum CLIP top 35mm)
# ---------------------------------------------------------------------------

class TestApplyHinges:
    def test_front_gets_hinge_cup_holes(self, base_door_cabinet):
        """Front door should get hinge cup drill ops."""
        result = decompose(base_door_cabinet)
        panels = apply_hinges(result.panels, base_door_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        cups = [op for op in front.machining_ops if op.drill_type == "hinge_cup"]
        assert len(cups) == 2

    def test_cup_diameter_is_35mm(self, base_door_cabinet):
        result = decompose(base_door_cabinet)
        panels = apply_hinges(result.panels, base_door_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        for op in front.machining_ops:
            if op.drill_type == "hinge_cup":
                assert op.diameter_mm == 35.0

    def test_cup_depth_is_13mm(self, base_door_cabinet):
        result = decompose(base_door_cabinet)
        panels = apply_hinges(result.panels, base_door_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        for op in front.machining_ops:
            if op.drill_type == "hinge_cup":
                assert op.depth_mm == 13.0

    def test_cup_x_is_5mm_from_left_edge(self, base_door_cabinet):
        result = decompose(base_door_cabinet)
        panels = apply_hinges(result.panels, base_door_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        for op in front.machining_ops:
            if op.drill_type == "hinge_cup":
                assert op.x_mm == pytest.approx(5.0)

    def test_screw_holes_per_hinge(self, base_door_cabinet):
        """Each hinge cup gets 2 screw holes (Blum 45mm spacing)."""
        result = decompose(base_door_cabinet)
        panels = apply_hinges(result.panels, base_door_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        screws = [op for op in front.machining_ops if op.drill_type == "hinge_screw"]
        assert len(screws) == 4  # 2 hinges × 2 screws

    def test_screw_spacing_blum_45mm(self, base_door_cabinet):
        """Blum screws are 45mm apart (±22.5 from cup centre Y)."""
        result = decompose(base_door_cabinet)
        panels = apply_hinges(result.panels, base_door_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)

        cups = sorted(
            [op for op in front.machining_ops if op.drill_type == "hinge_cup"],
            key=lambda o: o.y_mm,
        )
        screws = sorted(
            [op for op in front.machining_ops if op.drill_type == "hinge_screw"],
            key=lambda o: o.y_mm,
        )

        # First hinge: screws should be at cup_y ± 22.5
        cup_y = cups[0].y_mm
        assert screws[0].y_mm == pytest.approx(cup_y - 22.5)
        assert screws[1].y_mm == pytest.approx(cup_y + 22.5)

    def test_first_hinge_at_100mm_from_bottom(self, base_door_cabinet):
        """Default: first hinge at 100mm from bottom of door."""
        result = decompose(base_door_cabinet)
        panels = apply_hinges(result.panels, base_door_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        cups = sorted(
            [op for op in front.machining_ops if op.drill_type == "hinge_cup"],
            key=lambda o: o.y_mm,
        )
        assert cups[0].y_mm == pytest.approx(100)

    def test_second_hinge_at_100mm_from_top(self, base_door_cabinet):
        """Default: second hinge at 100mm from top of door."""
        result = decompose(base_door_cabinet)
        panels = apply_hinges(result.panels, base_door_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        cups = sorted(
            [op for op in front.machining_ops if op.drill_type == "hinge_cup"],
            key=lambda o: o.y_mm,
        )
        # Front height = 614; top hinge at y = 614 - 100 = 514
        assert cups[-1].y_mm == pytest.approx(614 - 100)

    def test_no_hinges_when_spec_has_none(self):
        """Cabinet with no hinge geometry → no hinge ops."""
        cab = CabinetInstance(
            id="X", type="dolna_drzwiowa", description="No hinges",
            width_mm=600, height_mm=400, depth_mm=300,
            body_material="U119_VL", back_material="HDF_3mm_bialy",
            front_material="U119_EM",
            hinges=None,
            shelves=[],
            fronts=[{"id": "F1", "typ": "drzwiowy_lewy", "ilosc_zawiasow": 2}],
        )
        result = decompose(cab)
        panels = apply_hinges(result.panels, cab)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        assert len(front.machining_ops) == 0


# ---------------------------------------------------------------------------
# Handle application
# ---------------------------------------------------------------------------

class TestApplyHandles:
    def test_drawer_front_gets_handle_holes(self, base_drawer_cabinet):
        result = decompose(base_drawer_cabinet)
        panels = apply_handles(result.panels, base_drawer_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        handles = [op for op in front.machining_ops if op.drill_type == "handle"]
        assert len(handles) == 2  # two holes for a bar handle

    def test_handle_diameter_is_5mm(self, base_drawer_cabinet):
        result = decompose(base_drawer_cabinet)
        panels = apply_handles(result.panels, base_drawer_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        for op in front.machining_ops:
            if op.drill_type == "handle":
                assert op.diameter_mm == 5.0

    def test_handle_spacing_256mm(self, base_drawer_cabinet):
        result = decompose(base_drawer_cabinet)
        panels = apply_handles(result.panels, base_drawer_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        handles = sorted(
            [op for op in front.machining_ops if op.drill_type == "handle"],
            key=lambda o: o.x_mm,
        )
        spacing = handles[1].x_mm - handles[0].x_mm
        assert spacing == pytest.approx(256.0)

    def test_handle_centred_on_front(self, base_drawer_cabinet):
        """Handle holes should be symmetrically centred on the front."""
        result = decompose(base_drawer_cabinet)
        panels = apply_handles(result.panels, base_drawer_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        handles = sorted(
            [op for op in front.machining_ops if op.drill_type == "handle"],
            key=lambda o: o.x_mm,
        )
        centre = front.width_mm / 2
        midpoint = (handles[0].x_mm + handles[1].x_mm) / 2
        assert midpoint == pytest.approx(centre)

    def test_handle_y_centred_vertically(self, base_drawer_cabinet):
        result = decompose(base_drawer_cabinet)
        panels = apply_handles(result.panels, base_drawer_cabinet)
        front = next(p for p in panels if p.role == PanelRole.FRONT_DRAWER)
        handles = [op for op in front.machining_ops if op.drill_type == "handle"]
        expected_y = front.height_mm / 2
        for h in handles:
            assert h.y_mm == pytest.approx(expected_y)

    def test_no_handle_when_none(self):
        """No HandleSpec → no handle holes."""
        cab = CabinetInstance(
            id="X", type="dolna_szufladowa", description="No handles",
            width_mm=600, height_mm=720, depth_mm=510,
            body_material="U119_VL", back_material="HDF_3mm_bialy",
            front_material="U119_EM",
            handles=None,
            shelves=[],
            fronts=[{"id": "F1", "typ": "szufladowy"}],
            drawers=[{"id": "S1", "typ": "metabox", "wysokosc": 200}],
        )
        result = decompose(cab)
        panels = apply_handles(result.panels, cab)
        for p in panels:
            assert len(p.machining_ops) == 0


# ---------------------------------------------------------------------------
# Convenience: apply_all_drilling
# ---------------------------------------------------------------------------

class TestApplyAllDrilling:
    def test_all_drilling_applies_system32_hinges_handles(self, base_door_cabinet):
        """Full drilling pipeline: System32 + hinges (no handles on door)."""
        result = decompose(base_door_cabinet)
        panels = apply_all_drilling(result.panels, base_door_cabinet)

        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        s32 = [op for op in left.machining_ops if op.drill_type == "system32"]
        assert len(s32) > 0

        front = next(p for p in panels if p.role == PanelRole.FRONT_DOOR)
        cups = [op for op in front.machining_ops if op.drill_type == "hinge_cup"]
        assert len(cups) == 2

    def test_all_drilling_on_drawer_cabinet(self, base_drawer_cabinet):
        """Full drilling pipeline for drawer cabinet: System32 + handles."""
        result = decompose(base_drawer_cabinet)
        panels = apply_all_drilling(result.panels, base_drawer_cabinet)

        left = next(p for p in panels if p.role == PanelRole.LEFT_SIDE)
        s32 = [op for op in left.machining_ops if op.drill_type == "system32"]
        assert len(s32) > 0

        drawer_fronts = [p for p in panels if p.role == PanelRole.FRONT_DRAWER]
        for front in drawer_fronts:
            handles = [op for op in front.machining_ops if op.drill_type == "handle"]
            assert len(handles) == 2

    def test_idempotent(self, base_door_cabinet):
        """Running pipeline twice on same panels gives same results."""
        result = decompose(base_door_cabinet)
        panels1 = apply_all_drilling(result.panels, base_door_cabinet)
        panels2 = apply_all_drilling(result.panels, base_door_cabinet)

        assert len(panels1) == len(panels2)
        for p1, p2 in zip(panels1, panels2):
            assert p1.id == p2.id
            assert len(p1.machining_ops) == len(p2.machining_ops)


# ---------------------------------------------------------------------------
# Hinge position calculator (pure math)
# ---------------------------------------------------------------------------

class TestHingePositions:
    """Pure function tests for _hinge_positions."""

    def test_single_hinge_centered(self):
        positions = _hinge_positions(front_height=400.0, count=1, first_pos=100.0)
        assert len(positions) == 1
        assert positions[0] == pytest.approx(200.0)

    def test_two_hinges_symmetric(self):
        positions = _hinge_positions(front_height=614.0, count=2, first_pos=100.0)
        assert positions[0] == pytest.approx(100.0)
        assert positions[1] == pytest.approx(514.0)

    def test_three_hinges_evenly_spaced(self):
        positions = _hinge_positions(front_height=713.0, count=3, first_pos=100.0)
        assert len(positions) == 3
        assert positions[0] == pytest.approx(100.0)
        assert positions[2] == pytest.approx(613.0)
        expected_middle = (100.0 + 613.0) / 2
        assert positions[1] == pytest.approx(expected_middle, abs=1.0)

    def test_four_hinges_evenly_spaced(self):
        positions = _hinge_positions(front_height=1000.0, count=4, first_pos=100.0)
        assert len(positions) == 4
        assert positions[0] == pytest.approx(100.0)
        assert positions[3] == pytest.approx(900.0)
