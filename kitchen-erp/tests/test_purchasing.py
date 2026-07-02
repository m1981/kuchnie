"""Tests for purchasing strategies"""
import pytest
from kitchen_erp.purchasing import (
    SheetMaterialStrategy,
    LinearMaterialStrategy,
    CountertopStrategy,
    ExactQuantityStrategy,
    get_strategy_for_material
)


def test_sheet_material_strategy_single_sheet():
    """Test sheet material strategy when one sheet is enough"""
    strategy = SheetMaterialStrategy(sheet_size_m2=5.8)
    
    # Need 4.5 m², should buy 1 sheet = 5.8 m²
    purchase_qty = strategy.calculate_purchase_quantity(4.5)
    
    assert purchase_qty == pytest.approx(5.8)
    assert strategy.get_waste_factor(4.5) == pytest.approx(5.8 / 4.5)


def test_sheet_material_strategy_multiple_sheets():
    """Test sheet material strategy when multiple sheets needed"""
    strategy = SheetMaterialStrategy(sheet_size_m2=5.8)
    
    # Need 7.5 m², should buy 2 sheets = 11.6 m²
    purchase_qty = strategy.calculate_purchase_quantity(7.5)
    
    assert purchase_qty == pytest.approx(11.6)
    assert strategy.get_waste_factor(7.5) == pytest.approx(11.6 / 7.5)


def test_sheet_material_strategy_exact_fit():
    """Test sheet material strategy when quantity exactly matches sheets"""
    strategy = SheetMaterialStrategy(sheet_size_m2=5.8)
    
    # Need exactly 2 sheets
    purchase_qty = strategy.calculate_purchase_quantity(11.6)
    
    assert purchase_qty == pytest.approx(11.6)
    assert strategy.get_waste_factor(11.6) == pytest.approx(1.0)


def test_linear_material_strategy_single_roll():
    """Test linear material strategy with one roll"""
    strategy = LinearMaterialStrategy(roll_length_m=50.0, waste_factor=1.10)
    
    # Need 40m, with 10% waste = 44m, fits in 1 roll
    purchase_qty = strategy.calculate_purchase_quantity(40.0)
    
    assert purchase_qty == pytest.approx(50.0)


def test_linear_material_strategy_multiple_rolls():
    """Test linear material strategy with multiple rolls"""
    strategy = LinearMaterialStrategy(roll_length_m=50.0, waste_factor=1.10)
    
    # Need 48m, with 10% waste = 52.8m, needs 2 rolls = 100m
    purchase_qty = strategy.calculate_purchase_quantity(48.0)
    
    assert purchase_qty == pytest.approx(100.0)


def test_linear_material_waste_factor():
    """Test that linear material waste factor includes both cutting and rounding"""
    strategy = LinearMaterialStrategy(roll_length_m=50.0, waste_factor=1.10)
    
    waste_factor = strategy.get_waste_factor(40.0)
    
    # 40m net -> 44m with cutting waste -> 50m purchased
    assert waste_factor == pytest.approx(50.0 / 40.0)


def test_countertop_strategy_single_piece():
    """Test countertop strategy with single piece"""
    # 4100mm x 600mm = 2.46 m²
    strategy = CountertopStrategy(standard_length_mm=4100, width_mm=600)
    
    # Need 2.0 m², fits in 1 piece
    purchase_qty = strategy.calculate_purchase_quantity(2.0)
    
    assert purchase_qty == pytest.approx(2.46)


def test_countertop_strategy_multiple_pieces():
    """Test countertop strategy with multiple pieces"""
    strategy = CountertopStrategy(standard_length_mm=4100, width_mm=600)
    
    # Need 3.5 m², needs 2 pieces = 4.92 m²
    purchase_qty = strategy.calculate_purchase_quantity(3.5)
    
    assert purchase_qty == pytest.approx(4.92)


def test_exact_quantity_strategy_no_waste():
    """Test exact quantity strategy with no waste factor"""
    strategy = ExactQuantityStrategy(waste_factor=1.0)
    
    purchase_qty = strategy.calculate_purchase_quantity(10.0)
    
    assert purchase_qty == 10.0
    assert strategy.get_waste_factor(10.0) == 1.0


def test_exact_quantity_strategy_with_buffer():
    """Test exact quantity strategy with waste buffer"""
    strategy = ExactQuantityStrategy(waste_factor=1.05)
    
    # Need 10, with 5% buffer = 10.5, rounds up to 11
    purchase_qty = strategy.calculate_purchase_quantity(10.0)
    
    assert purchase_qty == 11.0


def test_exact_quantity_strategy_fractional():
    """Test exact quantity strategy rounds up fractional quantities"""
    strategy = ExactQuantityStrategy(waste_factor=1.05)
    
    # Need 9.8, with 5% = 10.29, rounds up to 11
    purchase_qty = strategy.calculate_purchase_quantity(9.8)
    
    assert purchase_qty == 11.0


def test_get_strategy_for_material_board():
    """Test factory function returns correct strategy for boards"""
    strategy = get_strategy_for_material("Board")
    
    assert isinstance(strategy, SheetMaterialStrategy)


def test_get_strategy_for_material_edgebanding():
    """Test factory function returns correct strategy for edgebanding"""
    strategy = get_strategy_for_material("Edgebanding")
    
    assert isinstance(strategy, LinearMaterialStrategy)


def test_get_strategy_for_material_countertop():
    """Test factory function returns correct strategy for countertops"""
    strategy = get_strategy_for_material("Countertop")
    
    assert isinstance(strategy, CountertopStrategy)


def test_get_strategy_for_material_hardware():
    """Test factory function returns correct strategy for hardware"""
    strategy = get_strategy_for_material("Hardware")
    
    assert isinstance(strategy, ExactQuantityStrategy)


def test_get_strategy_for_material_unknown():
    """Test factory function returns default strategy for unknown category"""
    strategy = get_strategy_for_material("UnknownCategory")
    
    assert isinstance(strategy, ExactQuantityStrategy)


def test_sheet_material_zero_quantity():
    """Test sheet material strategy handles zero quantity"""
    strategy = SheetMaterialStrategy(sheet_size_m2=5.8)
    
    purchase_qty = strategy.calculate_purchase_quantity(0.0)
    
    assert purchase_qty == 0.0
    assert strategy.get_waste_factor(0.0) == 1.0


def test_realistic_kitchen_scenario():
    """Test realistic kitchen material purchasing scenario"""
    # Scenario: Kitchen needs 7.2 m² of corpus board
    board_strategy = SheetMaterialStrategy(sheet_size_m2=5.796)
    
    # Should need 2 sheets = 11.592 m²
    purchase_qty = board_strategy.calculate_purchase_quantity(7.2)
    waste_factor = board_strategy.get_waste_factor(7.2)
    
    assert purchase_qty == pytest.approx(11.592)
    assert waste_factor == pytest.approx(1.61, rel=0.01)  # 61% waste!
    
    # This demonstrates the problem mentioned in the LLM chat:
    # Program calculates 7.2 m² but you must buy 11.592 m²
