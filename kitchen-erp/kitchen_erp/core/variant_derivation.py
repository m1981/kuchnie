"""wk-593a317b increment 1 -- variant re-derivation (ONE decomposition).

Killer features 1+2 of docs/specs/purchasing-variants.md: a Variant is
parameters, and a substitution is geometry, not a price line.
``derive_variant`` resolves the variant's overrides against the project
defaults, maps every carcass cabinet through the ADR-011 domain adapter
with those parameters applied, calls ``kuchnie_core.decompose`` ONCE per
cabinet, and folds the results into the purchasing artifact set: rozrys
cut rows, CNC machining ops, BOM lines. Nothing is cached and nothing is
stored on the Variant -- every call re-derives from the current
parameters, so no artifact can drift from geometry and no stale artifact
can survive an override change.

Cascade coverage in this increment:
  * front decor      -> front material of every mapped cabinet (edging
                        rows and BOM front/edging lines follow; carcass
                        geometry untouched)
  * drawer system    -> drawer boxes + runner drilling ops re-derive
                        through the kuchnie_core ``DrawerSystem`` ABC
                        (LEGRABOX / TANDEMBOX / MERIVOBOX axis); runner
                        accessory lines follow
  * corner mechanism, hinge class, worktop -> recorded in the resolved
                        ``VariantParameters`` (provenance); their price /
                        stage-9 cascades are later increments
                        (wk-4c37f4ee, offer loop).
"""
import copy
from dataclasses import dataclass, replace

from kuchnie_core import DrawerSystemFactory
from kuchnie_core.bom import calculate_bom
from kuchnie_core.decomposer import decompose
from kuchnie_core.export.cutlist_csv import CutPiece, aggregate_panels
from kuchnie_core.export.edging_csv import EdgingRow, collect_edging_rows
from kuchnie_core.legrabox import RUNNER_AXIS_OFFSET_MM
from kuchnie_core.model import (
    CabinetInstance,
    DecompositionResult,
    MachiningOp,
    PanelRole,
)

from .domain_adapter import role_bucket, to_kuchnie_core
from .models import ProjectDefaults, Variant

# Baseline values when neither the variant nor the project pins an axis.
# The domain adapter has always emitted tandembox drawers (ADR-011 phase
# 2), so that stays the baseline tier.
BASELINE_DRAWER_SYSTEM = "tandembox_antaro"
BASELINE_CORNER_MECHANISM = "plain_shelves"
BASELINE_HINGE_CLASS = "standard"

# Drawer-box sizing for this increment: "M" is the one height code all
# three Blum systems share; NL 500 matches decompose_dolna_legrabox's
# default for standard 510-560mm base depths.
DRAWER_BOX_HEIGHT_CODE = "M"
DRAWER_BOX_NL_MM = 500


@dataclass(frozen=True)
class VariantParameters:
    """The variant's overrides resolved against the project defaults --
    the full parameter set (and provenance) one derivation ran with."""
    front_decor: str
    drawer_system: str
    corner_mechanism: str
    hinge_class: str
    worktop: str | None


def resolve_parameters(variant: Variant, defaults: ProjectDefaults) -> VariantParameters:
    """Fold the variant's typed overrides over the project baseline."""
    return VariantParameters(
        front_decor=(variant.front_decor.name if variant.front_decor
                     else defaults.front_mat.name),
        drawer_system=variant.drawer_system or BASELINE_DRAWER_SYSTEM,
        corner_mechanism=variant.corner_mechanism or BASELINE_CORNER_MECHANISM,
        hinge_class=variant.hinge_class or BASELINE_HINGE_CLASS,
        worktop=variant.worktop,
    )


@dataclass(frozen=True)
class BomLine:
    """One purchasing line: board by m2, edging by lm, accessories by szt."""
    name: str
    qty: float
    unit: str


@dataclass
class DerivedArtifacts:
    """The artifact set one derivation produced. Ephemeral by design --
    never persisted on the Variant, always re-derived (killer feature 1)."""
    variant_name: str
    parameters: VariantParameters
    results: list[DecompositionResult]          # one per carcass cabinet
    rozrys_rows: list[CutPiece]                 # aggregated cut list
    edging_rows: list[EdgingRow]                # edge-banding worklist
    cnc_ops: list[tuple[str, MachiningOp]]      # (panel_id, op)
    bom_lines: list[BomLine]


