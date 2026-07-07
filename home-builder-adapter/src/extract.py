"""Extract kitchen data from a home_builder_5 Blender scene.

Walks the Blender scene tree looking for IS_FRAMELESS_*_CAGE objects,
reads their custom properties (dimensions, cabinet type, drawer stacks),
converts from meters to millimeters, and produces a kuchnie_core.Kitchen.

This is the Anti-Corruption Layer between home_builder_5's vocabulary
(IS_FRAMELESS_CABINET_CAGE, CABINET_TYPE, Dim X/Y/Z, opening_sizes)
and kuchnie_core's domain model (Kitchen, Row, CabinetInstance).

IMPORTANT: This module requires bpy (Blender Python API). It only works
inside Blender's interpreter or with `pip install bpy`.

Reference: docs/archive/COLD-REVIEW-HOME-BUILDER-5.md
"""

from __future__ import annotations

from typing import Any

try:
    import bpy
except ImportError:
    raise ImportError(
        "home-builder-adapter requires bpy (Blender Python API). "
        "Install with: pip install bpy"
    )

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


def _extract_cabinet(obj: Any) -> dict[str, Any] | None:
    """Extract cabinet data from a single Blender object.

    Returns a dict with keys: type, width_mm, height_mm, depth_mm,
    toe_kick_mm, drawers. Returns None if not a cabinet cage.
    """
    if not obj.get(_PROP_CABINET_CAGE):
        return None

    cab_type = obj.get(_PROP_CABINET_TYPE, "BASE")
    dim_x = obj.get(_PROP_DIM_X, 0.0)
    dim_y = obj.get(_PROP_DIM_Y, 0.0)
    dim_z = obj.get(_PROP_DIM_Z, 0.0)
    toe_kick = obj.get(_PROP_TOE_KICK, 0.0)
    opening_sizes = obj.get(_PROP_OPENING_SIZES, [])

    return {
        "type": _TYPE_MAP.get(cab_type, "dolna_drzwiowa"),
        "width_mm": _m_to_mm(dim_x),
        "height_mm": _m_to_mm(dim_z),
        "depth_mm": _m_to_mm(dim_y),
        "toe_kick_mm": _m_to_mm(toe_kick),
        "drawers": [_m_to_mm(h) for h in opening_sizes if h > 0],
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
    - type: kuchnie_core cabinet type string
    - width_mm, height_mm, depth_mm: dimensions in mm
    - toe_kick_mm: plinth height in mm
    - drawers: list of drawer heights in mm (empty if no drawers)
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
