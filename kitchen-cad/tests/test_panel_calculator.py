"""Tests for panel_calculator — derive panel dimensions from CorpusSpec.

Naming convention in tests:
  W = external width, H = external height, D = external depth
  T = panel thickness, G = back groove depth, BT = back thickness
"""

from __future__ import annotations

import pytest

from kitchen_cad.models import EdgeSide, PanelRole, CorpusSpec
from kitchen_cad.panel_calculator import calculate_panels


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find(panels, role: PanelRole):
    """Return first panel with given role."""
    return next(p for p in panels if p.role == role)


def _find_all(panels, role: PanelRole):
    return [p for p in panels if p.role == role]


# ---------------------------------------------------------------------------
# Base door cabinet (800×720×510, T=18, G=8, BT=3)
# ---------------------------------------------------------------------------

class TestBaseDoorCabinet:
    """Expected panels for K01 (800×720×510, 1 shelf):
      - 2× side  (510 × 720 × 18)
      - 1× top   (764 × 502 × 18)
      - 1× bottom(764 × 502 × 18)
      - 1× shelf (764 × 465 × 18)   ← D - G - 37 (System 32 front offset)
      - 1× back  (764 × 720 × 3)
      - 1× front door (794 × 714 × 18) ← W-2*gap × H-2*gap
    """

    def test_total_panel_count(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        assert len(panels) == 7  # 2 sides + top + bottom + shelf + back + front

    def test_two_side_panels(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        sides = _find_all(panels, PanelRole.LEFT_SIDE) + \
                _find_all(panels, PanelRole.RIGHT_SIDE)
        assert len(sides) == 2

    def test_side_panel_dimensions(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        left = _find(panels, PanelRole.LEFT_SIDE)
        assert left.width == 510   # depth
        assert left.height == 720  # height
        assert left.thickness == 18

    def test_top_bottom_dimensions(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        top = _find(panels, PanelRole.TOP)
        assert top.width == 800 - 2 * 18   # 764
        assert top.height == 510 - 8        # 502 (depth - groove)

    def test_shelf_dimensions(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        shelf = _find(panels, PanelRole.SHELF)
        assert shelf.width == 764
        assert shelf.height == 510 - 8 - 37  # 465

    def test_back_panel_dimensions(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        back = _find(panels, PanelRole.BACK)
        assert back.width == 764    # W - 2T
        assert back.height == 720   # H
        assert back.thickness == 3

    def test_front_door_dimensions(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        front = _find(panels, PanelRole.FRONT_DOOR)
        assert front.width == 800 - 2 * 3   # 794
        assert front.height == 720 - 2 * 3   # 714
        assert front.thickness == 18

    def test_front_door_uses_front_material(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        front = _find(panels, PanelRole.FRONT_DOOR)
        assert front.material == "U119_EM"

    def test_corpus_panels_use_corpus_material(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        corpus_panels = [
            p for p in panels
            if p.role not in (PanelRole.BACK, PanelRole.FRONT_DOOR)
        ]
        for p in corpus_panels:
            assert p.material == "U119_VL"


# ---------------------------------------------------------------------------
# Edge banding
# ---------------------------------------------------------------------------

class TestEdgeBanding:
    """Standard edge banding rules:
      - Side panels: top + front (2 edges)
      - Top/bottom: front (1 edge)
      - Shelf: front (1 edge)
      - Back: none
      - Front door: all 4 edges
    """

    def test_side_panel_has_two_banded_edges(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        left = _find(panels, PanelRole.LEFT_SIDE)
        assert len(left.edges) == 2
        sides = {e.side for e in left.edges}
        assert EdgeSide.TOP in sides
        assert EdgeSide.LEFT in sides

    def test_top_panel_has_one_banded_edge(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        top = _find(panels, PanelRole.TOP)
        assert len(top.edges) == 1

    def test_shelf_has_one_banded_edge(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        shelf = _find(panels, PanelRole.SHELF)
        assert len(shelf.edges) == 1

    def test_back_has_no_banded_edges(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        back = _find(panels, PanelRole.BACK)
        assert len(back.edges) == 0

    def test_front_door_has_four_banded_edges(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        front = _find(panels, PanelRole.FRONT_DOOR)
        assert len(front.edges) == 4

    def test_edge_material_matches_spec(self, base_door_spec):
        panels = calculate_panels(base_door_spec)
        for panel in panels:
            for edge in panel.edges:
                assert edge.material == "ABS_0.8"


# ---------------------------------------------------------------------------
# Drawer cabinet
# ---------------------------------------------------------------------------

class TestBaseDrawerCabinet:
    """K02 (800×720×510, 2 drawers):
      - 2× side, 1× top, 1× bottom, 1× back
      - 2× drawer front
    """

    def test_total_panel_count(self, base_drawer_spec):
        panels = calculate_panels(base_drawer_spec)
        assert len(panels) == 7  # 2 sides + top + bottom + back + 2 fronts

    def test_two_drawer_fronts(self, base_drawer_spec):
        panels = calculate_panels(base_drawer_spec)
        fronts = _find_all(panels, PanelRole.FRONT_DRAWER)
        assert len(fronts) == 2

    def test_drawer_front_width(self, base_drawer_spec):
        panels = calculate_panels(base_drawer_spec)
        fronts = _find_all(panels, PanelRole.FRONT_DRAWER)
        for f in fronts:
            assert f.width == 800 - 2 * 3  # 794

    def test_no_shelf_panels(self, base_drawer_spec):
        panels = calculate_panels(base_drawer_spec)
        shelves = _find_all(panels, PanelRole.SHELF)
        assert len(shelves) == 0


# ---------------------------------------------------------------------------
# Wall cabinet
# ---------------------------------------------------------------------------

class TestWallCabinet:
    def test_shelf_depth_uses_system32_offset(self, wall_door_spec):
        panels = calculate_panels(wall_door_spec)
        shelf = _find(panels, PanelRole.SHELF)
        assert shelf.height == 300 - 8 - 37  # 255

    def test_front_door_dimensions(self, wall_door_spec):
        panels = calculate_panels(wall_door_spec)
        front = _find(panels, PanelRole.FRONT_DOOR)
        assert front.width == 800 - 2 * 3
        assert front.height == 720 - 2 * 3


# ---------------------------------------------------------------------------
# Two-door variant
# ---------------------------------------------------------------------------

class TestTwoDoorCabinet:
    def test_two_fronts_when_two_doors(self):
        spec = CorpusSpec(
            id="K03",
            name="Szafka 2-drzwiowa",
            corpus_type="base_door",
            width=800, height=720, depth=510,
            doors=[2, 2],  # two doors, each with 2 hinges
            hinges=None,
        )
        panels = calculate_panels(spec)
        fronts = _find_all(panels, PanelRole.FRONT_DOOR)
        assert len(fronts) == 2
        # Each door: (800 - 3*3) / 2 = 791/2 = 395.5
        assert fronts[0].width == pytest.approx(395.5)
