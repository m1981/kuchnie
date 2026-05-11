# kitchen_erp/models.py
from sqlmodel import SQLModel, Field, Relationship
from kitchen_erp.schemas import CabinetCostResult, CostTraceLine


class Material(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    brand: str | None = None      # NEW: e.g., "Egger", "Krono"
    category: str | None = None   # NEW: e.g., "Board", "Edge", "Back"
    price_per_unit: float
    unit: str
    sheet_size_m2: float = Field(default=5.796) # Domyślnie format 2800x2070
    has_woodgrain: bool = Field(default=False)  # Czy ma usłojenie (wymusza większy odpad na CNC)

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

    def calculate_cost(self, defaults: ProjectDefaults, waste_factor: float) -> CabinetCostResult:
        """
        LEGACY METHOD: Calculates cost using relationships. Assumes relationships are loaded.
        
        NOTE: This is the OLD cost calculation system. For new projects, use:
            from kitchen_erp.bom_generator import BOMGenerator
            generator = BOMGenerator(cabinet, defaults)
            bom_tree = generator.generate()
        
        This method is kept for backward compatibility during migration.
        See MIGRATION_GUIDE.md for details on switching to the new BOM system.
        """
        fixed_equipment = {
            "DISHWASHER", "OVEN", "COOKTOP", "HOOD", "SINK", "FAUCET",
            "APPLIANCE", "DECOR",
        }
        if self.module_kind in fixed_equipment:
            trace_line = CostTraceLine(
                category="Equipment",
                label=f"{self.name}: allowance",
                quantity=1,
                unit="pcs",
                unit_price=self.equipment_price,
                formula=f"1 pcs x {self.equipment_price:.2f}",
                subtotal=round(self.equipment_price, 2),
            )
            return CabinetCostResult(
                material_cost=0,
                hardware_cost=round(self.equipment_price, 2),
                total_cost=round(self.equipment_price, 2),
                trace_lines=[trace_line],
            )

        if self.module_kind == "COUNTERTOP":
            worktop_area_m2 = (self.width_mm * self.depth_mm) / 1_000_000
            worktop_cost = worktop_area_m2 * self.equipment_price
            trace_line = CostTraceLine(
                category="Material",
                label=f"{self.name}: worktop slab",
                quantity=round(worktop_area_m2, 4),
                unit="m2",
                unit_price=self.equipment_price,
                formula=f"{worktop_area_m2:.4f} m2 x {self.equipment_price:.2f}",
                subtotal=round(worktop_cost, 2),
            )
            return CabinetCostResult(
                material_cost=round(worktop_cost, 2),
                hardware_cost=0,
                total_cost=round(worktop_cost, 2),
                trace_lines=[trace_line],
            )

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
        corpus_cost = corpus_area_m2 * active_corpus.price_per_unit * waste_factor
        back_cost = back_area_m2 * defaults.back_mat.price_per_unit * waste_factor
        front_cost = front_area_m2 * active_front.price_per_unit * waste_factor
        edge_cost = edge_length_m * defaults.edge_band_mat.price_per_unit
        mat_cost = corpus_cost + back_cost + front_cost + edge_cost

        trace_lines = [
            CostTraceLine(
                category="Material",
                label=f"Corpus board: {active_corpus.brand or 'Generic'} {active_corpus.name}",
                quantity=round(corpus_area_m2, 4),
                unit=active_corpus.unit,
                unit_price=active_corpus.price_per_unit,
                waste_factor=waste_factor,
                formula=f"{corpus_area_m2:.4f} {active_corpus.unit} x {active_corpus.price_per_unit:.2f} x {waste_factor:.2f}",
                subtotal=round(corpus_cost, 2),
            ),
            CostTraceLine(
                category="Material",
                label=f"Back panel: {defaults.back_mat.brand or 'Generic'} {defaults.back_mat.name}",
                quantity=round(back_area_m2, 4),
                unit=defaults.back_mat.unit,
                unit_price=defaults.back_mat.price_per_unit,
                waste_factor=waste_factor,
                formula=f"{back_area_m2:.4f} {defaults.back_mat.unit} x {defaults.back_mat.price_per_unit:.2f} x {waste_factor:.2f}",
                subtotal=round(back_cost, 2),
            ),
            CostTraceLine(
                category="Material",
                label=f"Fronts: {active_front.brand or 'Generic'} {active_front.name}",
                quantity=round(front_area_m2, 4),
                unit=active_front.unit,
                unit_price=active_front.price_per_unit,
                waste_factor=waste_factor,
                formula=f"{front_area_m2:.4f} {active_front.unit} x {active_front.price_per_unit:.2f} x {waste_factor:.2f}",
                subtotal=round(front_cost, 2),
            ),
            CostTraceLine(
                category="Material",
                label=f"Edge banding: {defaults.edge_band_mat.brand or 'Generic'} {defaults.edge_band_mat.name}",
                quantity=round(edge_length_m, 4),
                unit=defaults.edge_band_mat.unit,
                unit_price=defaults.edge_band_mat.price_per_unit,
                formula=f"{edge_length_m:.4f} {defaults.edge_band_mat.unit} x {defaults.edge_band_mat.price_per_unit:.2f}",
                subtotal=round(edge_cost, 2),
            ),
        ]

        # 3. Hardware Cost
        hinges_per_door = 2
        if self.height_mm > 1600:
            hinges_per_door = 4
        elif self.height_mm > 900:
            hinges_per_door = 3

        total_hinges = hinges_per_door * self.door_count
        hinge_cost = total_hinges * defaults.hinge_sys.price_per_set
        drawer_cost = self.drawer_count * defaults.drawer_sys.price_per_set
        hw_cost = hinge_cost + drawer_cost
        trace_lines.extend([
            CostTraceLine(
                category="Hardware",
                label=f"Hinges: {defaults.hinge_sys.brand or 'Generic'} {defaults.hinge_sys.name}",
                quantity=total_hinges,
                unit="pcs",
                unit_price=defaults.hinge_sys.price_per_set,
                formula=f"{self.door_count} doors x {hinges_per_door} hinges x {defaults.hinge_sys.price_per_set:.2f}",
                subtotal=round(hinge_cost, 2),
            ),
            CostTraceLine(
                category="Hardware",
                label=f"Drawers: {defaults.drawer_sys.brand or 'Generic'} {defaults.drawer_sys.name}",
                quantity=self.drawer_count,
                unit="sets",
                unit_price=defaults.drawer_sys.price_per_set,
                formula=f"{self.drawer_count} drawers x {defaults.drawer_sys.price_per_set:.2f}",
                subtotal=round(drawer_cost, 2),
            ),
        ])

        return CabinetCostResult(
            material_cost=round(mat_cost, 2),
            hardware_cost=round(hw_cost, 2),
            total_cost=round(mat_cost + hw_cost, 2),
            trace_lines=trace_lines,
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
        from kitchen_erp.bom_generator import BOMGenerator
        from kitchen_erp.purchasing import get_strategy_for_material
        
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
