"""ADR-012 §1 — ``PanelRole`` enum + ``Panel.role`` field.

Motivation: downstream CAM code (``kitchen-cam.machining``) needs to filter
panels by structural role ("apply hinge cups to FRONT_DOOR only") without
regex-matching Polish user-facing names like "Lewy bok". This test file
locks in:

  * The enum vocabulary (9 English roles, per ADR-012).
  * ``Panel.role`` default is ``None`` (safe for hand-built panels and
    for non-carcass panels like LEGRABOX drawer-box back/base).
  * Each catalog decomposer assigns the correct role to every panel.
  * Round-trip: constructing a ``Panel`` with a ``role=`` keyword works.

Enum values are English (AGENTS.md rule: "Model fields English,
YAML keys Polish").
"""

from __future__ import annotations

import pytest

from kuchnie_core import PanelRole
from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import load_cabinet
from kuchnie_core.model import Panel


# ── Enum vocabulary ─────────────────────────────────────────────

class TestPanelRoleEnum:
    """The enum values are the exact set specified in ADR-012 §1."""

    def test_expected_members(self):
        # Frozen contract — new roles = new ADR + new test entry.
        assert {r.name for r in PanelRole} == {
            "LEFT_SIDE", "RIGHT_SIDE", "BOTTOM", "TOP",
            "SHELF", "BACK", "FRONT_DOOR", "FRONT_DRAWER", "PLINTH",
        }

    def test_values_are_english_snake_case(self):
        # Model layer stays English (AGENTS.md). Loader translates Polish YAML.
        for role in PanelRole:
            assert role.value == role.name.lower()

    def test_is_str_subclass(self):
        # ``str, Enum`` — allows ``role == "left_side"`` style comparisons
        # and JSON-serialises without special encoder.
        assert isinstance(PanelRole.LEFT_SIDE, str)
        assert PanelRole.LEFT_SIDE == "left_side"


# ── Default behaviour ───────────────────────────────────────────

class TestPanelRoleDefault:
    """``Panel.role`` is optional; defaults to ``None`` for legacy callers."""

    def test_default_is_none(self):
        p = Panel(
            id="p1", name="foo", material="mat",
            thickness_mm=18, width_mm=100, height_mm=200,
        )
        assert p.role is None

    def test_can_be_set_by_keyword(self):
        p = Panel(
            id="p1", name="Lewy bok", material="mat",
            thickness_mm=18, width_mm=500, height_mm=620,
            role=PanelRole.LEFT_SIDE,
        )
        assert p.role is PanelRole.LEFT_SIDE


# ── Catalog decomposers set roles correctly ─────────────────────

def _role_of(panels, panel_id_suffix):
    """Find the (unique) *carcass* panel whose id ends with ``_<suffix>`` and return its role.

    Drawer-box parts (id contains ``_drawer_``) are excluded so this helper
    works uniformly across K01 (no drawer boxes) and K02 (LEGRABOX with
    drawer-box back/base panels).
    """
    matches = [
        p for p in panels
        if p.id.endswith("_" + panel_id_suffix) and "_drawer_" not in p.id
    ]
    assert len(matches) == 1, f"expected 1 panel ending in _{panel_id_suffix}, got {len(matches)}"
    return matches[0].role


class TestK01Roles:
    """dolna_szufladowa (K01) — 2 sides, bottom, back, N drawer fronts."""

    @pytest.fixture
    def panels(self, k01_path):
        return decompose(load_cabinet(k01_path)).panels

    def test_left_side_role(self, panels):
        assert _role_of(panels, "left") is PanelRole.LEFT_SIDE

    def test_right_side_role(self, panels):
        assert _role_of(panels, "right") is PanelRole.RIGHT_SIDE

    def test_bottom_role(self, panels):
        assert _role_of(panels, "bottom") is PanelRole.BOTTOM

    def test_back_role(self, panels):
        assert _role_of(panels, "back") is PanelRole.BACK

    def test_drawer_fronts_role(self, panels):
        drawer_fronts = [p for p in panels if "_front_" in p.id]
        assert drawer_fronts, "expected at least one drawer front"
        assert all(p.role is PanelRole.FRONT_DRAWER for p in drawer_fronts)


