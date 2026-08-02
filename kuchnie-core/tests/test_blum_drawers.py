"""Blum drawer systems — TANDEMBOX antaro, MERIVOBOX, LEGRABOX.

Tests prove:
  1. All three systems have correct height codes and dimensions
  2. NL (nominal length) availability matrix is correct
  3. Dimension formulas produce correct panel sizes
  4. DrawerSystemFactory returns correct system by id
  5. Unified API across all three systems
"""

import pytest
from kuchnie_core.blum_drawers import (
    DrawerBoxSpec,
    DrawerSystem,
    DrawerSystemFactory,
    TandemboxAntaro,
    Merivobox,
    Legrabox,
)


# ── TANDEMBOX antaro ─────────────────────────────────────────────

class TestTandemboxAntaro:
    """Blum TANDEMBOX antaro — the workhorse drawer system."""

    def test_has_height_N(self):
        sys = TandemboxAntaro()
        assert "N" in sys.height_codes

    def test_has_height_M(self):
        sys = TandemboxAntaro()
        assert "M" in sys.height_codes

    def test_has_height_D(self):
        sys = TandemboxAntaro()
        assert "D" in sys.height_codes

    def test_height_N_side_height(self):
        sys = TandemboxAntaro()
        assert sys.side_height("N") == 83

    def test_height_M_side_height(self):
        sys = TandemboxAntaro()
        assert sys.side_height("M") == 116

    def test_height_D_side_height(self):
        sys = TandemboxAntaro()
        assert sys.side_height("D") == 199

    def test_height_N_back_panel_height(self):
        sys = TandemboxAntaro()
        assert sys.back_panel_height("N") == 56

    def test_height_M_back_panel_height(self):
        sys = TandemboxAntaro()
        assert sys.back_panel_height("M") == 89

    def test_height_D_back_panel_height(self):
        sys = TandemboxAntaro()
        assert sys.back_panel_height("D") == 172

    def test_valid_nl_values(self):
        sys = TandemboxAntaro()
        assert sys.valid_nl() == [270, 300, 350, 400, 450, 500, 550, 600, 650]

    def test_height_N_nl_availability(self):
        sys = TandemboxAntaro()
        # N available from 400-600
        assert sys.is_valid_combo("N", 400) is True
        assert sys.is_valid_combo("N", 500) is True
        assert sys.is_valid_combo("N", 600) is True
        assert sys.is_valid_combo("N", 270) is False
        assert sys.is_valid_combo("N", 650) is False

    def test_height_M_nl_availability(self):
        sys = TandemboxAntaro()
        # M available from 270-650
        assert sys.is_valid_combo("M", 270) is True
        assert sys.is_valid_combo("M", 650) is True

    def test_height_D_nl_availability(self):
        sys = TandemboxAntaro()
        # D available from 270-650
        assert sys.is_valid_combo("D", 270) is True
        assert sys.is_valid_combo("D", 650) is True

    def test_runner_clearance(self):
        sys = TandemboxAntaro()
        assert sys.runner_clearance_per_side_mm() == 12.5

    def test_lw_formula(self):
        """LW = KB - 2 × runner_clearance"""
        sys = TandemboxAntaro()
        assert sys.lw(600) == 575  # 600 - 2*12.5

    def test_base_panel_width(self):
        sys = TandemboxAntaro()
        # base_width = LW - 35
        assert sys.base_panel_width(575) == 540

    def test_back_panel_width(self):
        sys = TandemboxAntaro()
        # back_width = LW - 38
        assert sys.back_panel_width(575) == 537

    def test_base_panel_depth(self):
        sys = TandemboxAntaro()
        # base_depth = NL - 10
        assert sys.base_panel_depth(500) == 490


# ── MERIVOBOX ────────────────────────────────────────────────────

class TestMerivobox:
    """Blum MERIVOBOX — premium drawer system."""

    def test_has_height_N(self):
        sys = Merivobox()
        assert "N" in sys.height_codes

    def test_has_height_M(self):
        sys = Merivobox()
        assert "M" in sys.height_codes

    def test_has_height_E(self):
        sys = Merivobox()
        assert "E" in sys.height_codes

    def test_height_N_side_height(self):
        sys = Merivobox()
        assert sys.side_height("N") == 65.5

    def test_height_M_side_height(self):
        sys = Merivobox()
        assert sys.side_height("M") == 90

    def test_height_E_side_height(self):
        sys = Merivobox()
        assert sys.side_height("E") == 184

    def test_height_N_back_panel_height(self):
        sys = Merivobox()
        assert sys.back_panel_height("N") == 39

    def test_height_M_back_panel_height(self):
        sys = Merivobox()
        assert sys.back_panel_height("M") == 63

    def test_height_E_back_panel_height(self):
        sys = Merivobox()
        assert sys.back_panel_height("E") == 157

    def test_runner_clearance(self):
        sys = Merivobox()
        assert sys.runner_clearance_per_side_mm() == 12.5

    def test_lw_formula(self):
        sys = Merivobox()
        assert sys.lw(600) == 575


