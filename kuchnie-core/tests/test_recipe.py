"""Panel recipe — formulas as data (TopSolid/Polyboard pattern).

Tests prove:
  1. Recipe schema validates correctly
  2. Formula evaluator is safe (no eval())
  3. Panel dimensions computed from formulas match hardcoded values
  4. Recipe-based decomposition produces same results as catalog.py
"""

import pytest
from kuchnie_core.recipe import (
    PanelRecipe,
    RecipeSchema,
    evaluate_formula,
    RecipeValidationError,
)


# ── Formula evaluator ────────────────────────────────────────────

class TestFormulaEvaluator:
    """Safe formula evaluation — no eval(), only arithmetic."""

    def test_integer_literal(self):
        assert evaluate_formula("18", {}) == 18

    def test_float_literal(self):
        assert evaluate_formula("3.5", {}) == 3.5

    def test_variable_lookup(self):
        assert evaluate_formula("width", {"width": 800}) == 800

    def test_subtraction(self):
        assert evaluate_formula("width - 36", {"width": 800}) == 764

    def test_multiplication(self):
        assert evaluate_formula("2 * thickness", {"thickness": 18}) == 36

    def test_compound_expression(self):
        assert evaluate_formula("width - 2 * thickness", {"width": 800, "thickness": 18}) == 764

    def test_division(self):
        assert evaluate_formula("width / 2", {"width": 800}) == 400

    def test_parentheses(self):
        assert evaluate_formula("(width - gap) / 2", {"width": 800, "gap": 6}) == 397

    def test_complex_formula(self):
        """back_width = width - 2*side + 2*groove"""
        ctx = {"width": 800, "side": 18, "groove": 8}
        assert evaluate_formula("width - 2*side + 2*groove", ctx) == 780

    def test_missing_variable_raises(self):
        with pytest.raises(RecipeValidationError, match="Unknown variable"):
            evaluate_formula("width + missing", {"width": 800})

    def test_division_by_zero_raises(self):
        with pytest.raises(RecipeValidationError, match="Division by zero"):
            evaluate_formula("width / 0", {"width": 800})

    def test_rejects_function_calls(self):
        """Must not allow function calls like __import__ or eval."""
        with pytest.raises(RecipeValidationError):
            evaluate_formula("__import__('os')", {})

    def test_rejects_attribute_access(self):
        """Must not allow attribute access like obj.method."""
        with pytest.raises(RecipeValidationError):
            evaluate_formula("x.__class__", {"x": 1})


# ── PanelRecipe ──────────────────────────────────────────────────

class TestPanelRecipe:
    """A recipe defines how to compute one panel's dimensions."""

    def test_create_recipe(self):
        r = PanelRecipe(
            id="side",
            name="Lewy bok",
            width_formula="depth",
            height_formula="height - plinth",
            thickness_formula="side_thickness",
        )
        assert r.id == "side"

    def test_compute_width(self):
        r = PanelRecipe(
            id="side",
            name="Lewy bok",
            width_formula="depth",
            height_formula="height - plinth",
            thickness_formula="side_thickness",
        )
        ctx = {"depth": 510, "height": 720, "plinth": 100, "side_thickness": 18}
        assert r.compute_width(ctx) == 510

    def test_compute_height(self):
        r = PanelRecipe(
            id="side",
            name="Lewy bok",
            width_formula="depth",
            height_formula="height - plinth",
            thickness_formula="side_thickness",
        )
        ctx = {"depth": 510, "height": 720, "plinth": 100, "side_thickness": 18}
        assert r.compute_height(ctx) == 620

    def test_compute_thickness(self):
        r = PanelRecipe(
            id="side",
            name="Lewy bok",
            width_formula="depth",
            height_formula="height - plinth",
            thickness_formula="side_thickness",
        )
        ctx = {"depth": 510, "height": 720, "plinth": 100, "side_thickness": 18}
        assert r.compute_thickness(ctx) == 18


# ── RecipeSchema ─────────────────────────────────────────────────

