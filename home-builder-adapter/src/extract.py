"""Extract kitchen data from a home_builder_5 Blender scene.

Walks the Blender scene tree looking for IS_FRAMELESS_*_CAGE objects,
reads their custom properties and geometry-node inputs (dimensions,
cabinet type, drawer stacks, per-part material assignments), converts
from meters to millimeters, and produces a kuchnie_core.Kitchen.

This is the Anti-Corruption Layer between home_builder_5's vocabulary
(IS_FRAMELESS_CABINET_CAGE, CABINET_TYPE, Dim X/Y/Z, splitter/opening
cages) and kuchnie_core's domain model (Kitchen, Row, CabinetInstance).

Extraction r2 (wk-81a47ab8): drawer stacks are read from the cage
hierarchy the scene demonstrably stores (proof:
exercises/e2e-d60-legrabox/generated/cage-hierarchy.json):

    Bay -> Splitter Vertical (IS_FRAMELESS_SPLITTER_VERTICAL_CAGE)
        -> Opening N (IS_FRAMELESS_OPENING_CAGE, geo-node "Dim Z")
        -> Drawers insert -> Drawer Front (IS_DRAWER_FRONT)
        -> Drawer Box (IS_DRAWER_BOX + clearance props)

IMPORTANT: This module requires bpy (Blender Python API). It only works
inside Blender's interpreter or with `pip install bpy`.

Reference: docs/archive/COLD-REVIEW-HOME-BUILDER-5.md,
docs/hb5-headless-scripting.md
"""

from __future__ import annotations

import re
from typing import Any, Iterator

try:
    import bpy
except ImportError as err:
    raise ImportError(
        "home-builder-adapter requires bpy (Blender Python API). "
        "Install with: pip install bpy"
    ) from err

from kuchnie_core.model import CabinetInstance, Kitchen, Row


# ---------------------------------------------------------------------------
# Constants — home_builder_5 property names
# ---------------------------------------------------------------------------

_PROP_CABINET_CAGE = "IS_FRAMELESS_CABINET_CAGE"
_PROP_CABINET_TYPE = "CABINET_TYPE"
_PROP_DIM_X = "Dim X"  # width in meters
_PROP_DIM_Y = "Dim Y"  # depth in meters
_PROP_DIM_Z = "Dim Z"  # height in meters
_PROP_TOE_KICK = "Toe Kick Height"
_PROP_OPENING_SIZES = "opening_sizes"

# Cage-hierarchy markers (r2, wk-81a47ab8) — set by hb5's SplitterVertical /
# CabinetOpening / DrawerFront type classes and persisted as ID props.
_PROP_SPLITTER_CAGE = "IS_FRAMELESS_SPLITTER_VERTICAL_CAGE"
_PROP_OPENING_CAGE = "IS_FRAMELESS_OPENING_CAGE"
_PROP_DRAWER_FRONT = "IS_DRAWER_FRONT"
_PROP_DRAWER_BOX = "IS_DRAWER_BOX"
_PROP_CABINET_PART = "CABINET_PART"

# Geometry-node input sockets that carry material datablocks on parts.
# "Top Surface" is the face material on CabinetPart panels; drawer boxes
# carry a single "Material" socket (see cage-hierarchy.json).
_GN_MATERIAL_SOCKETS = ("Top Surface", "Material")

# hb5 names split openings "Opening 1".."Opening N" — the trailing index
# is the top-down position (SplitterVertical adds them top to bottom).
_TRAILING_INT_RE = re.compile(r"(\d+)\s*$")

# Cabinet type mapping: home_builder_5 → kuchnie_core type string
_TYPE_MAP = {
    "BASE": "dolna_drzwiowa",
    "TALL": "tall_oven",
    "UPPER": "gorna_drzwiowa",
}

# Blender scenes carry geometry, not decor codes. Materials stay explicitly
# unassigned; the BOM stage resolves them against the catalog (ADR-008).
_UNASSIGNED_MATERIAL = "unassigned"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _m_to_mm(m: float) -> int:
    """Convert meters to millimeters, rounded to integer."""
    return round(m * 1000)


# ---------------------------------------------------------------------------
# Cage-hierarchy walking (r2, wk-81a47ab8)
# ---------------------------------------------------------------------------

def _iter_subtree(obj: Any) -> Iterator[Any]:
    """Yield obj and every descendant (depth-first)."""
    yield obj
    for child in getattr(obj, "children", ()) or ():
        yield from _iter_subtree(child)


