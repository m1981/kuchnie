"""BOM Generator - orchestrates recipe loading, rules engine, and cost calculation"""
from kitchen_erp.schemas import BOMAssembly, BOMPart
from kitchen_erp.recipe_loader import get_recipe, eval_formula
from kitchen_erp.rules_engine import RulesEngine
from kitchen_erp.models import Cabinet, ProjectDefaults


class BOMGenerator:
    """
    Generates Bill of Materials (BOM) tree for a cabinet using recipes and rules.
    
    This is the main orchestrator that:
    1. Loads the recipe for the cabinet type
    2. Evaluates formulas to calculate material quantities
    3. Applies rules engine to add hardware based on tags
    4. Builds a hierarchical BOM tree structure
    """
    
    def __init__(self, cabinet: Cabinet, defaults: ProjectDefaults):
        """
        Initialize BOM generator.
        
        Args:
            cabinet: Cabinet instance to generate BOM for
            defaults: Project defaults containing material/hardware prices
        """
        self.cabinet = cabinet
        self.defaults = defaults
        self.rules_engine = RulesEngine()
    
    def generate(self) -> BOMAssembly:
        """
        Generate complete BOM tree for the cabinet.
        
        Returns:
            BOMAssembly root node containing all materials and hardware
        """
        # Load recipe for this cabinet type
        recipe = get_recipe(self.cabinet.module_kind)
        
        # Create root assembly
        root = BOMAssembly(name=f"{self.cabinet.name or recipe['name']}")
        
        # Get cabinet dimensions for formula evaluation
        dims = {
            "width_mm": self.cabinet.width_mm,
            "height_mm": self.cabinet.height_mm,
            "depth_mm": self.cabinet.depth_mm
        }
        
        # 1. Add corpus materials based on formulas
        formulas = recipe.get("formulas", {})
        corpus_m2 = 0
        back_m2 = 0
        front_m2 = 0

        # 1. Materiały płytowe
        if "corpus_m2" in formulas:
            corpus_m2 = eval_formula(formulas["corpus_m2"], dims)
            if corpus_m2 > 0:
                root.add_child(BOMPart(
                    name=f"Corpus: {self.defaults.corpus_mat.name}",
                    material_id=self.defaults.corpus_mat.id,
                    quantity_net=corpus_m2,
                    unit="m2",
                    unit_price=self.defaults.corpus_mat.price_per_unit
                ))
        
        if "back_m2" in formulas:
            back_m2 = eval_formula(formulas["back_m2"], dims)
            if back_m2 > 0:
                root.add_child(BOMPart(
                    name=f"Back panel: {self.defaults.back_mat.name}",
                    material_id=self.defaults.back_mat.id,
                    quantity_net=back_m2,
                    unit="m2",
                    unit_price=self.defaults.back_mat.price_per_unit
                ))
        
        if "front_m2" in formulas:
            front_m2 = eval_formula(formulas["front_m2"], dims)

            # Szafka dostaje materiał na front TYLKO jeśli:
            # 1. Przepis na to pozwala (front_m2 > 0) ORAZ
            # 2. Użytkownik dodał drzwi/szuflady LUB jest to moduł będący samym frontem (Zmywarka, Panel)
            has_physical_fronts = self.cabinet.door_count > 0 or self.cabinet.drawer_count > 0
            is_front_only_module = self.cabinet.module_kind in ["DISHWASHER", "SIDE_PANEL"]

            if front_m2 > 0 and (has_physical_fronts or is_front_only_module):
                front_mat = self.cabinet.override_front_mat or self.defaults.front_mat
                root.add_child(BOMPart(
                    name=f"Front: {front_mat.name}",
                    material_id=front_mat.id,
                    quantity_net=front_m2,
                    unit="m2",
                    unit_price=front_mat.price_per_unit
                ))
        
        # 2. Okleinowanie (Front + Korpus)
        front_edge_m = 2 * (dims["width_mm"] + dims["height_mm"]) / 1000 if front_m2 > 0 else 0
        corpus_edge_m = (2 * dims["height_mm"] + 3 * dims["width_mm"]) / 1000 if corpus_m2 > 0 else 0
        total_edge_m = front_edge_m + corpus_edge_m

        if total_edge_m > 0:
            root.add_child(BOMPart(
            name="Edge banding: Generic ABS",
                quantity_net=total_edge_m,
            unit="lm",
            unit_price=0.80
            ))
        
        # 3. USŁUGI CNC (Cięcie i Okleinowanie)
        total_board_m2 = corpus_m2 + back_m2 + front_m2
        if total_board_m2 > 0:
            root.add_child(BOMPart(
                name="CNC Service: Cutting & Nesting",
                quantity_net=total_board_m2,
                unit="m2",
                unit_price=15.00  # Ryczałt za cięcie 1m2
            ))

        if total_edge_m > 0:
            root.add_child(BOMPart(
                name="CNC Service: Edgebanding PUR",
                quantity_net=total_edge_m,
                unit="lm",
                unit_price=4.50  # Ryczałt za oklejenie 1mb
            ))

        # 4. Okucia z Rules Engine
        tags = recipe.get("tags", [])
        multipliers = {}
        
        if self.cabinet.door_count > 0:
            multipliers["has_doors"] = self.cabinet.door_count
        
        if self.cabinet.drawer_count > 0:
            multipliers["has_drawers"] = self.cabinet.drawer_count
        
        self.rules_engine.apply_rules(tags, root, multipliers)
        
        # ==========================================
        # 5. COKÓŁ (Plinth) - dla szafek dolnych
        # ==========================================
        # Sprawdzamy, czy szafka stoi na podłodze (BASE lub TALL).
        # Zmywarka też ma type="BASE", więc dostanie swój kawałek cokołu!
        if self.cabinet.type in ["BASE", "TALL"]:
            # Długość cokołu to po prostu szerokość szafki w metrach
            plinth_length_m = dims["width_mm"] / 1000

            if plinth_length_m > 0:
                # Płyta cokołowa (np. z MDF lub gotowy cokół PCV)
                root.add_child(BOMPart(
                    name="Plinth board (Cokół)",
                    quantity_net=plinth_length_m,
                    unit="lm",
                    unit_price=25.00, # Cena za 1 metr bieżący cokołu
                    waste_factor=1.10 # LinearMaterialStrategy: dodajemy 10% na docinki
                ))

                # Uszczelka cokołowa (chroni przed wodą z podłogi)
                root.add_child(BOMPart(
                    name="Plinth seal (Uszczelka)",
                    quantity_net=plinth_length_m,
                    unit="lm",
                    unit_price=3.50,
                    waste_factor=1.10
                ))

        root.calculate()
        
        return root
    

    
    def generate_cost_trace_lines(self):
        """
        Generate cost trace lines compatible with existing UI.
        
        This converts the BOM tree to the legacy CostTraceLine format
        for seamless integration with the current UI.
        
        Returns:
            List of CostTraceLine objects
        """
        from kitchen_erp.schemas import CostTraceLine
        
        tree = self.generate()
        parts = tree.get_all_parts()
        
        trace_lines = []
        for part in parts:
            if "CNC Service" in part.name:
                category = "Service"
            elif "Corpus" in part.name or "Back panel" in part.name or "Front" in part.name or "Edge banding" in part.name:
                category = "Material"
            else:
                category = "Hardware"
            
            # Create formula string for display
            formula = f"{part.quantity_net:.4f} {part.unit} x {part.unit_price:.2f}"
            if part.waste_factor > 1.0:
                formula += f" x {part.waste_factor:.2f}"
            
            trace_lines.append(CostTraceLine(
                category=category,
                label=part.name,
                quantity=part.quantity_net,
                unit=part.unit,
                unit_price=part.unit_price,
                subtotal=part.cost,
                formula=formula,
                waste_factor=part.waste_factor if part.waste_factor > 1.0 else None
            ))
        
        return trace_lines
