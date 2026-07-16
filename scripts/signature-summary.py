#!/usr/bin/env python3
"""Deterministic signature summary of the architecture-review surface.

Emits one sorted line per module-level def/class/method so that
`git diff` on the committed baseline (docs/architecture-signatures.txt)
shows exactly WHERE the API surface moved. This is the mechanical
tripwire of the signature review (docs/pattern-conformance.md
§ Re-running this review); the judgment pass itself stays with
`find ... | pysum --pipe` and an architect.

Usage: python3 scripts/signature-summary.py [--write]
  --write   rewrite docs/architecture-signatures.txt in place
"""
import ast
import sys
from pathlib import Path

PACKAGES = {
    "kuchnie_core": Path("kuchnie-core/src/kuchnie_core"),
    "kitchen_erp": Path("kitchen-erp/kitchen_erp"),
}
BASELINE = Path("docs/architecture-signatures.txt")


def sig(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args]
    if a.vararg:
        names.append("*" + a.vararg.arg)
    names += [x.arg for x in a.kwonlyargs]
    if a.kwarg:
        names.append("**" + a.kwarg.arg)
    return f"{fn.name}({', '.join(names)})"


def summarize() -> list[str]:
    lines = []
    for pkg, root in PACKAGES.items():
        for path in sorted(root.rglob("*.py")):
            if "test" in path.name or path.name == "__init__.py":
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                lines.append(f"{pkg}/{path.name}  <SYNTAX ERROR>")
                continue
            mod = f"{pkg}/{path.relative_to(root)}"
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lines.append(f"{mod}  def {sig(node)}")
                elif isinstance(node, ast.ClassDef):
                    bases = ", ".join(ast.unparse(b) for b in node.bases)
                    lines.append(f"{mod}  class {node.name}({bases})")
                    for sub in node.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            lines.append(f"{mod}    {node.name}.{sig(sub)}")
    return sorted(lines)


if __name__ == "__main__":
    out = "\n".join(summarize()) + "\n"
    if "--write" in sys.argv:
        BASELINE.write_text(out, encoding="utf-8")
        print(f"wrote {BASELINE} ({out.count(chr(10))} lines)")
    else:
        sys.stdout.write(out)
