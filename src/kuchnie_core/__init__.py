"""kuchnie-core: Kitchen cabinet decomposition engine."""

from .model import (
    Accessory,
    CabinetInstance,
    DecompositionResult,
    EdgeBand,
    HandleSpec,
    Kitchen,
    Panel,
    PanelRole,
    Row,
    ShelfPinSpec,
    WorktopSegment,
)
from .construction import ConstructionMethod, ConstructionMethodRegistry
from .blum_drawers import DrawerSystem, DrawerSystemFactory, TandemboxAntaro, Merivobox, Legrabox
from .blum_hinges import BlumHinge, BlumClipTop110, BlumClipTop95, BlumClipTop155, HingeFactory, HingeGeometry, calculate_hinge_count
from .recipe import PanelRecipe, RecipeSchema, evaluate_formula, RecipeValidationError
from .decomposer import decompose
from .bom import BOM, BOMItem, calculate_bom
from .loader import load_cabinet, load_kitchen
from .kitchen import all_panels, all_accessories, kitchen_bom, validate_rows
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
from .types import Direction, CabinetLevel, CabinetType, HandleType, DoorSide, Dimensions

__all__ = [
    # Models
    "Panel", "Accessory", "CabinetInstance", "DecompositionResult", "EdgeBand",
    "Kitchen", "Row", "WorktopSegment",
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
    "BOM", "BOMItem", "calculate_bom",
    # Loaders
    "load_cabinet", "load_kitchen",
    # Kitchen-level
    "all_panels", "all_accessories", "kitchen_bom", "validate_rows",
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
    "Direction", "CabinetLevel", "CabinetType", "HandleType", "DoorSide", "Dimensions",
]
