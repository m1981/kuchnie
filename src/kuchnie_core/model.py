"""Core domain models.

The atomic manufacturing unit is the Panel — not the cabinet.
Everything above panels is organizational. Everything on panels
(edges, machining ops) is decoration on that physical piece.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Union


class PanelRole(str, Enum):
    """Structural role of a panel within the cabinet carcass.

    Per ADR-012 §1. Enables role-based filtering in downstream CAM
    ("apply hinge cups to FRONT_DOOR only", "drill runner holes on
    LEFT_SIDE / RIGHT_SIDE only") without string matching on
    user-facing Polish names like "Lewy bok".

    English values keep the model layer English-only (AGENTS.md rule
    "Model fields English, YAML keys Polish"). Non-carcass panels
    (e.g. LEGRABOX drawer-box back/base) use ``role=None``.

    Value coverage in ``catalog.py`` decomposers (as of ADR-012 §1):
      * emitted today: LEFT_SIDE, RIGHT_SIDE, TOP, BOTTOM, SHELF, BACK,
        FRONT_DOOR, FRONT_DRAWER
      * aspirational (no decomposer emits yet): PLINTH — reserved for
        the future plinth-panel decomposition step. Locked in the enum
        so downstream CAM code can already ``match`` on it exhaustively
        without a follow-up model change.
    """
    LEFT_SIDE    = "left_side"
    RIGHT_SIDE   = "right_side"
    BOTTOM       = "bottom"
    TOP          = "top"
    SHELF        = "shelf"
    BACK         = "back"
    FRONT_DOOR   = "front_door"
    FRONT_DRAWER = "front_drawer"
    PLINTH       = "plinth"  # aspirational; see class docstring


@dataclass
class MachiningOp:
    """A machining operation on a panel — drill, groove, rabbet, dado.

    Coordinate system (panel lying flat, viewed from the machined face):
      x_mm  = distance from LEFT edge of panel
      y_mm  = distance from BOTTOM edge of panel (front edge for carcass sides)

    Fields ``face`` and ``drill_type`` (ADR-012 §2) let downstream CAM
    filter and route operations without string-matching on ``note``.
    Both default to safe values so existing constructors are unchanged.
    """
    type: str              # "drill", "groove", "rabbet", "dado"
    x_mm: float = 0
    y_mm: float = 0
    diameter_mm: float = 0  # for drill/bore
    depth_mm: float = 0     # 0 = through hole
    width_mm: float = 0     # for groove/rabbet
    length_mm: float = 0    # for groove
    note: str = ""
    # ADR-012 §2 — discriminators for CAM routing:
    face: str = "inside"    # "inside" | "outside" | "front" | "back"
    drill_type: str = ""    # "" | "system32" | "hinge_cup" | "hinge_screw"
                            # | "hinge_dowel" | "dowel_connector"
                            # | "minifix" | "handle" | "shelf_pin"
                            # (open string; kitchen-cam may extend the
                            # vocabulary without a core dependency inversion)


@dataclass
class EdgeBand:
    """Edge banding applied to ONE edge of a panel."""
    material: str        # e.g. "ABS_swiss_krono.U119_VL"
    thickness_mm: float  # 0.8
    length_mm: float     # length of THIS edge on the panel


@dataclass
class Panel:
    """A single physical panel — cut from board stock.

    Naming convention for width/height (viewed from cabinet front):
      - width  = horizontal dimension (left ↔ right)
      - height = vertical dimension   (floor ↔ ceiling)
    For depth-oriented panels (sides, shelves) this means:
      - width  = depth direction (front ↔ back)
      - height = vertical        (top ↔ bottom)
    """
    id: str
    name: str              # "Lewy bok", "Dno", "Półka P1"
    material: str          # material code, e.g. "swiss_krono.U119_VL"
    thickness_mm: int
    width_mm: float
    height_mm: float
    banded_edges: dict[str, EdgeBand] = field(default_factory=dict)
    # keys: "front", "back", "left", "right" — only edges that ARE banded
    machining_ops: list[MachiningOp] = field(default_factory=list)
    quantity: int = 1
    role: PanelRole | None = None   # ADR-012 §1 — structural role for CAM filtering


@dataclass
class ShelfPinSpec:
    """Shelf-pin drilling specification for a cabinet (ADR-012 §5).

    Applied to both carcass side panels: shelf pins are drilled from the
    inside face at fixed offsets from front and back edges. Two pins per
    side (front + back) support each shelf.

    Fields:
      * ``diameter_mm``     — pin hole diameter (typically 5mm).
      * ``depth_mm``        — blind-hole depth (typically 8mm; through
        holes weaken side panels).
      * ``front_offset_mm`` — X distance from the front edge of the side
        panel to the front pin row.
      * ``back_offset_mm``  — X distance from the back edge of the side
        panel to the back pin row.
      * ``max_per_row``     — maximum drillable pin positions along the
        vertical axis per shelf row per side. Typically 3 (two used,
        one optional). Actual quantity used per shelf is computed by the
        catalog decomposer (2 pins per side × 2 sides = 4 per shelf).
    """
    diameter_mm: float = 5.0
    depth_mm: float = 8.0
    front_offset_mm: float = 50.0
    back_offset_mm: float = 80.0
    max_per_row: int = 3


@dataclass
class HandleSpec:
    """Handle specification for a cabinet's front-facing pulls (ADR-012 §4).

    Replaces the loose ``handles: dict`` field that previously lived on
    ``CabinetInstance``. All values English (AGENTS.md rule); YAML loader
    translates Polish keys/values (e.g. ``typ: relingowy`` → ``type: 'bar'``).

    Fields:
      * ``type``             — ``"bar"`` | ``"knob"`` | ``"profile"`` | ``"recessed"``
      * ``spacing_mm``       — centre-to-centre distance between the two
        mounting screws ("rozstaw" in Polish).
      * ``hole_diameter_mm`` — pilot hole diameter for the mounting screws.
      * ``position``         — ``"center"`` | ``"top"`` | ``"bottom"``
        (vertical position of the handle on the front panel).
    """
    type: str = "bar"
    spacing_mm: float = 128.0
    hole_diameter_mm: float = 5.0
    position: str = "center"


# ── ADR-012 §6 — Discriminated cabinet-type config ──────────────
#
# Today ``CabinetInstance.type`` is a free string and variant-specific data
# lives in loose ``list[dict]`` fields (``drawers``, ``shelves``, ``fronts``).
# The seven dataclasses below give each cabinet variant a typed config; the
# loader synthesises one from the loose fields until every caller migrates.
#
# Naming follows the AGENTS.md rule: English fields, ``_mm`` suffix on
# millimetre quantities. Loader remains the Polish → English adapter.
#
# Discrimination is done by the concrete dataclass (``isinstance`` on the
# ``config`` attribute); no explicit ``type: Literal[...]`` field is needed
# — that keeps the model plain-dataclass and avoids the Pydantic tag pattern
# used by ``kitchen_cam.models``. All fields have safe defaults so a variant
# can be constructed with no arguments, and equality is structural.


@dataclass
class DrawerSlot:
    """One drawer within a base-drawer / sink-sorting configuration.

    Mirrors the shape of the legacy ``CabinetInstance.drawers`` dict entries
    (``id``, ``typ``, ``wysokosc`` …) but with English field names. Runner
    system is a free string so kitchen-cam can extend the vocabulary
    without a core dependency inversion (same rationale as
    ``MachiningOp.drill_type``).
    """
    id: str = ""
    system: str = "tandembox_antaro"
    height_mm: float = 0.0
    height_code: str = "M"
    nl_mm: float = 500.0
    capacity_kg: float = 40.0


@dataclass
class BaseDoorConfig:
    """Standard base or wall cabinet with doors + optional shelves."""
    shelves: list[float] = field(default_factory=list)  # positions from inside bottom (mm)
    doors: list[int] = field(default_factory=list)      # hinge count per door


@dataclass
class BaseDrawerConfig:
    """Base cabinet whose interior is a stack of drawers (Tandembox/LEGRABOX)."""
    drawers: list[DrawerSlot] = field(default_factory=list)


@dataclass
class CornerBlindConfig:
    """Corner cabinet with a blind front (L-shaped body)."""
    corner_side: str = "left"        # "left" | "right"
    second_width_mm: float = 0.0     # perpendicular width of the corner leg
    shelves: list[float] = field(default_factory=list)
    doors: list[int] = field(default_factory=list)


@dataclass
class CornerInternalConfig:
    """Corner internal cabinet with a diagonal back and a rotating carousel."""
    carousel: str = "optima_800"     # "optima_800" | "optima_900"
    shelves: list[float] = field(default_factory=list)
    doors: list[int] = field(default_factory=list)


@dataclass
class SinkConfig:
    """Sink base cabinet — no shelves, optional sorting drawer."""
    has_sorting_drawer: bool = False
    sorting_drawer: DrawerSlot | None = None
    doors: list[int] = field(default_factory=list)


@dataclass
class CargoConfig:
    """Base cabinet with a pull-out cargo basket (rail hardware)."""
    cargo_type: str = "mini_40"      # e.g. Blum VARIANT MULTI 40cm
    cargo_colour: str = "ocynk"      # "ocynk" | "bialy" | "grafit"
    doors: list[int] = field(default_factory=list)


@dataclass
class OvenConfig:
    """Tall oven-housing cabinet with a reinforced fixed shelf."""
    cavity_height_mm: float = 0.0
    has_ventilation: bool = True
    reinforced_shelf: bool = True


#: Discriminated union of every cabinet-config variant. Downstream code
#: dispatches with ``isinstance``; the concrete class IS the discriminator.
CabinetConfig = Union[
    BaseDoorConfig,
    BaseDrawerConfig,
    CornerBlindConfig,
    CornerInternalConfig,
    SinkConfig,
    CargoConfig,
    OvenConfig,
]


@dataclass
class Accessory:
    """A hardware item — not cut from board, purchased as-is."""
    id: str
    name: str
    type: str              # "hinge", "runner", "shelf_pin", "handle"
    quantity: int = 1
    unit_price: float = 0.0


@dataclass
class CabinetInstance:
    """A configured cabinet — loaded from YAML, ready for decomposition.

    This is the DESIGN-level description. It knows nothing about panels.
    The catalog / construction method turns it into panels.
    """
    id: str
    type: str              # "dolna_szufladowa", "gorna_drzwiowa"
    description: str
    width_mm: int
    height_mm: int
    depth_mm: int

    # Materials (codes referencing external catalog)
    body_material: str
    back_material: str
    front_material: str

    # Thicknesses
    thickness_side_mm: int = 18
    thickness_shelf_mm: int = 18
    thickness_bottom_mm: int = 18
    thickness_back_mm: int = 3
    thickness_front_mm: int = 18

    # Back panel construction
    back_type: str = "wpuszczane_w_nut"
    groove_depth_mm: int = 8

    # Edge banding (global default for this cabinet)
    edge_banding_type: str = "ABS"
    edge_banding_thickness_mm: float = 0.8

    # Plinth / legs
    plinth_height_mm: int = 100

    # Interior elements
    drawers: list[dict] = field(default_factory=list)
    shelves: list[dict] = field(default_factory=list)
    fronts: list[dict] = field(default_factory=list)
    handles: HandleSpec | None = None   # ADR-012 §4 — typed replacement for former dict
    shelf_pins: ShelfPinSpec = field(default_factory=ShelfPinSpec)  # ADR-012 §5
    # ADR-012 §6 — typed variant config. Legacy loose fields above stay
    # until callers migrate; ``loader._synthesise_config`` populates this
    # from them on load. Directly-constructed instances (tests, code) may
    # set it explicitly or leave it ``None``.
    config: CabinetConfig | None = None

    def __post_init__(self) -> None:
        """Validate dimensions after construction."""
        errors = self.validate()
        if errors:
            raise ValueError(
                f"Invalid CabinetInstance '{self.id}': {'; '.join(errors)}"
            )

    def validate(self) -> list[str]:
        """Check dimensional sanity.  Returns list of error messages (empty if valid)."""
        errors: list[str] = []
        if self.width_mm <= 0:
            errors.append(f"width_mm must be > 0, got {self.width_mm}")
        if self.height_mm <= 0:
            errors.append(f"height_mm must be > 0, got {self.height_mm}")
        if self.depth_mm <= 0:
            errors.append(f"depth_mm must be > 0, got {self.depth_mm}")
        if self.thickness_side_mm <= 0:
            errors.append(f"thickness_side_mm must be > 0, got {self.thickness_side_mm}")
        # Check that internal width is positive
        internal_w = self.width_mm - 2 * self.thickness_side_mm
        if internal_w <= 0:
            errors.append(
                f"Internal width would be {internal_w}mm. "
                f"Increase width_mm or reduce thickness_side_mm."
            )
        return errors


@dataclass
class DecompositionResult:
    """Output of decomposing one cabinet into physical parts."""
    cabinet_id: str
    cabinet_type: str
    panels: list[Panel] = field(default_factory=list)
    accessories: list[Accessory] = field(default_factory=list)


# ── Kitchen-level models ────────────────────────────────────────


@dataclass
class Row:
    """A row of cabinets along one wall."""
    id: str
    label: str               # "Ściana północna"
    wall_width_mm: int
    wall_height_mm: int
    cabinets: list[CabinetInstance] = field(default_factory=list)

    def used_width_mm(self) -> float:
        """Total width of all cabinets placed in this row."""
        return sum(c.width_mm for c in self.cabinets)

    def remaining_mm(self) -> float:
        """Free space left in the row."""
        return self.wall_width_mm - self.used_width_mm()


class GrainAxis:
    """Constants for board grain direction."""
    WIDTH = "width"   # grain runs along width_mm
    HEIGHT = "height"  # grain runs along height_mm


@dataclass
class WorktopSegment:
    """A worktop segment covering one row.

    Simple rectangle for now.  L-shapes and cutouts come in CAM stage.
    """
    row_id: str
    length_mm: float
    depth_mm: float = 600
    thickness_mm: int = 40
    material: str = ""


@dataclass
class Kitchen:
    """Top-level kitchen — the unit of work flowing through the whole system.

    This is what gets serialized to intermediate JSON,
    sent to the render backend, and consumed by the CLI.
    """
    version: str = "1.0"
    project_name: str = ""
    created: str = ""
    rows: list[Row] = field(default_factory=list)
    worktops: list[WorktopSegment] = field(default_factory=list)
