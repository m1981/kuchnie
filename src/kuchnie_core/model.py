"""Core domain models.

The atomic manufacturing unit is the Panel — not the cabinet.
Everything above panels is organizational. Everything on panels
(edges, machining ops) is decoration on that physical piece.
"""

from dataclasses import dataclass, field


@dataclass
class MachiningOp:
    """A machining operation on a panel — drill, groove, rabbet, dado.

    Coordinate system (panel lying flat, viewed from the machined face):
      x_mm  = distance from LEFT edge of panel
      y_mm  = distance from BOTTOM edge of panel (front edge for carcass sides)
    """
    type: str              # "drill", "groove", "rabbet", "dado"
    x_mm: float = 0
    y_mm: float = 0
    diameter_mm: float = 0  # for drill/bore
    depth_mm: float = 0     # 0 = through hole
    width_mm: float = 0     # for groove/rabbet
    length_mm: float = 0    # for groove
    note: str = ""


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

    # Interior elements
    drawers: list[dict] = field(default_factory=list)
    shelves: list[dict] = field(default_factory=list)
    fronts: list[dict] = field(default_factory=list)
    handles: dict = field(default_factory=dict)

    # Plinth / legs
    plinth_height_mm: int = 100


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
