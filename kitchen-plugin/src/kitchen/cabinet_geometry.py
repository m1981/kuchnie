"""Cabinet Geometry — European cabinet construction calculations.

Converts external cabinet dimensions to internal cavity and component
dimensions based on European frameless construction standards.

Reference: 18mm corpus board, 18-19mm front panels, 3mm HDF back.

This module depends only on src/core/.
"""

from dataclasses import dataclass


# European standard board thicknesses (mm)
DEFAULT_CORPUS_THICKNESS = 18   # Chipboard for carcass
DEFAULT_FRONT_THICKNESS = 19    # MDF/chipboard for fronts
DEFAULT_BACK_THICKNESS = 3      # HDF back panel

# Back panel groove parameters (mm)
DEFAULT_GROOVE_DEPTH = 9        # Depth of groove in corpus
DEFAULT_GROOVE_WIDTH = 3.2      # Width of groove (for 3mm HDF)
DEFAULT_GROOVE_OFFSET = 10      # Distance from rear edge to groove

# Front overlay defaults (mm) — how much front overlaps carcass edges
DEFAULT_OVERLAY_SIDE = 2        # Overlap on each side
DEFAULT_OVERLAY_TOP = 2         # Overlap on top
DEFAULT_OVERLAY_BOTTOM = 2      # Overlap on bottom


@dataclass(frozen=True)
class CabinetGeometry:
    """Calculate cabinet construction geometry.

    Converts external dimensions to internal cavity and component dimensions.
    Based on European frameless construction with 18mm corpus board.

    Coordinate system (cabinet-local):
    - Origin: front-left-bottom corner of carcass
    - Width: along +X (left to right)
    - Depth: along +Y (front to back, into room)
    - Height: along +Z (bottom to top)

    Example:
        geom = CabinetGeometry(600, 560, 720)
        assert geom.internal_width == 564  # 600 - 2*18
    """

    external_width: float   # mm
    external_depth: float   # mm
    external_height: float  # mm
    corpus_thickness: float = DEFAULT_CORPUS_THICKNESS
    back_thickness: float = DEFAULT_BACK_THICKNESS
    front_thickness: float = DEFAULT_FRONT_THICKNESS
    groove_offset: float = DEFAULT_GROOVE_OFFSET

    @property
    def internal_width(self) -> float:
        """Internal cavity width (external - 2 * corpus)."""
        return self.external_width - 2 * self.corpus_thickness

    @property
    def internal_depth(self) -> float:
        """Internal cavity depth (external - back panel offset).

        The back panel sits in a groove offset from the rear edge.
        Effective depth = external - groove_offset - back_thickness.
        """
        return self.external_depth - self.groove_offset - self.back_thickness

    @property
    def internal_height(self) -> float:
        """Internal cavity height (same as external for frameless)."""
        return self.external_height

    @property
    def side_panel_width(self) -> float:
        """Side panel depth (same as external depth)."""
        return self.external_depth

    @property
    def side_panel_height(self) -> float:
        """Side panel height (same as external height)."""
        return self.external_height

    @property
    def bottom_panel_width(self) -> float:
        """Bottom/top panel width (internal width)."""
        return self.internal_width

    @property
    def bottom_panel_depth(self) -> float:
        """Bottom/top panel depth (external - groove offset - back thickness)."""
        return self.internal_depth

    @property
    def back_panel_width(self) -> float:
        """Back panel width (internal width)."""
        return self.internal_width

    @property
    def back_panel_height(self) -> float:
        """Back panel height (external - small tolerance for assembly)."""
        return self.external_height - 3  # Small tolerance for assembly

    def front_dimensions(self, overlay_side: float = DEFAULT_OVERLAY_SIDE,
                         overlay_top: float = DEFAULT_OVERLAY_TOP,
                         overlay_bottom: float = DEFAULT_OVERLAY_BOTTOM) -> tuple:
        """Calculate front panel dimensions for overlay door.

        Args:
            overlay_side: Overlap on each side (mm)
            overlay_top: Overlap on top (mm)
            overlay_bottom: Overlap on bottom (mm)

        Returns:
            (width, height) of front panel in mm
        """
        width = self.external_width + 2 * overlay_side
        height = self.external_height + overlay_top + overlay_bottom
        return width, height

    def front_position(self, overlay_side: float = DEFAULT_OVERLAY_SIDE,
                       overlay_top: float = DEFAULT_OVERLAY_TOP,
                       overlay_bottom: float = DEFAULT_OVERLAY_BOTTOM) -> tuple:
        """Calculate front panel position relative to carcass origin.

        Origin is at front-left-bottom of carcass.
        Front extends forward (negative Y) by front_thickness.

        Args:
            overlay_side: Overlap on each side (mm)
            overlay_top: Overlap on top (mm)
            overlay_bottom: Overlap on bottom (mm)

        Returns:
            (x, y, z) position offset for front panel in mm
        """
        return (
            -overlay_side,           # Shift left by overlay
            -self.front_thickness,   # Extend forward
            -overlay_bottom,         # Shift down by overlay
        )
