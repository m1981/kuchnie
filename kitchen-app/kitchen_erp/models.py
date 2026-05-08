# kitchen_erp/models.py
from sqlmodel import SQLModel, Field, Relationship
from kitchen_erp.schemas import CabinetCostResult


class Material(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    brand: str | None = None      # NEW: e.g., "Egger", "Krono"
    category: str | None = None   # NEW: e.g., "Board", "Edge", "Back"
    price_per_unit: float
    unit: str


class HardwareSet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    brand: str | None = None      # NEW: e.g., "Blum", "Hettich"
    price_per_set: float

class ProjectDefaults(SQLModel, table=True):
    # Primary Key is also a Foreign Key to Project (1-to-1 relationship)
    project_id: int = Field(foreign_key="project.id", primary_key=True, ondelete="CASCADE")

    # Foreign Keys
    corpus_mat_id: int = Field(foreign_key="material.id")
    front_mat_id: int = Field(foreign_key="material.id")
    back_mat_id: int = Field(foreign_key="material.id")
    edge_band_mat_id: int = Field(foreign_key="material.id")
    hinge_sys_id: int = Field(foreign_key="hardwareset.id")
    drawer_sys_id: int = Field(foreign_key="hardwareset.id")

    # Relationships (Navigation properties)
    project: "Project" = Relationship(back_populates="defaults")

    corpus_mat: Material = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.corpus_mat_id]"})
    front_mat: Material = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.front_mat_id]"})
    back_mat: Material = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.back_mat_id]"})
    edge_band_mat: Material = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.edge_band_mat_id]"})
    hinge_sys: HardwareSet = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.hinge_sys_id]"})
    drawer_sys: HardwareSet = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.drawer_sys_id]"})

class Cabinet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", ondelete="CASCADE")

    name: str
    type: str
    width_mm: float
    height_mm: float
    depth_mm: float
    door_count: int = 0
    drawer_count: int = 0

    # NEW: Keep track of the order in the row
    order_index: int = 0

    # Local Overrides (Nullable Foreign Keys)
    override_front_mat_id: int | None = Field(default=None, foreign_key="material.id")
    override_corpus_mat_id: int | None = Field(default=None, foreign_key="material.id")

    # Relationships
    project: "Project" = Relationship(back_populates="cabinets")
    override_front_mat: Material | None = Relationship(sa_relationship_kwargs={"foreign_keys": "[Cabinet.override_front_mat_id]"})
    override_corpus_mat: Material | None = Relationship(sa_relationship_kwargs={"foreign_keys": "[Cabinet.override_corpus_mat_id]"})

    def calculate_cost(self, defaults: ProjectDefaults, waste_factor: float) -> CabinetCostResult:
        """Calculates cost using relationships. Assumes relationships are loaded."""

        # Fallback Pattern: Use override if it exists, otherwise use project default
        active_front = self.override_front_mat or defaults.front_mat
        active_corpus = self.override_corpus_mat or defaults.corpus_mat

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
            (corpus_area_m2 * active_corpus.price_per_unit * waste_factor) +
                (back_area_m2 * defaults.back_mat.price_per_unit * waste_factor) +
            (front_area_m2 * active_front.price_per_unit * waste_factor) +
            (edge_length_m * defaults.edge_band_mat.price_per_unit)
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

class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    customer_name: str
    waste_factor: float = 1.20
    labor_markup: float = 1.50

    # Relationships
    # cascade_delete=True ensures if we delete a project, its cabinets and defaults vanish too.
    cabinets: list[Cabinet] = Relationship(back_populates="project", cascade_delete=True)
    defaults: ProjectDefaults | None = Relationship(back_populates="project", cascade_delete=True)