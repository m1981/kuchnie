"""Machining operations — calculate hole positions for System 32, hinges, handles.

Imports from ``kuchnie_core.model`` (ADR-010 migration complete).
All coordinates are in mm, relative to bottom-left of the panel's
INSIDE face (face toward cabinet interior).

Convention for side panels:
  X = distance from the FRONT edge of the panel
  Y = distance from the BOTTOM edge of the panel
"""

from __future__ import annotations

import copy

from kuchnie_core.blum_hinges import HingeGeometry
from kuchnie_core.model import (
    CabinetInstance,
    HandleSpec,
    MachiningOp,
    Panel,
    PanelRole,
)


# ---------------------------------------------------------------------------
# System 32 constants (local to kitchen-cam)
# ---------------------------------------------------------------------------

SYSTEM32_OFFSET: float = 37.0   # mm from front/bottom edge
SYSTEM32_SPACING: float = 32.0  # mm between holes


# ---------------------------------------------------------------------------
# System 32
# ---------------------------------------------------------------------------

def system32_y_positions(height: float) -> list[float]:
    """Return Y positions for System 32 holes on a vertical panel."""
    positions: list[float] = []
    y = SYSTEM32_OFFSET
    while y <= height - SYSTEM32_OFFSET:
        positions.append(round(y, 2))
        y += SYSTEM32_SPACING
    return positions


def _shelf_pin_offsets(max_per_row: int, raster: float = SYSTEM32_SPACING) -> list[float]:
    """Symmetrical offsets from anchor: [0, +raster, -raster, ...]."""
    offsets = [0.0]
    i = 1
    while len(offsets) < max_per_row:
        offsets.append(round(i * raster, 2))
        if len(offsets) < max_per_row:
            offsets.append(round(-i * raster, 2))
        i += 1
    return offsets


def _get_shelf_positions(cab: CabinetInstance) -> list[float]:
    """Extract shelf positions from legacy shelves list."""
    return [
        s.get("pozycja_od_dolu", 0)
        for s in cab.shelves
        if "pozycja_od_dolu" in s
    ]


def _get_door_hinge_counts(cab: CabinetInstance) -> list[int]:
    """Extract door hinge counts from legacy fronts list."""
    return [
        f.get("ilosc_zawiasow", 2)
        for f in cab.fronts
        if f.get("typ", "").startswith("drzwiowy")
    ]


def apply_system32(panels: list[Panel], cab: CabinetInstance) -> list[Panel]:
    """Add System 32 (∅5 mm) machining ops to LEFT and RIGHT side panels.

    Returns a new list with copied panels — the originals are not modified.
    """
    panels = [copy.deepcopy(p) for p in panels]
    shelves = _get_shelf_positions(cab)

    for panel in panels:
        if panel.role not in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE):
            continue

        # --- main System 32 column (front row, X=37) ---
        for y in system32_y_positions(panel.height_mm):
            panel.machining_ops.append(MachiningOp(
                type="drill",
                x_mm=SYSTEM32_OFFSET,
                y_mm=y,
                diameter_mm=5.0,
                depth_mm=13.0,
                face="inside",
                drill_type="system32",
                note=f"S32 y={y:.0f}",
            ))

        # --- shelf-pin holes at shelf positions ---
        if not shelves:
            continue

        front_x = cab.shelf_pins.front_offset_mm
        back_x = cab.depth_mm - cab.shelf_pins.back_offset_mm
        offsets = _shelf_pin_offsets(cab.shelf_pins.max_per_row)

        for shelf_pos in shelves:
            y_shelf = cab.thickness_side_mm + shelf_pos

            for dy in offsets:
                panel.machining_ops.append(MachiningOp(
                    type="drill",
                    x_mm=front_x,
                    y_mm=round(y_shelf + dy, 2),
                    diameter_mm=cab.shelf_pins.diameter_mm,
                    depth_mm=cab.shelf_pins.depth_mm,
                    face="inside",
                    drill_type="shelf_pin",
                    note=f"shelf front y={y_shelf + dy:.0f}",
                ))

            for dy in offsets:
                panel.machining_ops.append(MachiningOp(
                    type="drill",
                    x_mm=back_x,
                    y_mm=round(y_shelf + dy, 2),
                    diameter_mm=cab.shelf_pins.diameter_mm,
                    depth_mm=cab.shelf_pins.depth_mm,
                    face="inside",
                    drill_type="shelf_pin",
                    note=f"shelf back y={y_shelf + dy:.0f}",
                ))

    return panels


