"""Cabinet type catalog — construction methods as first-class rules.

Each type has a decompose function that knows how to derive physical panels
from a CabinetInstance. This is the Polyboard pattern: the CONSTRUCTION METHOD
lives here, separate from the cabinet instance that only carries configuration.

Add new cabinet types by writing a new decompose_<type> function and
registering it in TYPE_REGISTRY.
"""

from __future__ import annotations

from .construction import ConstructionMethod
from .model import (
    Accessory,
    CabinetInstance,
    DecompositionResult,
    EdgeBand,
    HandleSpec,
    MachiningOp,
    Panel,
    PanelRole,
)

# Side-panel role lookup (used by every carcass decomposer)
_SIDE_ROLE: dict[str, PanelRole] = {
    "left":  PanelRole.LEFT_SIDE,
    "right": PanelRole.RIGHT_SIDE,
}

# ADR-012 §4 — English → Polish display map for user-facing BOM strings.
# Model fields are English; the BOM output text is Polish (customer-facing).
_HANDLE_TYPE_EN_TO_PL: dict[str, str] = {
    "bar":      "relingowy",
    "knob":     "kulisty",
    "profile":  "profilowy",
    "recessed": "wpuszczany",
}


def _handle_accessory_name(spec: HandleSpec) -> str:
    """Polish BOM label for a ``HandleSpec`` — preserves pre-ADR-012 output.

    Format: ``"Uchwyt <polish_type> (rozstaw <spacing>mm)"``. Falls back to
    the raw English ``type`` when unknown, so future values propagate.
    """
    label = _HANDLE_TYPE_EN_TO_PL.get(spec.type, spec.type)
    return f"Uchwyt {label} (rozstaw {int(spec.spacing_mm)}mm)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _method_from_cab(cab: CabinetInstance) -> ConstructionMethod:
    """Derive ConstructionMethod from CabinetInstance's thickness fields.

    This bridges the existing YAML-based config with the new ConstructionMethod
    pattern.  When CabinetInstance gets a construction_ref field, this will
    look up the method from the registry instead.
    """
    return ConstructionMethod(
        id=f"_derived_{cab.id}",
        name=f"Derived from {cab.id}",
        side_thickness_mm=cab.thickness_side_mm,
        top_thickness_mm=cab.thickness_side_mm,  # same as side in current model
        bottom_thickness_mm=cab.thickness_bottom_mm,
        shelf_thickness_mm=cab.thickness_shelf_mm,
        back_thickness_mm=cab.thickness_back_mm,
        front_thickness_mm=cab.thickness_front_mm,
        back_groove_depth_mm=cab.groove_depth_mm,
        edge_band_thickness_mm=cab.edge_banding_thickness_mm,
    )


def _normalize_edge_material(edge_type: str, board_material: str) -> str:
    """Construct edge band material identifier.

    Format: "{edge_type}_{board_material}"
    Example: "ABS_swiss_krono.U119_VL"

    This is a LOCAL identifier for BOM/cutlist purposes.
    It does NOT directly map to catalog DB edge codes (e.g. "K-8685-SM/BS/PD").
    The mapping between local identifiers and catalog codes happens at
    procurement time, when the BOM is matched against supplier catalogs.
    """
    return f"{edge_type}_{board_material}"


def _body_eb(cab: CabinetInstance, length_mm: float) -> EdgeBand:
    """Edge band for carcass panels (body material)."""
    return EdgeBand(
        material=_normalize_edge_material(cab.edge_banding_type, cab.body_material),
        thickness_mm=cab.edge_banding_thickness_mm,
        length_mm=length_mm,
    )


def _front_eb(cab: CabinetInstance, length_mm: float) -> EdgeBand:
    """Edge band for front panels (front material)."""
    return EdgeBand(
        material=_normalize_edge_material(cab.edge_banding_type, cab.front_material),
        thickness_mm=cab.edge_banding_thickness_mm,
        length_mm=length_mm,
    )


# ---------------------------------------------------------------------------
# dolna_szufladowa — base cabinet with drawers
# ---------------------------------------------------------------------------

