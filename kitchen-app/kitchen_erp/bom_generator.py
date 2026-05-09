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
            if front_m2 > 0 and self.cabinet.has_custom_front:
                # Only add front material if custom front is enabled
                front_mat = self.cabinet.local_front_mat or self.defaults.front_mat
                root.add_child(BOMPart(
                    name=f"Front: {front_mat.name}",
                    material_id=front_mat.id,
                    quantity_net=front_m2,
                    unit="m2",
                    unit_price=front_mat.price_per_unit
                ))
        
        # 2. Add edgebanding (simplified - based on perimeter)
        # This is a rough estimate; real calculation would need detailed edge list
        perimeter_m = 2 * (dims["width_mm"] + dims["height_mm"]) / 1000
        root.add_child(BOMPart(
            name="Edge banding: Generic ABS",
            quantity_net=perimeter_m,
            unit="lm",
            unit_price=0.80
        ))
        
        # 3. Apply rules engine to add hardware based on tags
        tags = recipe.get("tags", [])
        multipliers = {}
        
        if self.cabinet.door_count > 0:
            multipliers["has_doors"] = self.cabinet.door_count
        
        if self.cabinet.drawer_count > 0:
            multipliers["has_drawers"] = self.cabinet.drawer_count
        
        self.rules_engine.apply_rules(tags, root, multipliers)
        
        # 4. Calculate total cost
        root.calculate()
        
        return root
    
    def generate_flat_bom(self) -> list[dict]:
        """
        Generate a flat list of BOM items (for backward compatibility).
        
        Returns:
            List of dictionaries with material/hardware information
        """
        tree = self.generate()
        parts = tree.get_all_parts()
        
        flat_bom = []
        for part in parts:
            flat_bom.append({
                "name": part.name,
                "quantity_net": part.quantity_net,
                "unit": part.unit,
                "unit_price": part.unit_price,
                "waste_factor": part.waste_factor,
                "cost": part.cost
            })
        
        return flat_bom
    
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
            # Determine category based on part name
            if "Corpus" in part.name or "Back panel" in part.name or "Front" in part.name:
                category = "Material"
            elif "Edge banding" in part.name:
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