class TestRecipeSchema:
    """Schema validates recipe JSON structure."""

    def test_valid_schema(self):
        data = {
            "cabinet_type": "dolna_szufladowa",
            "construction_ref": "dowel_confirmat_18mm",
            "context_defaults": {
                "plinth": 100,
                "door_gap": 3,
                "shelf_clearance": 2,
            },
            "panels": [
                {
                    "id": "side_left",
                    "name": "Lewy bok",
                    "width_formula": "depth",
                    "height_formula": "height - plinth",
                    "thickness_formula": "side_thickness",
                    "material_ref": "body",
                    "edges": {"front": "body"},
                },
            ],
        }
        schema = RecipeSchema.from_dict(data)
        assert schema.cabinet_type == "dolna_szufladowa"
        assert len(schema.panels) == 1

    def test_missing_cabinet_type_raises(self):
        data = {"panels": []}
        with pytest.raises(RecipeValidationError, match="cabinet_type"):
            RecipeSchema.from_dict(data)

    def test_missing_panels_raises(self):
        data = {"cabinet_type": "test"}
        with pytest.raises(RecipeValidationError, match="panels"):
            RecipeSchema.from_dict(data)

    def test_panel_missing_id_raises(self):
        data = {
            "cabinet_type": "test",
            "panels": [{"name": "test", "width_formula": "1", "height_formula": "1", "thickness_formula": "1"}],
        }
        with pytest.raises(RecipeValidationError, match="id"):
            RecipeSchema.from_dict(data)

    def test_panel_missing_formula_raises(self):
        data = {
            "cabinet_type": "test",
            "panels": [{"id": "test", "name": "test", "width_formula": "1", "height_formula": "1"}],
        }
        with pytest.raises(RecipeValidationError, match="thickness_formula"):
            RecipeSchema.from_dict(data)


# ── Recipe-based decomposition ───────────────────────────────────

class TestRecipeDecomposition:
    """Recipe produces same panels as hardcoded catalog.py."""

    def test_side_panel_dimensions(self):
        """Recipe for side panel matches K01 expected values."""
        recipe = PanelRecipe(
            id="side",
            name="Lewy bok",
            width_formula="depth",
            height_formula="height - plinth",
            thickness_formula="side_thickness",
        )
        ctx = {"depth": 510, "height": 720, "plinth": 100, "side_thickness": 18}
        assert recipe.compute_width(ctx) == 510
        assert recipe.compute_height(ctx) == 620
        assert recipe.compute_thickness(ctx) == 18

    def test_bottom_panel_dimensions(self):
        """Recipe for bottom panel matches K01 expected values."""
        recipe = PanelRecipe(
            id="bottom",
            name="Dno",
            width_formula="width - 2 * side_thickness",
            height_formula="depth",
            thickness_formula="bottom_thickness",
        )
        ctx = {"width": 800, "depth": 510, "side_thickness": 18, "bottom_thickness": 18}
        assert recipe.compute_width(ctx) == 764
        assert recipe.compute_height(ctx) == 510

    def test_back_panel_dimensions(self):
        """Recipe for back panel matches K01 expected values."""
        recipe = PanelRecipe(
            id="back",
            name="Plecy",
            width_formula="width - 2*side_thickness + 2*groove_depth",
            height_formula="height - plinth + groove_depth",
            thickness_formula="back_thickness",
        )
        ctx = {
            "width": 800, "height": 720, "plinth": 100,
            "side_thickness": 18, "groove_depth": 8, "back_thickness": 3,
        }
        assert recipe.compute_width(ctx) == 780
        assert recipe.compute_height(ctx) == 628
        assert recipe.compute_thickness(ctx) == 3

    def test_door_front_single(self):
        """Recipe for single door front matches K01 expected values."""
        recipe = PanelRecipe(
            id="front_F1",
            name="Front F1",
            width_formula="width - 2*door_gap",
            height_formula="front_height",
            thickness_formula="front_thickness",
        )
        ctx = {"width": 800, "door_gap": 3, "front_height": 150, "front_thickness": 18}
        assert recipe.compute_width(ctx) == 794
        assert recipe.compute_height(ctx) == 150
