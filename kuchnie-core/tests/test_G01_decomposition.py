"""G01 — wall cabinet with doors (gorna_drzwiowa).

Proves: YAML load → decomposition → correct panels + accessories + BOM.

Expected panels (9):
  left side   300 × 720 × 18
  right side  300 × 720 × 18
  top         764 × 300 × 18
  bottom      764 × 300 × 18
  back        778 × 698 ×  3
  shelf P1    762 × 295 × 18
  shelf P2    762 × 295 × 18
  door F1     395.5 × 714 × 18
  door F2     395.5 × 714 × 18

Expected accessories (4):
  hinge F1 ×2 (blum_clip_35)
  hinge F2 ×2 (blum_clip_35)
  shelf pins ×8 (5mm)
  handles ×2 (relingowy)
"""

import pytest
from kuchnie_core.loader import load_cabinet
from kuchnie_core.decomposer import decompose
from kuchnie_core.bom import calculate_bom


# ── Loading ──────────────────────────────────────────────────────

def test_loads(g01_path):
    cab = load_cabinet(g01_path)
    assert cab.id == "G01"
    assert cab.type == "gorna_drzwiowa"
    assert cab.width_mm == 800
    assert cab.height_mm == 720
    assert cab.depth_mm == 300
    assert cab.plinth_height_mm == 0  # no plinth on wall cabinet


# ── Panel count ──────────────────────────────────────────────────

def test_panel_count(g01_path):
    result = decompose(load_cabinet(g01_path))
    assert len(result.panels) == 9


# ── Side panels ──────────────────────────────────────────────────

def test_side_dimensions(g01_path):
    result = decompose(load_cabinet(g01_path))
    sides = [p for p in result.panels if "bok" in p.name.lower()]
    assert len(sides) == 2
    for side in sides:
        assert side.height_mm == 720   # full height (no plinth)
        assert side.width_mm == 300
        assert side.thickness_mm == 18

def test_side_edge_banding(g01_path):
    result = decompose(load_cabinet(g01_path))
    sides = [p for p in result.panels if "bok" in p.name.lower()]
    for side in sides:
        assert side.banded_edges["front"].length_mm == 720
        assert len(side.banded_edges) == 1


# ── Top + Bottom ─────────────────────────────────────────────────

def test_top_bottom_count(g01_path):
    result = decompose(load_cabinet(g01_path))
    horiz = [p for p in result.panels if p.name in ("Góra", "Dno")]
    assert len(horiz) == 2

def test_top_bottom_dimensions(g01_path):
    result = decompose(load_cabinet(g01_path))
    horiz = [p for p in result.panels if p.name in ("Góra", "Dno")]
    for h in horiz:
        assert h.width_mm == 764     # 800 - 2×18
        assert h.height_mm == 300    # depth
        assert h.thickness_mm == 18


# ── Back panel ───────────────────────────────────────────────────

def test_back_dimensions(g01_path):
    result = decompose(load_cabinet(g01_path))
    back = next(p for p in result.panels if p.name == "Plecy")
    assert back.width_mm == 778    # 800 - 36 + 16 - 2 luz
    assert back.height_mm == 698   # 720 - 36 + 16 - 2 luz
    assert back.thickness_mm == 3
    assert back.banded_edges == {}


# ── Shelves ──────────────────────────────────────────────────────

def test_shelves_count(g01_path):
    result = decompose(load_cabinet(g01_path))
    shelves = [p for p in result.panels if "półka" in p.name.lower()]
    assert len(shelves) == 2

def test_shelf_dimensions(g01_path):
    result = decompose(load_cabinet(g01_path))
    shelves = [p for p in result.panels if "półka" in p.name.lower()]
    for s in shelves:
        assert s.width_mm == 762     # 764 - 2mm clearance
        assert s.height_mm == 295    # 300 - 5mm clearance from back
        assert s.thickness_mm == 18

def test_shelf_edge_banding(g01_path):
    result = decompose(load_cabinet(g01_path))
    shelves = [p for p in result.panels if "półka" in p.name.lower()]
    for s in shelves:
        assert "front" in s.banded_edges
        assert s.banded_edges["front"].length_mm == 762
        assert len(s.banded_edges) == 1


# ── Doors ────────────────────────────────────────────────────────

def test_doors_count(g01_path):
    result = decompose(load_cabinet(g01_path))
    doors = [p for p in result.panels if "front" in p.id]
    assert len(doors) == 2

def test_door_dimensions(g01_path):
    result = decompose(load_cabinet(g01_path))
    doors = [p for p in result.panels if "front" in p.id]
    for d in doors:
        # (800 - 3 - 3 - 3) / 2 = 395.5
        assert d.width_mm == pytest.approx(395.5, abs=0.1)
        assert d.height_mm == 714    # 720 - 3 - 3
        assert d.thickness_mm == 18

def test_door_edge_banding(g01_path):
    """Doors: all 4 edges banded with front material."""
    result = decompose(load_cabinet(g01_path))
    doors = [p for p in result.panels if "front" in p.id]
    for d in doors:
        assert len(d.banded_edges) == 4
        assert d.banded_edges["front"].length_mm == pytest.approx(395.5, abs=0.1)
        assert d.banded_edges["back"].length_mm == pytest.approx(395.5, abs=0.1)
        assert d.banded_edges["left"].length_mm == 714
        assert d.banded_edges["right"].length_mm == 714


# ── Accessories ──────────────────────────────────────────────────

def test_hinges(g01_path):
    result = decompose(load_cabinet(g01_path))
    hinges = [a for a in result.accessories if a.type == "hinge"]
    assert len(hinges) == 2    # one entry per door
    for h in hinges:
        assert h.quantity == 2  # 2 hinges per door

def test_shelf_pins(g01_path):
    result = decompose(load_cabinet(g01_path))
    pins = [a for a in result.accessories if a.type == "shelf_pin"]
    assert len(pins) == 1
    assert pins[0].quantity == 8  # 4 per shelf × 2 shelves

def test_handles(g01_path):
    result = decompose(load_cabinet(g01_path))
    handles = [a for a in result.accessories if a.type == "handle"]
    assert len(handles) == 1
    assert handles[0].quantity == 2

def test_no_runners(g01_path):
    """Door cabinets have hinges, not drawer runners."""
    result = decompose(load_cabinet(g01_path))
    runners = [a for a in result.accessories if a.type == "runner"]
    assert len(runners) == 0


# ── BOM ──────────────────────────────────────────────────────────

def test_bom_has_items(g01_path):
    result = decompose(load_cabinet(g01_path))
    bom = calculate_bom(result)
    assert bom.cabinet_id == "G01"
    assert len(bom.items) > 0
    panel_items = [i for i in bom.items if i.category == "panel"]
    assert len(panel_items) == 9

def test_bom_total_is_sum(g01_path):
    result = decompose(load_cabinet(g01_path))
    bom = calculate_bom(result)
    expected = round(sum(i.total for i in bom.items), 2)
    assert bom.total_cost == expected
