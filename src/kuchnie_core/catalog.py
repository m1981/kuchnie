"""Cabinet type catalog — construction methods as first-class rules.

Each type has a decompose function that knows how to derive physical panels
from a CabinetInstance. This is the Polyboard pattern: the CONSTRUCTION METHOD
lives here, separate from the cabinet instance that only carries configuration.

Add new cabinet types by writing a new decompose_<type> function and
registering it in TYPE_REGISTRY.
"""

from __future__ import annotations

from .model import Accessory, CabinetInstance, DecompositionResult, EdgeBand, Panel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _body_eb(cab: CabinetInstance, length_mm: float) -> EdgeBand:
    """Edge band for carcass panels (body material)."""
    return EdgeBand(
        material=f"{cab.edge_banding_type}_{cab.body_material}",
        thickness_mm=cab.edge_banding_thickness_mm,
        length_mm=length_mm,
    )


def _front_eb(cab: CabinetInstance, length_mm: float) -> EdgeBand:
    """Edge band for front panels (front material)."""
    return EdgeBand(
        material=f"{cab.edge_banding_type}_{cab.front_material}",
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
    r = DecompositionResult(cabinet_id=cab.id, cabinet_type=cab.type)

    side_h = cab.height_mm - cab.plinth_height_mm  # 720 - 100 = 620

    # -- Side panels (left + right) --
    for side, label in [("left", "Lewy bok"), ("right", "Prawy bok")]:
        r.panels.append(Panel(
            id=f"{cab.id}_{side}",
            name=label,
            material=cab.body_material,
            thickness_mm=cab.thickness_side_mm,
            width_mm=cab.depth_mm,
            height_mm=side_h,
            banded_edges={"front": _body_eb(cab, side_h)},
        ))

    # -- Bottom panel --
    bottom_w = cab.width_mm - 2 * cab.thickness_side_mm
    r.panels.append(Panel(
        id=f"{cab.id}_bottom",
        name="Dno",
        material=cab.body_material,
        thickness_mm=cab.thickness_bottom_mm,
        width_mm=bottom_w,
        height_mm=cab.depth_mm,
        banded_edges={"front": _body_eb(cab, bottom_w)},
    ))

    # -- Back panel (in groove, no banding) --
    back_w = cab.width_mm - 2 * cab.thickness_side_mm + 2 * cab.groove_depth_mm
    back_h = side_h + cab.groove_depth_mm  # extends into bottom groove
    r.panels.append(Panel(
        id=f"{cab.id}_back",
        name="Plecy",
        material=cab.back_material,
        thickness_mm=cab.thickness_back_mm,
        width_mm=back_w,
        height_mm=back_h,
        banded_edges={},  # HDF — never banded
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
            thickness_mm=cab.thickness_front_mm,
            width_mm=front_w,
            height_mm=front_h,
            banded_edges={
                "front": _front_eb(cab, front_w),
                "back":  _front_eb(cab, front_w),
                "left":  _front_eb(cab, front_h),
                "right": _front_eb(cab, front_h),
            },
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
    if cab.handles:
        n = len([f for f in cab.fronts if f.get("typ") == "szufladowy"])
        r.accessories.append(Accessory(
            id=f"{cab.id}_handles",
            name=f"Uchwyt {cab.handles.get('typ', 'standard')} "
                 f"(rozstaw {cab.handles.get('rozstaw', '')}mm)",
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
    r = DecompositionResult(cabinet_id=cab.id, cabinet_type=cab.type)

    # -- Side panels --
    for side, label in [("left", "Lewy bok"), ("right", "Prawy bok")]:
        r.panels.append(Panel(
            id=f"{cab.id}_{side}",
            name=label,
            material=cab.body_material,
            thickness_mm=cab.thickness_side_mm,
            width_mm=cab.depth_mm,
            height_mm=cab.height_mm,
            banded_edges={"front": _body_eb(cab, cab.height_mm)},
        ))

    # -- Top + Bottom panels --
    horiz_w = cab.width_mm - 2 * cab.thickness_side_mm
    for pos, label in [("top", "Góra"), ("bottom", "Dno")]:
        r.panels.append(Panel(
            id=f"{cab.id}_{pos}",
            name=label,
            material=cab.body_material,
            thickness_mm=cab.thickness_bottom_mm,
            width_mm=horiz_w,
            height_mm=cab.depth_mm,
            banded_edges={"front": _body_eb(cab, horiz_w)},
        ))

    # -- Back panel (in groove, no banding) --
    back_w = cab.width_mm - 2 * cab.thickness_side_mm + 2 * cab.groove_depth_mm
    back_h = cab.height_mm - 2 * cab.thickness_bottom_mm + 2 * cab.groove_depth_mm
    r.panels.append(Panel(
        id=f"{cab.id}_back",
        name="Plecy",
        material=cab.back_material,
        thickness_mm=cab.thickness_back_mm,
        width_mm=back_w,
        height_mm=back_h,
        banded_edges={},
    ))

    # -- Shelves --
    shelf_w = horiz_w - 2   # 1 mm clearance per side
    shelf_d = cab.depth_mm - 5  # clearance from back panel
    for shelf in cab.shelves:
        r.panels.append(Panel(
            id=f"{cab.id}_shelf_{shelf['id']}",
            name=f"Półka {shelf['id']}",
            material=cab.body_material,
            thickness_mm=cab.thickness_shelf_mm,
            width_mm=shelf_w,
            height_mm=shelf_d,
            banded_edges={"front": _body_eb(cab, shelf_w)},
        ))

    # -- Doors --
    door_fronts = [f for f in cab.fronts if f.get("typ", "").startswith("drzwiowy")]
    n_doors = len(door_fronts) or 1
    gap_total = 3 * (n_doors + 1)  # 3 mm per gap (left, right, between)
    door_w = (cab.width_mm - gap_total) / n_doors
    door_h = cab.height_mm - 6  # 3 mm top + 3 mm bottom

    for front in door_fronts:
        r.panels.append(Panel(
            id=f"{cab.id}_front_{front['id']}",
            name=f"Front {front['id']}",
            material=cab.front_material,
            thickness_mm=cab.thickness_front_mm,
            width_mm=door_w,
            height_mm=door_h,
            banded_edges={
                "front": _front_eb(cab, door_w),
                "back":  _front_eb(cab, door_w),
                "left":  _front_eb(cab, door_h),
                "right": _front_eb(cab, door_h),
            },
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
    if cab.handles and door_fronts:
        r.accessories.append(Accessory(
            id=f"{cab.id}_handles",
            name=f"Uchwyt {cab.handles.get('typ', 'standard')} "
                 f"(rozstaw {cab.handles.get('rozstaw', '')}mm)",
            type="handle",
            quantity=len(door_fronts),
        ))

    return r


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TYPE_REGISTRY: dict[str, callable] = {
    "dolna_szufladowa": decompose_dolna_szufladowa,
    "gorna_drzwiowa":   decompose_gorna_drzwiowa,
}
