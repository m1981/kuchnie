"""Core Tolerances — Named, configurable tolerances for CAD operations.

All tolerances are in millimeters unless otherwise specified.
Tolerances are immutable and can be overridden per-operation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Tolerances:
    """Named tolerances for CAD operations.

    All values in millimeters.
    """
    # Position tolerances
    position: float = 0.1        # mm — placement accuracy
    dimension: float = 0.5       # mm — size accuracy
    angle: float = 0.01          # radians — rotation accuracy

    # Gap tolerances
    cabinet_gap: float = 0.0     # mm — between carcass boxes
    front_gap: float = 2.0       # mm — between door/drawer fronts

    # Front offset (how far fronts protrude)
    front_offset: float = 1.0    # mm — front face protrusion
    clearance_offset: float = 1.0  # mm — geometric clearance

    # Mesh tolerances
    vertex_merge: float = 0.01   # mm — merge vertices closer than this
    normal_tolerance: float = 0.01  # radians — normal comparison

    # Validation thresholds
    min_cabinet_width: float = 100.0   # mm
    max_cabinet_width: float = 1200.0  # mm
    min_drawer_height: float = 30.0    # mm
    max_drawer_count: int = 6

    def is_position_close(self, a: float, b: float) -> bool:
        """Check if two positions are within position tolerance."""
        return abs(a - b) <= self.position

    def is_dimension_close(self, a: float, b: float) -> bool:
        """Check if two dimensions are within dimension tolerance."""
        return abs(a - b) <= self.dimension

    def is_angle_close(self, a: float, b: float) -> bool:
        """Check if two angles are within angle tolerance."""
        return abs(a - b) <= self.angle

    def with_overrides(self, **kwargs) -> 'Tolerances':
        """Create new Tolerances with overridden values."""
        import dataclasses
        return dataclasses.replace(self, **kwargs)


# Default tolerances (singleton)
DEFAULT_TOLERANCES = Tolerances()
