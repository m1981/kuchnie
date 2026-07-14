#!/usr/bin/env python3
"""coverage-audit — the R2-lite backward-trace join (ISO/IEC/IEEE 24765).

Joins the module inventory (the HAVE enumerator, scripts/code-inventory.py,
regenerated in-memory so the audit judges HEAD, not the committed snapshot)
against four trace sources:

  1. claim evidence_paths in .truth/claims.jsonl (non-retracted claims)
  2. feature-spec mentions (*/docs/specs/*.md + docs/specs/*.md)
  3. docs/capability-map.csv + docs/roadmap-map.csv
  4. test files (six components' tests + exercises/harness/tests + scripts/tests)

Verdict per module (concept doc §II.7 R2):
  TRACED    >= 2 sources, one of them a test
  MENTIONED >= 1 source otherwise
  DARK      0 sources

"Leave it dark" is not an emittable state — the DARK list goes to the
product owner for the adopt/attic/delete triage (a human verb; this script
never moves code). Spec: docs/specs/conformance-join.md (wk-9fb28a32).

Usage:
  python3 scripts/coverage-audit.py            # full report
  python3 scripts/coverage-audit.py --counts   # one line: TRACED=x MENTIONED=y DARK=z
  python3 scripts/coverage-audit.py --json     # {module: verdict}
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "code_inventory", REPO / "scripts" / "code-inventory.py")
code_inventory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(code_inventory)

TEST_ROOTS = [
    "kuchnie-core/tests", "kitchen-cam/tests", "kitchen-erp/tests",
    "home-builder-adapter/tests", "catalog/tests",
    "krono-compositor-mvp/tests", "exercises/harness/tests", "scripts/tests",
]


def _glob_re(pat: str) -> re.Pattern:
    out = []
    i = 0
    while i < len(pat):
        if pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif pat[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pat[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pat[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def claim_globs() -> list[re.Pattern]:
    """evidence_paths of non-retracted claims, as compiled glob regexes."""
    status: dict[str, str] = {}
    try:
        rows = json.loads(subprocess.run(
            ["scripts/truth", "list", "--json"], cwd=REPO,
            capture_output=True, text=True, timeout=60).stdout or "[]")
        status = {r["id"]: r["status"] for r in rows}
    except (json.JSONDecodeError, OSError):
        pass
    pats: set[str] = set()
    ledger = REPO / ".truth" / "claims.jsonl"
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("kind") != "claim":
                continue
            if status.get(ev.get("id", "")) == "retracted":
                continue
            for p in ev.get("payload", {}).get("evidence_paths") or []:
                pats.add(p)
    return [_glob_re(p) for p in sorted(pats)]


def spec_text() -> str:
    parts = []
    for f in sorted(REPO.rglob("docs/specs/*.md")):
        rel = f.relative_to(REPO)
        if any(p in {"attic", "node_modules", ".venv", "archive"}
               for p in rel.parts):
            continue
        parts.append(f.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def maps_text() -> str:
    parts = []
    for name in ("docs/capability-map.csv", "docs/roadmap-map.csv"):
        f = REPO / name
        if f.exists():
            parts.append(f.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def tests_text() -> str:
    parts = []
    for root in TEST_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            parts.append(f.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def audit() -> tuple[dict[str, dict], int]:
    """{module: {verdict, sources}} for judged modules, + skipped count.

    Definition-less __init__.py files are skipped (package markers and
    re-export shims, not units of behavior).
    """
    inv = code_inventory.walk()
    globs = claim_globs()
    specs = spec_text()
    maps = maps_text()
    tests = tests_text()
    out: dict[str, dict] = {}
    skipped = 0
    for rel, entry in sorted(inv.items()):
        if (rel.endswith("__init__.py") and not entry["classes"]
                and not entry["functions"]):
            skipped += 1
            continue
        dotted = entry["dotted"]
        alt = dotted.split(".", 1)[1] if "." in dotted else ""
        needles = [n for n in (rel, dotted, alt if "." in alt else "") if n]
        sources = set()
        if any(g.match(rel) for g in globs):
            sources.add("claims")
        if any(n in specs for n in needles):
            sources.add("specs")
        if any(n in maps for n in needles):
            sources.add("maps")
        if any(n in tests for n in needles):
            sources.add("tests")
        if len(sources) >= 2 and "tests" in sources:
            verdict = "TRACED"
        elif sources:
            verdict = "MENTIONED"
        else:
            verdict = "DARK"
        out[rel] = {"verdict": verdict, "sources": sorted(sources)}
    return out, skipped


def main() -> int:
    rows, skipped = audit()
    counts = {"TRACED": 0, "MENTIONED": 0, "DARK": 0}
    for r in rows.values():
        counts[r["verdict"]] += 1
    if "--json" in sys.argv:
        print(json.dumps({m: r["verdict"] for m, r in rows.items()},
                         indent=2, sort_keys=True))
        return 0
    if "--counts" in sys.argv:
        print(f"TRACED={counts['TRACED']} MENTIONED={counts['MENTIONED']} "
              f"DARK={counts['DARK']}")
        return 0
    print("coverage-audit (R2-lite): inventory vs {claims, specs, maps, tests}")
    for verdict in ("DARK", "MENTIONED", "TRACED"):
        mods = [m for m, r in rows.items() if r["verdict"] == verdict]
        print(f"\n{verdict} ({len(mods)}):")
        for m in mods:
            src = ",".join(rows[m]["sources"]) or "-"
            print(f"  {m}  [{src}]")
    print(f"\ncoverage-audit: TRACED {counts['TRACED']} · "
          f"MENTIONED {counts['MENTIONED']} · DARK {counts['DARK']} "
          f"({skipped} definition-less __init__ skipped; triage of DARK is "
          f"adopt/attic/delete — a product-owner decision)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
