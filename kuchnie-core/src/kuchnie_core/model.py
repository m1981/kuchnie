"""Core domain models.

The atomic manufacturing unit is the Panel — not the cabinet.
Everything above panels is organizational. Everything on panels
(edges, machining ops) is decoration on that physical piece.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .blum_hinges import HingeGeometry


class PanelRole(str, Enum):
    """Structural role of a panel within the cabinet carcass.

    Per ADR-012 §1. Enables role-based filtering in downstream CAM
    ("apply hinge cups to FRONT_DOOR only", "drill runner holes on
    LEFT_SIDE / RIGHT_SIDE only") without string matching on
    user-facing Polish names like "Lewy bok".

    English values keep the model layer English-only (AGENTS.md rule
    "Model fields English, YAML keys Polish"). Drawer-box board parts
    (back/base cut for LEGRABOX/TANDEMBOX boxes) carry DRAWER_BACK /
    DRAWER_BASE so pricing can bucket them apart from carcass board
    (they are often a different material than the corpus).

    Value coverage in decomposers (ADR-012 §1, extended by ADR-013):
      * emitted by ``catalog.py``: LEFT_SIDE, RIGHT_SIDE, TOP (wieniec and
        trawersy), BOTTOM, SHELF, BACK, FRONT_DOOR, FRONT_DRAWER, PLINTH
        (cokół — emitted by ``dolna_legrabox`` since wk-c3d0a0f0),
        FRONT_BLIND + FILLER (corner-blind cabinets since wk-31467921 —
        both cut from front material, but FRONT_BLIND is FIXED: hinge cups
        and handle drilling must never target it)
      * emitted by ``legrabox.py`` / ``blum_drawers.py``: DRAWER_BACK,
        DRAWER_BASE
    """
    LEFT_SIDE    = "left_side"
    RIGHT_SIDE   = "right_side"
    BOTTOM       = "bottom"
    TOP          = "top"
    SHELF        = "shelf"
    BACK         = "back"
    FRONT_DOOR   = "front_door"
    FRONT_DRAWER = "front_drawer"
    FRONT_BLIND  = "front_blind"   # fixed blind front (zaślepka) at a corner
    FILLER       = "filler"        # listwa maskująca at the internal corner
    DRAWER_BACK  = "drawer_back"
    DRAWER_BASE  = "drawer_base"
    PLINTH       = "plinth"  # aspirational; see class docstring


@dataclass
class MachiningOp:
    """A machining operation on a panel — drill, groove, rabbet, dado.

    Coordinate system (panel lying flat, viewed from the machined face):
      x_mm  = distance from LEFT edge of panel
              (for carcass side panels this is the cabinet FRONT edge)
      y_mm  = distance from BOTTOM edge of panel

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
    catalog_edge_code: str = ""  # supplier SKU for ordering (e.g. "K-8685-SM/BS/PD")
    # Purchase-identity width (mm). Supplier/decor-dependent (e.g. Egger 23mm
    # vs Kronospan-partner 22mm for 18mm board) — NOT derived by core, so it
    # defaults to 0.0 ("unknown") and is only populated when a caller (e.g.
    # the ERP catalog layer) knows the specific supplier roll.
    width_mm: float = 0.0


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
    grain: str | None = None        # GrainAxis.WIDTH | GrainAxis.HEIGHT | None
                                    # None = no grain constraint (free rotation
                                    # at nesting; "brak" in the rozrys Usłojenie
                                    # column)


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
        | ``"edge_pull"`` (uchwyt krawędziowy — widens the front side-reveal
        to ConstructionMethod.front_reveal_edge_pull_mm, G12)
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
    filler_width_mm: float = 50.0    # listwa at the internal corner (50–100)
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
    edge_banding_thickness_mm: float = 0.8  # corpus/carcass — owner-confirmed
    front_edge_banding_thickness_mm: float = 2.0  # fronts — owner-confirmed

    # Plinth / legs
    plinth_height_mm: int = 100

    # Interior elements
    # CONTRACT: drawers are listed BOTTOM-UP — decomposers accumulate the
    # runner axis from the bottom panel upward (G8). Loaders normalize
    # declared top-down input and reject ambiguous unequal stacks
    # (loader._normalize_drawer_order); hand-built instances must honor
    # the bottom-up order themselves.
    drawers: list[dict] = field(default_factory=list)
    shelves: list[dict] = field(default_factory=list)
    fronts: list[dict] = field(default_factory=list)
    handles: HandleSpec | None = None   # ADR-012 §4 — typed replacement for former dict
    shelf_pins: ShelfPinSpec = field(default_factory=ShelfPinSpec)  # ADR-012 §5
    hinges: HingeGeometry | None = None  # drilling geometry for CAM stage (from blum_hinges)
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
    """A row of cabinets along one wall.

    In L-layout vocabulary this is a **Run** — the existing Row, now
    optionally aware of where it starts, ends and points (spec:
    kuchnie-core/docs/specs/l-layout-model.md, ADR-034). The layout
    fields are additive and default to ``None``: a flat Kitchen whose
    Rows carry no positions keeps loading, validating and decomposing
    exactly as before (spec invariant 4).

    Layout fields (mm, kitchen-plan coordinates — the validator's
    ``*_position_mm`` [x, y] pairs):

    * ``start_position_mm`` / ``end_position_mm`` — where the run
      starts and ends along its wall.
    * ``direction`` — one of ``east|north|west|south``.
    * ``turn`` — ``left|right``, set on the Run AFTER the corner
      (mirrors the manifest contract read by
      ``validator.check_run_continuity``).
    * ``corner_participation`` — which leg role this Run plays in the
      Kitchen's :class:`CornerLink` (``"leg_a"`` or ``"leg_b"``);
      ``None`` for a Run not meeting a corner.
    """
    id: str
    label: str               # "Ściana północna"
    wall_width_mm: int
    wall_height_mm: int
    cabinets: list[CabinetInstance] = field(default_factory=list)
    # ── L-layout additive fields (spec: l-layout-model.md) ──────
    start_position_mm: list[float] | None = None   # [x, y]
    end_position_mm: list[float] | None = None     # [x, y]
    direction: str | None = None                   # east|north|west|south
    turn: str | None = None                        # left|right, on the run after the corner
    corner_participation: str | None = None        # leg_a|leg_b

    def used_width_mm(self) -> float:
        """Total width of all cabinets placed in this row."""
        return sum(c.width_mm for c in self.cabinets)

    def remaining_mm(self) -> float:
        """Free space left in the row."""
        return self.wall_width_mm - self.used_width_mm()

    def usable_width_mm(self, corner: CornerLink | None = None) -> float:
        """Wall width minus this leg's corner consumption + filler.

        Derived, not stored (spec invariant 1: the corner consumes
        width from BOTH legs). Precondition: the Kitchen's corner link
        is resolved and passed in. Called without a corner — or for a
        Run the corner does not reference — it degrades to the plain
        wall width, which is exactly the invariant-1 violation shape
        the spec names for a leg that ignores its corner consumption.
        """
        if corner is None or self.id not in (corner.run_a_id, corner.run_b_id):
            return float(self.wall_width_mm)
        return float(
            self.wall_width_mm
            - (corner.consumed_mm(self.id) + corner.filler_mm(self.id))
        )


# Ubiquitous-language alias (spec: l-layout-model.md — "Run: one straight
# stretch of cabinets along one wall — the existing Row, now aware of
# where it starts"). Same class, so flat-Kitchen JSON stays byte-compatible.
Run = Row


class GrainAxis:
    """Constants for board grain direction."""
    WIDTH = "width"   # grain runs along width_mm
    HEIGHT = "height"  # grain runs along height_mm


@dataclass
class WorktopSegment:
    """A worktop segment covering one row.

    Simple rectangle for now.  L-shape geometry comes in CAM stage;
    cutouts are carried here by name only (zlew, plyta, ...) — enough to
    count and price them per piece, machining comes later.
    """
    row_id: str
    length_mm: float
    depth_mm: float = 600
    thickness_mm: int = 40
    material: str = ""
    cutouts: list[str] = field(default_factory=list)


# ── L-layout: turn table + corner link (spec: l-layout-model.md) ─

# Duplicated verbatim from kuchnie_core.validator.check_run_continuity
# (the mapping there is function-local, so it cannot be imported).
# KNOWN QUIRK — the table is DEGENERATE: for a given from-direction,
# "left" and "right" map to the SAME next direction (e.g. east+left AND
# east+right → south). Tracked as follow-up wk-075803aa (bd kuchnie-wcj).
# Spec invariant 3 requires the model to FOLLOW the validator's mapping
# as-is, so the quirk is conformed to here, not fixed.
TURNS: dict[tuple[str, str], str] = {
    ("east", "left"): "south",
    ("east", "right"): "south",
    ("north", "left"): "west",
    ("north", "right"): "west",
    ("west", "left"): "north",
    ("west", "right"): "north",
    ("south", "left"): "east",
    ("south", "right"): "east",
}


def direction_after_turn(direction: str, turn: str) -> str:
    """Next run direction per the validator's TURNS mapping (see the
    degeneracy note on ``TURNS`` — wk-075803aa)."""
    try:
        return TURNS[(direction, turn)]
    except KeyError:
        raise ValueError(
            f"Unknown direction/turn pair ({direction!r}, {turn!r}); "
            f"directions: east|north|west|south, turns: left|right"
        ) from None


@dataclass(frozen=True)
class CornerLink:
    """The record that two Runs meet at a corner (spec: l-layout-model.md).

    Carries which Runs, the corner cabinet, the strategy placeholder
    (``"blind"`` today — full strategy semantics belong to the Stage-2
    corner-strategy spec) and the filler + consumed width per leg
    (spec invariant 1: the corner consumes width from BOTH legs).

    Construct through :meth:`for_kitchen` so both Run ids are checked
    against the Kitchen (spec invariant 5); the bare constructor exists
    for deserialization of a dict that already passed that check.
    """
    run_a_id: str
    run_b_id: str
    corner_cabinet_id: str
    strategy: str = "blind"           # placeholder; Stage-2 spec owns semantics
    filler_a_mm: float = 0.0
    filler_b_mm: float = 0.0
    consumed_a_mm: float = 0.0
    consumed_b_mm: float = 0.0

    @classmethod
    def for_kitchen(
        cls,
        kitchen: Kitchen,
        *,
        run_a_id: str,
        run_b_id: str,
        corner_cabinet_id: str,
        strategy: str = "blind",
        filler_a_mm: float = 0.0,
        filler_b_mm: float = 0.0,
        consumed_a_mm: float = 0.0,
        consumed_b_mm: float = 0.0,
    ) -> CornerLink:
        """Validated construction: both Run ids must exist in the Kitchen
        (spec invariant 5 — a corner naming an absent Run id is refused)."""
        known = {r.id for r in kitchen.rows}
        for rid in (run_a_id, run_b_id):
            if rid not in known:
                raise ValueError(
                    f"CornerLink references unknown Run id {rid!r}; "
                    f"Kitchen has rows {sorted(known)}"
                )
        if run_a_id == run_b_id:
            raise ValueError(
                f"CornerLink must join two distinct Runs; got {run_a_id!r} "
                f"for both legs"
            )
        for name, width in (
            ("filler_a_mm", filler_a_mm), ("filler_b_mm", filler_b_mm),
            ("consumed_a_mm", consumed_a_mm), ("consumed_b_mm", consumed_b_mm),
        ):
            if width < 0:
                raise ValueError(
                    f"CornerLink {name} must be >= 0, got {width}"
                )
        return cls(
            run_a_id=run_a_id,
            run_b_id=run_b_id,
            corner_cabinet_id=corner_cabinet_id,
            strategy=strategy,
            filler_a_mm=filler_a_mm,
            filler_b_mm=filler_b_mm,
            consumed_a_mm=consumed_a_mm,
            consumed_b_mm=consumed_b_mm,
        )

    def _leg(self, run_id: str) -> str:
        if run_id == self.run_a_id:
            return "a"
        if run_id == self.run_b_id:
            return "b"
        raise ValueError(
            f"Run id {run_id!r} is not a leg of this corner "
            f"({self.run_a_id!r}, {self.run_b_id!r})"
        )

    def filler_mm(self, run_id: str) -> float:
        """Filler width on the given leg."""
        return self.filler_a_mm if self._leg(run_id) == "a" else self.filler_b_mm

    def consumed_mm(self, run_id: str) -> float:
        """Width the corner cabinet consumes on the given leg."""
        return self.consumed_a_mm if self._leg(run_id) == "a" else self.consumed_b_mm


@dataclass
class Kitchen:
    """Top-level kitchen — the unit of work flowing through the whole system.

    This is what gets serialized to intermediate JSON,
    sent to the render backend, and consumed by the CLI.

    L-layout additions (spec: l-layout-model.md, ADR-034 — additive,
    optional, default empty/None; the flat ``rows`` list stays the
    storage shape):

    * ``legs`` — ordered Run (Row) ids walking the layout, e.g.
      ``["run_a", "run_b"]`` for an L.
    * ``corner`` — the :class:`CornerLink` joining two legs, or ``None``.
    """
    version: str = "1.0"
    project_name: str = ""
    created: str = ""
    rows: list[Row] = field(default_factory=list)
    worktops: list[WorktopSegment] = field(default_factory=list)
    # ── L-layout additive fields (spec: l-layout-model.md) ──────
    legs: list[str] = field(default_factory=list)
    corner: CornerLink | None = None

    def run_by_id(self, run_id: str) -> Row:
        """Look up a Run (Row) by id; raises ``KeyError`` when absent."""
        for row in self.rows:
            if row.id == run_id:
                return row
        raise KeyError(f"Kitchen has no run {run_id!r}")

    def geometry_manifest(self) -> dict:
        """Emit the geometry-manifest dict the validator already checks.

        The output language is exactly the contract of
        ``validator.validate_manifest`` / ``check_run_continuity``
        (spec invariants 2 and 3): a ``layout.runs`` list whose entries
        carry ``index``, ``label``, ``start_position_mm``,
        ``end_position_mm``, ``direction`` and ``turn`` — the same run
        shape as the reference manifests
        (``home-builder-adapter/output/meshes/ref_*_manifest.json``).
        ``objects`` stays empty: this model carries plan-sheet layout,
        not meshes (ADR-034 — the adapter produces object geometry).

        Precondition (Operation-contracts table): the selected Runs
        carry positions + directions; a Run missing either raises
        ``ValueError`` naming it.
        """
        run_ids = self.legs if self.legs else [r.id for r in self.rows]
        runs: list[dict] = []
        total_cabinets = 0
        for index, run_id in enumerate(run_ids):
            row = self.run_by_id(run_id)
            if (row.start_position_mm is None or row.end_position_mm is None
                    or row.direction is None):
                raise ValueError(
                    f"Run {run_id!r} lacks positions/direction — "
                    f"geometry_manifest() needs start_position_mm, "
                    f"end_position_mm and direction on every emitted run"
                )
            total_cabinets += len(row.cabinets)
            runs.append({
                "label": row.label or row.id,
                "index": index,
                "direction": row.direction,
                "turn": row.turn,
                "start_position_mm": [float(v) for v in row.start_position_mm],
                "end_position_mm": [float(v) for v in row.end_position_mm],
                "total_width_mm": row.wall_width_mm,
                "cabinet_count": len(row.cabinets),
                "cabinets": [c.id for c in row.cabinets],
            })
        layout_type = "l_shape" if self.corner is not None else (
            "i_shape" if len(runs) == 1 else "multi_run"
        )
        return {
            "format": "geometry_manifest",
            "version": "1.0",
            "units": "mm",
            "settings": {},
            "layout": {
                "type": layout_type,
                "run_count": len(runs),
                "total_cabinets": total_cabinets,
                "runs": runs,
            },
            "objects": [],
        }
