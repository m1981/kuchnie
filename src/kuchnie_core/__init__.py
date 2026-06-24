"""kuchnie-core: Kitchen cabinet decomposition engine."""

from .model import (
    Accessory,
    CabinetInstance,
    DecompositionResult,
    EdgeBand,
    Kitchen,
    Panel,
    Row,
    WorktopSegment,
)
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

__all__ = [
    # Models
    "Panel", "Accessory", "CabinetInstance", "DecompositionResult", "EdgeBand",
    "Kitchen", "Row", "WorktopSegment",
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
]
