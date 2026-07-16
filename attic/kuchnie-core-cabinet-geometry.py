# ATTIC TOMBSTONE — CabinetGeometry (2026-07-17, wk-0eb2781f)
# Moved from kuchnie-core/src/kuchnie_core/construction.py (lines 234-342)
# together with its pinning test (kuchnie-core-test-cabinet-construction.py).
# WHY: dormant twin of ConstructionMethod — zero production references
# repo-wide (tr-8e25dd76, arch-smells dormant-class detector); its
# external-minus-3 back formula conflicted with the shipped groove-seated
# formula (walking-skeleton G6 bug family, tr-8dfe366d). The 2026-07-16
# buildability orchestrator adopted CabinetInstance.validate +
# ConstructionMethod instead. Restore only with a superseding decision.

# European frameless construction calculations.
# Converts external dimensions to internal cavity and component dimensions.
# Migrated from former kitchen-plugin per ADR-009.
# TODO: consolidate with ConstructionMethod in a future migration.

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
        """Internal cavity depth (external - back panel offset)."""
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
        """Bottom/top panel depth."""
        return self.internal_depth

    @property
    def back_panel_width(self) -> float:
        """Back panel width (internal width)."""
        return self.internal_width

    @property
    def back_panel_height(self) -> float:
        """Back panel height (external - small tolerance for assembly)."""
        return self.external_height - 3

    def front_dimensions(self, overlay_side: float = DEFAULT_OVERLAY_SIDE,
                         overlay_top: float = DEFAULT_OVERLAY_TOP,
                         overlay_bottom: float = DEFAULT_OVERLAY_BOTTOM) -> tuple:
        """Calculate front panel dimensions for overlay door."""
        width = self.external_width + 2 * overlay_side
        height = self.external_height + overlay_top + overlay_bottom
        return width, height

    def front_position(self, overlay_side: float = DEFAULT_OVERLAY_SIDE,
                       overlay_top: float = DEFAULT_OVERLAY_TOP,
                       overlay_bottom: float = DEFAULT_OVERLAY_BOTTOM) -> tuple:
        """Calculate front panel position relative to carcass origin."""
        return (
            -overlay_side,
            -self.front_thickness,
            -overlay_bottom,
        )
