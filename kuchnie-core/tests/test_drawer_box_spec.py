"""DrawerBoxSpec + runner placement on the DrawerSystem ABC (kuchnie-b30 /
kuchnie-27b).

The defect these tests pin: the drawer runner-stacking loop used to exist
twice — once in ``catalog.decompose_dolna_legrabox`` (which could pass
``runner_y_mm`` into the module-level LEGRABOX decomposer) and once in
kitchen-erp's ``_attach_drawer_boxes`` (which could NOT, because the
``DrawerSystem`` ABC took neither ``runner_y_mm`` nor ``side_thickness``,
so it post-mutated the emitted ops instead).

Everything here is hand-computed from Blum planning data, never re-derived
from the code under test.
"""
from __future__ import annotations

import pytest

from kuchnie_core import legrabox
from kuchnie_core.blum_drawers import (
    DEFAULT_HEIGHT_CODE,
    DrawerBoxSpec,
    DrawerSystemFactory,
    Legrabox,
    Merivobox,
    TandemboxAntaro,
)

ALL_SYSTEM_IDS = ["tandembox_antaro", "merivobox", "legrabox"]


@pytest.fixture(params=ALL_SYSTEM_IDS)
def sys_id(request):
    return request.param


def spec_for(system, **over) -> DrawerBoxSpec:
    """A valid spec for ``system`` — NL 500 is available for every code."""
    kwargs = dict(
        cabinet_id="TEST",
        drawer_id="S1",
        kb=564,
        nl=500,
        runner_y_mm=55.0,
        height_code=system.default_height_code,
        side_thickness=18,
    )
    kwargs.update(over)
    return DrawerBoxSpec(**kwargs)


# ── The spec object itself (kuchnie-b30) ─────────────────────────

class TestDrawerBoxSpec:
    def test_spec_carries_vertical_placement_and_side_thickness(self):
        """The two data the ABC used to lack live on the spec."""
        spec = DrawerBoxSpec(cabinet_id="C", drawer_id="S1", kb=564, nl=500,
                             runner_y_mm=55.0, side_thickness=18)
        assert spec.runner_y_mm == 55.0
        assert spec.side_thickness == 18

    def test_runner_y_mm_is_required(self):
        """A runner op without a vertical position is scrap board."""
        with pytest.raises(TypeError):
            DrawerBoxSpec(cabinet_id="C", drawer_id="S1", kb=564, nl=500)

    def test_spec_is_frozen(self):
        spec = DrawerBoxSpec(cabinet_id="C", drawer_id="S1", kb=564, nl=500,
                             runner_y_mm=55.0)
        with pytest.raises(Exception):
            spec.runner_y_mm = 1.0  # type: ignore[misc]

    def test_height_code_defaults_to_none_meaning_ask_the_system(self):
        spec = DrawerBoxSpec(cabinet_id="C", drawer_id="S1", kb=564, nl=500,
                             runner_y_mm=55.0)
        assert spec.height_code is None


# ── The ABC now carries placement (kuchnie-27b) ──────────────────

class TestABCCarriesRunnerPlacement:
    def test_every_system_places_runner_ops_at_the_requested_height(self, sys_id):
        system = DrawerSystemFactory.get(sys_id)
        _, ops = system.decompose_drawer_box(spec_for(system, runner_y_mm=123.5))
        assert ops, f"{sys_id} emitted no runner ops"
        assert all(op.y_mm == 123.5 for op in ops), \
            f"{sys_id} ignored runner_y_mm: {[op.y_mm for op in ops]}"

    def test_every_system_uses_the_carcass_side_cam_convention(self, sys_id):
        """x = distance from the FRONT edge, y = above the BOTTOM edge.

        No caller may need to swap the axes afterwards — that post-mutation
        is the bug.
        """
        system = DrawerSystemFactory.get(sys_id)
        _, ops = system.decompose_drawer_box(spec_for(system, runner_y_mm=55.0))
        assert ops[0].x_mm == 46          # Blum's first screw, from the front
        assert ops[0].y_mm == 55.0
        assert all(op.face == "inside" for op in ops)
        assert all(op.drill_type == "runner_screw" for op in ops)

    def test_every_system_accepts_side_thickness_on_the_abc_path(self, sys_id):
        system = DrawerSystemFactory.get(sys_id)
        panels, _ = system.decompose_drawer_box(spec_for(system, side_thickness=18))
        assert len(panels) == 2

    def test_decompose_takes_exactly_one_argument_beyond_self(self, sys_id):
        """Param-bloat entry retired: the 10/11-parameter list is one spec."""
        import inspect
        system = DrawerSystemFactory.get(sys_id)
        params = inspect.signature(type(system).decompose_drawer_box).parameters
        assert list(params) == ["self", "spec"]
        acc = inspect.signature(type(system).make_runner_accessory).parameters
        assert list(acc) == ["self", "spec"]


# ── The stacking loop, defined once ──────────────────────────────

