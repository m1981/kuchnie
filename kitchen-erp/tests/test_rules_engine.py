"""Tests for rules engine (tag-based component addition).

Rules are pinned explicitly via get_default_hardware_rules() so tests stay
deterministic — a no-arg RulesEngine() loads from the app database, whose
contents these unit tests must not depend on.
"""
import pytest
from kitchen_erp.core.rules_engine import RulesEngine, get_default_hardware_rules
from kitchen_erp.core.schemas import BOMAssembly


def make_engine() -> RulesEngine:
    return RulesEngine(rules=get_default_hardware_rules())


def test_default_rules_shape():
    """Default rules carry the tags the recipes rely on."""
    rules = get_default_hardware_rules()
    for tag in ("is_base", "is_wall", "has_doors", "has_drawers",
                "is_pullout", "is_sink", "needs_plinth_vent"):
        assert tag in rules
        assert all({"name", "qty_per_unit", "unit", "price"} <= set(item)
                   for item in rules[tag])


def test_rules_engine_custom_rules():
    """Rules engine honours an explicitly injected rules dict."""
    custom_rules = {
        "custom_tag": [{"name": "Custom part", "qty_per_unit": 1, "unit": "pcs", "price": 10.0}]
    }

    engine = RulesEngine(rules=custom_rules)

    assert engine.rules == custom_rules
    assert "custom_tag" in engine.rules


def test_apply_rules_single_tag():
    """Applying rules for a single tag adds exactly its hardware."""
    engine = make_engine()
    assembly = BOMAssembly(name="Test Cabinet")

    engine.apply_rules(tags=["is_base"], assembly=assembly)

    parts = assembly.get_all_parts()
    assert len(parts) == 1
    assert parts[0].name == "Cabinet legs"
    assert parts[0].quantity_net == 4
    assert parts[0].unit == "pcs"


def test_apply_rules_multiple_tags():
    """has_doors adds hinges, bumpers AND a handle per current defaults."""
    engine = make_engine()
    assembly = BOMAssembly(name="Base Cabinet with Doors")

    engine.apply_rules(tags=["is_base", "has_doors"], assembly=assembly)

    part_names = [p.name for p in assembly.get_all_parts()]
    assert len(part_names) == 4  # legs + hinges + bumpers + handle
    assert "Cabinet legs" in part_names
    assert "Door hinges" in part_names
    assert "Door bumpers" in part_names
    assert "Handle (Uchwyt)" in part_names


def test_apply_rules_with_multipliers():
    """Door count multiplies every has_doors rule."""
    engine = make_engine()
    assembly = BOMAssembly(name="Cabinet with 2 Doors")

    engine.apply_rules(
        tags=["has_doors"],
        assembly=assembly,
        multipliers={"has_doors": 2}
    )

    parts = assembly.get_all_parts()

    hinges = next(p for p in parts if p.name == "Door hinges")
    bumpers = next(p for p in parts if p.name == "Door bumpers")
    handles = next(p for p in parts if p.name == "Handle (Uchwyt)")

    assert hinges.quantity_net == 4   # 2 hinges per door * 2 doors
    assert bumpers.quantity_net == 2  # 1 bumper per door * 2 doors
    assert handles.quantity_net == 2  # 1 handle per door * 2 doors


def test_apply_rules_drawer_multiplier():
    """Drawer count multiplies the drawer system and its handles."""
    engine = make_engine()
    assembly = BOMAssembly(name="Drawer Base with 4 Drawers")

    engine.apply_rules(
        tags=["is_base", "has_drawers"],
        assembly=assembly,
        multipliers={"has_drawers": 4}
    )

    parts = assembly.get_all_parts()

    drawer_system = next(p for p in parts if p.name == "Drawer System (Blum/Hettich)")
    assert drawer_system.quantity_net == 4  # 1 set per drawer * 4 drawers


def test_apply_rules_unknown_tag():
    """Unknown tags are safely ignored."""
    engine = make_engine()
    assembly = BOMAssembly(name="Test")

    engine.apply_rules(tags=["unknown_tag", "is_base"], assembly=assembly)

    parts = assembly.get_all_parts()
    assert len(parts) == 1
    assert parts[0].name == "Cabinet legs"


def test_get_required_hardware_for_tags():
    """Preview list covers every rule of every requested tag."""
    engine = make_engine()

    required = engine.get_required_hardware_for_tags(["is_base", "has_doors"])

    assert len(required) == 4  # legs + hinges + bumpers + handle

    names = [item["name"] for item in required]
    assert "Cabinet legs" in names
    assert "Door hinges" in names
    assert "Door bumpers" in names
    assert "Handle (Uchwyt)" in names


def test_get_required_hardware_empty_tags():
    engine = make_engine()

    required = engine.get_required_hardware_for_tags([])

    assert len(required) == 0


def test_rules_engine_cost_calculation():
    """Rule-added components contribute to assembly cost."""
    engine = make_engine()
    assembly = BOMAssembly(name="Test Cabinet")

    engine.apply_rules(tags=["is_base"], assembly=assembly)

    total_cost = assembly.calculate()

    # 4 legs * $1.50 = $6.00
    assert total_cost == pytest.approx(6.0)


def test_complex_cabinet_with_all_tags():
    """Sink base with doors: legs + 3 door items + mat + waste system."""
    engine = make_engine()
    assembly = BOMAssembly(name="Sink Base with Doors")

    engine.apply_rules(
        tags=["is_base", "has_doors", "is_sink"],
        assembly=assembly,
        multipliers={"has_doors": 1}
    )

    part_names = [p.name for p in assembly.get_all_parts()]
    assert len(part_names) == 6

    assert "Cabinet legs" in part_names
    assert "Door hinges" in part_names
    assert "Door bumpers" in part_names
    assert "Handle (Uchwyt)" in part_names
    assert "Sink cabinet mat" in part_names
    assert "Waste sorting system (Kosze)" in part_names
