"""Pinned tests for the R2-lite backward-trace slice (wk-9fb28a32).

Covers scripts/code-inventory.py (HAVE enumerator: determinism, AST
extraction, dotted names) and scripts/coverage-audit.py (glob translation
and the TRACED/MENTIONED/DARK verdict rule from
docs/specs/conformance-join.md).
Run: .venv/bin/python -m pytest scripts/tests -q
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), REPO / "scripts" / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


code_inventory = _load("code-inventory.py")
coverage_audit = _load("coverage-audit.py")


def test_walk_extracts_classes_functions_and_dotted_names() -> None:
    inv = code_inventory.walk()
    core_model = inv.get("kuchnie-core/src/kuchnie_core/model.py")
    assert core_model is not None
    assert core_model["dotted"] == "kuchnie_core.model"
    assert "Panel" in core_model["classes"]
    extract = inv.get("home-builder-adapter/src/extract.py")
    assert extract is not None and extract["dotted"] == "src.extract"


def test_walk_is_deterministic_and_matches_stdout() -> None:
    a = json.dumps(code_inventory.walk(), indent=2, sort_keys=True)
    b = json.dumps(code_inventory.walk(), indent=2, sort_keys=True)
    assert a == b
    proc = subprocess.run(
        ["python3", "scripts/code-inventory.py", "--stdout"],
        cwd=REPO, capture_output=True, text=True, timeout=120)
    assert proc.stdout == a + "\n"


def test_glob_translation_handles_doublestar_and_star() -> None:
    g = coverage_audit._glob_re
    assert g("kuchnie-core/src/**/*.py").match(
        "kuchnie-core/src/kuchnie_core/model.py")
    assert g("kitchen-cam/src/kitchen_cam/*").match(
        "kitchen-cam/src/kitchen_cam/machining.py")
    assert not g("kitchen-cam/src/kitchen_cam/*.py").match(
        "kitchen-cam/src/kitchen_cam/dxf/panel_dxf.py")  # * stops at /


def test_verdict_rule_traced_needs_two_sources_including_a_test() -> None:
    """TRACED >= 2 sources incl a test; 1+ = MENTIONED; 0 = DARK
    (concept II.7 R2 as fixed by the spec's mechanism notes)."""
    rows, _ = coverage_audit.audit()
    for r in rows.values():
        n = len(r["sources"])
        if r["verdict"] == "TRACED":
            assert n >= 2 and "tests" in r["sources"]
        elif r["verdict"] == "MENTIONED":
            assert n >= 1
            assert not (n >= 2 and "tests" in r["sources"])
        else:
            assert n == 0


def test_committed_inventory_is_fresh() -> None:
    """docs/code-inventory.json matches a regeneration at HEAD — the
    committed HAVE denominator cannot silently rot (wk-9fb28a32)."""
    committed = (REPO / "docs/code-inventory.json").read_text(encoding="utf-8")
    regen = json.dumps(code_inventory.walk(), indent=2, sort_keys=True) + "\n"
    assert committed == regen, (
        "docs/code-inventory.json is stale — run python3 "
        "scripts/code-inventory.py and commit it")
