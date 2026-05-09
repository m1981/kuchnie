"""Rules engine for tag-based component addition"""
from typing import Any
from kitchen_erp.schemas import BOMPart, BOMAssembly


# Hardware rules configuration - maps tags to required hardware
HARDWARE_RULES = {
    "is_base": [
        {"name": "Cabinet legs", "qty_per_unit": 4, "unit": "pcs", "price": 1.50}
    ],
    "is_wall": [
        {"name": "Wall mounting brackets", "qty_per_unit": 2, "unit": "pcs", "price": 3.00}
    ],
    "has_doors": [
        {"name": "Door hinges", "qty_per_unit": 2, "unit": "pcs", "price": 2.50},
        {"name": "Door bumpers", "qty_per_unit": 1, "unit": "pcs", "price": 0.20}
    ],
    "has_drawers": [
        {"name": "Drawer slides", "qty_per_unit": 1, "unit": "sets", "price": 35.00}
    ],
    "is_pullout": [
        {"name": "Pull-out mechanism", "qty_per_unit": 1, "unit": "sets", "price": 40.00}
    ],
    "is_sink": [
        {"name": "Sink cabinet mat", "qty_per_unit": 1, "unit": "pcs", "price": 8.00}
    ],
    "is_appliance": [
        {"name": "Appliance ventilation grille", "qty_per_unit": 1, "unit": "pcs", "price": 5.00}
    ]
}


class RulesEngine:
    """
    Applies tag-based rules to automatically add required hardware components.
    
    This implements the Observer/Strategy pattern where cabinet tags trigger
    the addition of specific hardware components.
    """
    
    def __init__(self, rules: dict[str, list[dict]] | None = None):
        """
        Initialize the rules engine.
        
        Args:
            rules: Optional custom rules dictionary. If None, uses HARDWARE_RULES.
        """
        self.rules = rules or HARDWARE_RULES
    
    def apply_rules(
        self,
        tags: list[str],
        assembly: BOMAssembly,
        multipliers: dict[str, int] | None = None
    ) -> BOMAssembly:
        """
        Apply hardware rules based on tags and add components to assembly.
        
        Args:
            tags: List of tags from the recipe (e.g., ["is_base", "has_doors"])
            assembly: BOMAssembly to add hardware components to
            multipliers: Optional dict to override quantities (e.g., {"has_doors": 2} for 2 doors)
        
        Returns:
            The modified assembly with hardware components added
        """
        multipliers = multipliers or {}
        
        for tag in tags:
            if tag in self.rules:
                for hardware_spec in self.rules[tag]:
                    # Calculate quantity based on multiplier (e.g., number of doors/drawers)
                    base_qty = hardware_spec["qty_per_unit"]
                    multiplier = multipliers.get(tag, 1)
                    total_qty = base_qty * multiplier
                    
                    # Create BOMPart for this hardware
                    part = BOMPart(
                        name=hardware_spec["name"],
                        quantity_net=total_qty,
                        unit=hardware_spec["unit"],
                        unit_price=hardware_spec["price"]
                    )
                    
                    assembly.add_child(part)
        
        return assembly
    
    def get_required_hardware_for_tags(self, tags: list[str]) -> list[dict[str, Any]]:
        """
        Get list of all hardware items required for given tags.
        
        Useful for preview/validation before building BOM.
        
        Args:
            tags: List of tags to check
            
        Returns:
            List of hardware specifications
        """
        required = []
        for tag in tags:
            if tag in self.rules:
                required.extend(self.rules[tag])
        return required
