"""Wall-Centric Positioning Model.

Industry standard approach for kitchen cabinet positioning:
- Cabinets are positioned relative to walls, not absolute coordinates
- Origin at back-left-bottom (wall face)
- Wall defines a local coordinate system

Key classes:
- Wall: defined by start/end points, has normal pointing into room
- Room: collection of walls with corner detection
- WallCabinet: positioned by (wall_id, offset_along_wall)
- CornerCabinet: references two walls (primary + secondary)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math


@dataclass
class Wall:
    """A wall segment defined by start and end points.

    Coordinate system:
    - Direction: from start to end (along wall)
    - Normal: perpendicular, pointing INTO room (left of direction)
    - Length: distance from start to end

    Example:
        Wall(id="back", start=(0, 0), end=(3000, 0))
        - Direction: (1, 0) (east)
        - Normal: (0, 1) (north, into room)
        - Length: 3000mm
    """
    id: str
    start: Tuple[float, float]
    end: Tuple[float, float]

    @property
    def length(self) -> float:
        """Wall length in mm."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return math.sqrt(dx * dx + dy * dy)

    @property
    def direction(self) -> Tuple[float, float]:
        """Normalized direction vector from start to end."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        length = self.length
        if length < 1e-6:
            return (1.0, 0.0)  # default east
        return (dx / length, dy / length)

    @property
    def normal(self) -> Tuple[float, float]:
        """Normal vector pointing into room (left of direction).

        If wall goes east (+X), normal points north (+Y).
        If wall goes north (+Y), normal points west (-X).
        """
        dx, dy = self.direction
        # Left perpendicular: rotate 90° CCW
        return (-dy, dx)

    def point_at_offset(self, offset: float) -> Tuple[float, float]:
        """Get world point at offset along wall."""
        dx, dy = self.direction
        return (
            self.start[0] + offset * dx,
            self.start[1] + offset * dy,
        )

    def point_at_depth(self, offset: float, depth: float) -> Tuple[float, float]:
        """Get world point at offset along wall and depth into room."""
        wall_point = self.point_at_offset(offset)
        nx, ny = self.normal
        return (
            wall_point[0] + depth * nx,
            wall_point[1] + depth * ny,
        )


@dataclass
class Room:
    """A room defined by a list of walls.

    Walls should form a closed polygon (though not required for validation).
    """
    walls: List[Wall]

    def get_wall(self, wall_id: str) -> Optional[Wall]:
        """Get wall by ID."""
        for wall in self.walls:
            if wall.id == wall_id:
                return wall
        return None

    @property
    def corners(self) -> List[Tuple[float, float]]:
        """Find corner points where walls meet.

        A corner exists where one wall's end equals another wall's start.
        """
        corners = []
        for i, wall_a in enumerate(self.walls):
            for j, wall_b in enumerate(self.walls):
                if i == j:
                    continue
                # Check if wall_a's end matches wall_b's start
                dx = abs(wall_a.end[0] - wall_b.start[0])
                dy = abs(wall_a.end[1] - wall_b.start[1])
                if dx < 1e-6 and dy < 1e-6:
                    corners.append(wall_a.end)
        return corners


@dataclass
class WallCabinet:
    """A cabinet positioned relative to a wall.

    Position is defined by:
    - wall_id: which wall the cabinet is on
    - offset: distance from wall start along wall direction
    - width, depth, height: cabinet dimensions

    Origin convention: back-left-bottom (at wall face)
    - Back face at Y=0 (wall face)
    - Front face at Y=depth (into room)
    """
    wall_id: str
    offset: float
    width: float
    depth: float
    height: float

    def world_position(self, wall: Wall) -> Tuple[float, float]:
        """Get world position of cabinet back-left corner (at wall face)."""
        return wall.point_at_offset(self.offset)

    def front_position(self, wall: Wall) -> Tuple[float, float]:
        """Get world position of cabinet front-left corner (into room)."""
        return wall.point_at_depth(self.offset, self.depth)

    def center_position(self, wall: Wall) -> Tuple[float, float]:
        """Get world position of cabinet center."""
        return wall.point_at_depth(
            self.offset + self.width / 2,
            self.depth / 2,
        )


@dataclass
class CornerCabinet:
    """A corner cabinet that spans two walls.

    Properties:
    - primary_wall: the wall where the main cabinet body sits
    - secondary_wall: the adjacent wall that the blind section extends into
    - width: total cabinet width (including blind section)
    - blind_depth: how far the blind section extends into secondary wall
    - blind_side: which side the blind section is on ("left" or "right")

    The corner cabinet reduces available space on the secondary wall
    by blind_depth.
    """
    primary_wall: str
    secondary_wall: str
    width: float
    blind_depth: float
    blind_side: str  # "left" or "right"

    @property
    def space_consumed_on_secondary(self) -> float:
        """Space consumed on secondary wall by blind section."""
        return self.blind_depth


@dataclass
class BoxVertices:
    """Vertices for a box with back-face origin (at wall face).

    Coordinate system:
    - Origin at back-left-bottom (wall face)
    - Width along +X (0 to width)
    - Depth along +Y (0=wall face to depth=into room)
    - Height along +Z (0 to height)
    """
    vertices: List[Tuple[float, float, float]]

    @property
    def back_face_y(self) -> float:
        """Y coordinate of back face (wall face)."""
        return 0.0

    @property
    def front_face_y(self) -> float:
        """Y coordinate of front face (into room)."""
        # Find max Y
        return max(v[1] for v in self.vertices)


def create_box_vertices(width: float, depth: float, height: float) -> List[Tuple[float, float, float]]:
    """Create box vertices with back-face origin (at wall face).

    Args:
        width: along +X
        depth: along +Y (0=wall face, depth=into room)
        height: along +Z

    Returns:
        List of 8 vertices for a box.

    Vertex order:
    0-3: back face (Y=0, wall face)
    4-7: front face (Y=depth, into room)
    """
    return [
        # Back face (Y=0, wall face)
        (0, 0, 0),          # 0: back-left-bottom
        (width, 0, 0),      # 1: back-right-bottom
        (width, 0, height), # 2: back-right-top
        (0, 0, height),     # 3: back-left-top
        # Front face (Y=depth, into room)
        (0, depth, 0),          # 4: front-left-bottom
        (width, depth, 0),      # 5: front-right-bottom
        (width, depth, height), # 6: front-right-top
        (0, depth, height),     # 7: front-left-top
    ]
