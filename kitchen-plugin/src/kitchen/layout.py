"""Kitchen Layout — Layout engine for cabinet placement.

Handles:
- Run-based layout (sequence of cabinets along a wall)
- Corner detection and reference
- Position calculation (wall-local → world)

This module depends on src/core/ and src/kitchen/.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict

from ..core.geometry import Vector2D, Vector3D, Transform2D
from ..core.types import Direction, CabinetType, Dimensions

from .wall import Wall, Room, CornerReference
from .cabinet import Cabinet, CabinetPlacement, Countertop


@dataclass
class Run:
    """A run of cabinets along a single wall.

    A run is defined by:
    - label: wall identifier
    - direction: travel direction (east, north, west, south)
    - cabinets: ordered list of cabinets
    - countertop: optional countertop definition
    """
    label: str
    direction: Direction
    cabinets: List[Cabinet]
    countertop: Optional[Countertop] = None

    @property
    def total_width(self) -> float:
        """Total width of all cabinets in run (mm)."""
        return sum(c.width for c in self.cabinets)


@dataclass
class Layout:
    """Complete kitchen layout.

    Contains:
    - Room definition (walls)
    - Runs (cabinet sequences)
    - Corner references
    - Placed cabinets (with world positions)
    """
    room: Room
    runs: List[Run]
    corners: List[CornerReference]
    placed_cabinets: List[CabinetPlacement]

    def get_placed_cabinets_for_wall(self, wall_id: str) -> List[CabinetPlacement]:
        """Get all cabinets placed on a specific wall."""
        return [p for p in self.placed_cabinets if p.cabinet.wall_id == wall_id]


class LayoutEngine:
    """Engine for calculating cabinet positions.

    Converts a sequence of runs with cabinets into world positions.
    """

    def __init__(self, cabinet_gap: float = 0.0, front_gap: float = 2.0):
        """Initialize layout engine.

        Args:
            cabinet_gap: Gap between carcass boxes (mm)
            front_gap: Gap between door/drawer fronts (mm)
        """
        self.cabinet_gap = cabinet_gap
        self.front_gap = front_gap

    def calculate_layout(
        self,
        runs: List[Run],
        base_depth: float = 560.0,
        wall_depth: float = 300.0,
        base_height: float = 720.0,
        wall_height: float = 720.0,
        plinth_height: float = 120.0,
        wall_mount_height: float = 1400.0,
    ) -> Layout:
        """Calculate complete layout from runs.

        Args:
            runs: List of cabinet runs
            base_depth: Base cabinet depth (mm)
            wall_depth: Wall cabinet depth (mm)
            base_height: Base cabinet body height (mm)
            wall_height: Wall cabinet height (mm)
            plinth_height: Plinth height (mm)
            wall_mount_height: Height for wall cabinet mounting (mm)

        Returns:
            Complete layout with walls, corners, and placed cabinets.
        """
        # Step 1: Create walls from runs
        walls = self._create_walls(runs)

        # Step 2: Create room
        room = Room(walls=walls)

        # Step 3: Detect corners
        corners = self._detect_corners(runs, room)

        # Step 4: Calculate cabinet positions
        placed = self._place_cabinets(
            runs, room,
            base_depth, wall_depth,
            base_height, wall_height,
            plinth_height, wall_mount_height,
        )

        return Layout(
            room=room,
            runs=runs,
            corners=corners,
            placed_cabinets=placed,
        )

    def _create_walls(self, runs: List[Run]) -> List[Wall]:
        """Create wall objects from runs.

        Each run's direction determines the wall orientation.
        First run starts at origin, subsequent runs start where previous ended.
        """
        walls = []
        current_x, current_y = 0.0, 0.0

        for run in runs:
            direction = run.direction
            dx, dy = direction.dx, direction.dy
            wall_length = run.total_width

            start = Vector2D(current_x, current_y)
            end = Vector2D(
                current_x + wall_length * dx,
                current_y + wall_length * dy,
            )

            wall = Wall(id=run.label, start=start, end=end)
            walls.append(wall)

            # Move to end of wall for next run
            current_x = end.x
            current_y = end.y

        return walls

    def _detect_corners(self, runs: List[Run], room: Room) -> List[CornerReference]:
        """Detect corner cabinets and create references."""
        corners = []

        for i in range(len(runs) - 1):
            current_run = runs[i]
            next_run = runs[i + 1]

            # Check if current run ends with corner cabinet
            if current_run.cabinets:
                last_cab = current_run.cabinets[-1]
                if last_cab.is_corner:
                    corner = CornerReference(
                        primary_wall_id=current_run.label,
                        secondary_wall_id=next_run.label,
                        blind_depth=last_cab.blind_depth or 300.0,
                        blind_side=last_cab.blind_side or "left",
                    )
                    corners.append(corner)

        return corners

    def _place_cabinets(
        self,
        runs: List[Run],
        room: Room,
        base_depth: float,
        wall_depth: float,
        base_height: float,
        wall_height: float,
        plinth_height: float,
        wall_mount_height: float,
    ) -> List[CabinetPlacement]:
        """Calculate world positions for all cabinets."""
        placed = []

        for run in runs:
            wall = room.get_wall(run.label)
            if wall is None:
                continue

            offset = 0.0
            for cab in run.cabinets:
                # Calculate position along wall
                wall_point = wall.point_at_offset(offset)

                # Add depth based on cabinet level
                if cab.level.value == "base":
                    depth = base_depth
                    z = plinth_height
                elif cab.level.value == "upper":
                    depth = wall_depth
                    z = wall_mount_height
                else:  # tall
                    depth = base_depth
                    z = 0.0

                # World position (back-left-bottom, at wall face)
                world_x = wall_point.x
                world_y = wall_point.y
                world_z = z

                # Rotation from wall direction
                rotation = wall.angle_rad

                placement = CabinetPlacement(
                    cabinet=cab,
                    world_position=Vector3D(world_x, world_y, world_z),
                    rotation_rad=rotation,
                )
                placed.append(placement)

                offset += cab.width + self.cabinet_gap

        return placed
