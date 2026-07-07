"""LEGRABOX decomposition tests.

Proves: MachiningOp model works, drawer box panels have correct
Blum-derived dimensions, runner drill ops land on side panels.
"""

import pytest
from pathlib import Path

from kuchnie_core.loader import load_cabinet
from kuchnie_core.decomposer import decompose
from kuchnie_core.model import MachiningOp
from kuchnie_core.legrabox import (
    lw, back_panel_width, base_panel_width, base_panel_depth,
    drawer_internal_width, drawer_internal_depth,
    HEIGHTS, validate_height_nl, validate_capacity,
    decompose_drawer_box,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# ── Formula unit tests ──────────────────────────────────────────

def test_lw_formula():
    """LW = KB − 2 × 13mm runner clearance"""
    assert lw(764) == 738       # 764 − 26
    assert lw(728) == 702       # 728 − 26


def test_back_panel_width():
    """Back panel width = LW − 38"""
    assert back_panel_width(738) == 700   # 738 − 38
    assert back_panel_width(702) == 664   # 702 − 38


def test_base_panel_width():
    """Base panel width = LW − 35"""
    assert base_panel_width(738) == 703
    assert base_panel_width(702) == 667


def test_base_panel_depth():
    """Base depth = NL − 10 (chipboard back)"""
    assert base_panel_depth(500) == 490
    assert base_panel_depth(400) == 390


def test_drawer_internal():
    """SKW = LW − 49,  SKL = NL − 10"""
    assert drawer_internal_width(738) == 689
    assert drawer_internal_depth(500) == 490


# ── Height codes ────────────────────────────────────────────────

def test_all_heights_present():
    assert set(HEIGHTS.keys()) == {"N", "M", "K", "C", "F"}


def test_height_C_dimensions():
    c = HEIGHTS["C"]
    assert c.side_height_mm == 177
    assert c.back_panel_height_mm == 148
    assert c.min_install_height_mm == 155


def test_height_N_dimensions():
    n = HEIGHTS["N"]
    assert n.side_height_mm == 66.5
    assert n.back_panel_height_mm == 39


def test_height_K_dimensions():
    k = HEIGHTS["K"]
    assert k.side_height_mm == 128.5
    assert k.back_panel_height_mm == 101


# ── Validation ──────────────────────────────────────────────────

def test_validate_valid_combo():
    assert validate_height_nl("C", 500) == []


def test_validate_invalid_nl_for_N():
    errors = validate_height_nl("N", 270)
    assert len(errors) == 1
    assert "270" in errors[0]


def test_validate_70kg_requires_nl_450_plus():
    assert validate_capacity(400, 70) != []
    assert validate_capacity(450, 70) == []


def test_validate_unknown_height():
    errors = validate_height_nl("Z", 500)
    assert "Unknown" in errors[0]


# ── Drawer box decomposition ────────────────────────────────────

def test_drawer_box_panel_count():
    """One LEGRABOX drawer → 2 board panels (back + base)."""
    panels, ops = decompose_drawer_box(
        cabinet_id="T1", drawer_id="S1",
        kb=764, nl=500, height_code="C", side_thickness=18,
        runner_y_mm=18,
    )
    assert len(panels) == 2
    assert panels[0].name.endswith("tył")
    assert panels[1].name.endswith("dno")


def test_drawer_box_back_dimensions():
    """Back: width = LW−38 = 738−38 = 700,  height = 148 (C code)."""
    panels, _ = decompose_drawer_box(
        cabinet_id="T1", drawer_id="S1",
        kb=764, nl=500, height_code="C", side_thickness=18,
        runner_y_mm=18,
    )
    back = panels[0]
    assert back.width_mm == 700
    assert back.height_mm == 148
    assert back.thickness_mm == 16   # Blum spec: 16mm chipboard


def test_drawer_box_base_dimensions():
    """Base: width = LW−35 = 703,  depth = NL−10 = 490."""
    panels, _ = decompose_drawer_box(
        cabinet_id="T1", drawer_id="S1",
        kb=764, nl=500, height_code="C", side_thickness=18,
        runner_y_mm=18,
    )
    base = panels[1]
    assert base.width_mm == 703
    assert base.height_mm == 490   # base depth
    assert base.thickness_mm == 16  # Blum spec: 16mm chipboard


def test_drawer_box_runner_ops_count():
    """Runner mounting ops for NL=500: 4 screw positions (from PoC table)."""
    _, ops = decompose_drawer_box(
        cabinet_id="T1", drawer_id="S1",
        kb=764, nl=500, height_code="C", side_thickness=18,
        runner_y_mm=18,
    )
    assert len(ops) == 4
    assert all(op.type == "drill" for op in ops)
    assert all(op.diameter_mm == 5 for op in ops)


def test_drawer_box_first_screw_position():
    """First runner screw at 46mm from front edge (x axis on side panels),
    at the runner height passed by the caller (y axis)."""
    _, ops = decompose_drawer_box(
        cabinet_id="T1", drawer_id="S1",
        kb=764, nl=500, height_code="C", side_thickness=18,
        runner_y_mm=18,
    )
    assert ops[0].x_mm == 46
    assert all(op.y_mm == 18 for op in ops)


# ── Full cabinet integration ────────────────────────────────────

def test_K02_loads():
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    assert cab.id == "K02"
    assert cab.type == "dolna_legrabox"


def test_K02_panel_count():
    """K02 with 2 LEGRABOX C-drawers:
      2 sides + 1 bottom + 1 back + 2 drawer backs + 2 drawer bases + 2 fronts = 10
    """
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    assert len(result.panels) == 10


def test_K02_has_machining_ops():
    """Carcass side panels must have runner drill ops."""
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    sides = [p for p in result.panels if "bok" in p.name.lower()]
    assert len(sides) == 2
    for side in sides:
        assert len(side.machining_ops) == 8   # 4 screws × 2 drawers
        assert all(op.type == "drill" for op in side.machining_ops)


def test_K02_runner_ops_positions():
    """Screws at 46/78mm from the front edge (x); each drawer's runner at
    its own stack height (y): S1 on the bottom panel (18), S2 one front
    height up (18 + 177 = 195)."""
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    side = next(p for p in result.panels if p.id.endswith("_left"))
    # First drawer screws
    assert side.machining_ops[0].x_mm == 46
    assert side.machining_ops[1].x_mm == 78
    assert side.machining_ops[0].y_mm == 18
    # Second drawer screws (offset in list by 4)
    assert side.machining_ops[4].x_mm == 46
    assert side.machining_ops[4].y_mm == 195


def test_K02_accessories():
    """2 runners + 2 handles."""
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    runners = [a for a in result.accessories if a.type == "runner"]
    handles = [a for a in result.accessories if a.type == "handle"]
    assert len(runners) == 2
    assert len(handles) == 1
    assert handles[0].quantity == 2
    assert "LEGRABOX" in runners[0].name


def test_K02_drawer_box_panel_dimensions():
    """Drawer back = 700 × 148,  drawer base = 703 × 490."""
    cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
    result = decompose(cab)
    drawer_backs = [p for p in result.panels if "tył" in p.name]
    drawer_bases = [p for p in result.panels if "dno" in p.name and "drawer" in p.id]
    assert len(drawer_backs) == 2
    assert len(drawer_bases) == 2
    assert drawer_backs[0].width_mm == 700
    assert drawer_backs[0].height_mm == 148
    assert drawer_bases[0].width_mm == 703
    assert drawer_bases[0].height_mm == 490
