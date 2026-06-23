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

from typing import List
from dataclasses import dataclass

from .kitchen.wall import Wall, Room, CornerReference
from .core.geometry import Vector2D
from .core.types import CabinetType, Direction, Dimensions
from .kitchen.cabinet import Cabinet, Countertop
from .kitchen.layout import Run, Layout, LayoutEngine


@dataclass(frozen=True)
class WallCabinet:
    """A cabinet positioned relative to a wall.

    Adapter concern — used by config_to_cabinets() to bridge
    raw config to wall-based positioning. Not a domain entity.
    The domain model uses Cabinet + CabinetPlacement instead.
    """
    wall_id: str
    offset: float
    width: float
    depth: float
    height: float

    def world_position(self, wall: Wall) -> Vector2D:
        """Get world position of cabinet back-left corner (at wall face)."""
        return wall.point_at_offset(self.offset)

    def front_position(self, wall: Wall) -> Vector2D:
        """Get world position of cabinet front-left corner (into room)."""
        return wall.point_at_depth(self.offset, self.depth)

    def center_position(self, wall: Wall) -> Vector2D:
        """Get world position of cabinet center."""
        return wall.point_at_depth(
            self.offset + self.width / 2,
            self.depth / 2,
        )


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


# ── Domain Conversion ────────────────────────────────────────────────
# Converts raw config dict → domain objects (Cabinet, Run, Layout)
# This is the adapter between Configuration context and Kitchen Design context.

# Map config string types to domain CabinetType enum
_CABINET_TYPE_MAP = {v.value: v for v in CabinetType}


def _config_to_cabinet(cab_dict: dict, wall_id: str, offset: float,
                       settings: dict) -> Cabinet:
    """Convert a single raw cabinet dict to a domain Cabinet object."""
    cab_type_str = cab_dict["type"]
    cab_type = _CABINET_TYPE_MAP.get(cab_type_str)
    if cab_type is None:
        raise ValueError(f"Unknown cabinet type: '{cab_type_str}'")

    # Resolve dimensions from settings based on level
    level = cab_type.level
    if level.value == "base":
        depth = settings.get("baseDepth", 560)
        height = settings.get("baseBodyHeight", 720)
        # Plinth adds to total height for positioning, but carcass height is body only
    elif level.value == "upper":
        depth = settings.get("wallDepth", 300)
        height = settings.get("wallHeight", 720)
    else:  # tall
        depth = settings.get("tallDepth", 560)
        height = settings.get("tallHeight", 2000)

    depth += cab_dict.get("depthOffset", 0)
    height += cab_dict.get("heightOffset", 0)

    dimensions = Dimensions(
        width=cab_dict["width"],
        depth=depth,
        height=height,
    )

    # Generate cabinet ID
    cab_id = f"{wall_id}_{level.value}_{cab_type_str}"

    return Cabinet(
        id=cab_id,
        cabinet_type=cab_type,
        wall_id=wall_id,
        offset=offset,
        dimensions=dimensions,
        drawer_count=cab_dict.get("drawers"),
        drawer_heights=cab_dict.get("drawerHeights"),
        blind_depth=cab_dict.get("blindDepth"),
        blind_side=cab_dict.get("blindSide"),
    )


def _config_to_direction(dir_str: str) -> Direction:
    """Convert direction string to domain Direction enum."""
    return {
        "east": Direction.EAST,
        "north": Direction.NORTH,
        "west": Direction.WEST,
        "south": Direction.SOUTH,
    }[dir_str]


def build_domain_layout(config: dict) -> Layout:
    """Convert raw config to domain Layout via LayoutEngine.

    This is the adapter between Configuration context and Kitchen Design context.
    It produces a proper domain Layout with:
    - Room (walls)
    - Runs (with typed Cabinet objects)
    - CornerReferences
    - CabinetPlacements (world positions computed by LayoutEngine)

    The returned Layout is independent of config format — it uses
    domain types only (Cabinet, Run, Direction, etc.).
    """
    settings = config.get("settings", {})
    runs_config = config.get("runs", [])

    # Create Room (walls)
    room = config_to_walls(config)

    # Detect corners
    corners = config_to_corners(config)

    # Build domain Runs with Cabinet objects
    cabinet_gap = settings.get("cabinetGap", 0)
    domain_runs: List[Run] = []

    for run_dict in runs_config:
        label = run_dict.get("label", "unnamed")
        direction_str = run_dict.get("direction", "east")

        # Resolve direction from turn if not explicitly set
        turn = run_dict.get("turn")
        if turn and domain_runs:
            prev_dir = domain_runs[-1].direction
            direction = prev_dir.turn(turn)
        else:
            direction = _config_to_direction(direction_str)

        # Build Cabinet objects for each section
        cabinets: List[Cabinet] = []

        for section in ("base", "upper", "tall"):
            offset = 0.0
            for cab_dict in run_dict.get(section, []):
                cab = _config_to_cabinet(cab_dict, label, offset, settings)
                cabinets.append(cab)
                offset += cab.width + cabinet_gap

        # Build Countertop if base cabinets exist
        countertop = None
        base_cabs = run_dict.get("base", [])
        if base_cabs:
            total_width = sum(c["width"] for c in base_cabs) + cabinet_gap * (len(base_cabs) - 1)
            ct_override = run_dict.get("countertop", {})
            countertop = Countertop(
                wall_id=label,
                start_offset=0.0,
                end_offset=total_width,
                thickness=ct_override.get("thickness",
                                          settings.get("counterThickness", 30)),
                overhang_front=ct_override.get("overhangFront",
                                              settings.get("counterOverhangFront", 20)),
                overhang_end=ct_override.get("overhangEnd",
                                            settings.get("counterOverhangEnd", 30)),
            )

        domain_runs.append(Run(
            label=label,
            direction=direction,
            cabinets=cabinets,
            countertop=countertop,
        ))

    # Run LayoutEngine to compute world positions
    engine = LayoutEngine(
        cabinet_gap=cabinet_gap,
        front_gap=settings.get("frontGap", 2),
    )

    return engine.calculate_layout(
        runs=domain_runs,
        base_depth=settings.get("baseDepth", 560),
        wall_depth=settings.get("wallDepth", 300),
        base_height=settings.get("baseBodyHeight", 720),
        wall_height=settings.get("wallHeight", 720),
        plinth_height=settings.get("plinthHeight", 120),
        wall_mount_height=settings.get("wallMountHeight", 1400),
    )
