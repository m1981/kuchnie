"""Recipe loading and management utilities"""
import json
from pathlib import Path
from typing import Any


_RECIPES_CACHE: dict[str, dict] | None = None


def load_recipes() -> dict[str, dict]:
    """Load all recipes from recipes.json file"""
    global _RECIPES_CACHE
    
    if _RECIPES_CACHE is not None:
        return _RECIPES_CACHE
    
    recipes_path = Path(__file__).parent / "recipes.json"
    
    if not recipes_path.exists():
        raise FileNotFoundError(f"Recipes file not found: {recipes_path}")
    
    with open(recipes_path, "r", encoding="utf-8") as f:
        _RECIPES_CACHE = json.load(f)
    
    return _RECIPES_CACHE


def get_recipe(recipe_id: str) -> dict[str, Any]:
    """Get a specific recipe by ID"""
    recipes = load_recipes()
    
    if recipe_id not in recipes:
        raise ValueError(f"Recipe '{recipe_id}' not found in recipes.json")
    
    return recipes[recipe_id]


def get_recipe_tags(recipe_id: str) -> list[str]:
    """Get tags for a specific recipe"""
    recipe = get_recipe(recipe_id)
    return recipe.get("tags", [])


def eval_formula(formula: str, cabinet_dims: dict[str, float]) -> float:
    """
    Safely evaluate a formula string with cabinet dimensions.
    
    Args:
        formula: Mathematical expression as string (e.g., "width_mm * height_mm / 1000000")
        cabinet_dims: Dictionary with dimension values (width_mm, height_mm, depth_mm)
    
    Returns:
        Calculated value as float
    """
    # Create a safe namespace with only math operations and cabinet dimensions
    safe_namespace = {
        '__builtins__': {},
        **cabinet_dims
    }
    
    try:
        result = eval(formula, safe_namespace)
        return float(result)
    except Exception as e:
        raise ValueError(f"Error evaluating formula '{formula}': {e}")


def clear_recipe_cache():
    """Clear the recipe cache (useful for testing)"""
    global _RECIPES_CACHE
    _RECIPES_CACHE = None
