"""Core Geometry Tests.

Tests for pure math types: Vector2D, Vector3D, BoundingBox, Transform2D.
These tests have NO external dependencies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import math
from src.core.geometry import Vector2D, Vector3D, BoundingBox, Transform2D


# ─── Vector2D Tests ──────────────────────────────────────────────────────────

class TestVector2D:
    """Test 2D vector operations."""

    def test_create_default(self):
        """Default vector is (0, 0)."""
        v = Vector2D()
        assert v.x == 0.0
        assert v.y == 0.0

    def test_create_with_values(self):
        """Can create vector with specific values."""
        v = Vector2D(3.0, 4.0)
        assert v.x == 3.0
        assert v.y == 4.0

    def test_addition(self):
        """Vector addition."""
        a = Vector2D(1, 2)
        b = Vector2D(3, 4)
        result = a + b
        assert result.x == 4.0
        assert result.y == 6.0

    def test_subtraction(self):
        """Vector subtraction."""
        a = Vector2D(5, 7)
        b = Vector2D(2, 3)
        result = a - b
        assert result.x == 3.0
        assert result.y == 4.0

    def test_scalar_multiplication(self):
        """Scalar multiplication."""
        v = Vector2D(3, 4)
        result = v * 2
        assert result.x == 6.0
        assert result.y == 8.0

    def test_scalar_multiplication_reversed(self):
        """Scalar multiplication (reversed)."""
        v = Vector2D(3, 4)
        result = 2 * v
        assert result.x == 6.0
        assert result.y == 8.0

    def test_dot_product(self):
        """Dot product."""
        a = Vector2D(1, 0)
        b = Vector2D(0, 1)
        assert a.dot(b) == 0.0  # Perpendicular

    def test_dot_product_parallel(self):
        """Dot product of parallel vectors."""
        a = Vector2D(1, 0)
        b = Vector2D(2, 0)
        assert a.dot(b) == 2.0

    def test_length(self):
        """Vector length."""
        v = Vector2D(3, 4)
        assert v.length() == pytest.approx(5.0)

    def test_length_zero(self):
        """Zero vector length."""
        v = Vector2D(0, 0)
        assert v.length() == 0.0

    def test_normalized(self):
        """Normalized vector has length 1."""
        v = Vector2D(3, 4)
        n = v.normalized()
        assert n.length() == pytest.approx(1.0)
        assert n.x == pytest.approx(0.6)
        assert n.y == pytest.approx(0.8)

    def test_normalized_zero(self):
        """Normalizing zero vector returns zero."""
        v = Vector2D(0, 0)
        n = v.normalized()
        assert n.x == 0.0
        assert n.y == 0.0

    def test_perpendicular(self):
        """Perpendicular vector (90° CCW)."""
        v = Vector2D(1, 0)  # East
        p = v.perpendicular()
        assert p.x == pytest.approx(0.0)
        assert p.y == pytest.approx(1.0)  # North

    def test_perpendicular_north(self):
        """Perpendicular of north is west."""
        v = Vector2D(0, 1)  # North
        p = v.perpendicular()
        assert p.x == pytest.approx(-1.0)  # West
        assert p.y == pytest.approx(0.0)

    def test_to_tuple(self):
        """Convert to tuple."""
        v = Vector2D(3, 4)
        assert v.to_tuple() == (3.0, 4.0)

    def test_immutable(self):
        """Vector is immutable (frozen)."""
        v = Vector2D(1, 2)
        with pytest.raises(AttributeError):
            v.x = 5


# ─── Vector3D Tests ──────────────────────────────────────────────────────────

class TestVector3D:
    """Test 3D vector operations."""

    def test_create_default(self):
        """Default vector is (0, 0, 0)."""
        v = Vector3D()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_create_with_values(self):
        """Can create vector with specific values."""
        v = Vector3D(1, 2, 3)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_addition(self):
        """Vector addition."""
        a = Vector3D(1, 2, 3)
        b = Vector3D(4, 5, 6)
        result = a + b
        assert result.x == 5.0
        assert result.y == 7.0
        assert result.z == 9.0

    def test_length(self):
        """Vector length."""
        v = Vector3D(1, 2, 2)
        assert v.length() == pytest.approx(3.0)

    def test_normalized(self):
        """Normalized vector."""
        v = Vector3D(3, 0, 4)
        n = v.normalized()
        assert n.length() == pytest.approx(1.0)

    def test_cross_product(self):
        """Cross product of X and Y axes is Z axis."""
        x = Vector3D(1, 0, 0)
        y = Vector3D(0, 1, 0)
        z = x.cross(y)
        assert z.x == pytest.approx(0.0)
        assert z.y == pytest.approx(0.0)
        assert z.z == pytest.approx(1.0)

    def test_to_mm(self):
        """Convert meters to millimeters."""
        v = Vector3D(0.5, 1.0, 1.5)
        mm = v.to_mm()
        assert mm.x == pytest.approx(500.0)
        assert mm.y == pytest.approx(1000.0)
        assert mm.z == pytest.approx(1500.0)

    def test_to_m(self):
        """Convert millimeters to meters."""
        v = Vector3D(500, 1000, 1500)
        m = v.to_m()
        assert m.x == pytest.approx(0.5)
        assert m.y == pytest.approx(1.0)
        assert m.z == pytest.approx(1.5)


# ─── BoundingBox Tests ────────────────────────────────────────────────────────

class TestBoundingBox:
    """Test bounding box operations."""

    def test_create(self):
        """Create bounding box."""
        bb = BoundingBox(
            min_point=Vector3D(0, 0, 0),
            max_point=Vector3D(100, 200, 300),
        )
        assert bb.width == pytest.approx(100.0)
        assert bb.depth == pytest.approx(200.0)
        assert bb.height == pytest.approx(300.0)

    def test_center(self):
        """Bounding box center."""
        bb = BoundingBox(
            min_point=Vector3D(0, 0, 0),
            max_point=Vector3D(100, 200, 300),
        )
        center = bb.center
        assert center.x == pytest.approx(50.0)
        assert center.y == pytest.approx(100.0)
        assert center.z == pytest.approx(150.0)

    def test_contains_point(self):
        """Point inside bounding box."""
        bb = BoundingBox(
            min_point=Vector3D(0, 0, 0),
            max_point=Vector3D(100, 100, 100),
        )
        assert bb.contains_point(Vector3D(50, 50, 50)) is True

    def test_contains_point_outside(self):
        """Point outside bounding box."""
        bb = BoundingBox(
            min_point=Vector3D(0, 0, 0),
            max_point=Vector3D(100, 100, 100),
        )
        assert bb.contains_point(Vector3D(150, 50, 50)) is False

    def test_intersects(self):
        """Overlapping bounding boxes."""
        bb1 = BoundingBox(Vector3D(0, 0, 0), Vector3D(100, 100, 100))
        bb2 = BoundingBox(Vector3D(50, 50, 50), Vector3D(150, 150, 150))
        assert bb1.intersects(bb2) is True

    def test_no_intersection(self):
        """Non-overlapping bounding boxes."""
        bb1 = BoundingBox(Vector3D(0, 0, 0), Vector3D(100, 100, 100))
        bb2 = BoundingBox(Vector3D(200, 200, 200), Vector3D(300, 300, 300))
        assert bb1.intersects(bb2) is False


# ─── Transform2D Tests ───────────────────────────────────────────────────────

class TestTransform2D:
    """Test 2D transformations."""

    def test_identity_transform(self):
        """Identity transform doesn't change point."""
        t = Transform2D()
        p = Vector2D(3, 4)
        result = t.apply_to_point(p)
        assert result.x == pytest.approx(3.0)
        assert result.y == pytest.approx(4.0)

    def test_translation(self):
        """Translation moves point."""
        t = Transform2D.from_translation(10, 20)
        p = Vector2D(3, 4)
        result = t.apply_to_point(p)
        assert result.x == pytest.approx(13.0)
        assert result.y == pytest.approx(24.0)

    def test_rotation_90(self):
        """90° CCW rotation."""
        t = Transform2D.from_rotation(math.pi / 2)
        p = Vector2D(1, 0)
        result = t.apply_to_point(p)
        assert result.x == pytest.approx(0.0)
        assert result.y == pytest.approx(1.0)

    def test_rotation_180(self):
        """180° rotation."""
        t = Transform2D.from_rotation(math.pi)
        p = Vector2D(1, 0)
        result = t.apply_to_point(p)
        assert result.x == pytest.approx(-1.0)
        assert result.y == pytest.approx(0.0)

    def test_position_and_direction(self):
        """Transform from position and direction."""
        # Wall at (100, 0) going east
        t = Transform2D.from_position_and_direction(100, 0, 1, 0)
        p = Vector2D(50, 30)  # 50 along wall, 30 into room
        result = t.apply_to_point(p)
        assert result.x == pytest.approx(150.0)  # 100 + 50
        assert result.y == pytest.approx(30.0)

    def test_position_and_direction_north(self):
        """Transform from position going north."""
        # Wall at (0, 100) going north
        t = Transform2D.from_position_and_direction(0, 100, 0, 1)
        p = Vector2D(50, 30)  # 50 along wall, 30 into room
        result = t.apply_to_point(p)
        assert result.x == pytest.approx(-30.0)  # -30 (into room = west)
        assert result.y == pytest.approx(150.0)  # 100 + 50
