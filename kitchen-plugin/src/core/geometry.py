"""Core Geometry Types — Pure math, no external dependencies.

Implements:
- Vector2D: 2D vector for wall coordinates
- Vector3D: 3D vector for world coordinates
- BoundingBox: Axis-aligned bounding box
- Transform: 2D transformation matrix

All types are immutable value objects (frozen dataclasses).
"""

from dataclasses import dataclass
from typing import Tuple
import math


@dataclass(frozen=True)
class Vector2D:
    """Immutable 2D vector.

    Used for wall coordinates (x, y) in plan view.
    """
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Vector2D':
        return Vector2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> 'Vector2D':
        return self.__mul__(scalar)

    def dot(self, other: 'Vector2D') -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        """Vector length (magnitude)."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalized(self) -> 'Vector2D':
        """Return unit vector in same direction."""
        len = self.length()
        if len < 1e-10:
            return Vector2D(0.0, 0.0)
        return Vector2D(self.x / len, self.y / len)

    def perpendicular(self) -> 'Vector2D':
        """Return perpendicular vector (90° CCW rotation).

        If vector points east (+X), perpendicular points north (+Y).
        """
        return Vector2D(-self.y, self.x)

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple."""
        return (self.x, self.y)


@dataclass(frozen=True)
class Vector3D:
    """Immutable 3D vector.

    Used for world coordinates (x, y, z).
    Convention: Z-up, right-hand rule.
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> 'Vector3D':
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> 'Vector3D':
        return self.__mul__(scalar)

    def dot(self, other: 'Vector3D') -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vector3D') -> 'Vector3D':
        """Cross product."""
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        """Vector length (magnitude)."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> 'Vector3D':
        """Return unit vector in same direction."""
        len = self.length()
        if len < 1e-10:
            return Vector3D(0.0, 0.0, 0.0)
        return Vector3D(self.x / len, self.y / len, self.z / len)

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)

    def to_mm(self) -> 'Vector3D':
        """Convert meters to millimeters."""
        return Vector3D(self.x * 1000, self.y * 1000, self.z * 1000)

    def to_m(self) -> 'Vector3D':
        """Convert millimeters to meters."""
        return Vector3D(self.x / 1000, self.y / 1000, self.z / 1000)


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box.

    Defined by minimum and maximum corners.
    """
    min_point: Vector3D
    max_point: Vector3D

    @property
    def width(self) -> float:
        """Width along X axis."""
        return self.max_point.x - self.min_point.x

    @property
    def depth(self) -> float:
        """Depth along Y axis."""
        return self.max_point.y - self.min_point.y

    @property
    def height(self) -> float:
        """Height along Z axis."""
        return self.max_point.z - self.min_point.z

    @property
    def center(self) -> Vector3D:
        """Center point."""
        return Vector3D(
            (self.min_point.x + self.max_point.x) / 2,
            (self.min_point.y + self.max_point.y) / 2,
            (self.min_point.z + self.max_point.z) / 2,
        )

    def contains_point(self, point: Vector3D) -> bool:
        """Check if point is inside bounding box."""
        return (
            self.min_point.x <= point.x <= self.max_point.x and
            self.min_point.y <= point.y <= self.max_point.y and
            self.min_point.z <= point.z <= self.max_point.z
        )

    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if two bounding boxes overlap."""
        return (
            self.min_point.x <= other.max_point.x and
            self.max_point.x >= other.min_point.x and
            self.min_point.y <= other.max_point.y and
            self.max_point.y >= other.min_point.y and
            self.min_point.z <= other.max_point.z and
            self.max_point.z >= other.min_point.z
        )


@dataclass(frozen=True)
class Transform2D:
    """Immutable 2D transformation matrix.

    Represents rotation and translation in 2D.
    Used for wall-local to world coordinate conversion.
    """
    cos: float = 1.0
    sin: float = 0.0
    tx: float = 0.0
    ty: float = 0.0

    @classmethod
    def from_rotation(cls, angle_rad: float) -> 'Transform2D':
        """Create rotation-only transform."""
        return cls(
            cos=math.cos(angle_rad),
            sin=math.sin(angle_rad),
            tx=0.0,
            ty=0.0,
        )

    @classmethod
    def from_translation(cls, tx: float, ty: float) -> 'Transform2D':
        """Create translation-only transform."""
        return cls(cos=1.0, sin=0.0, tx=tx, ty=ty)

    @classmethod
    def from_position_and_direction(cls, x: float, y: float, dx: float, dy: float) -> 'Transform2D':
        """Create transform from position and direction vector.

        Direction vector is normalized internally.
        """
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-10:
            return cls(cos=1.0, sin=0.0, tx=x, ty=y)
        return cls(
            cos=dx / length,
            sin=dy / length,
            tx=x,
            ty=y,
        )

    def apply_to_point(self, point: Vector2D) -> Vector2D:
        """Apply transform to a 2D point."""
        return Vector2D(
            self.cos * point.x - self.sin * point.y + self.tx,
            self.sin * point.x + self.cos * point.y + self.ty,
        )

    def apply_to_vector(self, vec: Vector2D) -> Vector2D:
        """Apply rotation only (no translation) to a vector."""
        return Vector2D(
            self.cos * vec.x - self.sin * vec.y,
            self.sin * vec.x + self.cos * vec.y,
        )
