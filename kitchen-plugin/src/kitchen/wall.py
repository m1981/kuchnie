"""Kitchen Wall — Wall model using core geometry types.

A wall is defined by:
- Start and end points (2D, plan view)
- Normal vector pointing into the room
- Length and direction

This module depends only on src/core/.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..core.geometry import Vector2D, Transform2D


@dataclass(frozen=True)
class Wall:
    """Immutable wall definition.

    Coordinate system (wall-local):
    - X axis: along wall (from start to end)
    - Y axis: into room (wall normal)
    - Origin: wall start point

    The wall defines a local coordinate system for cabinet placement.
    """
    id: str
    start: Vector2D
    end: Vector2D

    @property
    def direction(self) -> Vector2D:
        """Normalized direction vector from start to end."""
        return (self.end - self.start).normalized()

    @property
    def normal(self) -> Vector2D:
        """Normal vector pointing into room (left of direction).

        If wall goes east (+X), normal points north (+Y).
        """
        return self.direction.perpendicular()

    @property
    def length(self) -> float:
        """Wall length in mm."""
        return (self.end - self.start).length()

    @property
    def angle_rad(self) -> float:
        """Wall angle in radians (CCW from east)."""
        import math
        d = self.direction
        return math.atan2(d.y, d.x)

    @property
    def transform(self) -> Transform2D:
        """Transform from wall-local to world coordinates.

        Wall-local:
        - (0, 0) = wall start
        - (length, 0) = wall end
        - (x, y) = x along wall, y into room
        """
        return Transform2D.from_position_and_direction(
            self.start.x, self.start.y,
            self.direction.x, self.direction.y,
        )

    def point_at_offset(self, offset: float) -> Vector2D:
        """Get world point at offset along wall.

        Args:
            offset: Distance from wall start along wall direction.

        Returns:
            World coordinates of point.
        """
        wall_point = Vector2D(offset, 0)
        return self.transform.apply_to_point(wall_point)

    def point_at_depth(self, offset: float, depth: float) -> Vector2D:
        """Get world point at offset along wall and depth into room.

        Args:
            offset: Distance from wall start along wall direction.
            depth: Distance from wall face into room.

        Returns:
            World coordinates of point.
        """
        wall_point = Vector2D(offset, depth)
        return self.transform.apply_to_point(wall_point)


@dataclass(frozen=True)
class CornerReference:
    """Reference between two walls at a corner.

    A corner connects a primary wall to a secondary wall.
    The blind_depth reduces available space on the secondary wall.
    """
    primary_wall_id: str
    secondary_wall_id: str
    blind_depth: float  # mm
    blind_side: str     # "left" or "right"
    width: float = 0.0  # mm — total cabinet width (including blind section)

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


@dataclass
class Room:
    """Collection of walls forming a room.

    Walls should be ordered consistently (e.g., counterclockwise)
    so normals point into the room.
    """
    walls: List[Wall]

    def get_wall(self, wall_id: str) -> Optional[Wall]:
        """Get wall by ID."""
        for wall in self.walls:
            if wall.id == wall_id:
                return wall
        return None

    @property
    def corners(self) -> List[Tuple[Vector2D, str, str]]:
        """Find corner points where walls meet.

        Returns list of (point, wall_a_id, wall_b_id).
        """
        corners = []
        for i, wall_a in enumerate(self.walls):
            for j, wall_b in enumerate(self.walls):
                if i >= j:
                    continue
                # Check if wall_a's end matches wall_b's start
                dist = (wall_a.end - wall_b.start).length()
                if dist < 0.1:  # Within tolerance
                    corners.append((wall_a.end, wall_a.id, wall_b.id))
                # Check if wall_b's end matches wall_a's start
                dist = (wall_b.end - wall_a.start).length()
                if dist < 0.1:
                    corners.append((wall_a.start, wall_a.id, wall_b.id))
        return corners
