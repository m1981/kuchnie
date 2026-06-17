"""Drill engine — calculate hole positions for System 32, hinges, handles.

All coordinates are in mm, relative to bottom-left of the panel's
INSIDE face (face toward cabinet interior).

Convention for side panels:
  X = distance from the FRONT edge of the panel
  Y = distance from the BOTTOM edge of the panel
"""

from __future__ import annotations

from kitchen_cad.models import (
    CorpusSpec,
    DrillFace,
    DrillPoint,
    DrillType,
    HingeSpec,
    Panel,
    PanelRole,
)


# ---------------------------------------------------------------------------
# System 32
# ---------------------------------------------------------------------------

SYSTEM32_OFFSET = 37.0   # mm from front/bottom edge
SYSTEM32_SPACING = 32.0  # mm between holes


def system32_y_positions(height: float) -> list[float]:
    """Return Y positions for System 32 holes on a vertical panel.

    Holes start at 37 mm from the bottom and repeat every 32 mm,
    stopping before (height - 37) from the bottom.
    """
    positions: list[float] = []
    y = SYSTEM32_OFFSET
    while y <= height - SYSTEM32_OFFSET:
        positions.append(round(y, 2))
        y += SYSTEM32_SPACING
    return positions


def apply_system32(panels: list[Panel], spec: CorpusSpec) -> list[Panel]:
    """Add System 32 (∅5 mm) drill points to LEFT and RIGHT side panels.

    Also adds shelf-pin holes at shelf positions (front + back row).
    """
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
        #     Two rows per shelf: front (X=37) and back (X = depth - 37)
        back_x = spec.depth - SYSTEM32_OFFSET
        for shelf_pos in spec.shelves:
            # shelf_pos is measured from INSIDE bottom of the cabinet
            # On the side panel, the inside bottom starts at Y = panel_thickness
            # but we measure from the bottom of the panel (Y=0).
            # Inside bottom Y = spec.panel_thickness
            # shelf Y from panel bottom = panel_thickness + shelf_pos
            y_shelf = spec.panel_thickness + shelf_pos
            for x in (SYSTEM32_OFFSET, back_x):
                panel.drill_points.append(DrillPoint(
                    x=x,
                    y=y_shelf,
                    diameter=5.0,
                    depth=12.0,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.SHELF_PIN,
                    label=f"shelf pin y={y_shelf:.0f}",
                ))

    return panels


# ---------------------------------------------------------------------------
# Hinges (Blum CLIP top 35mm default)
# ---------------------------------------------------------------------------

def _default_hinge() -> HingeSpec:
    return HingeSpec()


def _hinge_positions(front_height: float, count: int, first_pos: float) -> list[float]:
    """Return Y positions for hinge cup centres on a door front.

    Positions measured from the BOTTOM of the front panel.
    """
    if count == 1:
        return [front_height / 2]
    if count == 2:
        return [first_pos, front_height - first_pos]
    # 3+ hinges: evenly spaced between first and last
    bottom = first_pos
    top = front_height - first_pos
    step = (top - bottom) / (count - 1)
    return [round(bottom + i * step, 2) for i in range(count)]


def apply_hinges(panels: list[Panel], spec: CorpusSpec) -> list[Panel]:
    """Add hinge drill points to FRONT_DOOR panels.

    For each hinge:
      - 1× cup hole  (∅35 mm, depth 13 mm)   at X = edge_to_cup_centre
      - 2× screw holes (∅3 mm, depth 2 mm)   at X = edge_to_cup_centre
        spaced screw_spacing/2 above and below cup centre Y
    """
    hinge = spec.hinges or _default_hinge()

    for panel in panels:
        if panel.role != PanelRole.FRONT_DOOR:
            continue

        # Determine how many hinges for this front
        # spec.doors list has one entry per front with hinge count
        # Find the matching front index
        door_fronts = [p for p in panels if p.role == PanelRole.FRONT_DOOR]
        idx = door_fronts.index(panel)
        if idx < len(spec.doors):
            count = spec.doors[idx]
        else:
            count = 0

        if count == 0:
            continue

        positions = _hinge_positions(panel.height, count, hinge.first_position)
        x_cup = hinge.edge_to_cup_centre
        half_spacing = hinge.screw_spacing / 2

        for y_cup in positions:
            # Cup hole
            panel.drill_points.append(DrillPoint(
                x=x_cup,
                y=y_cup,
                diameter=hinge.cup_diameter,
                depth=hinge.cup_depth,
                face=DrillFace.INSIDE,
                drill_type=DrillType.HINGE_CUP,
                label=f"cup y={y_cup:.0f}",
            ))
            # Screw holes (above and below cup)
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

    Bar handle: two ∅5 mm through-holes, centred horizontally and vertically.
    """
    if not spec.handles:
        return panels

    handles = spec.handles
    half_spacing = handles.spacing / 2

    for panel in panels:
        if panel.role != PanelRole.FRONT_DRAWER:
            continue

        cx = panel.width / 2   # horizontal centre
        cy = panel.height / 2  # vertical centre

        for dx in (-half_spacing, half_spacing):
            panel.drill_points.append(DrillPoint(
                x=round(cx + dx, 2),
                y=cy,
                diameter=handles.hole_diameter,
                depth=0,  # through hole
                face=DrillFace.INSIDE,
                drill_type=DrillType.HANDLE,
                label=f"handle x={cx + dx:.0f}",
            ))

    return panels


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def apply_all_drilling(panels: list[Panel], spec: CorpusSpec) -> list[Panel]:
    """Run all drill macros in the standard order."""
    panels = apply_system32(panels, spec)
    panels = apply_hinges(panels, spec)
    panels = apply_handles(panels, spec)
    return panels
