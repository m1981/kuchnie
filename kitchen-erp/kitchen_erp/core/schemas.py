# kitchen_erp/schemas.py
from pydantic import BaseModel, Field
from typing import Literal


# BOM Tree Structure (Composite Pattern)
class BOMNode(BaseModel):
    """Base class for BOM tree nodes"""
    name: str
    cost: float = 0.0
    
    def calculate(self) -> float:
        """Calculate and return the cost of this node"""
        raise NotImplementedError


class BOMPart(BOMNode):
    """Leaf node representing a single material/hardware part"""
    material_id: int | None = None
    quantity_net: float
    unit: Literal["m2", "lm", "pcs", "sets"]
    unit_price: float
    waste_factor: float = 1.0
    
    def calculate(self) -> float:
        self.cost = self.quantity_net * self.unit_price * self.waste_factor
        return self.cost


class BOMAssembly(BOMNode):
    """Composite node representing a collection of parts/assemblies"""
    children: list[BOMNode] = Field(default_factory=list)
    
    def calculate(self) -> float:
        total = 0.0
        for child in self.children:
            total += child.calculate()
        self.cost = total
        return self.cost
    
    def add_child(self, child: BOMNode):
        self.children.append(child)
    
    def get_all_parts(self) -> list[BOMPart]:
        """Recursively collect all BOMPart nodes"""
        parts = []
        for child in self.children:
            if isinstance(child, BOMPart):
                parts.append(child)
            elif isinstance(child, BOMAssembly):
                parts.extend(child.get_all_parts())
        return parts


# Legacy cost trace structures (kept for backward compatibility)
class CostTraceLine(BaseModel):
    category: str
    label: str
    quantity: float
    unit: str
    unit_price: float
    subtotal: float
    formula: str
    waste_factor: float | None = None


class CabinetCostResult(BaseModel):
    material_cost: float
    hardware_cost: float
    total_cost: float
    trace_lines: list[CostTraceLine] = Field(default_factory=list)
