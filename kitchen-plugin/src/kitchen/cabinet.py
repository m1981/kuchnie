"""Kitchen Cabinet — Cabinet model using core types.

A cabinet is defined by:
- Type (base-door, wall-drawers, etc.)
- Dimensions (width, depth, height)
- Position (wall_id, offset along wall)
- Properties (door side, drawer count, handle type, etc.)

This module depends only on src/core/.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from ..core.geometry import Vector2D, Vector3D, BoundingBox
from ..core.types import (
    CabinetType, CabinetLevel, HandleType, DoorSide, Dimensions
)


@dataclass(frozen=True)
class Cabinet:
    """Immutable cabinet definition.

    Position is defined relative to a wall:
    - wall_id: which wall the cabinet is on
    - offset: distance from wall start along wall direction

    Dimensions are in millimeters.
    """
    # Identity
    id: str
    cabinet_type: CabinetType
    wall_id: str

    # Position along wall
    offset: float  # mm from wall start

    # Dimensions
    dimensions: Dimensions

    # Properties
    door_side: Optional[DoorSide] = None
    drawer_count: Optional[int] = None
    drawer_heights: Optional[List[float]] = None
    shelf_count: int = 1
    handle_type: HandleType = HandleType.RAIL

    # Corner cabinet properties
    blind_depth: Optional[float] = None
    blind_side: Optional[str] = None

    # Appliance properties
    oven_height: Optional[float] = None
    fridge_height: Optional[float] = None

    @property
    def level(self) -> CabinetLevel:
        """Get cabinet level from type."""
        return self.cabinet_type.level

    @property
    def width(self) -> float:
        """Cabinet width in mm."""
        return self.dimensions.width

    @property
    def depth(self) -> float:
        """Cabinet depth in mm."""
        return self.dimensions.depth

    @property
    def height(self) -> float:
        """Cabinet height in mm."""
        return self.dimensions.height

    @property
    def is_corner(self) -> bool:
        """Check if this is a corner cabinet."""
        return self.cabinet_type.is_corner

    @property
    def is_filler(self) -> bool:
        """Check if this is a filler strip."""
        return self.cabinet_type == CabinetType.FILLER

    def bounding_box_local(self) -> BoundingBox:
        """Get bounding box in cabinet-local coordinates.

        Origin at back-left-bottom (wall face).
        """
        return BoundingBox(
            min_point=Vector3D(0, 0, 0),
            max_point=Vector3D(self.width, self.depth, self.height),
        )


@dataclass(frozen=True)
class CabinetPlacement:
    """A cabinet placed in world coordinates.

    Combines cabinet definition with calculated world position.
    """
    cabinet: Cabinet
    world_position: Vector3D  # Back-left-bottom corner (at wall face)
    rotation_rad: float       # Rotation around Z axis

    @property
    def bounding_box_world(self) -> BoundingBox:
        """Get bounding box in world coordinates.

        Simplified: assumes axis-aligned (rotation not applied to box).
        """
        return BoundingBox(
            min_point=self.world_position,
            max_point=Vector3D(
                self.world_position.x + self.cabinet.width,
                self.world_position.y + self.cabinet.depth,
                self.world_position.z + self.cabinet.height,
            ),
        )


@dataclass(frozen=True)
class Countertop:
    """Countertop spanning a run of cabinets.

    Defined by:
    - wall_id: which wall it's on
    - start_offset: offset from wall start
    - end_offset: offset from wall end
    - dimensions: thickness, depth, overhangs
    """
    wall_id: str
    start_offset: float
    end_offset: float
    thickness: float = 30.0    # mm
    overhang_front: float = 20.0  # mm
    overhang_end: float = 30.0    # mm

    @property
    def length(self) -> float:
        """Countertop length along wall."""
        return self.end_offset - self.start_offset
