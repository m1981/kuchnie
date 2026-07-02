"""Tests for rules engine (tag-based component addition)"""
import pytest
from kitchen_erp.rules_engine import RulesEngine, HARDWARE_RULES
from kitchen_erp.schemas import BOMAssembly


def test_rules_engine_initialization():
    """Test that rules engine initializes with default rules"""
    engine = RulesEngine()
    
    assert engine.rules == HARDWARE_RULES
    assert "is_base" in engine.rules
    assert "has_doors" in engine.rules


def test_rules_engine_custom_rules():
    """Test that rules engine can use custom rules"""
    custom_rules = {
        "custom_tag": [{"name": "Custom part", "qty_per_unit": 1, "unit": "pcs", "price": 10.0}]
    }
    
    engine = RulesEngine(rules=custom_rules)
    
    assert engine.rules == custom_rules
    assert "custom_tag" in engine.rules


def test_apply_rules_single_tag():
    """Test applying rules for a single tag"""
    engine = RulesEngine()
    assembly = BOMAssembly(name="Test Cabinet")
    
    engine.apply_rules(tags=["is_base"], assembly=assembly)
    
    parts = assembly.get_all_parts()
    assert len(parts) == 1
    assert parts[0].name == "Cabinet legs"
    assert parts[0].quantity_net == 4
    assert parts[0].unit == "pcs"


def test_apply_rules_multiple_tags():
    """Test applying rules for multiple tags"""
    engine = RulesEngine()
    assembly = BOMAssembly(name="Base Cabinet with Doors")
    
    engine.apply_rules(tags=["is_base", "has_doors"], assembly=assembly)
    
    parts = assembly.get_all_parts()
    assert len(parts) == 3  # legs + hinges + bumpers
    
    part_names = [p.name for p in parts]
    assert "Cabinet legs" in part_names
    assert "Door hinges" in part_names
    assert "Door bumpers" in part_names


def test_apply_rules_with_multipliers():
    """Test applying rules with quantity multipliers"""
    engine = RulesEngine()
    assembly = BOMAssembly(name="Cabinet with 2 Doors")
    
    # 2 doors means 2x the hinges and bumpers
    engine.apply_rules(
        tags=["has_doors"],
        assembly=assembly,
        multipliers={"has_doors": 2}
    )
    
    parts = assembly.get_all_parts()
    
    hinges = next(p for p in parts if p.name == "Door hinges")
    bumpers = next(p for p in parts if p.name == "Door bumpers")
    
    assert hinges.quantity_net == 4  # 2 hinges per door * 2 doors
    assert bumpers.quantity_net == 2  # 1 bumper per door * 2 doors


def test_apply_rules_drawer_multiplier():
    """Test applying rules for multiple drawers"""
    engine = RulesEngine()
    assembly = BOMAssembly(name="Drawer Base with 4 Drawers")
    
    engine.apply_rules(
        tags=["is_base", "has_drawers"],
        assembly=assembly,
        multipliers={"has_drawers": 4}
    )
    
    parts = assembly.get_all_parts()
    
    slides = next(p for p in parts if p.name == "Drawer slides")
    assert slides.quantity_net == 4  # 1 set per drawer * 4 drawers


def test_apply_rules_unknown_tag():
    """Test that unknown tags are safely ignored"""
    engine = RulesEngine()
    assembly = BOMAssembly(name="Test")
    
    engine.apply_rules(tags=["unknown_tag", "is_base"], assembly=assembly)
    
    parts = assembly.get_all_parts()
    # Should only add parts for "is_base", ignore "unknown_tag"
    assert len(parts) == 1
    assert parts[0].name == "Cabinet legs"


def test_get_required_hardware_for_tags():
    """Test getting list of required hardware for tags"""
    engine = RulesEngine()
    
    required = engine.get_required_hardware_for_tags(["is_base", "has_doors"])
    
    assert len(required) == 3  # legs + hinges + bumpers
    
    names = [item["name"] for item in required]
    assert "Cabinet legs" in names
    assert "Door hinges" in names
    assert "Door bumpers" in names


def test_get_required_hardware_empty_tags():
    """Test getting required hardware with no tags"""
    engine = RulesEngine()
    
    required = engine.get_required_hardware_for_tags([])
    
    assert len(required) == 0


def test_rules_engine_cost_calculation():
    """Test that rules engine components contribute to total cost"""
    engine = RulesEngine()
    assembly = BOMAssembly(name="Test Cabinet")
    
    engine.apply_rules(tags=["is_base"], assembly=assembly)
    
    total_cost = assembly.calculate()
    
    # 4 legs * $1.50 = $6.00
    assert total_cost == pytest.approx(6.0)


def test_complex_cabinet_with_all_tags():
    """Test a complex cabinet with multiple tags and multipliers"""
    engine = RulesEngine()
    assembly = BOMAssembly(name="Sink Base with Doors")
    
    engine.apply_rules(
        tags=["is_base", "has_doors", "is_sink"],
        assembly=assembly,
        multipliers={"has_doors": 1}
    )
    
    parts = assembly.get_all_parts()
    
    # Should have: legs, hinges, bumpers, sink mat
    assert len(parts) == 4
    
    part_names = [p.name for p in parts]
    assert "Cabinet legs" in part_names
    assert "Door hinges" in part_names
    assert "Door bumpers" in part_names
    assert "Sink cabinet mat" in part_names
