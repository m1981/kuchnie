#!/usr/bin/env python3
"""Ubiquitous-language check — code vocabulary vs docs/GLOSSARY.md.

Three findings, per the glossary's own contract ("if you introduce a new
domain class in code, add it here in the same commit"):

  missing-term    a DOMAIN-SURFACE class absent from the glossary.
                  Domain surface = kuchnie_core __init__ exports
                  + kitchen-erp SQLModel entities + any cross-context
                  collision name (NOT every dataclass/DTO/UI model).
  dead-record     a glossary entry whose "File of record" path no longer
                  exists (term may have moved or died).
  collision       the same public class name defined in >= 2 components
                  without a "Not to be confused with" line in its
                  glossary entry — the ubiquitous-language violation.

The committed baseline (docs/glossary-baseline.txt) is the accepted debt;
gate 63-glossary-drift.sh WARNs only on NEW lines.

Usage: python3 scripts/glossary-check.py [--write]
"""
import ast
import re
import sys
from pathlib import Path
from collections import defaultdict

GLOSSARY = Path("docs/GLOSSARY.md")
BASELINE = Path("docs/glossary-baseline.txt")
ROOTS = {"core": Path("kuchnie-core/src/kuchnie_core"),
         "erp": Path("kitchen-erp/kitchen_erp"),
         "cam": Path("kitchen-cam"),
         "adapter": Path("home-builder-adapter/src"),
         "catalog": Path("catalog"),
         "compositor": Path("krono-compositor-mvp")}
SKIP = ("test", "attic", "archive", "node_modules", ".venv",
        "migrations", "__pycache__")


def findings() -> list[str]:
    out = []
    text = GLOSSARY.read_text(encoding="utf-8")
    # strip fenced code blocks so the entry-format example doesn't count
    unfenced = re.sub(r"```.*?```", "", text, flags=re.S)
    # a heading may disambiguate several terms: "## A / B / C"
    terms = {w for h in re.findall(r"^## ([\w /-]+)$", unfenced, re.M)
             for w in re.findall(r"\w+", h)}

    classes: dict[str, set[str]] = defaultdict(set)
    sqlmodels, core_exports = set(), set()
    for comp, root in ROOTS.items():
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if any(s in str(p).lower() for s in SKIP):
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for n in tree.body:
                if isinstance(n, ast.ClassDef) and not n.name.startswith("_"):
                    classes[n.name].add(comp)
                    if any(isinstance(b, ast.Name) and b.id == "SQLModel"
                           for b in n.bases):
                        sqlmodels.add(n.name)
    init = ROOTS["core"] / "__init__.py"
    for n in ast.walk(ast.parse(init.read_text(encoding="utf-8"))):
        if isinstance(n, ast.ImportFrom):
            core_exports.update(a.asname or a.name for a in n.names)

    collisions = {n for n, comps in classes.items() if len(comps) >= 2}
    surface = (core_exports & set(classes)) | sqlmodels | collisions

    for name in sorted(surface - terms):
        out.append(f"missing-term  {name}  ({', '.join(sorted(classes[name]))})")
    for m in re.finditer(r"^## ([\w /-]+)$([\s\S]*?)(?=^## |\Z)", unfenced, re.M):
        head, body = m.group(1), m.group(2)
        rec = re.search(r"File of record:\*{0,2}\s*`([^`:]+)", body)
        if rec and not Path(rec.group(1).strip()).exists():
            out.append(f"dead-record   {head.strip()}  ({rec.group(1).strip()})")
        for term in re.findall(r"\w+", head):
            if term in collisions and "Not to be confused with" not in body:
                out.append(f"collision     {term}  defined in "
                           f"{', '.join(sorted(classes[term]))} — entry lacks "
                           f"'Not to be confused with'")
    for name in sorted(collisions - terms):
        out.append(f"collision     {name}  defined in "
                   f"{', '.join(sorted(classes[name]))} — no glossary entry")
    return sorted(out)


if __name__ == "__main__":
    lines = findings()
    body = "\n".join(lines) + "\n" if lines else ""
    if "--write" in sys.argv:
        BASELINE.write_text(body, encoding="utf-8")
        print(f"wrote {BASELINE} ({len(lines)} accepted finding(s))")
    else:
        sys.stdout.write(body)
