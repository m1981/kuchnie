"""kuchnie-core: Kitchen cabinet decomposition engine."""

from .model import (
    Accessory,
    BaseDoorConfig,
    BaseDrawerConfig,
    CabinetConfig,
    CabinetInstance,
    CargoConfig,
    CornerBlindConfig,
    CornerInternalConfig,
    CornerLink,
    DecompositionResult,
    DrawerSlot,
    EdgeBand,
    HandleSpec,
    Kitchen,
    OvenConfig,
    Panel,
    PanelRole,
    Row,
    Run,
    ShelfPinSpec,
    SinkConfig,
    WorktopSegment,
    direction_after_turn,
)
from .construction import ConstructionMethod, ConstructionMethodRegistry
from .blum_drawers import DrawerSystem, DrawerSystemFactory, TandemboxAntaro, Merivobox, Legrabox
from .blum_hinges import BlumHinge, BlumClipTop110, BlumClipTop95, BlumClipTop155, HingeFactory, HingeGeometry, calculate_hinge_count
from .recipe import PanelRecipe, RecipeSchema, evaluate_formula, RecipeValidationError
from .decomposer import decompose
from .bom import BOM, BOMItem, calculate_bom, worktop_bom_items
from .loader import load_cabinet, load_kitchen
from .kitchen import (
    all_panels, all_accessories, kitchen_bom, validate_rows,
)
from .findings import ADVISORY, BLOCKING, Finding, GateStatus
from .buildability import (
    BuildabilityError,
    BuildabilityVerdict,
    GateResult,
    HeightSet,
    evaluate_buildability,
    require_buildable,
    row_findings,
)
from .serialize import (
    kitchen_to_dict,
    kitchen_to_json,
    kitchen_to_json_str,
    kitchen_from_dict,
    kitchen_from_json,
    kitchen_from_json_str,
)
from .export.cutlist_csv import export_cutlist_csv, aggregate_panels
from .export.edging_csv import export_edging_csv, collect_edging_rows
from .geometry import Vector2D, Vector3D, BoundingBox, Transform2D, mm_to_m
from .standards import KitchenStandards
from .types import Dimensions

__all__ = [
    # Models
    "Panel", "Accessory", "CabinetInstance", "DecompositionResult", "EdgeBand",
    "Kitchen", "Row", "WorktopSegment",
    # L-layout model (spec: kuchnie-core/docs/specs/l-layout-model.md, ADR-034)
    "Run", "CornerLink", "direction_after_turn",
    "PanelRole", "HandleSpec", "ShelfPinSpec",
    # ADR-012 §6 — discriminated cabinet-config union
    "CabinetConfig", "DrawerSlot",
    "BaseDoorConfig", "BaseDrawerConfig",
    "CornerBlindConfig", "CornerInternalConfig",
    "SinkConfig", "CargoConfig", "OvenConfig",
    # Construction
    "ConstructionMethod", "ConstructionMethodRegistry",
    # Blum drawer systems
    "DrawerSystem", "DrawerSystemFactory", "TandemboxAntaro", "Merivobox", "Legrabox",
    # Blum hinges
    "BlumHinge", "BlumClipTop110", "BlumClipTop95", "BlumClipTop155", "HingeFactory", "calculate_hinge_count",
    # Recipes (formulas as data)
    "PanelRecipe", "RecipeSchema", "evaluate_formula", "RecipeValidationError",
    # Engine
    "decompose",
    "BOM", "BOMItem", "calculate_bom", "worktop_bom_items",
    # Loaders
    "load_cabinet", "load_kitchen",
    # Kitchen-level
    "HeightSet",
    "all_panels", "all_accessories", "kitchen_bom", "row_findings", "validate_rows",
    # Buildability verdict (UC-2 step 5, wk-89a668a2)
    "ADVISORY", "BLOCKING", "BuildabilityError", "BuildabilityVerdict", "Finding",
    "GateResult", "GateStatus", "evaluate_buildability", "require_buildable",
    # Serialization (intermediate format)
    "kitchen_to_dict", "kitchen_to_json", "kitchen_to_json_str",
    "kitchen_from_dict", "kitchen_from_json", "kitchen_from_json_str",
    # Export
    "export_cutlist_csv", "aggregate_panels",
    "export_edging_csv", "collect_edging_rows",
    # Geometry (migrated from former kitchen-plugin, per ADR-009)
    "Vector2D", "Vector3D", "BoundingBox", "Transform2D", "mm_to_m",
    # Standards
    "KitchenStandards",
    # Types
    "Dimensions",
]