def decompose_dolna_szufladowa(cab: CabinetInstance) -> DecompositionResult:
    """Decompose a base drawer cabinet (e.g. K01).

    Panels produced:
      1× left side, 1× right side, 1× bottom, 1× back,
      N× drawer fronts (one per drawer)
    """
    m = _method_from_cab(cab)
    r = DecompositionResult(cabinet_id=cab.id, cabinet_type=cab.type)

    side_h = cab.height_mm - cab.plinth_height_mm  # 720 - 100 = 620

    # -- Side panels (left + right) --
    for side, label in [("left", "Lewy bok"), ("right", "Prawy bok")]:
        r.panels.append(Panel(
            id=f"{cab.id}_{side}",
            name=label,
            material=cab.body_material,
            thickness_mm=m.side_thickness_mm,
            width_mm=cab.depth_mm,
            height_mm=side_h,
            banded_edges={"front": _body_eb(cab, side_h)},
            role=_SIDE_ROLE[side],
        ))

    # -- Bottom panel --
    bottom_w = m.carcass_bottom_width(cab.width_mm)
    r.panels.append(Panel(
        id=f"{cab.id}_bottom",
        name="Dno",
        material=cab.body_material,
        thickness_mm=m.bottom_thickness_mm,
        width_mm=bottom_w,
        height_mm=cab.depth_mm,
        banded_edges={"front": _body_eb(cab, bottom_w)},
        role=PanelRole.BOTTOM,
    ))

    # -- Back panel (in groove, no banding) --
    back_w = m.back_panel_width(cab.width_mm)
    back_h = m.back_panel_height(side_h)
    r.panels.append(Panel(
        id=f"{cab.id}_back",
        name="Plecy",
        material=cab.back_material,
        thickness_mm=m.back_thickness_mm,
        width_mm=back_w,
        height_mm=back_h,
        banded_edges={},  # HDF — never banded
        role=PanelRole.BACK,
    ))

    # -- Drawer fronts --
    for front in cab.fronts:
        if front.get("typ") != "szufladowy":
            continue
        drawer = next(
            (d for d in cab.drawers if d["id"] == front.get("powiazany")),
            None,
        )
        front_h = drawer["wysokosc"] if drawer else 150
        margin_l = front.get("margines_lewo", 3)
        margin_r = front.get("margines_prawo", 3)
        front_w = cab.width_mm - margin_l - margin_r

        r.panels.append(Panel(
            id=f"{cab.id}_front_{front['id']}",
            name=f"Front {front['id']}",
            material=cab.front_material,
            thickness_mm=m.front_thickness_mm,
            width_mm=front_w,
            height_mm=front_h,
            banded_edges={
                "front": _front_eb(cab, front_w),
                "back":  _front_eb(cab, front_w),
                "left":  _front_eb(cab, front_h),
                "right": _front_eb(cab, front_h),
            },
            role=PanelRole.FRONT_DRAWER,
        ))

    # -- Drawer runners (accessories) --
    for drawer in cab.drawers:
        r.accessories.append(Accessory(
            id=f"{cab.id}_runner_{drawer['id']}",
            name=f"Prowadnica {drawer['typ']} ({drawer['id']})",
            type="runner",
            quantity=1,
        ))

    # -- Handles --
    if cab.handles is not None:
        n = len([f for f in cab.fronts if f.get("typ") == "szufladowy"])
        r.accessories.append(Accessory(
            id=f"{cab.id}_handles",
            name=_handle_accessory_name(cab.handles),
            type="handle",
            quantity=n,
        ))

    return r


# ---------------------------------------------------------------------------
# gorna_drzwiowa — wall cabinet with doors
# ---------------------------------------------------------------------------

