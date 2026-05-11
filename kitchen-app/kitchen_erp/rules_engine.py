# kitchen_erp/rules_engine.py

# kitchen_erp/rules_engine.py

"""Rules engine for tag-based component addition"""
from typing import Any
from kitchen_erp.schemas import BOMPart, BOMAssembly


def get_default_hardware_rules():
    """Default hardware rules (used for initialization)"""
    return {
        "is_base": [
            {"name": "Cabinet legs", "qty_per_unit": 4, "unit": "pcs", "price": 1.50}
        ],
        "is_wall": [
            {"name": "Wall mounting brackets", "qty_per_unit": 2, "unit": "pcs", "price": 3.00}
        ],
        "has_doors": [
            {"name": "Door hinges", "qty_per_unit": 2, "unit": "pcs", "price": 15.00},
            {"name": "Door bumpers", "qty_per_unit": 1, "unit": "pcs", "price": 0.20},
            # NOWE: Uchwyt dla każdych drzwi
            {"name": "Handle (Uchwyt)", "qty_per_unit": 1, "unit": "pcs", "price": 25.00}
        ],
        "has_drawers": [
            {"name": "Drawer System (Blum/Hettich)", "qty_per_unit": 1, "unit": "sets", "price": 150.00},
            # NOWE: Uchwyt dla każdej szuflady
            {"name": "Handle (Uchwyt)", "qty_per_unit": 1, "unit": "pcs", "price": 25.00}
        ],
        "is_pullout": [
            {"name": "Pull-out mechanism (Cargo)", "qty_per_unit": 1, "unit": "sets", "price": 200.00}
        ],
        "is_sink": [
            {"name": "Sink cabinet mat", "qty_per_unit": 1, "unit": "pcs", "price": 8.00},
            # NOWE: Zestaw koszy na śmieci pod zlew
            {"name": "Waste sorting system (Kosze)", "qty_per_unit": 1, "unit": "sets", "price": 150.00}
        ],
        "needs_plinth_vent": [
            {"name": "Appliance ventilation grille", "qty_per_unit": 1, "unit": "pcs", "price": 5.00}
        ]
    }


def load_hardware_rules_from_db():
    """
    Load hardware rules from database.
    Falls back to default rules if database is empty or doesn't exist yet.
    """
    # Local imports to prevent circular dependency issues during app startup
    from kitchen_erp.database import engine
    from kitchen_erp.models import HardwareRule
    from sqlmodel import Session, select
    from sqlalchemy.exc import OperationalError

    try:
        # COMMERCIAL GRADE FIX: Use Session(engine) directly.
        # Using next(get_session()) leaves the generator open and leaks DB connections!
        with Session(engine) as session:
            rules = session.exec(select(HardwareRule)).all()

            if not rules:
                # Return default rules if database is empty
                return get_default_hardware_rules()

            # Convert database rules to dictionary format
            rules_dict = {}
            for rule in rules:
                if rule.tag not in rules_dict:
                    rules_dict[rule.tag] = []

                rules_dict[rule.tag].append({
                    "name": rule.hardware_name,
                    "qty_per_unit": rule.qty_per_unit,
                    "unit": rule.unit,
                    "price": rule.price
                })

            return rules_dict
    except OperationalError:
        # Fallback to defaults if database/table not initialized yet
        return get_default_hardware_rules()
    except Exception:
        # Fallback for any other errors
        return get_default_hardware_rules()


class RulesEngine:
    """
    Applies tag-based rules to automatically add required hardware components.

    This implements the Observer/Strategy pattern where cabinet tags trigger
    the addition of specific hardware components.
    """

    # COMMERCIAL GRADE FIX: Cache rules at the class level.
    # This prevents N+1 queries (hitting the DB every time a cabinet is processed).
    _cached_rules = None

    def __init__(self, rules: dict[str, list[dict]] | None = None):
        """
        Initialize the rules engine.

        Args:
            rules: Optional custom rules dictionary. If None, loads from database.
        """
        if rules is not None:
            self.rules = rules
        else:
            # Only hit the database the very first time a RulesEngine is created
            if RulesEngine._cached_rules is None:
                RulesEngine._cached_rules = load_hardware_rules_from_db()
            self.rules = RulesEngine._cached_rules

    @classmethod
    def clear_cache(cls):
        """
        Call this method if rules are updated in the database during runtime
        to force the engine to fetch fresh data on the next instantiation.
        """
        cls._cached_rules = None

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