# ATTIC TOMBSTONE — dormant kuchnie_core.types enums (2026-07-17, wk-0eb2781f)
# Moved from kuchnie-core/src/kuchnie_core/types.py: Direction,
# CabinetLevel, CabinetType, HandleType, DoorSide.
# WHY: a parallel English cabinet vocabulary (base-door family) disjoint
# from the living Polish TYPE_REGISTRY keys (dolna_drzwiowa family) that
# CabinetInstance.type and the decomposers consume — tr-3a97dc10; zero
# consumers outside types.py across all components (arch-smells corpus
# scan). Dimensions stayed in types.py (consumed by standards.py).
# If run-continuity or a future planner needs Direction, restore it
# with a superseding decision and real consumers.

from enum import Enum

class Direction(Enum):
    """Cardinal directions for wall orientation.

    Convention: right-hand rule, Z-up.
    - East: +X
    - North: +Y
    - West: -X
    - South: -Y
    """
    EAST = "east"
    NORTH = "north"
    WEST = "west"
    SOUTH = "south"

    @property
    def dx(self) -> float:
        """X component of direction vector."""
        return {
            Direction.EAST: 1.0,
            Direction.NORTH: 0.0,
            Direction.WEST: -1.0,
            Direction.SOUTH: 0.0,
        }[self]

    @property
    def dy(self) -> float:
        """Y component of direction vector."""
        return {
            Direction.EAST: 0.0,
            Direction.NORTH: 1.0,
            Direction.WEST: 0.0,
            Direction.SOUTH: -1.0,
        }[self]

    @property
    def angle_rad(self) -> float:
        """Angle in radians (CCW from east)."""
        import math
        return math.atan2(self.dy, self.dx)

    def turn(self, turn_direction: str) -> 'Direction':
        """Apply a turn (left/right) to get new direction.

        Args:
            turn_direction: "left" or "right"

        Returns:
            New direction after turn.
        """
        turns = {
            (Direction.EAST, "left"): Direction.NORTH,
            (Direction.EAST, "right"): Direction.SOUTH,
            (Direction.NORTH, "left"): Direction.WEST,
            (Direction.NORTH, "right"): Direction.EAST,
            (Direction.WEST, "left"): Direction.SOUTH,
            (Direction.WEST, "right"): Direction.NORTH,
            (Direction.SOUTH, "left"): Direction.EAST,
            (Direction.SOUTH, "right"): Direction.WEST,
        }
        return turns.get((self, turn_direction), self)


class CabinetLevel(Enum):
    """Cabinet height level."""
    BASE = "base"      # Floor-level (plinth + carcass)
    UPPER = "upper"    # Wall-mounted
    TALL = "tall"      # Floor-to-ceiling


class CabinetType(Enum):
    """Cabinet type enumeration."""
    # Base cabinets
    BASE_DOOR = "base-door"
    BASE_DOOR_DOUBLE = "base-door-double"
    BASE_DRAWERS = "base-drawers"
    BASE_DRAWER_DOOR = "base-drawer-door"
    BASE_SINK = "base-sink"

    # Corner cabinets
    CORNER_BLIND = "corner-blind"
    CORNER_DIAGONAL = "corner-diagonal"

    # Wall cabinets
    WALL_DOOR = "wall-door"
    WALL_DOOR_DOUBLE = "wall-door-double"
    WALL_DRAWERS = "wall-drawers"
    WALL_GLASS = "wall-glass"
    WALL_LIFT_UP = "wall-lift-up"

    # Tall cabinets
    TALL_OVEN = "tall-oven"
    TALL_FRIDGE = "tall-fridge"
    TALL_PANTRY = "tall-pantry"

    # Utility
    FILLER = "filler"

    @property
    def level(self) -> CabinetLevel:
        """Get the cabinet level for this type."""
        level_map = {
            CabinetType.BASE_DOOR: CabinetLevel.BASE,
            CabinetType.BASE_DOOR_DOUBLE: CabinetLevel.BASE,
            CabinetType.BASE_DRAWERS: CabinetLevel.BASE,
            CabinetType.BASE_DRAWER_DOOR: CabinetLevel.BASE,
            CabinetType.BASE_SINK: CabinetLevel.BASE,
            CabinetType.CORNER_BLIND: CabinetLevel.BASE,
            CabinetType.CORNER_DIAGONAL: CabinetLevel.BASE,
            CabinetType.WALL_DOOR: CabinetLevel.UPPER,
            CabinetType.WALL_DOOR_DOUBLE: CabinetLevel.UPPER,
            CabinetType.WALL_DRAWERS: CabinetLevel.UPPER,
            CabinetType.WALL_GLASS: CabinetLevel.UPPER,
            CabinetType.WALL_LIFT_UP: CabinetLevel.UPPER,
            CabinetType.TALL_OVEN: CabinetLevel.TALL,
            CabinetType.TALL_FRIDGE: CabinetLevel.TALL,
            CabinetType.TALL_PANTRY: CabinetLevel.TALL,
            CabinetType.FILLER: CabinetLevel.BASE,
        }
        return level_map.get(self, CabinetLevel.BASE)

    @property
    def is_corner(self) -> bool:
        """Check if this is a corner cabinet type."""
        return self in (CabinetType.CORNER_BLIND, CabinetType.CORNER_DIAGONAL)


class HandleType(Enum):
    """Handle type enumeration."""
    RAIL = "rail"
    GOLA = "gola"
    RECESSED = "recessed"
    KNOB = "knob"
    PUSH = "push"
    NONE = "none"


class DoorSide(Enum):
    """Door opening direction."""
    LEFT = "left"
    RIGHT = "right"
    DOUBLE = "double"