def decompose_gorna_drzwiowa(cab: CabinetInstance) -> DecompositionResult:
    """Decompose a wall cabinet with doors (e.g. G01).

    Panels produced:
      1× left side, 1× right side, 1× top, 1× bottom, 1× back,
      N× shelves, N× door fronts
    """
    m = _method_from_cab(cab)
    r = DecompositionResult(cabinet_id=cab.id, cabinet_type=cab.type)

    # -- Side panels --
    for side, label in [("left", "Lewy bok"), ("right", "Prawy bok")]:
        r.panels.append(Panel(
            id=f"{cab.id}_{side}",
            name=label,
            material=cab.body_material,
            thickness_mm=m.side_thickness_mm,
            width_mm=cab.depth_mm,
            height_mm=cab.height_mm,
            banded_edges={"front": _body_eb(cab, cab.height_mm)},
            role=_SIDE_ROLE[side],
        ))

    # -- Top + Bottom panels --
    horiz_w = m.carcass_bottom_width(cab.width_mm)
    _horiz_role = {"top": PanelRole.TOP, "bottom": PanelRole.BOTTOM}
    for pos, label in [("top", "Góra"), ("bottom", "Dno")]:
        r.panels.append(Panel(
            id=f"{cab.id}_{pos}",
            name=label,
            material=cab.body_material,
            thickness_mm=m.bottom_thickness_mm,
            width_mm=horiz_w,
            height_mm=cab.depth_mm,
            banded_edges={"front": _body_eb(cab, horiz_w)},
            role=_horiz_role[pos],
        ))

    # -- Back panel (in groove, no banding) --
    back_w = m.back_panel_width(cab.width_mm)
    back_h = cab.height_mm - 2 * m.bottom_thickness_mm + 2 * m.back_groove_depth_mm
    r.panels.append(Panel(
        id=f"{cab.id}_back",
        name="Plecy",
        material=cab.back_material,
        thickness_mm=m.back_thickness_mm,
        width_mm=back_w,
        height_mm=back_h,
        banded_edges={},
        role=PanelRole.BACK,
    ))

    # -- Shelves --
    shelf_w = m.shelf_width(cab.width_mm)
    shelf_d = cab.depth_mm - 5  # clearance from back panel
    for shelf in cab.shelves:
        r.panels.append(Panel(
            id=f"{cab.id}_shelf_{shelf['id']}",
            name=f"Półka {shelf['id']}",
            material=cab.body_material,
            thickness_mm=m.shelf_thickness_mm,
            width_mm=shelf_w,
            height_mm=shelf_d,
            banded_edges={"front": _body_eb(cab, shelf_w)},
            role=PanelRole.SHELF,
        ))

    # -- Doors --
    door_fronts = [f for f in cab.fronts if f.get("typ", "").startswith("drzwiowy")]
    n_doors = len(door_fronts) or 1
    door_w = m.door_width(cab.width_mm, n_doors)
    door_h = m.door_height(cab.height_mm)

    for front in door_fronts:
        r.panels.append(Panel(
            id=f"{cab.id}_front_{front['id']}",
            name=f"Front {front['id']}",
            material=cab.front_material,
            thickness_mm=m.front_thickness_mm,
            width_mm=door_w,
            height_mm=door_h,
            banded_edges={
                "front": _front_eb(cab, door_w),
                "back":  _front_eb(cab, door_w),
                "left":  _front_eb(cab, door_h),
                "right": _front_eb(cab, door_h),
            },
            role=PanelRole.FRONT_DOOR,
        ))

    # -- Hinges --
    for front in door_fronts:
        n_hinges = front.get("ilosc_zawiasow", 2)
        r.accessories.append(Accessory(
            id=f"{cab.id}_hinge_{front['id']}",
            name=f"Zawias {front.get('zawias', 'standard')}",
            type="hinge",
            quantity=n_hinges,
        ))

    # -- Shelf pins (4 per shelf) --
    if cab.shelves:
        r.accessories.append(Accessory(
            id=f"{cab.id}_shelf_pins",
            name="Kołek półkowy 5 mm",
            type="shelf_pin",
            quantity=len(cab.shelves) * 4,
        ))

    # -- Handles --
    if cab.handles is not None and door_fronts:
        r.accessories.append(Accessory(
            id=f"{cab.id}_handles",
            name=_handle_accessory_name(cab.handles),
            type="handle",
            quantity=len(door_fronts),
        ))

    return r


# ---------------------------------------------------------------------------
# dolna_drzwiowa — base cabinet with doors
# ---------------------------------------------------------------------------

