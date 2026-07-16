"""Core Types — immutable value objects.

The former cabinet-vocabulary enums (Direction, CabinetLevel, CabinetType,
HandleType, DoorSide) were a dormant parallel vocabulary to the Polish
TYPE_REGISTRY keys and live in attic/kuchnie-core-types-enums.py
(tr-3a97dc10, wk-0eb2781f).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dimensions:
    """Immutable cabinet dimensions (all mm)."""
    width: float   # mm
    depth: float   # mm
    height: float  # mm

    def with_offsets(self, depth_offset_mm: float = 0,
                     height_offset_mm: float = 0) -> 'Dimensions':
        """Create new dimensions with offsets applied."""
        return Dimensions(
            width=self.width,
            depth=self.depth + depth_offset_mm,
            height=self.height + height_offset_mm,
        )

