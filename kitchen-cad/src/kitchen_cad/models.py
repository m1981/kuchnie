"""Domain models for parametric kitchen cabinet design.

All dimensions in millimeters (mm).
Coordinate system: origin at bottom-left of panel face.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# System 32 constants (shared across modules)
# ---------------------------------------------------------------------------

SYSTEM32_OFFSET: float = 37.0   # mm from front/bottom edge
SYSTEM32_SPACING: float = 32.0  # mm between holes


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CorpusType(str, Enum):
    """Cabinet corpus type — selects which config variant to use."""
    BASE_DOOR = "base_door"
    BASE_DRAWER = "base_drawer"
    CORNER_BLIND = "corner_blind"


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
    """Face of a panel where drilling occurs."""
    INSIDE = "inside"
    OUTSIDE = "outside"
    FRONT = "front"
    BACK = "back"


class DrillType(str, Enum):
    SYSTEM_32 = "system32"
    HINGE_CUP = "puszka_zawiasu"
    HINGE_SCREW = "znacznik_wkret"
    HINGE_DOWEL = "kolek_zawiasu"
    DOWEL_CONNECTOR = "kolek_laczacy"
    MINIFIX = "minifix"
    HANDLE = "uchwyt"
    SHELF_PIN = "podporka_polki"


class CornerSide(str, Enum):
    """Which side the corner cabinet opens from."""
    LEFT = "left"
    RIGHT = "right"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class EdgeBand(BaseModel):
    """Edge banding specification for one side of a panel."""
    side: EdgeSide
    material: str = "ABS_0.8"


class DrillPoint(BaseModel):
    """A single drill hole on a panel face."""
    x: float = Field(ge=0, description="mm from left edge")
    y: float = Field(ge=0, description="mm from bottom edge")
    diameter: float = Field(gt=0, description="mm")
    depth: float = Field(ge=0, description="mm; 0 = through hole")
    face: DrillFace
    drill_type: DrillType
    label: str = ""


# ---------------------------------------------------------------------------
# Hardware specifications
# ---------------------------------------------------------------------------

class HingeSpec(BaseModel):
    """Hinge specification for a door."""
    type: str = "blum_clip_35"
    cup_diameter: float = 35.0
    cup_depth: float = 13.0
    screw_spacing: float = 45.0
    screw_offset_x: float = 9.5
    screw_diameter: float = 3.0
    screw_depth: float = 2.0
    edge_to_cup_centre: float = 5.0
    count: int = 2
    first_position: float = 100.0


class DrawerSpec(BaseModel):
    """Single drawer specification."""
    internal_height: float = Field(gt=0, description="mm — usable internal height")
    runner_type: str = "blum_metabox"


class HandleSpec(BaseModel):
    """Handle specification."""
    type: str = "bar"
    spacing: float = 256.0
    position: str = "center"
    hole_diameter: float = 5.0


# ---------------------------------------------------------------------------
# Cabinet variant configs (discriminated union)
# ---------------------------------------------------------------------------

class BaseDoorConfig(BaseModel):
    """Standard base cabinet with doors and shelves."""
    type: Literal["base_door"] = "base_door"
    shelves: list[float] = Field(
        default_factory=list,
        description="Shelf positions from inside bottom (mm)",
    )
    doors: list[int] = Field(
        default_factory=list,
        description="Hinge count per door, one entry per door",
    )


class BaseDrawerConfig(BaseModel):
    """Base cabinet with drawers only."""
    type: Literal["base_drawer"] = "base_drawer"
    drawers: list[DrawerSpec] = Field(
        default_factory=list,
        description="Drawer specs, top to bottom",
    )


class CornerBlindConfig(BaseModel):
    """Corner cabinet with blind front (L-shaped body)."""
    type: Literal["corner_blind"] = "corner_blind"
    corner_side: CornerSide
    second_width: float = Field(
        gt=0,
        description="mm — perpendicular width of the corner extension",
    )
    shelves: list[float] = Field(
        default_factory=list,
        description="Shelf positions from inside bottom (mm)",
    )
    doors: list[int] = Field(
        default_factory=list,
        description="Hinge count per door, one entry per door",
    )


CabinetConfig = Annotated[
    Union[BaseDoorConfig, BaseDrawerConfig, CornerBlindConfig],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Panel aggregate
# ---------------------------------------------------------------------------

class Panel(BaseModel):
    """A single panel (formatka) to be cut from board material."""
    id: str
    role: PanelRole
    width: float = Field(gt=0, description="mm — cutting width")
    height: float = Field(gt=0, description="mm — cutting height")
    thickness: float = Field(gt=0, description="mm")
    material: str
    quantity: int = 1
    edges: list[EdgeBand] = Field(default_factory=list)
    drill_points: list[DrillPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Corpus specification (top-level aggregate)
# ---------------------------------------------------------------------------

class CorpusSpec(BaseModel):
    """Full specification of a corpus (cabinet).

    Supports two construction styles:

    1. New (recommended): use `config` with a discriminated union variant::

        CorpusSpec(
            id="K01", name="...", width=800, height=720, depth=510,
            config=BaseDoorConfig(shelves=[352], doors=[2]),
        )

    2. Legacy (backward-compatible): use `corpus_type` + flat fields::

        CorpusSpec(
            id="K01", name="...", width=800, height=720, depth=510,
            corpus_type="base_door", shelves=[352], doors=[2],
        )

    Both styles produce identical results. The legacy fields are
    automatically converted to the appropriate config variant.
    """
    id: str
    name: str

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

    # Hardware
    hinges: HingeSpec | None = Field(default_factory=HingeSpec)
    handles: HandleSpec | None = None

    # Shelf pin parameters
    shelf_pin_diameter: float = 5.0
    shelf_pin_depth: float = 8.0
    shelf_pin_front_offset: float = 50.0
    shelf_pin_back_offset: float = 80.0
    shelf_pin_max_per_row: int = 3

    # Front gaps
    front_gap: float = Field(default=3.0, ge=0)

    # Type-specific configuration (discriminated union)
    config: CabinetConfig | None = Field(default=None)

    # --- Legacy fields (for backward compatibility) ---
    corpus_type: str | None = Field(default=None, exclude=True)
    shelves: list[float] = Field(default_factory=list, exclude=True)
    drawers: list[DrawerSpec] = Field(default_factory=list, exclude=True)
    doors: list[int] = Field(default_factory=list, exclude=True)

    @model_validator(mode="after")
    def _sync_config_from_legacy(self) -> "CorpusSpec":
        """Convert legacy flat fields to config variant if config is not set."""
        if self.config is not None:
            return self

        if self.corpus_type is None:
            # Default to base_door with empty config
            self.config = BaseDoorConfig()
            return self

        ct = self.corpus_type
        if ct in ("base_door", "wall_door", "wall_lifter", "tall"):
            self.config = BaseDoorConfig(
                shelves=self.shelves,
                doors=self.doors,
            )
        elif ct == "base_drawer":
            self.config = BaseDrawerConfig(
                drawers=self.drawers,
            )
        elif ct == "corner_blind":
            self.config = CornerBlindConfig(
                corner_side=CornerSide.LEFT,
                second_width=self.depth,
                shelves=self.shelves,
                doors=self.doors,
            )
        else:
            self.config = BaseDoorConfig(
                shelves=self.shelves,
                doors=self.doors,
            )

        return self

    @property
    def corpus_type_resolved(self) -> str:
        """Return the resolved corpus type string."""
        return self.config.type

    @property
    def shelves_resolved(self) -> list[float]:
        """Shelf positions from config (backward-compatible accessor)."""
        if isinstance(self.config, (BaseDoorConfig, CornerBlindConfig)):
            return self.config.shelves
        return []

    @property
    def drawers_resolved(self) -> list[DrawerSpec]:
        """Drawer specs from config (backward-compatible accessor)."""
        if isinstance(self.config, BaseDrawerConfig):
            return self.config.drawers
        return []

    @property
    def doors_resolved(self) -> list[int]:
        """Door hinge counts from config (backward-compatible accessor)."""
        if isinstance(self.config, (BaseDoorConfig, CornerBlindConfig)):
            return self.config.doors
        return []