def decompose_dolna_drzwiowa(cab: CabinetInstance) -> DecompositionResult:
    """Decompose a base cabinet with doors.

    Panels produced:
      1× left side, 1× right side, 1× bottom, 1× back,
      N× shelves, N× door fronts
    """
    m = _method_from_cab(cab)
    r = DecompositionResult(cabinet_id=cab.id, cabinet_type=cab.type)

    side_h = cab.height_mm - cab.plinth_height_mm

    # -- Side panels (left + right) --
    for side, label in [("left", "Lewy bok"), ("right", "Prawy bok")]:
        r.panels.append(Panel(
            id=f"{cab.id}_{side}",
            name=label,
            material=cab.body_material,
            thickness_mm=m.side_thickness_mm,
            width_mm=cab.depth_mm,
            height_mm=side_h,
            banded_edges={"front": _body_eb(cab, side_h)},
            role=_SIDE_ROLE[side],
        ))

    # -- Bottom panel --
    bottom_w = m.carcass_bottom_width(cab.width_mm)
    r.panels.append(Panel(
        id=f"{cab.id}_bottom",
        name="Dno",
        material=cab.body_material,
        thickness_mm=m.bottom_thickness_mm,
        width_mm=bottom_w,
        height_mm=cab.depth_mm,
        banded_edges={"front": _body_eb(cab, bottom_w)},
        role=PanelRole.BOTTOM,
    ))

    # -- Back panel (in groove, no banding) --
    back_w = m.back_panel_width(cab.width_mm)
    back_h = m.back_panel_height(side_h)
    r.panels.append(Panel(
        id=f"{cab.id}_back",
        name="Plecy",
        material=cab.back_material,
        thickness_mm=m.back_thickness_mm,
        width_mm=back_w,
        height_mm=back_h,
        banded_edges={},
        role=PanelRole.BACK,
    ))

    # -- Shelves --
    shelf_w = m.shelf_width(cab.width_mm)
    shelf_d = cab.depth_mm - 5  # clearance from back panel
    for shelf in cab.shelves:
        r.panels.append(Panel(
            id=f"{cab.id}_shelf_{shelf['id']}",
            name=f"Półka {shelf['id']}",
            material=cab.body_material,
            thickness_mm=m.shelf_thickness_mm,
            width_mm=shelf_w,
            height_mm=shelf_d,
            banded_edges={"front": _body_eb(cab, shelf_w)},
            role=PanelRole.SHELF,
        ))

    # -- Door fronts --
    door_fronts = [f for f in cab.fronts if f.get("typ", "").startswith("drzwiowy")]
    n_doors = len(door_fronts) or 1
    door_w = m.door_width(cab.width_mm, n_doors)
    door_h = m.door_height(side_h)

    for front in door_fronts:
        r.panels.append(Panel(
            id=f"{cab.id}_front_{front['id']}",
            name=f"Front {front['id']}",
            material=cab.front_material,
            thickness_mm=m.front_thickness_mm,
            width_mm=door_w,
            height_mm=door_h,
            banded_edges={
                "front": _front_eb(cab, door_w),
                "back":  _front_eb(cab, door_w),
                "left":  _front_eb(cab, door_h),
                "right": _front_eb(cab, door_h),
            },
            role=PanelRole.FRONT_DOOR,
        ))

    # -- Hinges --
    for front in door_fronts:
        n_hinges = front.get("ilosc_zawiasow", 2)
        r.accessories.append(Accessory(
            id=f"{cab.id}_hinge_{front['id']}",
            name=f"Zawias {front.get('zawias', 'standard')}",
            type="hinge",
            quantity=n_hinges,
        ))

    # -- Shelf pins (4 per shelf) --
    if cab.shelves:
        r.accessories.append(Accessory(
            id=f"{cab.id}_shelf_pins",
            name="Kołek półkowy 5 mm",
            type="shelf_pin",
            quantity=len(cab.shelves) * 4,
        ))

    # -- Handles --
    if cab.handles is not None and door_fronts:
        r.accessories.append(Accessory(
            id=f"{cab.id}_handles",
            name=_handle_accessory_name(cab.handles),
            type="handle",
            quantity=len(door_fronts),
        ))

    return r


# ---------------------------------------------------------------------------
# dolna_legrabox — base cabinet with Blum LEGRABOX drawers
# ---------------------------------------------------------------------------

