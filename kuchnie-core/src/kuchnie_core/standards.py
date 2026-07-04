"""Kitchen Standards — European kitchen cabinet standards (32mm system).

Defines standard dimensions, tolerances, and validation rules
for European frameless kitchen cabinets.

This module depends only on src/core/.
"""

from dataclasses import dataclass
from typing import List, Set

from kuchnie_core.types import Dimensions


# Standard cabinet widths (mm)
STANDARD_WIDTHS: Set[float] = {300, 400, 450, 500, 600, 800, 900, 1000, 1200}

# Standard drawer heights (mm)
STANDARD_DRAWER_HEIGHTS: Set[float] = {100, 120, 150, 160, 200, 240, 300}


@dataclass(frozen=True)
class KitchenStandards:
    """European kitchen cabinet standards.

    All dimensions in millimeters.
    Based on 32mm system (increments of 32mm).
    """
    # Base cabinet standards
    base_body_height: float = 720.0      # Carcass height without plinth
    base_depth: float = 560.0            # Carcass depth
    plinth_height: float = 120.0         # Plinth height
    plinth_setback: float = 60.0         # Plinth setback from front

    # Wall cabinet standards
    wall_height: float = 720.0           # Wall cabinet height
    wall_depth: float = 300.0            # Wall cabinet depth
    wall_mount_height: float = 1400.0    # Height from floor to bottom of wall cabinet

    # Tall cabinet standards
    tall_height: float = 2000.0          # Tall cabinet height
    tall_depth: float = 560.0            # Tall cabinet depth

    # Countertop standards
    counter_thickness: float = 30.0      # Countertop thickness
    counter_overhang_front: float = 20.0 # Front overhang
    counter_overhang_end: float = 30.0   # End overhang

    # Gap standards
    cabinet_gap: float = 0.0             # Between carcass boxes
    front_gap: float = 2.0               # Between door/drawer fronts

    # Offset standards
    front_offset: float = 1.0            # mm — how far fronts protrude from carcass
    clearance_offset: float = 1.0        # mm — geometric clearance for blind corners etc.

    # Tolerance standards
    position_tolerance: float = 0.1      # mm
    dimension_tolerance: float = 0.5     # mm

    # Validation thresholds
    min_cabinet_width: float = 100.0     # mm
    max_cabinet_width: float = 1200.0    # mm
    min_drawer_height: float = 30.0      # mm
    max_drawer_count: int = 6

    @property
    def base_total_height(self) -> float:
        """Base cabinet total height (plinth + body)."""
        return self.plinth_height + self.base_body_height

    @property
    def standard_widths(self) -> Set[float]:
        """Standard cabinet widths."""
        return STANDARD_WIDTHS

    def is_standard_width(self, width: float) -> bool:
        """Check if width is a standard size."""
        return any(abs(width - sw) < self.dimension_tolerance
                   for sw in STANDARD_WIDTHS)

    def get_dimensions(self, level: str) -> Dimensions:
        """Get standard dimensions for a cabinet level.

        Args:
            level: "base", "upper", or "tall"

        Returns:
            Standard dimensions for that level.
        """
        if level == "base":
            return Dimensions(
                width=600,  # Default width
                depth=self.base_depth,
                height=self.base_body_height,
            )
        elif level == "upper":
            return Dimensions(
                width=600,
                depth=self.wall_depth,
                height=self.wall_height,
            )
        else:  # tall
            return Dimensions(
                width=600,
                depth=self.tall_depth,
                height=self.tall_height,
            )


# Default European standards
EUROPEAN_STANDARDS = KitchenStandards()