# ── LEGRABOX (updated from existing) ────────────────────────────

class TestLegrabox:
    """Blum LEGRABOX — premium drawer system (already existed, now unified API)."""

    def test_has_height_N(self):
        sys = Legrabox()
        assert "N" in sys.height_codes

    def test_has_height_M(self):
        sys = Legrabox()
        assert "M" in sys.height_codes

    def test_has_height_K(self):
        sys = Legrabox()
        assert "K" in sys.height_codes

    def test_has_height_C(self):
        sys = Legrabox()
        assert "C" in sys.height_codes

    def test_has_height_F(self):
        sys = Legrabox()
        assert "F" in sys.height_codes

    def test_height_C_side_height(self):
        sys = Legrabox()
        assert sys.side_height("C") == 177

    def test_runner_clearance(self):
        sys = Legrabox()
        assert sys.runner_clearance_per_side_mm() == 13


# ── DrawerSystemFactory ──────────────────────────────────────────

class TestDrawerSystemFactory:
    """Factory returns correct system by id."""

    def test_get_tandembox(self):
        sys = DrawerSystemFactory.get("tandembox_antaro")
        assert isinstance(sys, TandemboxAntaro)

    def test_get_merivobox(self):
        sys = DrawerSystemFactory.get("merivobox")
        assert isinstance(sys, Merivobox)

    def test_get_legrabox(self):
        sys = DrawerSystemFactory.get("legrabox")
        assert isinstance(sys, Legrabox)

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match="unknown_drawer_system"):
            DrawerSystemFactory.get("unknown_drawer_system")

    def test_list_systems(self):
        systems = DrawerSystemFactory.list_ids()
        assert "tandembox_antaro" in systems
        assert "merivobox" in systems
        assert "legrabox" in systems


# ── Unified DrawerSystem interface ───────────────────────────────

class TestDrawerSystemInterface:
    """All systems implement the same interface."""

    @pytest.fixture(params=["tandembox_antaro", "merivobox", "legrabox"])
    def sys(self, request):
        return DrawerSystemFactory.get(request.param)

    def test_has_height_codes(self, sys):
        assert len(sys.height_codes) >= 3

    def test_side_height_returns_positive(self, sys):
        for code in sys.height_codes:
            assert sys.side_height(code) > 0

    def test_back_panel_height_returns_positive(self, sys):
        for code in sys.height_codes:
            assert sys.back_panel_height(code) > 0

    def test_runner_clearance_positive(self, sys):
        assert sys.runner_clearance_per_side_mm() > 0

    def test_lw_less_than_kb(self, sys):
        assert sys.lw(600) < 600

    def test_valid_nl_not_empty(self, sys):
        assert len(sys.valid_nl()) > 0

    def test_decompose_drawer_box_returns_panels_and_ops(self, sys):
        panels, ops = sys.decompose_drawer_box(DrawerBoxSpec(
            cabinet_id="TEST",
            drawer_id="D1",
            kb=600,
            nl=500,
            runner_y_mm=55.0,
            height_code=sys.height_codes[0],
        ))
        assert len(panels) == 2  # back + base
        assert all(p.width_mm > 0 for p in panels)
        assert all(p.height_mm > 0 for p in panels)

    def test_decompose_invalid_height_code_raises(self, sys):
        with pytest.raises(ValueError, match="Unknown height code"):
            sys.decompose_drawer_box(DrawerBoxSpec(
                cabinet_id="TEST", drawer_id="D1",
                kb=600, nl=500, runner_y_mm=55.0, height_code="X"
            ))

    def test_decompose_invalid_nl_raises(self, sys):
        with pytest.raises(ValueError, match="not available"):
            sys.decompose_drawer_box(DrawerBoxSpec(
                cabinet_id="TEST", drawer_id="D1",
                kb=600, nl=999, runner_y_mm=55.0,
                height_code=sys.height_codes[0]
            ))

    def test_lw_too_small_raises(self, sys):
        with pytest.raises(ValueError, match="too small"):
            sys.lw(10)  # too small for runners
