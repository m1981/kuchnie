"""Wall Builder — Converts config to wall-based representation.

Bridges the gap between:
- Config format (runs with turn directions)
- Wall model (walls with start/end points)

Functions:
- config_to_walls: Convert runs to Room with Wall objects
- config_to_cabinets: Convert cabinets to WallCabinet objects
- config_to_corners: Detect corner cabinets
- build_layout: Full pipeline (config → positioned cabinets)
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import math

from .kitchen.wall import Wall, Room, WallCabinet, CornerReference
from .core.geometry import Vector2D


# Direction vectors
DIRECTIONS = {
    "east": (1, 0),
    "north": (0, 1),
    "west": (-1, 0),
    "south": (0, -1),
}

# Turn mapping: (current_direction, turn) → new_direction
TURNS = {
    ("east", "left"): "north",
    ("east", "right"): "south",
    ("north", "left"): "west",
    ("north", "right"): "east",
    ("west", "left"): "south",
    ("west", "right"): "north",
    ("south", "left"): "east",
    ("south", "right"): "west",
}


@dataclass
class PositionedCabinet:
    """A cabinet with calculated world position."""
    wall_id: str
    offset: float
    width: float
    depth: float
    height: float
    level: str  # "base", "upper", "tall"
    cabinet_type: str
    world_x: float = 0.0
    world_y: float = 0.0
    world_z: float = 0.0
    rotation: float = 0.0  # radians


@dataclass
class Layout:
    """Complete layout with walls, cabinets, and corners."""
    room: Room
    cabinets: List[PositionedCabinet]
    corners: List[CornerReference]


def _get_run_width(run: dict, settings: dict) -> float:
    """Calculate total width of a run (base section)."""
    base_cabs = run.get("base", [])
    if not base_cabs:
        return 0.0
    cabinet_gap = settings.get("cabinetGap", 0)
    return sum(c["width"] for c in base_cabs) + cabinet_gap * (len(base_cabs) - 1)


def config_to_walls(config: dict) -> Room:
    """Convert config runs to Room with Wall objects.

    First run starts at origin, going east.
    Subsequent runs turn from previous direction.
    """
    settings = config.get("settings", {})
    runs = config.get("runs", [])

    if not runs:
        return Room(walls=[])

    walls = []
    current_x, current_y = 0.0, 0.0
    direction = "east"  # First run goes east

    for i, run in enumerate(runs):
        label = run.get("label", f"wall_{i}")

        # Apply turn (except for first run)
        turn = run.get("turn")
        if turn and i > 0:
            key = (direction, turn)
            if key in TURNS:
                direction = TURNS[key]

        # Get direction vector
        dx, dy = DIRECTIONS[direction]

        # Calculate wall length from base cabinets
        wall_length = _get_run_width(run, settings)

        # Create wall
        start = Vector2D(current_x, current_y)
        end = Vector2D(current_x + wall_length * dx, current_y + wall_length * dy)

        wall = Wall(id=label, start=start, end=end)
        walls.append(wall)

        # Move to end of wall for next run
        current_x = end.x
        current_y = end.y

    return Room(walls=walls)


def config_to_cabinets(config: dict) -> List[WallCabinet]:
    """Convert config cabinets to WallCabinet objects.

    Each cabinet gets:
    - wall_id: which run/wall it belongs to
    - offset: distance from wall start
    - width, depth, height: dimensions
    """
    settings = config.get("settings", {})
    cabinet_gap = settings.get("cabinetGap", 0)
    cabinets = []

    for run in config.get("runs", []):
        label = run.get("label", "unnamed")

        # Process base cabinets
        offset = 0.0
        for cab in run.get("base", []):
            cab_type = cab.get("type", "")
            if cab_type == "filler":
                depth = settings.get("baseDepth", 560)
                height = settings.get("baseBodyHeight", 720) + settings.get("plinthHeight", 120)
            else:
                depth = settings.get("baseDepth", 560) + cab.get("depthOffset", 0)
                height = settings.get("baseBodyHeight", 720) + settings.get("plinthHeight", 120)

            wall_cab = WallCabinet(
                wall_id=label,
                offset=offset,
                width=cab["width"],
                depth=depth,
                height=height,
            )
            cabinets.append(wall_cab)
            offset += cab["width"] + cabinet_gap

        # Process upper cabinets (same offsets as base)
        offset = 0.0
        for cab in run.get("upper", []):
            depth = settings.get("wallDepth", 300)
            height = settings.get("wallHeight", 720)

            wall_cab = WallCabinet(
                wall_id=label,
                offset=offset,
                width=cab["width"],
                depth=depth,
                height=height,
            )
            cabinets.append(wall_cab)
            offset += cab["width"] + cabinet_gap

    return cabinets


def config_to_corners(config: dict) -> List[CornerReference]:
    """Detect corner cabinets in config.

    Corner cabinets are at the end of a run (or start of connecting run).
    They reference two walls: primary (current) and secondary (next).
    """
    corners = []
    runs = config.get("runs", [])

    for i in range(len(runs) - 1):
        current_run = runs[i]
        next_run = runs[i + 1]
        current_label = current_run.get("label", f"wall_{i}")
        next_label = next_run.get("label", f"wall_{i+1}")

        # Check if current run ends with corner cabinet
        base_cabs = current_run.get("base", [])
        if base_cabs:
            last_cab = base_cabs[-1]
            if last_cab.get("type", "").startswith("corner-"):
                corner = CornerReference(
                    primary_wall_id=current_label,
                    secondary_wall_id=next_label,
                    width=last_cab["width"],
                    blind_depth=last_cab.get("blindDepth", 300),
                    blind_side=last_cab.get("blindSide", "left"),
                )
                corners.append(corner)

        # Check if next run starts with corner cabinet
        next_base = next_run.get("base", [])
        if next_base:
            first_cab = next_base[0]
            if first_cab.get("type", "").startswith("corner-"):
                corner = CornerReference(
                    primary_wall_id=next_label,
                    secondary_wall_id=current_label,
                    width=first_cab["width"],
                    blind_depth=first_cab.get("blindDepth", 300),
                    blind_side=first_cab.get("blindSide", "left"),
                )
                corners.append(corner)

    return corners


def build_layout(config: dict) -> Layout:
    """Full pipeline: config → positioned cabinets.

    Steps:
    1. Convert config to walls
    2. Convert config to cabinets
    3. Calculate world positions for each cabinet
    4. Detect corner cabinets
    """
    settings = config.get("settings", {})

    # Step 1: Create walls
    room = config_to_walls(config)

    # Step 2: Create cabinets with wall references
    wall_cabinets = config_to_cabinets(config)

    # Step 3: Calculate world positions
    positioned = []
    for wc in wall_cabinets:
        wall = room.get_wall(wc.wall_id)
        if wall is None:
            continue

        # Get position along wall
        wall_point = wall.point_at_offset(wc.offset)

        # Add depth (into room)
        normal = wall.normal
        world_x = wall_point.x + wc.depth * normal.x
        world_y = wall_point.y + wc.depth * normal.y

        # Calculate rotation from wall direction
        direction = wall.direction
        rotation = math.atan2(direction.y, direction.x)

        # Determine Z based on level
        # (simplified - would need more logic for upper/tall)
        world_z = 0.0

        cab = PositionedCabinet(
            wall_id=wc.wall_id,
            offset=wc.offset,
            width=wc.width,
            depth=wc.depth,
            height=wc.height,
            level="base",  # simplified
            cabinet_type="base-door",
            world_x=world_x,
            world_y=world_y,
            world_z=world_z,
            rotation=rotation,
        )
        positioned.append(cab)

    # Step 4: Detect corners
    corners = config_to_corners(config)

    return Layout(room=room, cabinets=positioned, corners=corners)
