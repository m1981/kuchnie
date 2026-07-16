"""ConstructionMethod — first-class construction rules (Polyboard pattern).

Separates HOW a cabinet is built from WHAT the cabinet is.
One method can be shared across many cabinet types.

Key insight from Polyboard: if you change from cam-lock to dowel
construction, you swap the method — you don't rewrite every cabinet type.
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Front gap constants ──────────────────────────────────────────

_FRONT_GAP_VERTICAL_MM = 3   # vertical gap between stacked fronts and at
                             # top/bottom — unchanged by the G12 decision


@dataclass(frozen=True)
class ConstructionMethod:
    """Immutable construction recipe — reusable across cabinet types.

    All thicknesses in mm.  Formulas derive panel dimensions from
    cabinet width/height using these parameters.
    """

    id: str
    name: str

    # Panel thicknesses
    side_thickness_mm: int = 18
    top_thickness_mm: int = 18
    bottom_thickness_mm: int = 18
    shelf_thickness_mm: int = 18
    back_thickness_mm: int = 3
    front_thickness_mm: int = 18

    # Joinery
    joinery_type: str = "dowel_confirmat"   # "dowel_confirmat" | "camlock" | "dado" | "glue"
    back_attachment: str = "groove"          # "groove" | "rabbet" | "stapled"
    back_groove_depth_mm: int = 8
    back_clearance_mm: int = 2               # assembly clearance ("luz") per axis

    # Front side-reveal (G12, PO decision 2026-07-14): horizontal margin
    # per side. Shop standard 2mm; edge-pull handles (uchwyt krawędziowy)
    # need 3mm — front_reveal() picks by handle type. Change the shop
    # standard HERE (or per registered method); per-front margines_lewo/
    # margines_prawo overrides in the YAML still win.
    front_reveal_mm: float = 2.0
    front_reveal_edge_pull_mm: float = 3.0

    # Edge banding defaults
    edge_band_thickness_mm: float = 0.8      # 0.4 / 0.8 / 1.0 / 2.0

    # System 32 grid
    system32_offset_mm: int = 37             # distance from edge to first hole
    system32_spacing_mm: int = 32            # hole pitch

    # Hardware defaults
    default_hinge: str = "blum_cliptop_110"
    default_runner_brand: str = "blum"

    # ── Derived dimension formulas ───────────────────────────────

    def carcass_bottom_width(self, cabinet_width_mm: int) -> int:
        """Bottom/top panel width = cabinet_width - 2 × side_thickness."""
        return cabinet_width_mm - 2 * self.side_thickness_mm

    def back_panel_width(self, cabinet_width_mm: int) -> int:
        """Back panel width = cabinet_width - 2×side + 2×groove_depth - clearance.

        Back sits in grooves cut into both sides, so it's wider than the
        internal space, minus assembly clearance so it can be slid in.
        """
        return (
            cabinet_width_mm
            - 2 * self.side_thickness_mm
            + 2 * self.back_groove_depth_mm
            - self.back_clearance_mm
        )

    def back_panel_height(self, side_height_mm: int) -> int:
        """Back panel height = side_h - bottom - top + 2×groove_depth - clearance.

        Back sits in grooves cut into the bottom panel and the top panel
        (or rear top stretcher laid flat), so it spans the internal height
        plus both groove depths, minus assembly clearance. Never exceeds
        the sides.
        """
        return (
            side_height_mm
            - self.bottom_thickness_mm
            - self.top_thickness_mm
            + 2 * self.back_groove_depth_mm
            - self.back_clearance_mm
        )

    def shelf_width(self, cabinet_width_mm: int) -> int:
        """Shelf width = bottom_width - 2mm clearance (1mm per side)."""
        return self.carcass_bottom_width(cabinet_width_mm) - 2

    def front_reveal(self, handle_type: str | None = None) -> float:
        """Horizontal side-reveal for fronts (G12 shop setting).

        Edge-pull handles (type 'edge_pull') get the wider reveal; every
        other handle type — and handleless fronts — get the shop standard.
        """
        if handle_type == "edge_pull":
            return self.front_reveal_edge_pull_mm
        return self.front_reveal_mm

    def door_width(self, cabinet_width_mm: int, door_count: int = 1,
                   reveal_mm: float | None = None) -> float:
        """Door width = (cabinet_width - reveal_total) / door_count.

        Horizontal reveal on each side + between doors (front_reveal();
        pass reveal_mm to apply a handle-dependent value).
        """
        reveal = self.front_reveal_mm if reveal_mm is None else reveal_mm
        gap_total = reveal * (door_count + 1)
        return (cabinet_width_mm - gap_total) / door_count

    def door_height(self, cabinet_height_mm: int) -> int:
        """Door height = cabinet_height - 2 × 3mm (vertical gaps, fixed)."""
        return cabinet_height_mm - 2 * _FRONT_GAP_VERTICAL_MM

    def drawer_front_width(self, cabinet_width_mm: int,
                           margin_mm: float | None = None) -> float:
        """Drawer front width = cabinet_width - 2 × side reveal."""
        margin = self.front_reveal_mm if margin_mm is None else margin_mm
        return cabinet_width_mm - 2 * margin

    def validate_cabinet_width(self, cabinet_width_mm: int) -> list[str]:
        """Check that cabinet width is large enough for this construction.

        Returns list of error messages (empty if valid).
        """
        errors: list[str] = []
        min_width = 2 * self.side_thickness_mm + 10  # 10mm minimum internal
        if cabinet_width_mm < min_width:
            errors.append(
                f"Cabinet width {cabinet_width_mm}mm too small for "
                f"{self.side_thickness_mm}mm sides. Minimum: {min_width}mm"
            )
        bottom_w = self.carcass_bottom_width(cabinet_width_mm)
        if bottom_w <= 0:
            errors.append(
                f"Bottom panel width would be {bottom_w}mm (negative). "
                f"Increase cabinet width or reduce side thickness."
            )
        return errors


class ConstructionMethodRegistry:
    """Named collection of construction methods."""

    def __init__(self) -> None:
        self._methods: dict[str, ConstructionMethod] = {}

    def __len__(self) -> int:
        return len(self._methods)

    def register(self, method: ConstructionMethod) -> None:
        """Add a method.  Raises ValueError if id already registered."""
        if method.id in self._methods:
            raise ValueError(
                f"ConstructionMethod '{method.id}' already registered"
            )
        self._methods[method.id] = method

    def get(self, method_id: str) -> ConstructionMethod:
        """Retrieve by id.  Raises KeyError if not found."""
        if method_id not in self._methods:
            raise KeyError(f"ConstructionMethod '{method_id}' not found")
        return self._methods[method_id]

    def list_ids(self) -> list[str]:
        """Return all registered method ids."""
        return list(self._methods.keys())

    @classmethod
    def default(cls) -> ConstructionMethodRegistry:
        """Registry pre-loaded with common European construction methods."""
        reg = cls()

        reg.register(ConstructionMethod(
            id="dowel_confirmat_18mm",
            name="Dowel + Confirmat 18mm (standard)",
            side_thickness_mm=18,
            top_thickness_mm=18,
            bottom_thickness_mm=18,
            shelf_thickness_mm=18,
            back_thickness_mm=3,
            front_thickness_mm=18,
            joinery_type="dowel_confirmat",
            back_attachment="groove",
            back_groove_depth_mm=8,
        ))

        reg.register(ConstructionMethod(
            id="camlock_18mm",
            name="Cam Lock 18mm (RTA / flat-pack)",
            side_thickness_mm=18,
            top_thickness_mm=18,
            bottom_thickness_mm=18,
            shelf_thickness_mm=18,
            back_thickness_mm=3,
            front_thickness_mm=18,
            joinery_type="camlock",
            back_attachment="groove",
            back_groove_depth_mm=8,
        ))

        reg.register(ConstructionMethod(
            id="dowel_16mm",
            name="Dowel 16mm (budget / lightweight)",
            side_thickness_mm=16,
            top_thickness_mm=16,
            bottom_thickness_mm=16,
            shelf_thickness_mm=16,
            back_thickness_mm=2.5,
            front_thickness_mm=16,
            joinery_type="dowel_confirmat",
            back_attachment="groove",
            back_groove_depth_mm=6,
        ))

        return reg
