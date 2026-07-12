"""K01 — base cabinet with 2 drawers (dolna_szufladowa).

Proves: YAML load → decomposition → correct panels + accessories + BOM.

Expected panels (6):
  left side   510 × 620 × 18
  right side  510 × 620 × 18
  bottom      764 × 510 × 18
  back        778 × 598 ×  3
  front S1    794 × 150 × 18
  front S2    794 × 300 × 18

Expected accessories (3):
  runner S1 (blum_metabox)
  runner S2 (blum_metabox)
  handles  ×2 (relingowy)
"""

import pytest
from kuchnie_core.loader import load_cabinet
from kuchnie_core.decomposer import decompose
from kuchnie_core.bom import calculate_bom


# ── Loading ──────────────────────────────────────────────────────

def test_loads(k01_path):
    cab = load_cabinet(k01_path)
    assert cab.id == "K01"
    assert cab.type == "dolna_szufladowa"
    assert cab.width_mm == 800
    assert cab.height_mm == 720
    assert cab.depth_mm == 510
    assert cab.plinth_height_mm == 100


# ── Panel count ──────────────────────────────────────────────────

def test_panel_count(k01_path):
    result = decompose(load_cabinet(k01_path))
    assert len(result.panels) == 6


# ── Side panels ──────────────────────────────────────────────────

def test_side_dimensions(k01_path):
    result = decompose(load_cabinet(k01_path))
    sides = [p for p in result.panels if "bok" in p.name.lower()]
    assert len(sides) == 2
    for side in sides:
        assert side.height_mm == 620   # 720 - 100 plinth
        assert side.width_mm == 510    # depth
        assert side.thickness_mm == 18

def test_side_edge_banding(k01_path):
    result = decompose(load_cabinet(k01_path))
    sides = [p for p in result.panels if "bok" in p.name.lower()]
    for side in sides:
        assert "front" in side.banded_edges
        assert side.banded_edges["front"].length_mm == 620
        assert len(side.banded_edges) == 1  # only front edge


# ── Bottom panel ─────────────────────────────────────────────────

def test_bottom_dimensions(k01_path):
    result = decompose(load_cabinet(k01_path))
    bottom = next(p for p in result.panels if p.name == "Dno")
    assert bottom.width_mm == 764    # 800 - 2×18
    assert bottom.height_mm == 510   # depth
    assert bottom.thickness_mm == 18

def test_bottom_edge_banding(k01_path):
    result = decompose(load_cabinet(k01_path))
    bottom = next(p for p in result.panels if p.name == "Dno")
    assert "front" in bottom.banded_edges
    assert bottom.banded_edges["front"].length_mm == 764


# ── Back panel ───────────────────────────────────────────────────

def test_back_dimensions(k01_path):
    result = decompose(load_cabinet(k01_path))
    back = next(p for p in result.panels if p.name == "Plecy")
    assert back.width_mm == 778     # 800 - 36 + 16 - 2 luz
    assert back.height_mm == 598    # 620 - 36 + 16 - 2 luz (in grooves, never above sides)
    assert back.thickness_mm == 3
    assert back.banded_edges == {}  # HDF — never banded


# ── Drawer fronts ────────────────────────────────────────────────

def test_drawer_fronts_count(k01_path):
    result = decompose(load_cabinet(k01_path))
    fronts = [p for p in result.panels if "front" in p.id]
    assert len(fronts) == 2

def test_drawer_front_F1(k01_path):
    result = decompose(load_cabinet(k01_path))
    f1 = next(p for p in result.panels if "_front_F1" in p.id)
    assert f1.width_mm == 794     # 800 - 3 - 3
    assert f1.height_mm == 150
    assert f1.thickness_mm == 18
    assert len(f1.banded_edges) == 4  # all 4 edges

def test_drawer_front_F2(k01_path):
    result = decompose(load_cabinet(k01_path))
    f2 = next(p for p in result.panels if "_front_F2" in p.id)
    assert f2.width_mm == 794
    assert f2.height_mm == 300

def test_drawer_front_edge_lengths(k01_path):
    """Front/back edges run along width, left/right along height."""
    result = decompose(load_cabinet(k01_path))
    f1 = next(p for p in result.panels if "_front_F1" in p.id)
    assert f1.banded_edges["front"].length_mm == 794
    assert f1.banded_edges["back"].length_mm == 794
    assert f1.banded_edges["left"].length_mm == 150
    assert f1.banded_edges["right"].length_mm == 150


# ── Accessories ──────────────────────────────────────────────────

def test_runners(k01_path):
    result = decompose(load_cabinet(k01_path))
    runners = [a for a in result.accessories if a.type == "runner"]
    assert len(runners) == 2
    for r in runners:
        assert r.quantity == 1

def test_handles(k01_path):
    result = decompose(load_cabinet(k01_path))
    handles = [a for a in result.accessories if a.type == "handle"]
    assert len(handles) == 1
    assert handles[0].quantity == 2   # one per drawer front

def test_no_hinges(k01_path):
    """Drawer cabinets have runners, not hinges."""
    result = decompose(load_cabinet(k01_path))
    hinges = [a for a in result.accessories if a.type == "hinge"]
    assert len(hinges) == 0


# ── BOM ──────────────────────────────────────────────────────────

def test_bom_has_items(k01_path):
    result = decompose(load_cabinet(k01_path))
    bom = calculate_bom(result, board_prices={
        "swiss_krono.U119_VL": 45.00,
        "HDF_3mm": 15.00,
        "swiss_krono.U119_EM": 62.00,
    })
    assert bom.cabinet_id == "K01"
    assert len(bom.items) > 0
    # panels + edge bands + accessories
    panel_items = [i for i in bom.items if i.category == "panel"]
    assert len(panel_items) == 6

def test_bom_total_is_sum(k01_path):
    result = decompose(load_cabinet(k01_path))
    bom = calculate_bom(result)
    expected = round(sum(i.total for i in bom.items), 2)
    assert bom.total_cost == expected
