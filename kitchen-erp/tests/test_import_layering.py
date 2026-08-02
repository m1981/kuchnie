"""core/ import layering (kuchnie-5un).

`models.py` deferred an import of `core.survey` inside
`Project.transition_stage` purely because `survey.py` imported `Project`
back at module load. The dependency is inverted: `survey.py` needs
`Project` for typing only, so the runtime edge runs one way —
models -> survey — and no import hides in a function body.
"""
import ast
import inspect

from kitchen_erp.core import models as models_module
from kitchen_erp.core import survey as survey_module

PKG = "kitchen_erp"


def _tree(module) -> ast.Module:
    return ast.parse(inspect.getsource(module))


def _type_checking_import_ids(tree: ast.Module) -> set[int]:
    return {
        id(n)
        for stmt in tree.body
        if isinstance(stmt, ast.If)
        and isinstance(stmt.test, ast.Name)
        and stmt.test.id == "TYPE_CHECKING"
        for n in ast.walk(stmt)
        if isinstance(n, ast.ImportFrom)
    }


def _runtime_sibling_imports(module, *, toplevel_only: bool) -> set[str]:
    tree = _tree(module)
    guarded = _type_checking_import_ids(tree)
    nodes = tree.body if toplevel_only else list(ast.walk(tree))
    out: set[str] = set()
    for node in nodes:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if id(node) in guarded:
            continue
        if node.level == 0 and not node.module.startswith(PKG):
            continue
        out.add(node.module.split(".")[-1])
    return out


def test_survey_does_not_import_models_at_runtime():
    """`Project` is a type annotation in survey.py, nothing more."""
    assert "models" not in _runtime_sibling_imports(
        survey_module, toplevel_only=False)


def test_models_imports_survey_at_module_level_not_in_a_method():
    toplevel = _runtime_sibling_imports(models_module, toplevel_only=True)
    anywhere = _runtime_sibling_imports(models_module, toplevel_only=False)
    assert "survey" in toplevel
    assert "survey" not in (anywhere - toplevel), (
        "a deferred import of core.survey crept back into models.py")
