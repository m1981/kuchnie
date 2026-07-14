#!/usr/bin/env python3
"""code-inventory — the HAVE enumerator (R2 backward trace, ISO/IEC/IEEE 24765).

AST-walks the six component source trees and emits docs/code-inventory.json:
one entry per module (repo-relative path) with its top-level classes and
functions. Deterministic (sorted keys, sorted names, no timestamps) so the
committed file diffs cleanly and re-running with no source change is
byte-stable. Spec: docs/specs/conformance-join.md (wk-9fb28a32); concept:
docs/reviews/two-ledger-concept-2026-07-15.md §II.6.

Usage:
  python3 scripts/code-inventory.py            # (re)write docs/code-inventory.json
  python3 scripts/code-inventory.py --stdout   # print instead of writing

The inventory is an enumerator, not a judge — verdicts (TRACED/MENTIONED/
DARK) come from scripts/coverage-audit.py.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "code-inventory.json"

# The six component source roots (ground truth tr-076ed1ea) with the prefix
# each strips to form the dotted name tests/specs import it by.
ROOTS: list[tuple[str, str]] = [
    ("kuchnie-core/src", "kuchnie-core/src"),
    ("kitchen-cam/src", "kitchen-cam/src"),
    ("kitchen-erp/kitchen_erp", "kitchen-erp"),
    ("home-builder-adapter/src", "home-builder-adapter"),
    ("catalog", ""),  # imported as catalog.* (and scripts.* in its own venv)
    ("krono-compositor-mvp/src", "krono-compositor-mvp/src"),
]
EXCLUDE_PARTS = {"__pycache__", "tests", "test", "node_modules", ".venv",
                 "venv", "attic", "archive", "public", "data"}


def walk() -> dict[str, dict]:
    inv: dict[str, dict] = {}
    for root, strip in ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.py")):
            rel = f.relative_to(REPO)
            if any(p in EXCLUDE_PARTS or p.endswith(".egg-info")
                   for p in rel.parts):
                continue
            dotted = str(rel)[len(strip):].lstrip("/") if strip else str(rel)
            dotted = dotted[:-3].replace("/", ".")
            if dotted.endswith(".__init__"):
                dotted = dotted[: -len(".__init__")]
            entry: dict = {"component": root.split("/")[0],
                           "dotted": dotted, "classes": [], "functions": []}
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                entry["parse_error"] = True
            else:
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        entry["classes"].append(node.name)
                    elif isinstance(node, (ast.FunctionDef,
                                           ast.AsyncFunctionDef)):
                        entry["functions"].append(node.name)
                entry["classes"].sort()
                entry["functions"].sort()
            inv[str(rel)] = entry
    return inv


def main() -> int:
    text = json.dumps(walk(), indent=2, sort_keys=True) + "\n"
    if "--stdout" in sys.argv:
        sys.stdout.write(text)
        return 0
    OUT.write_text(text, encoding="utf-8")
    n = text.count('"dotted"')
    print(f"wrote {OUT} ({n} modules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
