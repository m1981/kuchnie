# kitchen_erp/models.py
from typing import Optional
from sqlmodel import SQLModel, Field
from kitchen_erp.schemas import CabinetCostResult


class Material(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price_per_unit: float
    unit: str


class HardwareSet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price_per_set: float


class ProjectDefaults(SQLModel):
    # Note: Not a table yet, just a data structure for our calculation logic
    corpus_mat: Material
    front_mat: Material
    back_mat: Material
    edge_band_mat: Material
    hinge_sys: HardwareSet
    drawer_sys: HardwareSet


class Cabinet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str
    width_mm: float
    height_mm: float
    depth_mm: float
    door_count: int = 0
    drawer_count: int = 0

    def calculate_cost(self, defaults: ProjectDefaults, waste_factor: float) -> CabinetCostResult:
        # 1. Area Calculations (mm2 to m2)
        corpus_area_m2 = ((2 * self.height_mm * self.depth_mm) +
                          (2 * self.width_mm * self.depth_mm)) / 1_000_000
        back_area_m2 = (self.height_mm * self.width_mm) / 1_000_000
        front_area_m2 = (
                                    self.height_mm * self.width_mm) / 1_000_000 if self.door_count > 0 or self.drawer_count > 0 else 0

        # Edge Banding (mm to linear meters)
        edge_length_m = ((self.height_mm * 2 + self.width_mm * 2) * 2) / 1000

        # 2. Material Cost
        mat_cost = (
                (corpus_area_m2 * defaults.corpus_mat.price_per_unit * waste_factor) +
                (back_area_m2 * defaults.back_mat.price_per_unit * waste_factor) +
                (front_area_m2 * defaults.front_mat.price_per_unit * waste_factor) +
                (edge_length_m * defaults.edge_band_mat.price_per_unit)  # No waste on edge banding
        )

        # 3. Hardware Cost
        hinges_per_door = 2
        if self.height_mm > 1600:
            hinges_per_door = 4
        elif self.height_mm > 900:
            hinges_per_door = 3

        total_hinges = hinges_per_door * self.door_count
        hw_cost = (total_hinges * defaults.hinge_sys.price_per_set) + (
                    self.drawer_count * defaults.drawer_sys.price_per_set)

        return CabinetCostResult(
            material_cost=round(mat_cost, 2),
            hardware_cost=round(hw_cost, 2),
            total_cost=round(mat_cost + hw_cost, 2)
        )