"""Core domain models.

The atomic manufacturing unit is the Panel — not the cabinet.
Everything above panels is organizational. Everything on panels
(edges, machining ops) is decoration on that physical piece.
"""

from dataclasses import dataclass, field


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
