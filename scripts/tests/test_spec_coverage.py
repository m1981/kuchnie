"""Pinned tests for the spec-coverage matrix slice (conformance-join).

Covers scripts/spec-coverage.py: id extraction, component grouping, and
the structural contract of the --json output (both axes present, verdict
rollup consistent with coverage-audit, forward-trace modules confined to
the inventory).
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


spec_coverage = _load("spec-coverage.py")
coverage_audit = _load("coverage-audit.py")


def test_id_regex_and_component_grouping() -> None:
    ids = spec_coverage.ID_RE.findall(
        "stands on tr-4f3bd57d and wk-593a317b, not tr-XYZ or wk-123")
    assert ids == ["tr-4f3bd57d", "wk-593a317b"]
    assert spec_coverage.component(
        "kuchnie-core/src/kuchnie_core/model.py") == "kuchnie-core"
    assert spec_coverage.component("catalog/api.py") == "catalog"


def test_json_output_contract() -> None:
    proc = subprocess.run(
        ["python3", "scripts/spec-coverage.py", "--json"],
        cwd=REPO, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert set(data) == {"components", "specs"}

    rows, _ = coverage_audit.audit()
    inventory = set(rows)
    # rollup axis: every inventoried module is counted in its component
    total = sum(sum(v.values()) for v in data["components"].values())
    assert total == len(inventory)
    for v in data["components"].values():
        assert set(v) == {"TRACED", "MENTIONED", "DARK"}

    # forward axis: every spec row is well-formed and reaches only
    # inventoried modules; no ids cited means nothing reached
    assert data["specs"], "spec sweep found no specs"
    for s in data["specs"]:
        assert {"spec", "uc", "ids", "live", "dead",
                "modules", "components"} <= set(s)
        assert set(s["modules"]) <= inventory
        if s["ids"] == 0:
            assert s["modules"] == []
        assert s["components"] == sorted(
            {spec_coverage.component(m) for m in s["modules"]})