class TestRunnerAxisHeights:
    """The arithmetic that used to be copy-pasted into kitchen-erp."""

    def test_stack_starts_above_the_bottom_panel(self):
        system = Legrabox()
        heights = system.runner_axis_heights([{"id": "S1"}], bottom_thickness_mm=18)
        assert heights == [18 + legrabox.RUNNER_AXIS_OFFSET_MM]

    def test_explicit_front_height_advances_the_stack(self):
        """d60's stack: 18mm bottom, fronts 140/287/287 bottom-up."""
        system = Legrabox()
        drawers = [{"id": "S1", "height_code": "M", "wysokosc": 140},
                   {"id": "S2", "height_code": "C", "wysokosc": 287},
                   {"id": "S3", "height_code": "C", "wysokosc": 287}]
        assert system.runner_axis_heights(drawers, 18) == [55.0, 195.0, 482.0]

    def test_missing_front_height_falls_back_to_the_metal_side_height(self):
        system = Legrabox()
        drawers = [{"id": "S1", "height_code": "M"}, {"id": "S2", "height_code": "M"}]
        # LEGRABOX M side height = 90.5
        assert system.runner_axis_heights(drawers, 18) == [55.0, 145.5]

    def test_fallback_uses_the_systems_own_default_height_code(self):
        """No height_code at all -> the system's default, not a caller's."""
        assert TandemboxAntaro().runner_axis_heights(
            [{"id": "S1"}, {"id": "S2"}], 18) == [55.0, 55.0 + 116]   # M
        assert Legrabox().runner_axis_heights(
            [{"id": "S1"}, {"id": "S2"}], 18) == [55.0, 55.0 + 177]   # C


# ── One default height code, defined once ────────────────────────

class TestSharedDefaultHeightCode:
    def test_shared_default_is_defined_once_on_the_abc(self):
        assert DEFAULT_HEIGHT_CODE == "M"
        assert TandemboxAntaro().default_height_code == DEFAULT_HEIGHT_CODE
        assert Merivobox().default_height_code == DEFAULT_HEIGHT_CODE

    def test_legrabox_default_comes_from_the_legrabox_module(self):
        """ADR-006: no LEGRABOX datum is duplicated outside legrabox.py.
        Core (catalog.decompose_dolna_legrabox) has always defaulted to C
        and core is the domain authority, so C wins over kitchen-erp's M.
        """
        assert legrabox.DEFAULT_HEIGHT_CODE == "C"
        assert Legrabox().default_height_code == legrabox.DEFAULT_HEIGHT_CODE

    def test_every_systems_default_is_one_of_its_own_height_codes(self, sys_id):
        system = DrawerSystemFactory.get(sys_id)
        assert system.default_height_code in system.height_codes

    def test_spec_without_height_code_resolves_to_the_system_default(self, sys_id):
        system = DrawerSystemFactory.get(sys_id)
        spec = DrawerBoxSpec(cabinet_id="T", drawer_id="S1", kb=564, nl=500,
                             runner_y_mm=55.0)
        panels, _ = system.decompose_drawer_box(spec)
        explicit, _ = system.decompose_drawer_box(
            DrawerBoxSpec(cabinet_id="T", drawer_id="S1", kb=564, nl=500,
                          runner_y_mm=55.0, height_code=system.default_height_code))
        assert [(p.width_mm, p.height_mm) for p in panels] == \
               [(p.width_mm, p.height_mm) for p in explicit]


# ── LEGRABOX: the ABC and the module are one implementation ──────

class TestLegraboxAbcDelegatesToTheModule:
    """ADR-006 — ``legrabox`` is the single LEGRABOX data/formula source.

    Before this change the ``Legrabox`` class inherited the ABC's generic
    single-screw op, so the ERP path drilled ONE runner screw where the
    core path drilled four.
    """

    def test_panels_and_ops_are_identical_to_the_module_function(self):
        spec = DrawerBoxSpec(cabinet_id="D60S3", drawer_id="S2", kb=564, nl=500,
                             runner_y_mm=195.0, height_code="C", side_thickness=18)
        abc_panels, abc_ops = Legrabox().decompose_drawer_box(spec)
        mod_panels, mod_ops = legrabox.decompose_drawer_box(spec)

        assert [(p.id, p.width_mm, p.height_mm, p.thickness_mm, p.role)
                for p in abc_panels] == \
               [(p.id, p.width_mm, p.height_mm, p.thickness_mm, p.role)
                for p in mod_panels]
        assert [(o.x_mm, o.y_mm, o.diameter_mm, o.depth_mm, o.face,
                 o.drill_type, o.note) for o in abc_ops] == \
               [(o.x_mm, o.y_mm, o.diameter_mm, o.depth_mm, o.face,
                 o.drill_type, o.note) for o in mod_ops]

    def test_abc_path_emits_all_four_nl500_runner_screws(self):
        spec = DrawerBoxSpec(cabinet_id="T", drawer_id="S1", kb=564, nl=500,
                             runner_y_mm=55.0, height_code="C")
        _, ops = Legrabox().decompose_drawer_box(spec)
        assert [op.x_mm for op in ops] == [46, 78, 110, 398]

    def test_runner_accessory_is_identical_to_the_module_function(self):
        spec = DrawerBoxSpec(cabinet_id="D60S3", drawer_id="S2", kb=564, nl=500,
                             runner_y_mm=195.0, height_code="C", capacity_kg=40)
        assert Legrabox().make_runner_accessory(spec).name == \
               legrabox.make_runner_accessory(spec).name


# ── Validation survives the signature change ─────────────────────

class TestValidationStillApplies:
    def test_unknown_height_code_raises(self, sys_id):
        system = DrawerSystemFactory.get(sys_id)
        with pytest.raises(ValueError, match="Unknown height code"):
            system.decompose_drawer_box(spec_for(system, height_code="X"))

    def test_unavailable_nl_raises(self, sys_id):
        system = DrawerSystemFactory.get(sys_id)
        with pytest.raises(ValueError, match="not available"):
            system.decompose_drawer_box(spec_for(system, nl=999))
