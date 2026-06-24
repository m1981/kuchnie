"""kuchnie-core: Kitchen cabinet decomposition engine."""

from .model import Panel, Accessory, CabinetInstance, DecompositionResult, EdgeBand
from .decomposer import decompose
from .bom import BOM, BOMItem, calculate_bom
from .loader import load_cabinet

__all__ = [
    "Panel", "Accessory", "CabinetInstance", "DecompositionResult", "EdgeBand",
    "decompose",
    "BOM", "BOMItem", "calculate_bom",
    "load_cabinet",
]
