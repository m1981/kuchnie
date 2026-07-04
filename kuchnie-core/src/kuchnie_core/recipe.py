"""Panel recipe — formulas as data (TopSolid/Polyboard pattern).

Instead of hardcoding panel dimensions in Python functions,
recipes store them as arithmetic expressions:

    shelf.width = cabinet_width - 2 * side_thickness - shelf_clearance

This enables:
  - UI preview of formula results before decomposition
  - Validation without running code
  - New cabinet types as JSON files (no code changes)
  - Formula graph visualization

Security: uses Python AST parsing — NO eval().
"""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, field
from typing import Any


# ── Exceptions ───────────────────────────────────────────────────

class RecipeValidationError(Exception):
    """Raised when recipe data or formula is invalid."""
    pass


# ── Safe formula evaluator ───────────────────────────────────────

# Allowed operators — no function calls, no attribute access
_OPERATORS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def evaluate_formula(formula: str, context: dict[str, float]) -> float:
    """Safely evaluate an arithmetic formula with variable substitution.

    Allowed:
      - Numbers (int, float)
      - Variables from context dict
      - Arithmetic: +, -, *, /, //, %
      - Parentheses
      - Unary minus

    NOT allowed (raises RecipeValidationError):
      - Function calls (eval, __import__, etc.)
      - Attribute access (obj.method)
      - Comparisons, boolean ops
      - Any other AST node types
    """
    try:
        tree = ast.parse(formula, mode='eval')
    except SyntaxError as e:
        raise RecipeValidationError(f"Invalid formula syntax: {formula!r}") from e

    return _eval_node(tree.body, context)


def _eval_node(node: ast.AST, ctx: dict[str, float]) -> float:
    """Recursively evaluate an AST node."""
    # Numbers
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise RecipeValidationError(
            f"Unsupported constant type: {type(node.value).__name__}"
        )

    # Variables
    if isinstance(node, ast.Name):
        if node.id not in ctx:
            raise RecipeValidationError(
                f"Unknown variable: {node.id!r}. "
                f"Available: {sorted(ctx.keys())}"
            )
        return float(ctx[node.id])

    # Binary operations
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise RecipeValidationError(
                f"Unsupported operator: {op_type.__name__}"
            )
        left = _eval_node(node.left, ctx)
        right = _eval_node(node.right, ctx)

        # Division by zero check
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise RecipeValidationError("Division by zero")

        return _OPERATORS[op_type](left, right)

    # Unary operations
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise RecipeValidationError(
                f"Unsupported unary operator: {op_type.__name__}"
            )
        operand = _eval_node(node.operand, ctx)
        return _OPERATORS[op_type](operand)

    # Everything else is forbidden
    raise RecipeValidationError(
        f"Unsupported expression type: {type(node).__name__}. "
        f"Only arithmetic expressions with variables are allowed."
    )


# ── PanelRecipe ──────────────────────────────────────────────────

@dataclass(frozen=True)
class PanelRecipe:
    """Recipe for computing one panel's dimensions from context variables.

    Formulas are strings evaluated against a context dict.
    """
    id: str
    name: str
    width_formula: str
    height_formula: str
    thickness_formula: str
    material_ref: str = "body"      # "body", "back", "front", or literal code
    edges: dict[str, str] = field(default_factory=dict)
    quantity: int = 1

    def compute_width(self, context: dict[str, float]) -> float:
        """Evaluate width formula against context."""
        return evaluate_formula(self.width_formula, context)

    def compute_height(self, context: dict[str, float]) -> float:
        """Evaluate height formula against context."""
        return evaluate_formula(self.height_formula, context)

    def compute_thickness(self, context: dict[str, float]) -> float:
        """Evaluate thickness formula against context."""
        return evaluate_formula(self.thickness_formula, context)


# ── RecipeSchema ─────────────────────────────────────────────────

@dataclass
class RecipeSchema:
    """Complete recipe for a cabinet type — all panels + context defaults."""
    cabinet_type: str
    construction_ref: str = "dowel_confirmat_18mm"
    context_defaults: dict[str, float] = field(default_factory=dict)
    panels: list[PanelRecipe] = field(default_factory=list)
    accessories: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeSchema:
        """Parse and validate recipe dict.

        Raises RecipeValidationError if required fields are missing.
        """
        if "cabinet_type" not in data:
            raise RecipeValidationError("Recipe missing 'cabinet_type'")
        if "panels" not in data:
            raise RecipeValidationError("Recipe missing 'panels'")

        panels = []
        for i, p in enumerate(data["panels"]):
            if "id" not in p:
                raise RecipeValidationError(f"Panel {i} missing 'id'")
            if "name" not in p:
                raise RecipeValidationError(f"Panel {i} missing 'name'")
            for field_name in ("width_formula", "height_formula", "thickness_formula"):
                if field_name not in p:
                    raise RecipeValidationError(
                        f"Panel {p.get('id', i)} missing '{field_name}'"
                    )
            panels.append(PanelRecipe(
                id=p["id"],
                name=p["name"],
                width_formula=p["width_formula"],
                height_formula=p["height_formula"],
                thickness_formula=p["thickness_formula"],
                material_ref=p.get("material_ref", "body"),
                edges=p.get("edges", {}),
                quantity=p.get("quantity", 1),
            ))

        return cls(
            cabinet_type=data["cabinet_type"],
            construction_ref=data.get("construction_ref", "dowel_confirmat_18mm"),
            context_defaults=data.get("context_defaults", {}),
            panels=panels,
            accessories=data.get("accessories", []),
        )
