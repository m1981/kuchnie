# kitchen_erp/schemas.py
from pydantic import BaseModel, Field


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
