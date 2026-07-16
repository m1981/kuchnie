#!/usr/bin/env python3
"""Shared vocabulary literals — the raw material of stringly-typed protocols.

Emits one line per identifier-like string literal (len 6-30, snake/CONST/
kebab case) that appears in >= 3 production modules of one component
package. Each is a de-facto shared constant living as scattered copies —
the dual-LW / dolna_* / module_kind failure family.

The committed baseline (docs/shared-literals-baseline.txt) is today's
accepted debt; gate 62-vocab-drift.sh WARNs only on NEW entries, so the
list can only be grown deliberately.

Usage: python3 scripts/shared-literals.py [--write]
"""
import ast
import re
import sys
from pathlib import Path

PACKAGES = {
    "kuchnie_core": Path("kuchnie-core/src/kuchnie_core"),
    "kitchen_erp": Path("kitchen-erp/kitchen_erp"),
}
BASELINE = Path("docs/shared-literals-baseline.txt")
IDENTIFIERISH = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{5,29}$")


def collect() -> list[str]:
    lines = []
    for pkg, root in PACKAGES.items():
        share: dict[str, set[str]] = {}
        for p in root.rglob("*.py"):
            if "test" in p.name or p.name == "__init__.py":
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                        and IDENTIFIERISH.match(n.value)):
                    share.setdefault(n.value, set()).add(p.stem)
        for s, mods in share.items():
            if len(mods) >= 3:
                lines.append(f"{pkg}  {s}  [{', '.join(sorted(mods))}]")
    return sorted(lines)


if __name__ == "__main__":
    out = "\n".join(collect()) + "\n"
    if "--write" in sys.argv:
        BASELINE.write_text(out, encoding="utf-8")
        print(f"wrote {BASELINE} ({out.count(chr(10))} entries)")
    else:
        sys.stdout.write(out)
