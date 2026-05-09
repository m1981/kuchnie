"""Tests for recipe loading and formula evaluation"""
import pytest
from kitchen_erp.recipe_loader import (
    load_recipes,
    get_recipe,
    get_recipe_tags,
    eval_formula,
    clear_recipe_cache
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear recipe cache before each test"""
    clear_recipe_cache()
    yield
    clear_recipe_cache()


def test_load_recipes():
    """Test that recipes.json loads successfully"""
    recipes = load_recipes()
    
    assert isinstance(recipes, dict)
    assert len(recipes) > 0
    assert "DRAWER_BASE" in recipes
    assert "WALL_CABINET" in recipes


def test_get_recipe():
    """Test retrieving a specific recipe"""
    recipe = get_recipe("DRAWER_BASE")
    
    assert recipe["name"] == "Drawer base"
    assert recipe["type"] == "BASE"
    assert "is_base" in recipe["tags"]
    assert "has_drawers" in recipe["tags"]


def test_get_recipe_not_found():
    """Test that getting non-existent recipe raises error"""
    with pytest.raises(ValueError, match="Recipe 'NONEXISTENT' not found"):
        get_recipe("NONEXISTENT")


def test_get_recipe_tags():
    """Test retrieving tags for a recipe"""
    tags = get_recipe_tags("DRAWER_BASE")
    
    assert "is_base" in tags
    assert "has_drawers" in tags


def test_eval_formula_simple():
    """Test formula evaluation with simple dimensions"""
    cabinet_dims = {
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 560
    }
    
    # Test area calculation
    formula = "(width_mm * height_mm) / 1000000"
    result = eval_formula(formula, cabinet_dims)
    
    assert result == pytest.approx(0.576, rel=1e-6)


def test_eval_formula_complex():
    """Test formula evaluation with complex expression"""
    cabinet_dims = {
        "width_mm": 400,
        "height_mm": 802,
        "depth_mm": 560
    }
    
    # Corpus calculation: 2 sides + 2 front/back + top/bottom
    formula = "((2 * height_mm * depth_mm) + (2 * width_mm * depth_mm) + (width_mm * height_mm)) / 1000000"
    result = eval_formula(formula, cabinet_dims)
    
    expected = ((2 * 802 * 560) + (2 * 400 * 560) + (400 * 802)) / 1000000
    assert result == pytest.approx(expected, rel=1e-6)


def test_eval_formula_invalid():
    """Test that invalid formulas raise errors"""
    cabinet_dims = {"width_mm": 800}
    
    with pytest.raises(ValueError, match="Error evaluating formula"):
        eval_formula("width_mm / 0", cabinet_dims)


def test_recipe_cache():
    """Test that recipes are cached after first load"""
    recipes1 = load_recipes()
    recipes2 = load_recipes()
    
    # Should be the same object (cached)
    assert recipes1 is recipes2
