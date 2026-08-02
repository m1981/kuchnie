"""kuchnie-27b: the drawer runner-stacking loop must exist ONCE.

Before this test, ``catalog.decompose_dolna_legrabox`` and
``variant_derivation._attach_drawer_boxes`` were two copies of the same
loop. The ERP copy could not express vertical placement (the DrawerSystem
ABC took neither ``runner_y_mm`` nor ``side_thickness``), so it mutated
the emitted ops afterwards::

    op.x_mm, op.y_mm = op.y_mm, runner_y

These tests pin that both paths now produce the SAME runner drilling ops
and the SAME drawer-box panels for the same cabinet — which is only
possible if there is one implementation left.
"""
from __future__ import annotations

import pytest

from kuchnie_core.blum_drawers import DrawerBoxSpec, DrawerSystemFactory, Legrabox
from kuchnie_core.catalog import decompose_dolna_legrabox
from kuchnie_core.model import CabinetInstance, DecompositionResult, PanelRole

from kitchen_erp.core.variant_derivation import _attach_drawer_boxes

DRAWERS = [
    {"id": "S1", "height_code": "M", "nl": 500, "capacity_kg": 40, "wysokosc": 140},
    {"id": "S2", "height_code": "C", "nl": 500, "capacity_kg": 40, "wysokosc": 287},
    {"id": "S3", "height_code": "C", "nl": 500, "capacity_kg": 40, "wysokosc": 287},
]

# Hand-computed (never re-derived from the code under test):
#   bottom 18mm + RUNNER_AXIS_OFFSET_MM 37 = 55 for the lowest drawer,
#   then + 140, then + 287  ->  55 / 195 / 482.
EXPECTED_RUNNER_Y = [55.0, 195.0, 482.0]
# NL500 LEGRABOX pre-punched screw marks, from the front edge.
EXPECTED_RUNNER_X = [46, 78, 110, 398]


def cabinet(cab_type: str) -> CabinetInstance:
    return CabinetInstance(
        id="D60S3",
        type=cab_type,
        description="parity fixture",
        width_mm=600,
        height_mm=820,
        depth_mm=560,
        body_material="PLYTA_BIALA_18",
        back_material="HDF_BIALA_3",
        front_material="K5307_18",
        thickness_back_mm=3,
        plinth_height_mm=100,
        drawers=[dict(d) for d in DRAWERS],
        fronts=[{"id": f"F{i}", "typ": "szufladowy", "powiazany": f"S{i}"}
                for i in (1, 2, 3)],
        edge_banding_type="abs",
    )


def runner_ops(result: DecompositionResult) -> list[tuple]:
    return [
        (p.role.value, op.x_mm, op.y_mm, op.diameter_mm, op.depth_mm,
         op.face, op.drill_type, op.note)
        for p in result.panels
        if p.role in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE)
        for op in p.machining_ops
        if op.drill_type == "runner_screw"
    ]


def box_panels(result: DecompositionResult) -> list[tuple]:
    return sorted(
        (p.id, p.width_mm, p.height_mm, p.thickness_mm, p.role.value)
        for p in result.panels if "_drawer_" in p.id
    )


def erp_result() -> DecompositionResult:
    """What the ERP variant path produces for the same cabinet."""
    inst = cabinet("dolna_szufladowa")
    # Only the carcass sides matter for the comparison; reuse the core
    # decomposition's sides but strip every op so _attach_drawer_boxes
    # supplies them all.
    core = decompose_dolna_legrabox(cabinet("dolna_legrabox"))
    stripped = DecompositionResult(cabinet_id=core.cabinet_id,
                                   cabinet_type="dolna_szufladowa")
    for p in core.panels:
        if "_drawer_" in p.id:
            continue
        p.machining_ops = []
        stripped.panels.append(p)
    _attach_drawer_boxes(stripped, inst, "legrabox")
    return stripped


class TestStackingPathsAgree:
    def test_runner_ops_are_identical_between_core_and_erp(self):
        core = runner_ops(decompose_dolna_legrabox(cabinet("dolna_legrabox")))
        erp = runner_ops(erp_result())
        assert core == erp

    def test_drawer_box_panels_are_identical_between_core_and_erp(self):
        core = box_panels(decompose_dolna_legrabox(cabinet("dolna_legrabox")))
        erp = box_panels(erp_result())
        assert core == erp

    def test_runner_ops_match_the_hand_computed_stack(self):
        """Both paths must be right, not merely equal to each other."""
        ops = runner_ops(decompose_dolna_legrabox(cabinet("dolna_legrabox")))
        expected = [
            (side, x, y, 5, 12, "inside", "runner_screw",
             f"LEGRABOX {code} runner screw (NL=500)")
            for side in ("left_side", "right_side")
            for y, code in zip(EXPECTED_RUNNER_Y, ("M", "C", "C"))
            for x in EXPECTED_RUNNER_X
        ]
        assert ops == expected


class TestNoPostMutationLeftBehind:
    def test_variant_derivation_no_longer_swaps_op_axes(self):
        import inspect

        import kitchen_erp.core.variant_derivation as vd

        src = inspect.getsource(vd)
        assert "op.x_mm, op.y_mm = op.y_mm" not in src, \
            "the axis-swap post-mutation is back"

    def test_variant_derivation_defines_no_height_code_default_of_its_own(self):
        import kitchen_erp.core.variant_derivation as vd

        assert not hasattr(vd, "DRAWER_BOX_HEIGHT_CODE"), \
            "the default height code must come from the drawer system"

    def test_erp_uses_the_systems_own_default_height_code(self):
        """C for LEGRABOX (core is the domain authority), M elsewhere."""
        assert Legrabox().default_height_code == "C"
        assert DrawerSystemFactory.get("tandembox_antaro").default_height_code == "M"
        assert DrawerSystemFactory.get("merivobox").default_height_code == "M"


class TestErpDrivesTheAbcDirectly:
    @pytest.mark.parametrize("system_id", ["tandembox_antaro", "merivobox", "legrabox"])
    def test_every_system_places_runners_without_post_mutation(self, system_id):
        inst = cabinet("dolna_szufladowa")
        for d in inst.drawers:
            d.pop("height_code")
        result = DecompositionResult(cabinet_id=inst.id, cabinet_type=inst.type)
        core = decompose_dolna_legrabox(cabinet("dolna_legrabox"))
        for p in core.panels:
            if "_drawer_" not in p.id:
                p.machining_ops = []
                result.panels.append(p)
        _attach_drawer_boxes(result, inst, system_id)

        ys = sorted({op.y_mm for op in runner_y_ops(result)})
        assert ys == EXPECTED_RUNNER_Y
        assert all(op.x_mm != 0 for op in runner_y_ops(result))


def runner_y_ops(result):
    return [op for p in result.panels for op in p.machining_ops
            if op.drill_type == "runner_screw"]


class TestSpecIsTheOnlyArgument:
    def test_attach_drawer_boxes_builds_a_spec(self):
        """The ERP path goes through DrawerBoxSpec, not a 10-arg call."""
        import inspect

        import kitchen_erp.core.variant_derivation as vd

        assert "DrawerBoxSpec" in inspect.getsource(vd._attach_drawer_boxes)
        assert DrawerBoxSpec is not None
