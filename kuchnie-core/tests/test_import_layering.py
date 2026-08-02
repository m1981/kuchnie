"""Intra-package import layering (kuchnie-5un).

`kitchen.py` (aggregation) and `buildability.py` (gates) used to import
each other through function-local imports — a genuine mutual module
dependency wearing a lazy-import disguise. The shared vocabulary they
argued over (`Finding`, `GateStatus`, `ADVISORY`, `BLOCKING`) is the
property of neither, so it lives in the leaf module `findings.py`, and
the remaining dependency runs one way only: kitchen -> buildability.

These tests are structural: they fail if the cycle grows back.
"""
import ast
import inspect
import subprocess
import sys
from pathlib import Path

import kuchnie_core
from kuchnie_core import buildability as buildability_module
from kuchnie_core import findings as findings_module
from kuchnie_core import kitchen as kitchen_module

PKG = "kuchnie_core"
SRC = Path(kuchnie_core.__file__).parent


def _tree(module) -> ast.Module:
    return ast.parse(inspect.getsource(module))


def _sibling_imports(module, *, toplevel_only: bool) -> set[str]:
    """Sibling modules this module imports, by module name.

    ``toplevel_only`` restricts the scan to statements at module scope;
    otherwise every import anywhere in the file is reported (function
    bodies included — deferred imports are still dependencies).
    """
    tree = _tree(module)
    nodes = tree.body if toplevel_only else list(ast.walk(tree))
    out: set[str] = set()
    for node in nodes:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if node.level == 0 and not node.module.startswith(PKG):
            continue
        out.add(node.module.split(".")[-1])
    return out


def _deferred_imports(module) -> set[str]:
    """Sibling modules imported ONLY inside a function body."""
    return _sibling_imports(module, toplevel_only=False) - _sibling_imports(
        module, toplevel_only=True
    )


# ── findings.py is a leaf ───────────────────────────────────────

def test_findings_module_has_no_intra_package_imports():
    """The shared vocabulary must depend on nothing in the package —
    that is what makes it safe for both layers to import at the top."""
    assert _sibling_imports(findings_module, toplevel_only=False) == set()


def test_findings_imports_standalone_in_a_fresh_interpreter():
    """Importing the leaf alone must not drag the package in."""
    proc = subprocess.run(
        [sys.executable, "-c",
         "import importlib, sys;"
         "m = importlib.import_module('kuchnie_core.findings');"
         "print(m.BLOCKING, m.ADVISORY, m.GateStatus.PASSED.value,"
         " m.Finding('G1', m.BLOCKING, 'x').to_dict()['gate'])"],
        capture_output=True, text=True,
        cwd=str(SRC.parent.parent),
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["blocking", "advisory", "passed", "G1"]


# ── the cycle is gone ───────────────────────────────────────────

def test_buildability_does_not_import_kitchen_at_all():
    assert "kitchen" not in _sibling_imports(
        buildability_module, toplevel_only=False)


def test_kitchen_imports_buildability_only_at_module_level():
    assert "buildability" in _sibling_imports(
        kitchen_module, toplevel_only=True)
    assert "buildability" not in _deferred_imports(kitchen_module)


def test_gate_layer_imports_its_vocabulary_at_module_level():
    """Finding/GateStatus/ADVISORY/BLOCKING come from findings.py, at the
    top of the file — never from inside a function body."""
    assert "findings" in _sibling_imports(
        buildability_module, toplevel_only=True)
    for module in (buildability_module, kitchen_module):
        assert "findings" not in _deferred_imports(module), (
            f"{module.__name__} defers the Finding vocabulary")


def test_both_modules_import_cleanly_in_either_order():
    for first, second in (("kitchen", "buildability"),
                          ("buildability", "kitchen")):
        proc = subprocess.run(
            [sys.executable, "-c",
             f"import importlib;"
             f"a = importlib.import_module('kuchnie_core.{first}');"
             f"b = importlib.import_module('kuchnie_core.{second}');"
             f"print('ok')"],
            capture_output=True, text=True,
            cwd=str(SRC.parent.parent),
        )
        assert proc.returncode == 0, f"{first} then {second}: {proc.stderr}"
        assert proc.stdout.strip() == "ok"


# ── the public surface is untouched by the move ─────────────────

def test_public_api_survives_the_move():
    from kuchnie_core import (
        ADVISORY, BLOCKING, Finding, GateStatus, HeightSet, row_findings,
        validate_rows,
    )
    # the historic module paths callers already import from
    from kuchnie_core.kitchen import (  # noqa: F401
        HeightSet as KitchenHeightSet,
        row_findings as kitchen_row_findings,
        validate_rows as kitchen_validate_rows,
    )
    from kuchnie_core.buildability import (  # noqa: F401
        ADVISORY as B_ADVISORY,
        BLOCKING as B_BLOCKING,
        Finding as BFinding,
        GateStatus as BGateStatus,
    )
    assert KitchenHeightSet is HeightSet
    assert kitchen_row_findings is row_findings
    assert kitchen_validate_rows is validate_rows
    assert (BFinding, BGateStatus, B_ADVISORY, B_BLOCKING) == (
        Finding, GateStatus, ADVISORY, BLOCKING)
    for name in ("HeightSet", "row_findings", "validate_rows", "Finding",
                 "GateStatus", "ADVISORY", "BLOCKING"):
        assert name in kuchnie_core.__all__
