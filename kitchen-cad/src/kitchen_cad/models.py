"""Domain models for parametric kitchen cabinet design.

All dimensions in millimeters (mm).
Coordinate system: origin at bottom-left of panel face.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PanelRole(str, Enum):
    LEFT_SIDE = "bok_lewy"
    RIGHT_SIDE = "bok_prawy"
    BOTTOM = "dno"
    TOP = "gora"
    SHELF = "polka"
    BACK = "plecy"
    FRONT_DOOR = "front_drzwi"
    FRONT_DRAWER = "front_szuflada"


class EdgeSide(str, Enum):
    TOP = "gora"
    BOTTOM = "dol"
    LEFT = "lewo"
    RIGHT = "prawo"


class DrillFace(str, Enum):
    """Face of a panel where drilling occurs.

    Convention: names refer to the panel's position in the assembled cabinet.
    "inside" = face toward cabinet interior.
    """
    INSIDE = "inside"   # face toward cabinet interior
    OUTSIDE = "outside" # face away from cabinet (e.g. outside of side panel)
    FRONT = "front"     # front face of panel (as laid flat for cutting)
    BACK = "back"       # back face of panel


class DrillType(str, Enum):
    SYSTEM_32 = "system32"              # ∅5 mm
    HINGE_CUP = "puszka_zawiasu"       # ∅35 mm
    HINGE_SCREW = "znacznik_wkret"     # ∅3 mm, depth 2 mm
    HINGE_DOWEL = "kolek_zawiasu"      # ∅8 mm, depth 13.5 mm
    DOWEL_CONNECTOR = "kolek_laczacy"  # ∅8 mm
    MINIFIX = "minifix"                # ∅15 mm
    HANDLE = "uchwyt"                  # ∅5 mm, through
    SHELF_PIN = "podporka_polki"       # ∅5 mm


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class EdgeBand(BaseModel):
    """Edge banding specification for one side of a panel."""
    side: EdgeSide
    material: str = "ABS_0.8"


class DrillPoint(BaseModel):
    """A single drill hole on a panel face.

    Coordinates relative to bottom-left corner of the specified face.
    """
    x: float = Field(ge=0, description="mm from left edge")
    y: float = Field(ge=0, description="mm from bottom edge")
    diameter: float = Field(gt=0, description="mm")
    depth: float = Field(ge=0, description="mm; 0 = through hole")
    face: DrillFace
    drill_type: DrillType
    label: str = ""


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------

class Panel(BaseModel):
    """A single panel (formatka) to be cut from board material.

    width × height are the CUTTING dimensions on the raw board.
    """
    id: str
    role: PanelRole
    width: float = Field(gt=0, description="mm — cutting width")
    height: float = Field(gt=0, description="mm — cutting height")
    thickness: float = Field(gt=0, description="mm")
    material: str
    quantity: int = 1
    edges: list[EdgeBand] = Field(default_factory=list)
    drill_points: list[DrillPoint] = Field(default_factory=list)


class HingeSpec(BaseModel):
    """Hinge specification for a door."""
    type: str = "blum_clip_35"
    cup_diameter: float = 35.0
    cup_depth: float = 13.0
    screw_spacing: float = 45.0       # mm between screw centres (Blum=45, Hettich=52)
    screw_offset_x: float = 9.5       # mm from cup centre toward panel interior
    screw_diameter: float = 3.0
    screw_depth: float = 2.0
    edge_to_cup_centre: float = 5.0   # mm from panel edge to cup centre
    count: int = 2                     # number of hinges per door
    first_position: float = 100.0      # mm from top of front


class DrawerSpec(BaseModel):
    """Drawer specification."""
    internal_height: float = Field(gt=0, description="mm — usable internal height")
    runner_type: str = "blum_metabox"


class HandleSpec(BaseModel):
    """Handle specification."""
    type: str = "bar"
    spacing: float = 256.0            # mm between hole centres
    position: str = "center"          # center | top | bottom
    hole_diameter: float = 5.0


class CorpusSpec(BaseModel):
    """Full specification of a corpus (cabinet).

    All dimensions are EXTERNAL (including side panels).
    """
    id: str
    name: str
    corpus_type: str = Field(
        description="base_door | base_drawer | wall_door | wall_lifter | tall"
    )

    # External dimensions
    width: float = Field(gt=0, description="mm — external width")
    height: float = Field(gt=0, description="mm — external height")
    depth: float = Field(gt=0, description="mm — external depth")

    # Construction
    panel_thickness: float = 18.0
    back_thickness: float = 3.0
    back_groove_depth: float = 8.0

    # Materials
    material_corpus: str = "U119_VL"
    material_back: str = "HDF_3mm_bialy"
    material_front: str = "U119_EM"

    # Edge banding
    edge_material: str = "ABS_0.8"

    # Internal structure
    shelves: list[float] = Field(
        default_factory=list,
        description="Shelf positions measured from INSIDE bottom (mm)",
    )
    drawers: list[DrawerSpec] = Field(default_factory=list)
    doors: list[int] = Field(
        default_factory=list,
        description="Number of hinges per door, one entry per door",
    )

    # Hardware
    hinges: HingeSpec | None = None
    handles: HandleSpec | None = None

    # Front gaps (margins between front and cabinet edges)
    front_gap: float = Field(
        default=3.0, ge=0,
        description="Gap on each side between front and cabinet edge (mm)",
    )
