"""Drill engine — calculate hole positions for System 32, hinges, handles.

All coordinates are in mm, relative to bottom-left of the panel's
INSIDE face (face toward cabinet interior).

Convention for side panels:
  X = distance from the FRONT edge of the panel
  Y = distance from the BOTTOM edge of the panel
"""

from __future__ import annotations

import copy

from kitchen_cam.models import (
    SYSTEM32_OFFSET,
    SYSTEM32_SPACING,
    BaseDoorConfig,
    BaseDrawerConfig,
    CargoConfig,
    CornerBlindConfig,
    CornerInternalConfig,
    CorpusSpec,
    DrillFace,
    DrillPoint,
    DrillType,
    HingeSpec,
    OvenConfig,
    Panel,
    PanelRole,
    SinkConfig,
)


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


def _get_shelf_positions(spec: CorpusSpec) -> list[float]:
    """Extract shelf positions from config, if available."""
    config = spec.config
    if isinstance(config, (BaseDoorConfig, CornerBlindConfig, CornerInternalConfig)):
        return config.shelves
    return []


def _get_door_hinge_counts(spec: CorpusSpec) -> list[int]:
    """Extract door hinge counts from config, if available."""
    config = spec.config
    if isinstance(config, (BaseDoorConfig, CornerBlindConfig, CornerInternalConfig, SinkConfig, CargoConfig)):
        return config.doors
    return []


def apply_system32(panels: list[Panel], spec: CorpusSpec) -> list[Panel]:
    """Add System 32 (∅5 mm) drill points to LEFT and RIGHT side panels.

    Returns a new list with copied panels — the originals are not modified.
    """
    panels = [copy.deepcopy(p) for p in panels]
    shelves = _get_shelf_positions(spec)

    for panel in panels:
        if panel.role not in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE):
            continue

        # --- main System 32 column (front row, X=37) ---
        for y in system32_y_positions(panel.height):
            panel.drill_points.append(DrillPoint(
                x=SYSTEM32_OFFSET,
                y=y,
                diameter=5.0,
                depth=13.0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.SYSTEM_32,
                label=f"S32 y={y:.0f}",
            ))

        # --- shelf-pin holes at shelf positions ---
        if not shelves:
            continue

        front_x = spec.shelf_pin_front_offset
        back_x = spec.depth - spec.shelf_pin_back_offset
        offsets = _shelf_pin_offsets(spec.shelf_pin_max_per_row)

        for shelf_pos in shelves:
            y_shelf = spec.panel_thickness + shelf_pos

            for dy in offsets:
                panel.drill_points.append(DrillPoint(
                    x=front_x,
                    y=round(y_shelf + dy, 2),
                    diameter=spec.shelf_pin_diameter,
                    depth=spec.shelf_pin_depth,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.SHELF_PIN,
                    label=f"shelf front y={y_shelf + dy:.0f}",
                ))

            for dy in offsets:
                panel.drill_points.append(DrillPoint(
                    x=back_x,
                    y=round(y_shelf + dy, 2),
                    diameter=spec.shelf_pin_diameter,
                    depth=spec.shelf_pin_depth,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.SHELF_PIN,
                    label=f"shelf back y={y_shelf + dy:.0f}",
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


def apply_hinges(panels: list[Panel], spec: CorpusSpec) -> list[Panel]:
    """Add hinge drill points to FRONT_DOOR panels.

    Returns a new list with copied panels — the originals are not modified.
    """
    panels = [copy.deepcopy(p) for p in panels]
    hinge = spec.hinges
    door_hinge_counts = _get_door_hinge_counts(spec)

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

        positions = _hinge_positions(panel.height, count, hinge.first_position)
        x_cup = hinge.edge_to_cup_centre
        half_spacing = hinge.screw_spacing / 2

        for y_cup in positions:
            panel.drill_points.append(DrillPoint(
                x=x_cup,
                y=y_cup,
                diameter=hinge.cup_diameter,
                depth=hinge.cup_depth,
                face=DrillFace.INSIDE,
                drill_type=DrillType.HINGE_CUP,
                label=f"cup y={y_cup:.0f}",
            ))
            for dy, suffix in ((-half_spacing, "top"), (half_spacing, "bot")):
                panel.drill_points.append(DrillPoint(
                    x=x_cup,
                    y=round(y_cup + dy, 2),
                    diameter=hinge.screw_diameter,
                    depth=hinge.screw_depth,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.HINGE_SCREW,
                    label=f"screw {suffix} y={y_cup + dy:.0f}",
                ))

    return panels


# ---------------------------------------------------------------------------
# Handles
# ---------------------------------------------------------------------------

def apply_handles(panels: list[Panel], spec: CorpusSpec) -> list[Panel]:
    """Add handle drill holes to drawer fronts.

    Returns a new list with copied panels — the originals are not modified.
    """
    panels = [copy.deepcopy(p) for p in panels]

    if not spec.handles:
        return panels

    handles = spec.handles
    half_spacing = handles.spacing / 2

    for panel in panels:
        if panel.role != PanelRole.FRONT_DRAWER:
            continue

        cx = panel.width / 2
        cy = panel.height / 2

        for dx in (-half_spacing, half_spacing):
            panel.drill_points.append(DrillPoint(
                x=round(cx + dx, 2),
                y=cy,
                diameter=handles.hole_diameter,
                depth=0,
                face=DrillFace.INSIDE,
                drill_type=DrillType.HANDLE,
                label=f"handle x={cx + dx:.0f}",
            ))

    return panels


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def apply_all_drilling(panels: list[Panel], spec: CorpusSpec) -> list[Panel]:
    """Run all drill macros in the standard order.

    Returns a new list with copied panels — the originals are not modified.
    """
    panels = apply_system32(panels, spec)
    panels = apply_hinges(panels, spec)
    panels = apply_handles(panels, spec)
    return panels
