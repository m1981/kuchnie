"""Tests for BOM tree structure (Composite pattern)"""
import pytest
from kitchen_erp.schemas import BOMPart, BOMAssembly


def test_bom_part_calculation():
    """Test that BOMPart calculates cost correctly"""
    part = BOMPart(
        name="Corpus Board",
        material_id=1,
        quantity_net=0.5,
        unit="m2",
        unit_price=12.50,
        waste_factor=1.20
    )
    
    cost = part.calculate()
    
    assert cost == pytest.approx(0.5 * 12.50 * 1.20)
    assert part.cost == cost


def test_bom_part_no_waste():
    """Test BOMPart without waste factor"""
    part = BOMPart(
        name="Hinges",
        quantity_net=4,
        unit="pcs",
        unit_price=2.50,
        waste_factor=1.0
    )
    
    cost = part.calculate()
    
    assert cost == pytest.approx(10.0)


def test_bom_assembly_single_child():
    """Test BOMAssembly with single child"""
    assembly = BOMAssembly(name="Test Assembly")
    
    part = BOMPart(
        name="Part 1",
        quantity_net=2,
        unit="pcs",
        unit_price=5.0
    )
    
    assembly.add_child(part)
    cost = assembly.calculate()
    
    assert cost == pytest.approx(10.0)
    assert assembly.cost == cost


def test_bom_assembly_multiple_children():
    """Test BOMAssembly with multiple children"""
    assembly = BOMAssembly(name="Cabinet")
    
    assembly.add_child(BOMPart(
        name="Corpus",
        quantity_net=1.0,
        unit="m2",
        unit_price=12.50,
        waste_factor=1.20
    ))
    
    assembly.add_child(BOMPart(
        name="Hinges",
        quantity_net=4,
        unit="pcs",
        unit_price=2.50
    ))
    
    cost = assembly.calculate()
    
    expected = (1.0 * 12.50 * 1.20) + (4 * 2.50)
    assert cost == pytest.approx(expected)


def test_bom_assembly_nested():
    """Test nested BOMAssembly (assembly within assembly)"""
    cabinet = BOMAssembly(name="Cabinet")
    drawer = BOMAssembly(name="Drawer")
    
    # Add parts to drawer
    drawer.add_child(BOMPart(
        name="Drawer bottom",
        quantity_net=0.2,
        unit="m2",
        unit_price=12.50
    ))
    
    drawer.add_child(BOMPart(
        name="Drawer slides",
        quantity_net=1,
        unit="sets",
        unit_price=35.0
    ))
    
    # Add drawer and other parts to cabinet
    cabinet.add_child(drawer)
    cabinet.add_child(BOMPart(
        name="Cabinet corpus",
        quantity_net=1.0,
        unit="m2",
        unit_price=12.50
    ))
    
    cost = cabinet.calculate()
    
    expected = (0.2 * 12.50) + 35.0 + (1.0 * 12.50)
    assert cost == pytest.approx(expected)


def test_get_all_parts_flat():
    """Test getting all parts from flat assembly"""
    assembly = BOMAssembly(name="Test")
    
    part1 = BOMPart(name="Part 1", quantity_net=1, unit="pcs", unit_price=5.0)
    part2 = BOMPart(name="Part 2", quantity_net=2, unit="pcs", unit_price=3.0)
    
    assembly.add_child(part1)
    assembly.add_child(part2)
    
    parts = assembly.get_all_parts()
    
    assert len(parts) == 2
    assert part1 in parts
    assert part2 in parts


def test_get_all_parts_nested():
    """Test getting all parts from nested assembly"""
    root = BOMAssembly(name="Root")
    sub1 = BOMAssembly(name="Sub1")
    sub2 = BOMAssembly(name="Sub2")
    
    part1 = BOMPart(name="Part 1", quantity_net=1, unit="pcs", unit_price=5.0)
    part2 = BOMPart(name="Part 2", quantity_net=2, unit="pcs", unit_price=3.0)
    part3 = BOMPart(name="Part 3", quantity_net=3, unit="pcs", unit_price=2.0)
    
    sub1.add_child(part1)
    sub2.add_child(part2)
    sub2.add_child(part3)
    
    root.add_child(sub1)
    root.add_child(sub2)
    
    parts = root.get_all_parts()
    
    assert len(parts) == 3
    assert part1 in parts
    assert part2 in parts
    assert part3 in parts