def _gn_input(obj: Any, name: str) -> Any:
    """Read a geometry-nodes modifier input socket by name, or None.

    hb5 stores opening heights (Dim Z) and part materials as geo-node
    modifier inputs, NOT ID props (tr-e60f4fe0). Traversal mirrors
    exercises/harness/hb5.py::dump_cage_hierarchy, which produced the
    committed proof cage-hierarchy.json.
    """
    for mod in getattr(obj, "modifiers", None) or ():
        if getattr(mod, "type", None) != "NODES":
            continue
        group = getattr(mod, "node_group", None)
        if group is None:
            continue
        for item in group.interface.items_tree:
            if (item.item_type == "SOCKET" and item.in_out == "INPUT"
                    and item.name == name):
                try:
                    return mod[item.identifier]
                except (KeyError, TypeError):
                    return None
    return None


def _subtree_has(obj: Any, prop: str) -> bool:
    """True if obj or any descendant carries a truthy ID prop `prop`."""
    return any(node.get(prop) for node in _iter_subtree(obj))


def _opening_top_down_index(obj: Any) -> int:
    """Sort key: hb5 names openings 'Opening 1..N' TOP-DOWN."""
    m = _TRAILING_INT_RE.search(getattr(obj, "name", "") or "")
    return int(m.group(1)) if m else 0


def _opening_height_m(opening: Any) -> float:
    """Opening height in meters: geo-node 'Dim Z', bbox fallback."""
    val = _gn_input(opening, _PROP_DIM_Z)
    if val:
        return float(val)
    dims = getattr(opening, "dimensions", None)
    return float(dims[2]) if dims is not None else 0.0


def _extract_drawer_stack(cage: Any) -> list[int]:
    """Per-drawer opening heights in mm, ordered BOTTOM-UP.

    Walks Bay -> Splitter Vertical -> Opening N and keeps the openings
    whose insert subtree contains a drawer front (IS_DRAWER_FRONT) — an
    opening holding a door or shelves is not a drawer.

    ORDER CONTRACT: CabinetInstance.drawers is BOTTOM-UP (G8, pinned by
    tr-00330365 and kuchnie-core/tests/test_drawer_order.py). hb5's
    SplitterVertical enumerates 'Opening 1..N' TOP-DOWN (openings are
    added "from Top to Bottom" — types_frameless.py), so the scene order
    is REVERSED here. Getting this wrong drilled the M-drawer runner rows
    at the bottom of the e2e side panel (GAP-REPORT P4).
    """
    for node in _iter_subtree(cage):
        if not node.get(_PROP_SPLITTER_CAGE):
            continue
        openings = sorted(
            (ch for ch in getattr(node, "children", ()) or ()
             if ch.get(_PROP_OPENING_CAGE)),
            key=_opening_top_down_index,
        )
        heights_top_down = [
            _m_to_mm(_opening_height_m(op))
            for op in openings
            if _subtree_has(op, _PROP_DRAWER_FRONT)
        ]
        if heights_top_down:
            return list(reversed(heights_top_down))  # top-down -> bottom-up
    return []


def _part_materials(cage: Any) -> dict[str, str | None]:
    """Per-part material/finish assignment NAMES stored on cage parts.

    Values are hb5 style-material names (e.g. 'Default Style Finish'),
    NOT catalog decor codes — no resolver exists yet, so CabinetInstance
    material fields stay unassigned (ADR-008) and these names ride along
    for the BOM stage / a future resolver. A part whose sockets carry no
    material stays None — same GAP posture as the exercise legs.
    """
    materials: dict[str, str | None] = {}
    for node in _iter_subtree(cage):
        if not (node.get(_PROP_CABINET_PART) or node.get(_PROP_DRAWER_BOX)):
            continue
        name = None
        for socket in _GN_MATERIAL_SOCKETS:
            mat = _gn_input(node, socket)
            name = getattr(mat, "name", None)
            if name:
                break
        materials[getattr(node, "name", f"part_{len(materials)}")] = (
            name or None
        )
    return materials


