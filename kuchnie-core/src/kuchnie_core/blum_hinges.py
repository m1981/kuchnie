"""Blum ClipTop hinge catalog — 110°, 95°, 155°.

Sources:
  - Blum Catalogue 2024/2025 (CLIP top hinges)
  - Standard European concealed hinge specifications

All dimensions in mm unless noted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .model import Accessory


# ── Hinge drilling geometry (ADR-012 §3) ─────────────────────────

@dataclass(frozen=True)
class HingeGeometry:
    """All drilling geometry a CAM stage needs for one hinge.

    Field defaults match Blum CLIP top 110° standard European kitchen
    hinges (35mm cup, 45mm plate screw spacing, 3mm pilot holes).
    Concrete ``BlumHinge`` subclasses may override the ``geometry``
    property to supply different values if a hinge in the catalog has
    non-standard drilling.

    Coordinate note (matches ``MachiningOp`` on the door panel):
      * ``edge_to_cup_centre_mm`` — distance from door edge to cup centre
        along the short axis (X), i.e. how far the cup sits inboard from
        the hinge-side edge.
      * ``first_position_mm``     — distance from door top edge to the
        first hinge cup centre along the long axis (Y).
      * ``screw_spacing_mm``      — centre-to-centre of the two plate
        screws (parallel to the door edge).
      * ``screw_offset_x_mm``     — distance from door edge to the plate
        screw axis.
    """
    cup_diameter_mm: int = 35     # cup drill diameter (Blum CLIP top: 35mm)
    cup_drill_depth_mm: int = 13  # cup drill depth (Blum CLIP top: 13mm)
    edge_to_cup_centre_mm: float = 5.0
    screw_spacing_mm: float = 45.0
    screw_offset_x_mm: float = 9.5
    screw_diameter_mm: float = 3.0
    screw_depth_mm: float = 2.0
    first_position_mm: float = 100.0   # first cup centre from door top


# ── Abstract base ────────────────────────────────────────────────

class BlumHinge(ABC):
    """Unified interface for Blum hinges."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier (e.g. 'blum_cliptop_110')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""
        ...

    @property
    @abstractmethod
    def opening_angle_deg(self) -> int:
        """Opening angle in degrees."""
        ...

    @property
    @abstractmethod
    def cup_diameter_mm(self) -> int:
        """Cup drill diameter in mm."""
        ...

    @property
    @abstractmethod
    def cup_drill_depth_mm(self) -> int:
        """Cup drill depth in mm."""
        ...

    @property
    @abstractmethod
    def mounting_type(self) -> str:
        """Mounting type: 'clip', 'screw-on', 'press-in'."""
        ...

    @property
    @abstractmethod
    def overlay_types(self) -> list[str]:
        """Supported overlay types: 'full', 'half', 'inset'."""
        ...

    @property
    @abstractmethod
    def closing_type(self) -> str:
        """Closing mechanism: 'blumotion', 'tip-on', 'none'."""
        ...

    @property
    @abstractmethod
    def is_default(self) -> bool:
        """Whether this is the default hinge choice."""
        ...

    def to_accessory(self, cabinet_id: str, door_id: str, quantity: int = 2) -> Accessory:
        """Create an Accessory entry for BOM."""
        return Accessory(
            id=f"{cabinet_id}_hinge_{door_id}",
            name=f"Zawias {self.name}",
            type="hinge",
            quantity=quantity,
        )

    @property
    def geometry(self) -> HingeGeometry:
        """Return drilling geometry for this hinge (ADR-012 §3).

        Default implementation combines the concrete subclass's cup
        drilling data (``cup_diameter_mm`` / ``cup_drill_depth_mm``)
        with the standard European plate-screw geometry from ADR-012.
        Subclasses may override this property to provide non-standard
        values.
        """
        return HingeGeometry(
            cup_diameter_mm=self.cup_diameter_mm,
            cup_drill_depth_mm=self.cup_drill_depth_mm,
        )