class TestG01Roles:
    """gorna_drzwiowa (G01) — 2 sides, top, bottom, back, N shelves, N doors."""

    @pytest.fixture
    def panels(self, g01_path):
        return decompose(load_cabinet(g01_path)).panels

    def test_left_side_role(self, panels):
        assert _role_of(panels, "left") is PanelRole.LEFT_SIDE

    def test_right_side_role(self, panels):
        assert _role_of(panels, "right") is PanelRole.RIGHT_SIDE

    def test_top_role(self, panels):
        assert _role_of(panels, "top") is PanelRole.TOP

    def test_bottom_role(self, panels):
        assert _role_of(panels, "bottom") is PanelRole.BOTTOM

    def test_back_role(self, panels):
        assert _role_of(panels, "back") is PanelRole.BACK

    def test_shelves_role(self, panels):
        shelves = [p for p in panels if "_shelf_" in p.id]
        assert shelves, "G01 fixture must define at least one shelf"
        assert all(p.role is PanelRole.SHELF for p in shelves)

    def test_door_fronts_role(self, panels):
        doors = [p for p in panels if "_front_" in p.id]
        assert doors, "G01 fixture must define at least one door front"
        assert all(p.role is PanelRole.FRONT_DOOR for p in doors)


class TestLegraboxRoles:
    """dolna_legrabox — carcass gets roles; drawer-box back/base stay None.

    The LEGRABOX drawer box (back + base panels) is not part of the fixed
    carcass role enum — those panels intentionally keep ``role=None``.
    This test locks that in so a future contributor doesn't quietly extend
    the enum without a new ADR.
    """

    @pytest.fixture
    def panels(self):
        from pathlib import Path
        fixtures = Path(__file__).resolve().parent.parent / "fixtures"
        return decompose(load_cabinet(fixtures / "K02_legrabox.yaml")).panels

    def test_carcass_left_side(self, panels):
        assert _role_of(panels, "left") is PanelRole.LEFT_SIDE

    def test_carcass_right_side(self, panels):
        assert _role_of(panels, "right") is PanelRole.RIGHT_SIDE

    def test_carcass_bottom(self, panels):
        assert _role_of(panels, "bottom") is PanelRole.BOTTOM

    def test_carcass_back(self, panels):
        assert _role_of(panels, "back") is PanelRole.BACK

    def test_drawer_box_panels_have_no_role(self, panels):
        # Drawer box back + base — intermediate parts, not carcass roles.
        drawer_parts = [p for p in panels if "_drawer_" in p.id]
        assert drawer_parts, "LEGRABOX fixture must produce drawer-box panels"
        assert all(p.role is None for p in drawer_parts)

    def test_drawer_fronts_have_role(self, panels):
        # Drawer FRONTS (visible face panels) do get FRONT_DRAWER role.
        fronts = [p for p in panels if "_front_" in p.id]
        assert fronts, "LEGRABOX fixture must define at least one drawer front"
        assert all(p.role is PanelRole.FRONT_DRAWER for p in fronts)


# ── Role-based filtering (the whole point) ──────────────────────

class TestRoleBasedFiltering:
    """The primary use case: downstream CAM filters panels by role."""

    def test_find_carcass_sides(self, k01_path):
        panels = decompose(load_cabinet(k01_path)).panels
        sides = [
            p for p in panels
            if p.role in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE)
        ]
        assert len(sides) == 2

    def test_find_door_fronts_only(self, g01_path):
        panels = decompose(load_cabinet(g01_path)).panels
        doors = [p for p in panels if p.role is PanelRole.FRONT_DOOR]
        # G01 has door fronts; none are drawer fronts.
        assert doors
        assert all("Front" in p.name for p in doors)
