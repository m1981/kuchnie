# kitchen_erp/core/models.py
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship

# Project/Order spine (wk-02a62298): stage vocabulary is the L1 process
# stage list in docs/specs/process-coverage.md, in pipeline order. Stage 10
# (Delivery & installation) is "out, permanent" per that spec, so it is not
# a stage a Project can occupy — the sequence skips 9 -> 11.
STAGE_SEQUENCE: list[str] = [
    "1_first_visit",       # First visit (decors) -- krono-compositor-mvp + catalog
    "2_pomiar",             # Pomiar -- kitchen-erp project record, attachments only
    "3_layout_design",      # Layout & design -- home_builder_5 / home-builder-adapter
    "4_decomposition",      # Decomposition -- kuchnie-core
    "5_purchasing",         # Purchasing -- kitchen-erp (rozrys CSV, board/hardware orders)
    "6_cutting_edging",     # Cutting & edging -- external service
    "7_cam_drilling",       # CAM / drilling -- kitchen-cam
    "8_assembly_outputs",   # Assembly outputs -- kitchen-cam
    "9_worktops",           # Worktops -- kuchnie-core BOM + catalog
    "11_handover_archive",  # Handover archive -- kitchen-erp project record
]

STAGE_LABELS: dict[str, str] = {
    "1_first_visit": "First visit (decors)",
    "2_pomiar": "Pomiar",
    "3_layout_design": "Layout & design",
    "4_decomposition": "Decomposition",
    "5_purchasing": "Purchasing",
    "6_cutting_edging": "Cutting & edging",
    "7_cam_drilling": "CAM / drilling",
    "8_assembly_outputs": "Assembly outputs",
    "9_worktops": "Worktops",
    "11_handover_archive": "Handover archive",
}

DEFAULT_STAGE = STAGE_SEQUENCE[0]


class StageTransitionError(ValueError):
    """Raised by Project.transition_stage for an unknown stage or a
    backward/no-op move. This is the only sanctioned way to change
    Project.stage -- nothing else should assign it directly."""


