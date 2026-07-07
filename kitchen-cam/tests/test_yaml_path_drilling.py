"""Seam test: YAML fixture → kuchnie_core.decompose → kitchen-cam drilling.

The unit tests in this suite build CabinetInstance objects by hand (with
``hinges=HingeGeometry(...)`` set explicitly), so they never exercise the
real production path where cabinets come from the YAML loader. The 2026-07
cold review found doors got ZERO hinge drillings on that path — this file
keeps the whole seam covered.

Reference data (Blum CLIP top 110°, not derived from code under test):
  cup ⌀35 mm, cup depth 13 mm.
G01 fixture: two doors, 2 hinges each, first cup 100 mm from door edge,
18 mm fronts.
"""

from pathlib import Path

from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import load_cabinet
from kuchnie_core.model import PanelRole

from kitchen_cam.machining import apply_all_drilling

FIXTURES = Path(__file__).resolve().parents[2] / "kuchnie-core" / "fixtures"


def _drilled_g01_panels():
    cab = load_cabinet(FIXTURES / "G01.yaml")
    return apply_all_drilling(decompose(cab).panels, cab), cab


class TestG01DoorsGetHingeDrillings:

    def test_each_door_has_two_cups_and_four_screws(self):
        panels, _ = _drilled_g01_panels()
        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        assert len(doors) == 2
        for door in doors:
            cups = [op for op in door.machining_ops
                    if op.drill_type == "hinge_cup"]
            screws = [op for op in door.machining_ops
                      if op.drill_type == "hinge_screw"]
            assert len(cups) == 2, f"{door.name}: expected 2 hinge cups"
            assert len(screws) == 4

    def test_cup_geometry_is_blum_cliptop(self):
        panels, _ = _drilled_g01_panels()
        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        for door in doors:
            for op in door.machining_ops:
                if op.drill_type != "hinge_cup":
                    continue
                assert op.diameter_mm == 35
                assert op.depth_mm == 13

    def test_drill_depth_stays_inside_board(self):
        """Physical invariant: a cup drilled through an 18mm front is a
        ruined door."""
        panels, _ = _drilled_g01_panels()
        for p in panels:
            for op in p.machining_ops:
                if op.depth_mm:  # 0 = through-hole by convention
                    assert op.depth_mm < p.thickness_mm, (p.name, op.note)

    def test_hinge_ops_inside_panel_bounds(self):
        panels, _ = _drilled_g01_panels()
        doors = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        for door in doors:
            for op in door.machining_ops:
                assert 0 <= op.x_mm <= door.width_mm, (door.name, op.note)
                assert 0 <= op.y_mm <= door.height_mm, (door.name, op.note)

    def test_sides_still_get_system32(self):
        """Guard: the hinge fix must not disturb the System 32 columns."""
        panels, _ = _drilled_g01_panels()
        sides = [p for p in panels
                 if p.role in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE)]
        assert len(sides) == 2
        for side in sides:
            s32 = [op for op in side.machining_ops
                   if op.drill_type == "system32"]
            assert s32, f"{side.name}: System 32 column missing"