def _extract_cabinet(obj: Any) -> dict[str, Any] | None:
    """Extract cabinet data from a single Blender object.

    Returns a dict with keys: type, width_mm, height_mm, depth_mm,
    toe_kick_mm, drawers. Returns None if not a cabinet cage.
    """
    if not obj.get(_PROP_CABINET_CAGE):
        return None

    cab_type = obj.get(_PROP_CABINET_TYPE, "BASE")
    # hb5 stores cabinet dimensions as geometry-node modifier inputs, NOT
    # ID props (tr-e60f4fe0) — the evaluated cage bounding box is the
    # reliable carrier. Legacy 'Dim X/Y/Z' ID props win when present.
    dims = getattr(obj, "dimensions", None)

    def _dim(prop: str, axis: int) -> float:
        explicit = obj.get(prop)
        if explicit:
            return explicit
        return float(dims[axis]) if dims is not None else 0.0

    dim_x = _dim(_PROP_DIM_X, 0)
    dim_y = _dim(_PROP_DIM_Y, 1)
    dim_z = _dim(_PROP_DIM_Z, 2)
    toe_kick = obj.get(_PROP_TOE_KICK, 0.0)

    # r2 (wk-81a47ab8): the drawer stack IS stored in the scene — read it
    # from the splitter/opening cage hierarchy. Returned bottom-up (G8).
    drawer_heights = _extract_drawer_stack(obj)
    if not drawer_heights:
        # r1 legacy path unchanged: opening_sizes never persists on real
        # hb5 cages (transient python attribute) — read stays for
        # legacy/faked scenes; empty otherwise.
        opening_sizes = obj.get(_PROP_OPENING_SIZES, [])
        drawer_heights = [_m_to_mm(h) for h in opening_sizes if h > 0]
        kuchnie_type = _TYPE_MAP.get(cab_type, "dolna_drzwiowa")
    else:
        # A BASE cabinet with a persisted drawer stack is a drawer
        # cabinet, not the r1 dolna_drzwiowa fallback (gap E2).
        kuchnie_type = (
            "dolna_legrabox" if cab_type == "BASE"
            else _TYPE_MAP.get(cab_type, "dolna_drzwiowa")
        )

    return {
        "type": kuchnie_type,
        "width_mm": _m_to_mm(dim_x),
        "height_mm": _m_to_mm(dim_z),
        "depth_mm": _m_to_mm(dim_y),
        "toe_kick_mm": _m_to_mm(toe_kick),
        "drawers": drawer_heights,
        "part_materials": _part_materials(obj),
    }


def _count_shelves(obj: Any) -> int:
    """Count shelf objects inside a cabinet cage."""
    count = 0
    for child in obj.children:
        if child.get("IS_FRAMELESS_INTERIOR_PART"):
            count += 1
    return count


def extract_cabinets_from_scene() -> list[dict[str, Any]]:
    """Walk the current Blender scene and extract all cabinet data.

    Returns a list of dicts, each representing one cabinet with:
    - type: kuchnie_core cabinet type string (BASE with a persisted
      drawer stack -> dolna_legrabox)
    - width_mm, height_mm, depth_mm: dimensions in mm
    - toe_kick_mm: plinth height in mm
    - drawers: per-drawer opening heights in mm, BOTTOM-UP (G8,
      tr-00330365); empty if no drawers
    - part_materials: part name -> hb5 material name (None = unassigned)
    - shelves: number of shelves
    """
    cabinets = []
    for obj in bpy.data.objects:
        cab = _extract_cabinet(obj)
        if cab is not None:
            cab["shelves"] = _count_shelves(obj)
            cabinets.append(cab)
    return cabinets


def cabinets_to_kitchen(cabinets: list[dict[str, Any]]) -> Kitchen:
    """Convert extracted cabinet dicts into a kuchnie_core.Kitchen.

    All cabinets go into a single Row (the user can restructure later).
    Wall dimensions are inferred from the cabinets — Blender scenes don't
    carry an explicit wall entity for us to read.
    """
    cab_instances = []
    for i, cab in enumerate(cabinets):
        cab_instances.append(CabinetInstance(
            id=f"cab_{i:03d}",
            type=cab["type"],
            description=f"Extracted from Blender ({cab['type']})",
            width_mm=cab["width_mm"],
            height_mm=cab["height_mm"],
            depth_mm=cab["depth_mm"],
            body_material=_UNASSIGNED_MATERIAL,
            back_material=_UNASSIGNED_MATERIAL,
            front_material=_UNASSIGNED_MATERIAL,
            plinth_height_mm=cab["toe_kick_mm"],
            # cab["drawers"] arrives BOTTOM-UP from _extract_drawer_stack
            # and is passed through unchanged — CabinetInstance.drawers is
            # bottom-up by contract (G8, tr-00330365,
            # kuchnie-core/tests/test_drawer_order.py), so S1 = bottom.
            drawers=[
                {"id": f"S{j + 1}", "wysokosc": h}
                for j, h in enumerate(cab.get("drawers", []))
            ],
        ))

    row = Row(
        id="row_0",
        label="Extracted Row",
        wall_width_mm=sum(c.width_mm for c in cab_instances),
        wall_height_mm=max((c.height_mm for c in cab_instances), default=0),
        cabinets=cab_instances,
    )

    return Kitchen(
        rows=[row],
        project_name="Extracted Kitchen",
    )


def extract_kitchen_from_blend() -> Kitchen:
    """Full pipeline: walk scene → extract → convert to Kitchen.

    This is the main entry point for the adapter.
    """
    cabinets = extract_cabinets_from_scene()
    return cabinets_to_kitchen(cabinets)