class Material(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    brand: str | None = None      # NEW: e.g., "Egger", "Krono"
    category: str | None = None   # NEW: e.g., "Board", "Edge", "Back"
    price_per_unit: float
    unit: str
    sheet_size_m2: float = Field(default=5.796) # Domyślnie format 2800x2070
    has_woodgrain: bool = Field(default=False)  # Czy ma usłojenie (wymusza większy odpad na CNC)
    # Mirror key (ADR-011 phase 3): set = identity owned by the catalog
    # service (material_mirror converges it); NULL = local-born row
    # (admin UI / utility), never touched by the mirror.
    catalog_variant_id: str | None = Field(default=None, index=True)

class HardwareSet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    brand: str | None = None      # NEW: e.g., "Blum", "Hettich"
    price_per_set: float


class HardwareRule(SQLModel, table=True):
    """Tag-based hardware rules for automatic component addition"""
    id: int | None = Field(default=None, primary_key=True)
    tag: str  # e.g., "is_base", "has_doors"
    hardware_name: str  # e.g., "Cabinet legs", "Door hinges"
    qty_per_unit: int  # How many per cabinet/door/drawer
    unit: str  # "pcs", "sets"
    price: float  # Price per unit
    description: str | None = None  # Optional description

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
    module_kind: str = "BASE_CABINET"
    x_mm: float = 0
    y_mm: float = 0
    equipment_price: float = 0

    # NEW: Keep track of the order in the row
    order_index: int = 0

    # Local Overrides (Nullable Foreign Keys)
    override_front_mat_id: int | None = Field(default=None, foreign_key="material.id")
    override_corpus_mat_id: int | None = Field(default=None, foreign_key="material.id")

    # Relationships
    project: "Project" = Relationship(back_populates="cabinets")
    override_front_mat: Material | None = Relationship(sa_relationship_kwargs={"foreign_keys": "[Cabinet.override_front_mat_id]"})
    override_corpus_mat: Material | None = Relationship(sa_relationship_kwargs={"foreign_keys": "[Cabinet.override_corpus_mat_id]"})
    
    @property
    def has_custom_front(self) -> bool:
        """
        Check if this cabinet should have custom front material.
        
        Used by BOM generator to determine if front material should be included.
        Returns False for equipment-only cabinets.
        """
        fixed_equipment = {
            "DISHWASHER", "OVEN", "COOKTOP", "HOOD", "SINK", "FAUCET",
            "APPLIANCE", "DECOR", "COUNTERTOP"
        }
        return self.module_kind not in fixed_equipment
    
    @property
    def local_front_mat(self) -> Material | None:
        """
        Get the front material for this cabinet (override or None).
        
        Used by BOM generator. If None, generator will use project defaults.
        """
        return self.override_front_mat

class ArtifactRef(SQLModel, table=True):
    """A reference to an artifact produced along the spine (stages 1-11):
    rozrys CSV, BOM export, CNC program, offer PDF, etc. `path` holds a
    filesystem path or an external id/URL -- this table never stores the
    artifact bytes themselves."""
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", ondelete="CASCADE")
    kind: str  # e.g. "rozrys_csv", "bom", "cnc_program", "offer_pdf"
    path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: "Project" = Relationship(back_populates="artifact_refs")


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    customer_name: str
    waste_factor: float = 1.20
    labor_markup: float = 1.50

    # Project/Order spine (wk-02a62298)
    stage: str = Field(default=DEFAULT_STAGE)

    # Customer contact, beyond the bare customer_name
    customer_email: str | None = None
    customer_phone: str | None = None
    customer_address: str | None = None

    # Lifecycle dates -- all nullable; created_at auto-stamps at creation,
    # the rest are set explicitly as the project moves through the spine.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    quoted_at: datetime | None = None
    ordered_at: datetime | None = None
    production_at: datetime | None = None
    installed_at: datetime | None = None

    # Relationships
    # cascade_delete=True ensures if we delete a project, its cabinets and defaults vanish too.
    cabinets: list[Cabinet] = Relationship(back_populates="project", cascade_delete=True)
    defaults: ProjectDefaults | None = Relationship(back_populates="project", cascade_delete=True)
    artifact_refs: list[ArtifactRef] = Relationship(back_populates="project", cascade_delete=True)

    def transition_stage(self, new_stage: str) -> None:
        """Move the project forward to `new_stage` in STAGE_SEQUENCE order.

        Raises StageTransitionError for an unknown stage id or any
        backward/no-op move -- stage only ever advances, and only through
        this method (no UI or caller may assign .stage directly).
        """
        if new_stage not in STAGE_SEQUENCE:
            raise StageTransitionError(f"unknown stage: {new_stage!r}")
        current_idx = STAGE_SEQUENCE.index(self.stage)
        new_idx = STAGE_SEQUENCE.index(new_stage)
        if new_idx <= current_idx:
            raise StageTransitionError(
                f"cannot move from {self.stage!r} to {new_stage!r}: "
                "stage only advances forward"
            )
        self.stage = new_stage

    def add_artifact(self, kind: str, path: str) -> ArtifactRef:
        """Record an artifact reference for this project (rozrys CSV, BOM,
        CNC program, offer PDF, ...). Caller is responsible for
        session.add()/commit() when persistence is desired."""
        return ArtifactRef(project=self, kind=kind, path=path)

    def generate_project_bom(self):
        """
        Generate complete BOM for entire project using new BOM generator system.
        
        This method demonstrates the new architecture:
        1. Generates BOM tree for each cabinet
        2. Aggregates materials across all cabinets
        3. Applies purchasing strategies (full sheets, rolls, etc.)
        4. Returns project-level cost breakdown
        
        Returns:
            dict with keys:
                - total_cost: float
                - material_cost: float
                - hardware_cost: float
                - bom_trees: list of (cabinet_name, BOMAssembly) tuples
                - aggregated_materials: dict of aggregated material quantities
        
        Example:
            project = session.get(Project, project_id)
            result = project.generate_project_bom()
            print(f"Total project cost: ${result['total_cost']:.2f}")
        """
        from .bom_generator import BOMGenerator
        from .purchasing import get_strategy_for_material
        
        if not self.defaults:
            raise ValueError("Project has no defaults configured")
        
        # Generate BOM trees for all cabinets
        bom_trees = []
        for cabinet in self.cabinets:
            generator = BOMGenerator(cabinet, self.defaults)
            bom_tree = generator.generate()
            bom_trees.append((cabinet.name or cabinet.module_kind, bom_tree))
        
        # Aggregate materials
        material_aggregation = {}
        hardware_aggregation = {}
        
        for cab_name, bom_tree in bom_trees:
            for part in bom_tree.get_all_parts():
                if part.material_id:
                    # Material with database ID
                    key = (part.material_id, part.unit)
                    if key not in material_aggregation:
                        material_aggregation[key] = {
                            "name": part.name,
                            "quantity_net": 0,
                            "unit": part.unit,
                            "unit_price": part.unit_price,
                            "material_id": part.material_id
                        }
                    material_aggregation[key]["quantity_net"] += part.quantity_net
                else:
                    # Hardware without material_id
                    if part.name not in hardware_aggregation:
                        hardware_aggregation[part.name] = {
                            "quantity_net": 0,
                            "unit": part.unit,
                            "unit_price": part.unit_price
                        }
                    hardware_aggregation[part.name]["quantity_net"] += part.quantity_net
        
        # Apply purchasing strategies
        total_material_cost = 0.0
        for (mat_id, unit), data in material_aggregation.items():
            # Get material category from database
            # Note: In real usage, you'd need a session here
            # This is just a demonstration of the concept
            material_category = "Board"  # Placeholder
            
            strategy = get_strategy_for_material(material_category)
            purchase_qty = strategy.calculate_purchase_quantity(data["quantity_net"])
            waste_factor = strategy.get_waste_factor(data["quantity_net"])
            
            cost = purchase_qty * data["unit_price"]
            total_material_cost += cost
            
            data["quantity_purchase"] = purchase_qty
            data["waste_factor"] = waste_factor
            data["cost"] = cost
        
        # Calculate hardware cost
        total_hardware_cost = 0.0
        for name, data in hardware_aggregation.items():
            cost = data["quantity_net"] * data["unit_price"]
            total_hardware_cost += cost
            data["cost"] = cost
        
        return {
            "total_cost": total_material_cost + total_hardware_cost,
            "material_cost": total_material_cost,
            "hardware_cost": total_hardware_cost,
            "bom_trees": bom_trees,
            "aggregated_materials": material_aggregation,
            "aggregated_hardware": hardware_aggregation
        }