def derive_variant(variant: Variant) -> DerivedArtifacts:
    """Re-derive the full artifact set for ``variant`` -- UC-4 step 1.

    One ``decompose`` call per carcass cabinet, with the variant's
    parameters applied BEFORE decomposition; rozrys, CNC and BOM all fold
    from those same results, so a substitution cascades everywhere or
    nowhere. Raises ValueError when the project has no defaults (there is
    no baseline to override).
    """
    project = variant.project
    if project is None or project.defaults is None:
        raise ValueError(
            f"variant {variant.name!r} has no project defaults to derive from"
        )
    defaults = project.defaults
    params = resolve_parameters(variant, defaults)

    results: list[DecompositionResult] = []
    for cabinet in sorted(project.cabinets, key=lambda c: c.order_index):
        inst = to_kuchnie_core(cabinet, defaults)
        if inst is None:
            continue  # appliances/fillers stay on erp recipe formulas
        inst = _apply_parameters(inst, cabinet.override_front_mat is not None, params)
        result = decompose(inst)  # THE one decomposition for this cabinet
        if inst.drawers:
            _attach_drawer_boxes(result, inst, params.drawer_system)
        results.append(result)

    panels = [p for r in results for p in r.panels]
    return DerivedArtifacts(
        variant_name=variant.name,
        parameters=params,
        results=results,
        rozrys_rows=aggregate_panels(panels),
        edging_rows=collect_edging_rows(panels),
        cnc_ops=[(p.id, op) for p in panels for op in p.machining_ops],
        bom_lines=_bom_lines(results),
    )


def _apply_parameters(
    inst: CabinetInstance,
    has_cabinet_front_override: bool,
    params: VariantParameters,
) -> CabinetInstance:
    """Push the variant's parameters into the domain instance.

    A per-cabinet front override (Cabinet.override_front_mat) is a
    deliberate exception and survives the variant's decor axis.
    """
    if not has_cabinet_front_override and inst.front_material != params.front_decor:
        inst = replace(inst, front_material=params.front_decor)
    for drawer in inst.drawers:
        drawer["typ"] = params.drawer_system
    return inst


def _attach_drawer_boxes(
    result: DecompositionResult, inst: CabinetInstance, system_id: str
) -> None:
    """Derive drawer-box panels + runner drilling ops from the variant's
    drawer system -- the substitution axis of purchasing-variants.md.

    Mirrors decompose_dolna_legrabox's stacking: drawers are listed
    bottom-up (CabinetInstance contract), the runner screw axis sits
    RUNNER_AXIS_OFFSET_MM above each zone's floor, and the mounting ops
    land on BOTH carcass side panels as independent copies.
    """
    system = DrawerSystemFactory.get(system_id)
    kb = inst.width_mm - 2 * inst.thickness_side_mm  # carcass internal width
    side_panels = [p for p in result.panels
                   if p.role in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE)]

    runner_y = float(inst.thickness_bottom_mm) + RUNNER_AXIS_OFFSET_MM
    for drawer in inst.drawers:
        box_panels, ops = system.decompose_drawer_box(
            cabinet_id=inst.id,
            drawer_id=drawer["id"],
            kb=kb,
            nl=drawer.get("nl", DRAWER_BOX_NL_MM),
            height_code=drawer.get("height_code", DRAWER_BOX_HEIGHT_CODE),
        )
        result.panels.extend(box_panels)
        for op in ops:
            # The DrawerSystem ABC emits the screw offset along the depth
            # in y_mm; recast to the carcass-side CAM convention (x from
            # FRONT edge, y from BOTTOM edge) and place the runner axis in
            # the stack -- vertical placement is the caller's job (see
            # kuchnie_core.legrabox.decompose_drawer_box).
            op.x_mm, op.y_mm = op.y_mm, runner_y
            op.drill_type = op.drill_type or "runner_screw"
        for side in side_panels:
            side.machining_ops.extend(copy.deepcopy(ops))
        runner_y += (drawer.get("wysokosc")
                     or system.side_height(drawer.get("height_code", DRAWER_BOX_HEIGHT_CODE)))


def _bom_lines(results: list[DecompositionResult]) -> list[BomLine]:
    """Purchasing views over the canonical BOM fold (ADR-015).

    Board grouped by (pricing bucket, actual panel material) -- so a
    per-cabinet front override prices under its own decor instead of
    being lumped into the variant's; edging per band material;
    accessories verbatim from the decomposers (runner lines carry the
    variant's drawer system in their name). No panel arithmetic here:
    every quantity is a BOMItem.measure from kuchnie_core.calculate_bom.
    """
    items = [item for r in results for item in calculate_bom(r).items]

    board: dict[tuple[str, str], float] = {}
    for item in items:
        if item.category == "panel":
            key = (role_bucket(item.role), item.material)
            board[key] = board.get(key, 0.0) + item.measure

    lines: list[BomLine] = []
    for bucket in ("corpus", "front", "back", "box"):
        for material, m2 in sorted(
            (mat, m2) for (b, mat), m2 in board.items() if b == bucket and m2
        ):
            lines.append(BomLine(material, round(m2, 3), "m2"))

    edging_lm: dict[str, float] = {}
    for item in items:
        if item.category == "edge_band":
            edging_lm[item.material] = edging_lm.get(item.material, 0.0) + item.measure
    for material, lm in sorted(edging_lm.items()):
        lines.append(BomLine(f"obrzeze {material}", round(lm, 3), "lm"))

    for item in items:
        if item.category == "accessory":
            lines.append(BomLine(item.description, item.quantity, "szt"))
    return lines
