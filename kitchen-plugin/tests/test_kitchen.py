"""Kitchen Module Tests.

Tests for Wall, Cabinet, Layout, and Standards.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import math
from src.core.geometry import Vector2D, Vector3D
from src.core.types import Direction, CabinetType, Dimensions

from src.kitchen.wall import Wall, Room, CornerReference
from src.kitchen.cabinet import Cabinet, CabinetPlacement
from src.kitchen.layout import Run, LayoutEngine
from src.kitchen.standards import KitchenStandards, EUROPEAN_STANDARDS


# ─── Wall Tests ──────────────────────────────────────────────────────────────

class TestWall:
    """Test wall model."""

    def test_wall_creation(self):
        """Create a wall."""
        wall = Wall(
            id="back",
            start=Vector2D(0, 0),
            end=Vector2D(3000, 0),
        )
        assert wall.id == "back"
        assert wall.length == pytest.approx(3000.0)

    def test_wall_direction_east(self):
        """Wall going east."""
        wall = Wall("back", Vector2D(0, 0), Vector2D(3000, 0))
        d = wall.direction
        assert d.x == pytest.approx(1.0)
        assert d.y == pytest.approx(0.0)

    def test_wall_direction_north(self):
        """Wall going north."""
        wall = Wall("left", Vector2D(0, 0), Vector2D(0, 2000))
        d = wall.direction
        assert d.x == pytest.approx(0.0)
        assert d.y == pytest.approx(1.0)

    def test_wall_normal_east(self):
        """Wall going east has normal pointing north."""
        wall = Wall("back", Vector2D(0, 0), Vector2D(3000, 0))
        n = wall.normal
        assert n.x == pytest.approx(0.0)
        assert n.y == pytest.approx(1.0)

    def test_wall_point_at_offset(self):
        """Get point at offset along wall."""
        wall = Wall("back", Vector2D(100, 0), Vector2D(3100, 0))
        p = wall.point_at_offset(500)
        assert p.x == pytest.approx(600.0)
        assert p.y == pytest.approx(0.0)

    def test_wall_point_at_depth(self):
        """Get point at offset and depth into room."""
        wall = Wall("back", Vector2D(0, 0), Vector2D(3000, 0))
        p = wall.point_at_depth(500, 560)
        assert p.x == pytest.approx(500.0)
        assert p.y == pytest.approx(560.0)

    def test_wall_transform(self):
        """Wall transform converts local to world."""
        wall = Wall("back", Vector2D(100, 50), Vector2D(3100, 50))
        t = wall.transform
        # Local (0,0) = wall start
        p = t.apply_to_point(Vector2D(0, 0))
        assert p.x == pytest.approx(100.0)
        assert p.y == pytest.approx(50.0)


# ─── Room Tests ──────────────────────────────────────────────────────────────

class TestRoom:
    """Test room model."""

    def test_room_creation(self):
        """Create a room with walls."""
        room = Room(walls=[
            Wall("back", Vector2D(0, 0), Vector2D(3000, 0)),
            Wall("left", Vector2D(0, 0), Vector2D(0, 2400)),
        ])
        assert len(room.walls) == 2

    def test_room_get_wall(self):
        """Get wall by ID."""
        room = Room(walls=[
            Wall("back", Vector2D(0, 0), Vector2D(3000, 0)),
            Wall("left", Vector2D(0, 0), Vector2D(0, 2400)),
        ])
        wall = room.get_wall("back")
        assert wall.id == "back"

    def test_room_corners(self):
        """Detect corners where walls meet."""
        room = Room(walls=[
            Wall("back", Vector2D(0, 0), Vector2D(3000, 0)),
            Wall("right", Vector2D(3000, 0), Vector2D(3000, 2400)),
        ])
        corners = room.corners
        assert len(corners) == 1
        point, wall_a, wall_b = corners[0]
        assert point.x == pytest.approx(3000.0)
        assert point.y == pytest.approx(0.0)


# ─── Cabinet Tests ───────────────────────────────────────────────────────────

class TestCabinet:
    """Test cabinet model."""

    def test_cabinet_creation(self):
        """Create a cabinet."""
        cab = Cabinet(
            id="cab_001",
            cabinet_type=CabinetType.BASE_DOOR,
            wall_id="back",
            offset=0,
            dimensions=Dimensions(600, 560, 720),
        )
        assert cab.width == 600
        assert cab.depth == 560
        assert cab.height == 720

    def test_cabinet_level(self):
        """Cabinet level from type."""
        base = Cabinet("b", CabinetType.BASE_DOOR, "w", 0, Dimensions(600, 560, 720))
        upper = Cabinet("u", CabinetType.WALL_DOOR, "w", 0, Dimensions(600, 300, 720))
        assert base.level.value == "base"
        assert upper.level.value == "upper"

    def test_cabinet_is_corner(self):
        """Corner cabinet detection."""
        corner = Cabinet("c", CabinetType.CORNER_BLIND, "w", 0, Dimensions(900, 560, 720))
        regular = Cabinet("r", CabinetType.BASE_DOOR, "w", 0, Dimensions(600, 560, 720))
        assert corner.is_corner is True
        assert regular.is_corner is False

    def test_cabinet_bounding_box(self):
        """Cabinet bounding box in local coordinates."""
        cab = Cabinet("c", CabinetType.BASE_DOOR, "w", 0, Dimensions(600, 560, 720))
        bb = cab.bounding_box_local()
        assert bb.width == pytest.approx(600.0)
        assert bb.depth == pytest.approx(560.0)
        assert bb.height == pytest.approx(720.0)


# ─── Layout Engine Tests ─────────────────────────────────────────────────────

class TestLayoutEngine:
    """Test layout engine."""

    def test_single_run_layout(self):
        """Single run creates one wall with cabinets."""
        engine = LayoutEngine()
        runs = [
            Run(
                label="back",
                direction=Direction.EAST,
                cabinets=[
                    Cabinet("c1", CabinetType.BASE_DOOR, "back", 0, Dimensions(600, 560, 720)),
                    Cabinet("c2", CabinetType.BASE_DOOR, "back", 600, Dimensions(600, 560, 720)),
                ],
            ),
        ]

        layout = engine.calculate_layout(runs)
        assert len(layout.room.walls) == 1
        assert len(layout.placed_cabinets) == 2

    def test_cabinet_positions(self):
        """Cabinets get correct world positions."""
        engine = LayoutEngine()
        runs = [
            Run(
                label="back",
                direction=Direction.EAST,
                cabinets=[
                    Cabinet("c1", CabinetType.BASE_DOOR, "back", 0, Dimensions(600, 560, 720)),
                    Cabinet("c2", CabinetType.BASE_DOOR, "back", 600, Dimensions(600, 560, 720)),
                ],
            ),
        ]

        layout = engine.calculate_layout(runs)
        c1 = layout.placed_cabinets[0]
        c2 = layout.placed_cabinets[1]

        assert c1.world_position.x == pytest.approx(0.0)
        assert c2.world_position.x == pytest.approx(600.0)

    def test_two_run_layout(self):
        """Two runs create two walls."""
        engine = LayoutEngine()
        runs = [
            Run("back", Direction.EAST, [
                Cabinet("c1", CabinetType.BASE_DOOR, "back", 0, Dimensions(600, 560, 720)),
            ]),
            Run("left", Direction.NORTH, [
                Cabinet("c2", CabinetType.BASE_DOOR, "left", 0, Dimensions(600, 560, 720)),
            ]),
        ]

        layout = engine.calculate_layout(runs)
        assert len(layout.room.walls) == 2

    def test_corner_detection(self):
        """Corner cabinet creates corner reference."""
        engine = LayoutEngine()
        runs = [
            Run("back", Direction.EAST, [
                Cabinet("c1", CabinetType.BASE_DOOR, "back", 0, Dimensions(600, 560, 720)),
                Cabinet("corner", CabinetType.CORNER_BLIND, "back", 600,
                        Dimensions(900, 560, 720), blind_depth=400, blind_side="right"),
            ]),
            Run("left", Direction.NORTH, [
                Cabinet("c2", CabinetType.BASE_DOOR, "left", 0, Dimensions(600, 560, 720)),
            ]),
        ]

        layout = engine.calculate_layout(runs)
        assert len(layout.corners) == 1
        assert layout.corners[0].blind_depth == 400


# ─── Standards Tests ─────────────────────────────────────────────────────────

class TestStandards:
    """Test European kitchen standards."""

    def test_default_standards(self):
        """Default European standards."""
        s = EUROPEAN_STANDARDS
        assert s.base_body_height == 720.0
        assert s.base_depth == 560.0
        assert s.wall_depth == 300.0

    def test_standard_width_check(self):
        """Check if width is standard."""
        s = EUROPEAN_STANDARDS
        assert s.is_standard_width(600) is True
        assert s.is_standard_width(650) is False

    def test_base_total_height(self):
        """Base total height = plinth + body."""
        s = EUROPEAN_STANDARDS
        assert s.base_total_height == pytest.approx(840.0)

    def test_get_dimensions(self):
        """Get standard dimensions by level."""
        s = EUROPEAN_STANDARDS
        base = s.get_dimensions("base")
        assert base.depth == pytest.approx(560.0)
        assert base.height == pytest.approx(720.0)