# ── Concrete implementations ────────────────────────────────────

class BlumClipTop110(BlumHinge):
    """Standard concealed hinge — 110° opening angle.

    Use for: full overlay, half overlay, inset doors.
    This is the default choice for most European kitchens.
    """

    @property
    def id(self) -> str:
        return "blum_cliptop_110"

    @property
    def name(self) -> str:
        return "Blum CLIP top 110°"

    @property
    def opening_angle_deg(self) -> int:
        return 110

    @property
    def cup_diameter_mm(self) -> int:
        return 35

    @property
    def cup_drill_depth_mm(self) -> int:
        return 13

    @property
    def mounting_type(self) -> str:
        return "clip"

    @property
    def overlay_types(self) -> list[str]:
        return ["full", "half", "inset"]

    @property
    def closing_type(self) -> str:
        return "blumotion"

    @property
    def is_default(self) -> bool:
        return True


class BlumClipTop95(BlumHinge):
    """Hinge for inset doors — 95° opening angle.

    Use for: inset doors where 110° would hit the carcass.
    """

    @property
    def id(self) -> str:
        return "blum_cliptop_95"

    @property
    def name(self) -> str:
        return "Blum CLIP top 95°"

    @property
    def opening_angle_deg(self) -> int:
        return 95

    @property
    def cup_diameter_mm(self) -> int:
        return 35

    @property
    def cup_drill_depth_mm(self) -> int:
        return 13

    @property
    def mounting_type(self) -> str:
        return "clip"

    @property
    def overlay_types(self) -> list[str]:
        return ["inset"]

    @property
    def closing_type(self) -> str:
        return "blumotion"

    @property
    def is_default(self) -> bool:
        return False


class BlumClipTop155(BlumHinge):
    """Wide-angle hinge — 155° opening angle.

    Use for: corner cabinets, full-access applications.
    """

    @property
    def id(self) -> str:
        return "blum_cliptop_155"

    @property
    def name(self) -> str:
        return "Blum CLIP top 155°"

    @property
    def opening_angle_deg(self) -> int:
        return 155

    @property
    def cup_diameter_mm(self) -> int:
        return 35

    @property
    def cup_drill_depth_mm(self) -> int:
        return 13

    @property
    def mounting_type(self) -> str:
        return "clip"

    @property
    def overlay_types(self) -> list[str]:
        return ["full"]

    @property
    def closing_type(self) -> str:
        return "blumotion"

    @property
    def is_default(self) -> bool:
        return False


# ── Factory ──────────────────────────────────────────────────────

_HINGES: dict[str, type[BlumHinge]] = {
    "blum_cliptop_110": BlumClipTop110,
    "blum_cliptop_95": BlumClipTop95,
    "blum_cliptop_155": BlumClipTop155,
}


class HingeFactory:
    """Factory for Blum hinges."""

    @staticmethod
    def get(hinge_id: str) -> BlumHinge:
        """Get hinge by id.  Raises KeyError if not found."""
        if hinge_id not in _HINGES:
            raise KeyError(f"Unknown hinge: {hinge_id!r}")
        return _HINGES[hinge_id]()

    @staticmethod
    def get_default() -> BlumHinge:
        """Get the default hinge (ClipTop 110°)."""
        return BlumClipTop110()

    @staticmethod
    def list_ids() -> list[str]:
        """List all available hinge ids."""
        return list(_HINGES.keys())


# ── Hinge count calculator ───────────────────────────────────────

def calculate_hinge_count(door_height_mm: int) -> int:
    """Calculate number of hinges needed based on door height.

    Blum standard:
      - Up to 1200mm: 2 hinges
      - 1201-1800mm: 3 hinges
      - 1801-2400mm: 4 hinges

    Minimum is always 2 hinges.
    """
    if door_height_mm <= 1200:
        return 2
    elif door_height_mm <= 1800:
        return 3
    else:
        return 4