# ---------------------------------------------------------------------------
# Hinges (Blum CLIP top 35mm default)
# ---------------------------------------------------------------------------

def _hinge_positions(front_height: float, count: int, first_pos: float) -> list[float]:
    """Return Y positions for hinge cup centres on a door front."""
    if count == 1:
        return [front_height / 2]
    if count == 2:
        return [first_pos, front_height - first_pos]
    bottom = first_pos
    top = front_height - first_pos
    step = (top - bottom) / (count - 1)
    return [round(bottom + i * step, 2) for i in range(count)]


def apply_hinges(panels: list[Panel], cab: CabinetInstance) -> list[Panel]:
    """Add hinge drill machining ops to FRONT_DOOR panels.

    Returns a new list with copied panels — the originals are not modified.
    """
    panels = [copy.deepcopy(p) for p in panels]

    # YAML-loaded cabinets carry no explicit HingeGeometry — fall back to
    # the Blum CLIP top defaults; hinge counts still come from the fronts.
    hinge = cab.hinges or HingeGeometry()

    door_hinge_counts = _get_door_hinge_counts(cab)

    for panel in panels:
        if panel.role != PanelRole.FRONT_DOOR:
            continue

        door_fronts = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        idx = door_fronts.index(panel)
        if idx < len(door_hinge_counts):
            count = door_hinge_counts[idx]
        else:
            count = 0

        if count == 0:
            continue

        positions = _hinge_positions(panel.height_mm, count, hinge.first_position_mm)
        x_cup = hinge.edge_to_cup_centre_mm
        half_spacing = hinge.screw_spacing_mm / 2

        for y_cup in positions:
            panel.machining_ops.append(MachiningOp(
                type="drill",
                x_mm=x_cup,
                y_mm=y_cup,
                diameter_mm=hinge.cup_diameter_mm,
                depth_mm=hinge.cup_drill_depth_mm,
                face="inside",
                drill_type="hinge_cup",
                note=f"cup y={y_cup:.0f}",
            ))
            for dy, suffix in ((-half_spacing, "top"), (half_spacing, "bot")):
                panel.machining_ops.append(MachiningOp(
                    type="drill",
                    x_mm=x_cup,
                    y_mm=round(y_cup + dy, 2),
                    diameter_mm=hinge.screw_diameter_mm,
                    depth_mm=hinge.screw_depth_mm,
                    face="inside",
                    drill_type="hinge_screw",
                    note=f"screw {suffix} y={y_cup + dy:.0f}",
                ))

    return panels


# ---------------------------------------------------------------------------
# Handles
# ---------------------------------------------------------------------------

def apply_handles(panels: list[Panel], cab: CabinetInstance) -> list[Panel]:
    """Add handle drill holes to drawer fronts.

    Returns a new list with copied panels — the originals are not modified.
    """
    panels = [copy.deepcopy(p) for p in panels]

    if not cab.handles:
        return panels

    handles: HandleSpec = cab.handles
    half_spacing = handles.spacing_mm / 2

    for panel in panels:
        if panel.role != PanelRole.FRONT_DRAWER:
            continue

        cx = panel.width_mm / 2
        cy = panel.height_mm / 2

        for dx in (-half_spacing, half_spacing):
            panel.machining_ops.append(MachiningOp(
                type="drill",
                x_mm=round(cx + dx, 2),
                y_mm=cy,
                diameter_mm=handles.hole_diameter_mm,
                depth_mm=0,
                face="inside",
                drill_type="handle",
                note=f"handle x={cx + dx:.0f}",
            ))

    return panels


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def apply_all_drilling(panels: list[Panel], cab: CabinetInstance) -> list[Panel]:
    """Run all drill macros in the standard order.

    Returns a new list with copied panels — the originals are not modified.
    """
    panels = apply_system32(panels, cab)
    panels = apply_hinges(panels, cab)
    panels = apply_handles(panels, cab)
    return panels