def decompose_dolna_legrabox(cab: CabinetInstance) -> DecompositionResult:
    """Decompose a base cabinet with LEGRABOX drawer system.

    Differs from dolna_szufladowa:
      - Drawer BOX panels (back + base) are produced as separate panels
      - Runner mounting drill ops are added to carcass side panels
      - Runner accessories carry LEGRABOX part numbers
    """
    from .legrabox import (
        decompose_drawer_box,
        make_runner_accessory,
        validate_height_nl,
    )

    m = _method_from_cab(cab)
    r = DecompositionResult(cabinet_id=cab.id, cabinet_type=cab.type)
    side_h = cab.height_mm - cab.plinth_height_mm

    # -- Side panels (left + right) — runner drill ops accumulated here --
    left_ops: list[MachiningOp] = []
    right_ops: list[MachiningOp] = []

    for side, label, ops_list in [
        ("left",  "Lewy bok", left_ops),
        ("right", "Prawy bok", right_ops),
    ]:
        r.panels.append(Panel(
            id=f"{cab.id}_{side}",
            name=label,
            material=cab.body_material,
            thickness_mm=m.side_thickness_mm,
            width_mm=cab.depth_mm,
            height_mm=side_h,
            banded_edges={"front": _body_eb(cab, side_h)},
            machining_ops=ops_list,
            role=_SIDE_ROLE[side],
        ))

    # -- Bottom panel --
    bottom_w = m.carcass_bottom_width(cab.width_mm)
    r.panels.append(Panel(
        id=f"{cab.id}_bottom",
        name="Dno",
        material=cab.body_material,
        thickness_mm=m.bottom_thickness_mm,
        width_mm=bottom_w,
        height_mm=cab.depth_mm,
        banded_edges={"front": _body_eb(cab, bottom_w)},
        role=PanelRole.BOTTOM,
    ))

    # -- Back panel --
    back_w = m.back_panel_width(cab.width_mm)
    back_h = m.back_panel_height(side_h)
    r.panels.append(Panel(
        id=f"{cab.id}_back",
        name="Plecy",
        material=cab.back_material,
        thickness_mm=m.back_thickness_mm,
        width_mm=back_w,
        height_mm=back_h,
        banded_edges={},
        role=PanelRole.BACK,
    ))

    # -- Drawer boxes + runner mounting ops --
    for drawer in cab.drawers:
        did = drawer["id"]
        height_code = drawer.get("height_code", "C")
        nl = drawer.get("nl", 500)
        capacity = drawer.get("capacity_kg", 40)

        box_panels, runner_ops = decompose_drawer_box(
            cabinet_id=cab.id,
            drawer_id=did,
            kb=m.carcass_bottom_width(cab.width_mm),  # KB = internal width
            nl=nl,
            height_code=height_code,
            side_thickness=m.side_thickness_mm,
        )
        r.panels.extend(box_panels)

        # Mounting ops go on BOTH side panels (mirrored)
        left_ops.extend(runner_ops)
        right_ops.extend(runner_ops)

        # Runner accessory (purchased part)
        r.accessories.append(make_runner_accessory(
            cabinet_id=cab.id,
            drawer_id=did,
            height_code=height_code,
            nl=nl,
            capacity_kg=capacity,
        ))

    # -- Drawer fronts --
    for front in cab.fronts:
        if front.get("typ") != "szufladowy":
            continue
        drawer = next(
            (d for d in cab.drawers if d["id"] == front.get("powiazany")),
            None,
        )
        front_h = drawer["wysokosc"] if drawer else 150
        margin_l = front.get("margines_lewo", 3)
        margin_r = front.get("margines_prawo", 3)
        front_w = cab.width_mm - margin_l - margin_r

        r.panels.append(Panel(
            id=f"{cab.id}_front_{front['id']}",
            name=f"Front {front['id']}",
            material=cab.front_material,
            thickness_mm=m.front_thickness_mm,
            width_mm=front_w,
            height_mm=front_h,
            banded_edges={
                "front": _front_eb(cab, front_w),
                "back":  _front_eb(cab, front_w),
                "left":  _front_eb(cab, front_h),
                "right": _front_eb(cab, front_h),
            },
            role=PanelRole.FRONT_DRAWER,
        ))

    # -- Handles --
    if cab.handles is not None:
        n = len([f for f in cab.fronts if f.get("typ") == "szufladowy"])
        r.accessories.append(Accessory(
            id=f"{cab.id}_handles",
            name=_handle_accessory_name(cab.handles),
            type="handle",
            quantity=n,
        ))

    return r


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TYPE_REGISTRY: dict[str, callable] = {
    "dolna_szufladowa": decompose_dolna_szufladowa,
    "dolna_drzwiowa":   decompose_dolna_drzwiowa,
    "dolna_legrabox":   decompose_dolna_legrabox,
    "gorna_drzwiowa":   decompose_gorna_drzwiowa,
}
