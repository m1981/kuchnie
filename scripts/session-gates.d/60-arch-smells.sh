#!/usr/bin/env bash
# Architecture-smell watch: WARN on the mechanically detectable smells the
# 2026-07-16 signature review found (docs/pattern-conformance.md § Re-running
# this review). WARN-only by design, same posture as 50-new-dark.sh —
# promoting to FAIL is Michał's call. Never exits non-zero.
# Detects, per component package (kuchnie_core, kitchen_erp):
#   1. mutual-import module pairs (incl. deferred imports inside functions)
#   2. cross-module imports of _underscore-private names
#   3. the same deferred import repeated 3+ times in one module
cd "$(git rev-parse --show-toplevel)"
python3 - <<'PY'
import ast
from collections import Counter
from pathlib import Path

PACKAGES = {
    "kuchnie_core": Path("kuchnie-core/src/kuchnie_core"),
    "kitchen_erp": Path("kitchen-erp/kitchen_erp"),
}
warnings = []

for pkg, root in PACKAGES.items():
    if not root.exists():
        continue
    files = [p for p in root.rglob("*.py")
             if "test" not in p.name and p.name != "__init__.py"]
    modnames = {p.stem for p in files}
    imports: dict[str, set[str]] = {}
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        mod = path.stem
        sibs, repeated = set(), Counter()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            target = node.module.split(".")[-1]
            is_sibling = (node.level >= 1 or node.module.startswith(pkg)) \
                and target in modnames and target != mod
            if not is_sibling:
                continue
            sibs.add(target)
            names = ", ".join(a.name for a in node.names)
            repeated[f"from {target} import {names}"] += 1
            for a in node.names:
                if a.name.startswith("_"):
                    warnings.append(
                        f"private-import  {pkg}/{mod}.py imports "
                        f"{target}.{a.name} (underscore contract across modules)")
        imports[mod] = sibs
        for stmt, n in repeated.items():
            if n >= 3:
                warnings.append(
                    f"repeat-import   {pkg}/{mod}.py repeats '{stmt}' {n}x "
                    f"(hoist it or split the module)")
    for a, targets in sorted(imports.items()):
        for b in sorted(targets):
            if a < b and a in imports.get(b, set()):
                warnings.append(
                    f"import-cycle    {pkg}: {a}.py <-> {b}.py import each "
                    f"other (deferred imports count)")

if warnings:
    print(f"arch-smells: WARN {len(warnings)} finding(s) "
          "(mechanical layer of the signature review):")
    for w in warnings:
        print(f"  WARN  {w}")
else:
    print("arch-smells: 0 findings")
raise SystemExit(0)
PY
