#!/usr/bin/env bash
# Architecture-smell watch: WARN on the mechanically detectable smells the
# 2026-07-16 signature review found (docs/pattern-conformance.md § Re-running
# this review). WARN-only by design, same posture as 50-new-dark.sh —
# promoting to FAIL is Michał's call. Never exits non-zero.
# Detects, per component package (kuchnie_core, kitchen_erp):
#   1. mutual-import module pairs (incl. deferred imports inside functions)
#   2. cross-module imports of _underscore-private names
#   3. the same deferred import repeated 3+ times in one module
#   4. dormant classes: public class with >= 3 methods referenced by no
#      other production module repo-wide and exported by no __init__
#      (the CabinetGeometry family — dead geometry twins)
#   5. god classes: >= 25 methods (the KitchenState family)
#   6. duplicate module-level def names across modules (the dual-LW
#      formula family, ADR-006)
#   7. unit-suffix lint (kuchnie_core only): dimension-named parameters
#      without a unit suffix — unit ambiguity is how CAM scraps boards
#   8. param bloat: functions taking >= 8 parameters (parameter-object
#      candidates)
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
dormant_candidates: list[tuple[str, Path, str]] = []

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

    # 4-6: class/def surface smells (one more pass, cheap)
    texts = {p: p.read_text(encoding="utf-8") for p in files}
    toplevel_defs: dict[str, list[str]] = {}
    for path in files:
        try:
            tree = ast.parse(texts[path])
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                if len(methods) >= 25:
                    warnings.append(
                        f"god-class       {pkg}/{path.stem}.py: {node.name} has "
                        f"{len(methods)} methods (split responsibilities)")
                if not node.name.startswith("_") and len(methods) >= 3:
                    dormant_candidates.append((pkg, path, node.name))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_") and len(node.args.args) > 0:
                    toplevel_defs.setdefault(node.name, []).append(path.stem)
        # 7-8: signature hygiene over EVERY def, nested included
        DIM = {"width", "height", "depth", "length", "offset",
               "thickness", "clearance", "radius", "diameter"}
        UNIT_SUFFIX = ("_mm", "_m", "_m2", "_lm", "_deg", "_rad", "_kg")
        NON_DIM_SUFFIX = ("_code", "_count", "_id", "_key", "_name")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            nparams = len(node.args.posonlyargs) + len(node.args.args) \
                + len(node.args.kwonlyargs)
            if nparams >= 8:
                warnings.append(
                    f"param-bloat     {pkg}/{path.stem}.py: {node.name}() takes "
                    f"{nparams} parameters (parameter-object candidate)")
            if pkg != "kuchnie_core":
                continue
            for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
                base = a.arg.split("_")[0]
                if base in DIM and not a.arg.endswith(UNIT_SUFFIX) \
                        and not a.arg.endswith(NON_DIM_SUFFIX):
                    warnings.append(
                        f"unit-suffix     {pkg}/{path.stem}.py: "
                        f"{node.name}({a.arg}) — dimension parameter without "
                        f"a unit suffix (mm? m? scrap risk)")
    for name, mods in sorted(toplevel_defs.items()):
        if len(mods) > 1:
            warnings.append(
                f"dup-def         {pkg}: def {name}() defined at module level "
                f"in {', '.join(sorted(mods))} (dual-source formula risk, ADR-006)")

# dormant-class needs the repo-wide production corpus (a class consumed by
# another component, a subpackage __init__, or kitchen-cam is not dormant)
CORPUS_ROOTS = [Path("kuchnie-core/src"), Path("kitchen-erp/kitchen_erp"),
                Path("kitchen-cam"), Path("home-builder-adapter/src"),
                Path("catalog")]
corpus: dict[Path, str] = {}
for cr in CORPUS_ROOTS:
    if cr.exists():
        for p in cr.rglob("*.py"):
            if "test" not in p.name and "/tests/" not in str(p):
                corpus[p] = p.read_text(encoding="utf-8", errors="ignore")
for pkg, path, name in dormant_candidates:
    refs = sum(1 for p, t in corpus.items() if p != path and name in t)
    # same-file AST references (annotations, factory dicts, instantiation)
    # keep a class alive; docstring examples are strings, not Name nodes
    tree = ast.parse(corpus.get(path, path.read_text(encoding="utf-8")))
    own = sum(1 for n in ast.walk(tree)
              if isinstance(n, ast.Name) and n.id == name)
    if refs == 0 and own == 0:
        warnings.append(
            f"dormant-class   {pkg}/{path.stem}.py: {name} (>=3 methods) has "
            f"no production reference outside its file repo-wide "
            f"(dead twin candidate)")

if warnings:
    print(f"arch-smells: WARN {len(warnings)} finding(s) "
          "(mechanical layer of the signature review):")
    for w in warnings:
        print(f"  WARN  {w}")
else:
    print("arch-smells: 0 findings")
raise SystemExit(0)
PY
