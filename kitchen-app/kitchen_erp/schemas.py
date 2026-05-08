# kitchen_erp/schemas.py
from pydantic import BaseModel

class CabinetCostResult(BaseModel):
    material_cost: float
    hardware_cost: float
    total_cost: float