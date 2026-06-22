"""Wall-Centric Positioning Model Tests.

Industry standard: cabinets are positioned relative to walls, not absolute coordinates.

Key concepts:
- Wall: defined by start/end points, has a normal pointing into room
- Run: sequence of cabinets along a wall
- Cabinet: positioned by (wall_id, offset_along_wall)
- Corner: references two walls (primary + secondary)

Origin convention: back-left-bottom (at wall face)
- Width: along wall (+X in wall-local space)
- Depth: into room (+Y in wall-local space)
- Height: up (+Z)

This is a refactor from our current front-left-bottom origin.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from math import pi


# ─── Wall Model Tests ─────────────────────────────────────────────────────────

class TestWallModel:
    """Test the Wall data structure."""

    def test_wall_has_id(self):
        """Wall must have an identifier."""
        from src.wall_model import Wall
        wall = Wall(id="back_wall", start=(0, 0), end=(3000, 0))
        assert wall.id == "back_wall"

    def test_wall_has_start_and_end(self):
        """Wall is defined by start and end points."""
        from src.wall_model import Wall
        wall = Wall(id="back_wall", start=(0, 0), end=(3000, 0))
        assert wall.start == (0, 0)
        assert wall.end == (3000, 0)

    def test_wall_length(self):
        """Wall length = distance from start to end."""
        from src.wall_model import Wall
        wall = Wall(id="back_wall", start=(0, 0), end=(3000, 0))
        assert wall.length == 3000

    def test_wall_direction(self):
        """Wall direction = normalized vector from start to end."""
        from src.wall_model import Wall
        wall = Wall(id="back_wall", start=(0, 0), end=(3000, 0))
        assert wall.direction == (1, 0)

    def test_wall_direction_diagonal(self):
        """Wall direction works for diagonal walls."""
        from src.wall_model import Wall
        wall = Wall(id="diag", start=(0, 0), end=(3000, 4000))
        dx, dy = wall.direction
        assert abs(dx - 0.6) < 1e-6  # 3000/5000
        assert abs(dy - 0.8) < 1e-6  # 4000/5000

    def test_wall_normal_points_into_room(self):
        """Wall normal points into the room (left of direction)."""
        from src.wall_model import Wall
        # Wall going east (+X), normal should point north (+Y)
        wall = Wall(id="back_wall", start=(0, 0), end=(3000, 0))
        nx, ny = wall.normal
        assert abs(nx) < 1e-6
        assert abs(ny - 1.0) < 1e-6

    def test_wall_normal_for_south_wall(self):
        """South wall going east, normal points into room (north)."""
        from src.wall_model import Wall
        # For a south wall, direction should be east (+X) so normal points north (+Y)
        # Wall ordering: counterclockwise around room
        wall = Wall(id="south_wall", start=(0, 0), end=(3000, 0))
        nx, ny = wall.normal
        assert abs(nx) < 1e-6
        assert abs(ny - 1.0) < 1e-6  # Normal points north


# ─── Room Model Tests ─────────────────────────────────────────────────────────

class TestRoomModel:
    """Test the Room data structure."""

    def test_room_has_walls(self):
        """Room is defined by a list of walls."""
        from src.wall_model import Room, Wall
        room = Room(walls=[
            Wall(id="back", start=(0, 0), end=(3000, 0)),
            Wall(id="left", start=(0, 0), end=(0, 2400)),
        ])
        assert len(room.walls) == 2

    def test_room_wall_by_id(self):
        """Can look up wall by ID."""
        from src.wall_model import Room, Wall
        room = Room(walls=[
            Wall(id="back", start=(0, 0), end=(3000, 0)),
            Wall(id="left", start=(0, 0), end=(0, 2400)),
        ])
        wall = room.get_wall("back")
        assert wall.id == "back"

    def test_room_wall_corners(self):
        """Room can compute corner points where walls meet."""
        from src.wall_model import Room, Wall
        room = Room(walls=[
            Wall(id="back", start=(0, 0), end=(3000, 0)),
            Wall(id="right", start=(3000, 0), end=(3000, 2400)),
        ])
        corners = room.corners
        assert len(corners) == 1
        assert corners[0] == (3000, 0)


# ─── Wall-Relative Cabinet Tests ──────────────────────────────────────────────

class TestWallRelativeCabinet:
    """Test cabinet positioning relative to wall."""

    def test_cabinet_has_wall_reference(self):
        """Cabinet must reference a wall."""
        from src.wall_model import WallCabinet
        cab = WallCabinet(
            wall_id="back_wall",
            offset=0,
            width=600,
            depth=560,
            height=720,
        )
        assert cab.wall_id == "back_wall"

    def test_cabinet_has_offset_along_wall(self):
        """Cabinet position = offset from wall start."""
        from src.wall_model import WallCabinet
        cab = WallCabinet(
            wall_id="back_wall",
            offset=600,
            width=600,
            depth=560,
            height=720,
        )
        assert cab.offset == 600

    def test_cabinet_to_world_coords(self):
        """Cabinet can convert local position to world coordinates."""
        from src.wall_model import Wall, WallCabinet

        wall = Wall(id="back", start=(0, 0), end=(3000, 0))
        cab = WallCabinet(
            wall_id="back",
            offset=600,
            width=600,
            depth=560,
            height=720,
        )

        # World position: wall.start + offset * wall.direction
        world = cab.world_position(wall)
        assert abs(world[0] - 600) < 1e-6  # X = 600
        assert abs(world[1]) < 1e-6         # Y = 0 (at wall)

    def test_cabinet_world_depth(self):
        """Cabinet depth extends into room (along wall normal)."""
        from src.wall_model import Wall, WallCabinet

        wall = Wall(id="back", start=(0, 0), end=(3000, 0))
        cab = WallCabinet(
            wall_id="back",
            offset=0,
            width=600,
            depth=560,
            height=720,
        )

        # Front of cabinet = wall.start + depth * wall.normal
        front = cab.front_position(wall)
        assert abs(front[0]) < 1e-6      # X = 0
        assert abs(front[1] - 560) < 1e-6  # Y = 560 (into room)


# ─── Back-Face Origin Tests ───────────────────────────────────────────────────

class TestBackFaceOrigin:
    """Test that cabinet origin is at back-left-bottom (wall face)."""

    def test_box_origin_at_wall_face(self):
        """Box origin should be at back-left-bottom (Y=0 is wall face)."""
        from src.wall_model import create_box_vertices

        verts = create_box_vertices(width=600, depth=560, height=720)

        # Back face at Y=0 (wall face)
        back_verts = [v for v in verts if abs(v[1]) < 1e-6]
        assert len(back_verts) == 4  # 4 vertices at Y=0

        # Front face at Y=depth (into room)
        front_verts = [v for v in verts if abs(v[1] - 560) < 1e-6]
        assert len(front_verts) == 4

    def test_box_width_along_x(self):
        """Width extends along +X."""
        from src.wall_model import create_box_vertices

        verts = create_box_vertices(width=600, depth=560, height=720)
        min_x = min(v[0] for v in verts)
        max_x = max(v[0] for v in verts)

        assert abs(min_x) < 1e-6
        assert abs(max_x - 600) < 1e-6

    def test_box_height_along_z(self):
        """Height extends along +Z."""
        from src.wall_model import create_box_vertices

        verts = create_box_vertices(width=600, depth=560, height=720)
        min_z = min(v[2] for v in verts)
        max_z = max(v[2] for v in verts)

        assert abs(min_z) < 1e-6
        assert abs(max_z - 720) < 1e-6


# ─── Corner Reference Tests ──────────────────────────────────────────────────

class TestCornerWallReferences:
    """Test that corner cabinets reference two walls."""

    def test_corner_has_primary_wall(self):
        """Corner cabinet must have a primary wall."""
        from src.wall_model import CornerCabinet
        corner = CornerCabinet(
            primary_wall="back",
            secondary_wall="left",
            width=900,
            blind_depth=400,
            blind_side="right",
        )
        assert corner.primary_wall == "back"

    def test_corner_has_secondary_wall(self):
        """Corner cabinet must have a secondary wall."""
        from src.wall_model import CornerCabinet
        corner = CornerCabinet(
            primary_wall="back",
            secondary_wall="left",
            width=900,
            blind_depth=400,
            blind_side="right",
        )
        assert corner.secondary_wall == "left"

    def test_corner_blind_depth(self):
        """Corner cabinet has blind depth."""
        from src.wall_model import CornerCabinet
        corner = CornerCabinet(
            primary_wall="back",
            secondary_wall="left",
            width=900,
            blind_depth=400,
            blind_side="right",
        )
        assert corner.blind_depth == 400

    def test_corner_reduces_secondary_wall_space(self):
        """Corner blind depth reduces available space on secondary wall."""
        from src.wall_model import CornerCabinet
        corner = CornerCabinet(
            primary_wall="back",
            secondary_wall="left",
            width=900,
            blind_depth=400,
            blind_side="right",
        )
        # Available space on secondary wall = wall_length - blind_depth
        assert corner.space_consumed_on_secondary == 400
