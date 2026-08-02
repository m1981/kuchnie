"""Cabinet type catalog — construction methods as first-class rules.

Each type has a decompose function that knows how to derive physical panels
from a CabinetInstance. This is the Polyboard pattern: the CONSTRUCTION METHOD
lives here, separate from the cabinet instance that only carries configuration.

Add new cabinet types by writing a new decompose_<type> function and
registering it in TYPE_REGISTRY.
"""

from __future__ import annotations

import copy

from .construction import ConstructionMethod
from .model import (
    Accessory,
    CabinetInstance,
    CornerBlindConfig,
    DecompositionResult,
    EdgeBand,
    GrainAxis,
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
    "edge_pull": "krawędziowy",
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

def method_from_cab(cab: CabinetInstance) -> ConstructionMethod:
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
        thickness_mm=cab.front_edge_banding_thickness_mm,
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
    m = method_from_cab(cab)
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
        reveal = m.front_reveal(cab.handles.type if cab.handles else None)
        margin_l = front.get("margines_lewo", reveal)
        margin_r = front.get("margines_prawo", reveal)
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
            grain=GrainAxis.HEIGHT,
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
    m = method_from_cab(cab)
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
    back_h = m.back_panel_height(cab.height_mm)  # sides run full height on wall cabinets
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
    door_w = m.door_width(cab.width_mm, n_doors,
                          m.front_reveal(cab.handles.type if cab.handles else None))
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
            grain=GrainAxis.HEIGHT,
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
            name=f"Kołek półkowy {int(cab.shelf_pins.diameter_mm)} mm",
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
    m = method_from_cab(cab)
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
    door_w = m.door_width(cab.width_mm, n_doors,
                          m.front_reveal(cab.handles.type if cab.handles else None))
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
            grain=GrainAxis.HEIGHT,
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
            name=f"Kołek półkowy {int(cab.shelf_pins.diameter_mm)} mm",
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

_STRETCHER_WIDTH_MM = 100        # trawers górny, na płask
_CONFIRMAT_EDGE_OFFSET_MM = 50   # first/last confirmat from panel edge
_PLINTH_SIDE_INSET_MM = 2        # cokół recessed 2 mm per side
_PLINTH_FLOOR_GAP_MM = 3


def _hdf_groove_op(depth_mm: float, length_mm: float) -> MachiningOp:
    """HDF back groove. Coordinate exception: x_mm is the groove CENTRELINE
    measured from the REAR edge (groove near-edge 10 mm off the rear)."""
    return MachiningOp(
        type="groove",
        x_mm=12.0,
        width_mm=4.0,
        depth_mm=depth_mm,
        length_mm=length_mm,
        face="inside",
        note="wpust HDF 4mm, krawedz 10mm od tylnej krawedzi",
    )


def _confirmat_side_ops(cab: CabinetInstance, m: ConstructionMethod,
                        side_h: float) -> list[MachiningOp]:
    """Through-drills in a side panel for confirmats into the bottom panel
    and both top stretchers (Ø7 through + countersink, pilot in the mating
    edge is drilled on assembly)."""
    xs = [_CONFIRMAT_EDGE_OFFSET_MM, cab.depth_mm / 2,
          cab.depth_mm - _CONFIRMAT_EDGE_OFFSET_MM]
    ops = [MachiningOp(
        type="drill", x_mm=x, y_mm=m.bottom_thickness_mm / 2,
        diameter_mm=7, depth_mm=m.side_thickness_mm,
        face="outside", drill_type="confirmat",
        note="konfirmat 7x50 do dna (przelot)",
    ) for x in xs]
    for x, which in [(_STRETCHER_WIDTH_MM / 2, "przedniego"),
                     (cab.depth_mm - _STRETCHER_WIDTH_MM / 2, "tylnego")]:
        ops.append(MachiningOp(
            type="drill", x_mm=x, y_mm=side_h - m.top_thickness_mm / 2,
            diameter_mm=7, depth_mm=m.side_thickness_mm,
            face="outside", drill_type="confirmat",
            note=f"konfirmat 7x50 do trawersu {which} (przelot)",
        ))
    return ops

def _count_confirmat_ops(ops_lists: list[list[MachiningOp]]) -> int:
    """Single source of truth for the Konfirmat 7x50 purchase quantity:
    count the confirmat through-drill ops actually emitted on the given
    side-panel ops lists (G13) rather than deriving the count separately."""
    return sum(1 for ops in ops_lists for op in ops if op.drill_type == "confirmat")


def _confirmat_accessory(cab: CabinetInstance, ops_lists: list[list[MachiningOp]]) -> Accessory:
    """Konfirmat 7x50 — stock draw (Ilosc_zamowiona=0 downstream, never a
    PO line per the 2026-08-01 owner confirmation). Quantity DERIVED from
    the confirmat ops actually emitted, not hard-coded (G13)."""
    return Accessory(
        id=f"{cab.id}_confirmat",
        name="Konfirmat 7x50",
        type="fastener",
        quantity=_count_confirmat_ops(ops_lists),
    )


def _euro_screw_accessory(cab: CabinetInstance, n_profiles: int) -> Accessory:
    """Wkret euro 6.3x13 — stock draw, 4 screws per runner cabinet-profile
    (G13). ``n_profiles`` is 2 × drawer count (each drawer's runner mounts
    on both the left and right carcass side)."""
    return Accessory(
        id=f"{cab.id}_euro_screw",
        name="Wkret euro 6.3x13",
        type="fastener",
        quantity=4 * n_profiles,
    )


def _plinth_hardware_accessories(cab: CabinetInstance) -> list[Accessory]:
    """Nozka regulowana 100 mm ×4 + Klips cokolu + zaczep ×4 — clip-on
    cokół hardware, gated on plinth_height_mm > 0 (G13)."""
    if cab.plinth_height_mm <= 0:
        return []
    return [
        Accessory(
            id=f"{cab.id}_legs",
            name="Nozka regulowana 100 mm",
            type="leg",
            quantity=4,
        ),
        Accessory(
            id=f"{cab.id}_plinth_clips",
            name="Klips cokolu + zaczep",
            type="plinth_clip",
            quantity=4,
        ),
    ]


def _hdf_back_fastener_accessory(cab: CabinetInstance) -> Accessory | None:
    """Zszywki/wkrety HDF — 1 kpl stock draw, gated on an HDF back panel
    (G13). Returns None when the back material is not HDF."""
    if "hdf" not in cab.back_material.lower():
        return None
    return Accessory(
        id=f"{cab.id}_hdf_fasteners",
        name="Zszywki/wkrety HDF",
        type="fastener",
        quantity=1,
    )


def decompose_dolna_legrabox(cab: CabinetInstance) -> DecompositionResult:
    """Decompose a base cabinet with LEGRABOX drawer system.

    Differs from dolna_szufladowa:
      - Drawer BOX panels (back + base) are produced as separate panels
      - Runner mounting drill ops are added to carcass side panels
      - Runner accessories carry LEGRABOX part numbers
    """
    from .blum_drawers import DrawerBoxSpec, Legrabox

    m = method_from_cab(cab)
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

    # -- Bottom panel (HDF groove milled 10mm off the rear edge) --
    bottom_w = m.carcass_bottom_width(cab.width_mm)
    r.panels.append(Panel(
        id=f"{cab.id}_bottom",
        name="Dno",
        material=cab.body_material,
        thickness_mm=m.bottom_thickness_mm,
        width_mm=bottom_w,
        height_mm=cab.depth_mm,
        banded_edges={"front": _body_eb(cab, bottom_w)},
        machining_ops=[_hdf_groove_op(m.back_groove_depth_mm, bottom_w)],
        role=PanelRole.BOTTOM,
    ))

    # -- Top stretchers (trawersy) — drawer carcass has no full top; two
    # flat rails keep it square (wk-c3d0a0f0). Rear one carries the groove.
    for pos, label, banded in [("przedni", "Trawers przedni", True),
                               ("tylny", "Trawers tylny", False)]:
        r.panels.append(Panel(
            id=f"{cab.id}_trawers_{pos}",
            name=label,
            material=cab.body_material,
            thickness_mm=m.top_thickness_mm,
            width_mm=bottom_w,
            height_mm=_STRETCHER_WIDTH_MM,
            banded_edges={"front": _body_eb(cab, bottom_w)} if banded else {},
            machining_ops=(
                [] if banded
                else [_hdf_groove_op(m.back_groove_depth_mm, bottom_w)]
            ),
            role=PanelRole.TOP,
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
    # Drawers stack bottom-up; the screw-axis heights come from the drawer
    # system's shared stacking helper (kuchnie-27b — kitchen-erp used to
    # carry a second copy of this arithmetic). The height code a drawer
    # leaves unset comes from the system too (LEGRABOX: "C").
    system = Legrabox()
    for drawer, runner_y in zip(
        cab.drawers,
        system.runner_axis_heights(cab.drawers, m.bottom_thickness_mm),
    ):
        spec = DrawerBoxSpec(
            cabinet_id=cab.id,
            drawer_id=drawer["id"],
            kb=m.carcass_bottom_width(cab.width_mm),  # KB = internal width
            nl=drawer.get("nl", 500),
            runner_y_mm=runner_y,
            height_code=drawer.get("height_code"),
            side_thickness=m.side_thickness_mm,
            capacity_kg=drawer.get("capacity_kg", 40),
        )

        box_panels, runner_ops = system.decompose_drawer_box(spec)
        r.panels.extend(box_panels)

        # Mounting ops go on BOTH side panels (mirrored) — each side gets
        # its own instances; downstream CAM mutates ops per side.
        left_ops.extend(runner_ops)
        right_ops.extend(copy.deepcopy(runner_ops))

        # Runner accessory (purchased part)
        r.accessories.append(system.make_runner_accessory(spec))

    # -- Joinery + groove on the side panels (after runner ops so the
    # runner drill indices stay stable for downstream consumers) --
    for ops_list in (left_ops, right_ops):
        if "confirmat" in m.joinery_type:
            ops_list.extend(_confirmat_side_ops(cab, m, side_h))
        ops_list.append(_hdf_groove_op(m.back_groove_depth_mm, side_h))

    # -- G13: hardware accessories derived from the emitted ops/config --
    if "confirmat" in m.joinery_type:
        r.accessories.append(_confirmat_accessory(cab, [left_ops, right_ops]))
    if cab.drawers:
        r.accessories.append(
            _euro_screw_accessory(cab, n_profiles=2 * len(cab.drawers))
        )
    r.accessories.extend(_plinth_hardware_accessories(cab))
    hdf_fastener = _hdf_back_fastener_accessory(cab)
    if hdf_fastener is not None:
        r.accessories.append(hdf_fastener)

    # -- Drawer fronts --
    for front in cab.fronts:
        if front.get("typ") != "szufladowy":
            continue
        drawer = next(
            (d for d in cab.drawers if d["id"] == front.get("powiazany")),
            None,
        )
        front_h = drawer["wysokosc"] if drawer else 150
        reveal = m.front_reveal(cab.handles.type if cab.handles else None)
        margin_l = front.get("margines_lewo", reveal)
        margin_r = front.get("margines_prawo", reveal)
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
            grain=GrainAxis.HEIGHT,
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

    # -- Plinth (cokół, clip-on) --
    if cab.plinth_height_mm > 0:
        plinth_w = cab.width_mm - 2 * _PLINTH_SIDE_INSET_MM
        r.panels.append(Panel(
            id=f"{cab.id}_cokol",
            name="Cokół",
            material=cab.body_material,
            thickness_mm=m.side_thickness_mm,
            width_mm=plinth_w,
            height_mm=cab.plinth_height_mm - _PLINTH_FLOOR_GAP_MM,
            banded_edges={"front": _body_eb(cab, plinth_w)},
            role=PanelRole.PLINTH,
        ))

    return r


# ---------------------------------------------------------------------------
# dolna_narozna_slepa — blind base corner cabinet
# ---------------------------------------------------------------------------

_CORNER_FILLER_WIDTH_MM = 50.0   # playbook phase 3: 50–100 mm at the corner
_CORNER_MIN_OPENING_MM = 250     # narrower than this and the door is unusable


def decompose_dolna_narozna_slepa(cab: CabinetInstance) -> DecompositionResult:
    """Decompose a blind base corner cabinet (dolna narożna ślepa).

    Front layout along the cabinet width, corner end first:

        [ blind front (hidden behind the perpendicular run) | filler | door(s) ]

    * blind zone width = ``CornerBlindConfig.second_width_mm`` — the depth of
      the perpendicular run whose body stands in front of it (the loader
      defaults it to this cabinet's own depth);
    * filler = ``CornerBlindConfig.filler_width_mm`` strip (playbook phase 3
      mandate: without it handles collide at the internal corner);
    * door(s) share the remaining visible opening via the standard gap
      formula.

    Carcass matches the dolna_legrabox reference emission: two trawersy
    (rear one carries the HDF groove), groove-seated reduced back, cokół,
    and joinery-gated confirmat drills + HDF grooves on the sides.
    The blind front is FIXED (PanelRole.FRONT_BLIND) — no hinges, no
    handle; only its filler-facing vertical edge is banded.
    """
    m = method_from_cab(cab)
    r = DecompositionResult(cabinet_id=cab.id, cabinet_type=cab.type)
    side_h = cab.height_mm - cab.plinth_height_mm

    cfg = cab.config if isinstance(cab.config, CornerBlindConfig) else None
    corner_side = cfg.corner_side if cfg else "left"
    blind_w = (cfg.second_width_mm if cfg and cfg.second_width_mm > 0
               else cab.depth_mm)
    filler_w = cfg.filler_width_mm if cfg else _CORNER_FILLER_WIDTH_MM

    visible_w = cab.width_mm - blind_w - filler_w
    if visible_w < _CORNER_MIN_OPENING_MM:
        raise ValueError(
            f"Corner-blind opening {visible_w}mm too narrow "
            f"(width {cab.width_mm} - blind {blind_w} - filler {filler_w}); "
            f"minimum {_CORNER_MIN_OPENING_MM}mm"
        )

    # -- Side panels (confirmats + HDF groove, joinery-gated) --
    for side, label in [("left", "Lewy bok"), ("right", "Prawy bok")]:
        ops: list[MachiningOp] = []
        if "confirmat" in m.joinery_type:
            ops.extend(_confirmat_side_ops(cab, m, side_h))
        ops.append(_hdf_groove_op(m.back_groove_depth_mm, side_h))
        r.panels.append(Panel(
            id=f"{cab.id}_{side}",
            name=label,
            material=cab.body_material,
            thickness_mm=m.side_thickness_mm,
            width_mm=cab.depth_mm,
            height_mm=side_h,
            banded_edges={"front": _body_eb(cab, side_h)},
            machining_ops=ops,
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
        machining_ops=[_hdf_groove_op(m.back_groove_depth_mm, bottom_w)],
        role=PanelRole.BOTTOM,
    ))

    # -- Top stretchers (rear one carries the groove) --
    for pos, label, banded in [("przedni", "Trawers przedni", True),
                               ("tylny", "Trawers tylny", False)]:
        r.panels.append(Panel(
            id=f"{cab.id}_trawers_{pos}",
            name=label,
            material=cab.body_material,
            thickness_mm=m.top_thickness_mm,
            width_mm=bottom_w,
            height_mm=_STRETCHER_WIDTH_MM,
            banded_edges={"front": _body_eb(cab, bottom_w)} if banded else {},
            machining_ops=(
                [] if banded
                else [_hdf_groove_op(m.back_groove_depth_mm, bottom_w)]
            ),
            role=PanelRole.TOP,
        ))

    # -- Back panel (groove-seated, reduced) --
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

    # -- Shelves (span the full internal width, blind zone included) --
    shelf_w = m.shelf_width(cab.width_mm)
    shelf_d = cab.depth_mm - 5
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

    door_h = m.door_height(side_h)

    # -- Blind front (zaślepka) — fixed, hidden except the filler-side sliver --
    blind_visible_edge = "right" if corner_side == "left" else "left"
    r.panels.append(Panel(
        id=f"{cab.id}_front_slepy",
        name="Front ślepy",
        material=cab.front_material,
        thickness_mm=m.front_thickness_mm,
        width_mm=blind_w,
        height_mm=door_h,
        banded_edges={blind_visible_edge: _front_eb(cab, door_h)},
        role=PanelRole.FRONT_BLIND,
        grain=GrainAxis.HEIGHT,
    ))

    # -- Filler (listwa maskująca) --
    r.panels.append(Panel(
        id=f"{cab.id}_listwa",
        name="Listwa narożna",
        material=cab.front_material,
        thickness_mm=m.front_thickness_mm,
        width_mm=filler_w,
        height_mm=door_h,
        banded_edges={
            "front": _front_eb(cab, filler_w),
            "back":  _front_eb(cab, filler_w),
            "left":  _front_eb(cab, door_h),
            "right": _front_eb(cab, door_h),
        },
        role=PanelRole.FILLER,
        grain=GrainAxis.HEIGHT,
    ))

    # -- Door fronts (share the visible opening) --
    door_fronts = [f for f in cab.fronts if f.get("typ", "").startswith("drzwiowy")]
    n_doors = len(door_fronts) or 1
    door_w = m.door_width(visible_w, n_doors,
                          m.front_reveal(cab.handles.type if cab.handles else None))
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
            grain=GrainAxis.HEIGHT,
        ))

    # -- Hinges + shelf pins + handles --
    for front in door_fronts:
        r.accessories.append(Accessory(
            id=f"{cab.id}_hinge_{front['id']}",
            name=f"Zawias {front.get('zawias', 'standard')}",
            type="hinge",
            quantity=front.get("ilosc_zawiasow", 2),
        ))
    if cab.shelves:
        r.accessories.append(Accessory(
            id=f"{cab.id}_shelf_pins",
            name=f"Kołek półkowy {int(cab.shelf_pins.diameter_mm)} mm",
            type="shelf_pin",
            quantity=len(cab.shelves) * 4,
        ))
    if cab.handles is not None and door_fronts:
        r.accessories.append(Accessory(
            id=f"{cab.id}_handles",
            name=_handle_accessory_name(cab.handles),
            type="handle",
            quantity=len(door_fronts),
        ))

    # -- Plinth (full width; the perpendicular run's plinth butts into it) --
    if cab.plinth_height_mm > 0:
        plinth_w = cab.width_mm - 2 * _PLINTH_SIDE_INSET_MM
        r.panels.append(Panel(
            id=f"{cab.id}_cokol",
            name="Cokół",
            material=cab.body_material,
            thickness_mm=m.side_thickness_mm,
            width_mm=plinth_w,
            height_mm=cab.plinth_height_mm - _PLINTH_FLOOR_GAP_MM,
            banded_edges={"front": _body_eb(cab, plinth_w)},
            role=PanelRole.PLINTH,
        ))

    return r


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TYPE_REGISTRY: dict[str, callable] = {
    "dolna_szufladowa":    decompose_dolna_szufladowa,
    "dolna_drzwiowa":      decompose_dolna_drzwiowa,
    "dolna_legrabox":      decompose_dolna_legrabox,
    "dolna_narozna_slepa": decompose_dolna_narozna_slepa,
    "gorna_drzwiowa":      decompose_gorna_drzwiowa,
}
