#!/usr/bin/env python3
"""spec-coverage — the R2 join re-cut per spec and per component.

Where coverage-audit.py answers "is each module traced by *anything*"
(repo-wide totals), this script answers the two questions it aggregates
away:

  1. Per COMPONENT: how much of its source inventory is TRACED /
     MENTIONED / DARK (backward trace, same verdicts as coverage-audit).
  2. Per SPEC: which ledger ids it cites, how many are live, and which
     source modules those live claims' evidence_paths actually reach
     (forward trace: spec -> tr-id -> evidence_paths -> module).

The chain is the repo's convention (docs/spec-convention.md): specs
carry facts only as ledger ids; claims carry evidence_paths; so
spec->code traceability is a JOIN, never a prose assertion. This script
is an enumerator, not a judge — it moves no code and edits no specs.

Usage:
  python3 scripts/spec-coverage.py            # full report
  python3 scripts/spec-coverage.py --json     # machine-readable
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts" / f"{name.replace('_', '-')}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

code_inventory = _load("code_inventory")
coverage_audit = _load("coverage_audit")

ID_RE = re.compile(r"\b(?:tr|wk)-[0-9a-f]{8}\b")
UC_RE = re.compile(r"Serves:\s*(UC-\d+)")

LIVE = {"live"}
DEAD = {"stale", "diverged", "retracted", "cancelled"}


def component(rel: str) -> str:
    return rel.split("/", 1)[0]


def ledger_status() -> dict[str, str]:
    out: dict[str, str] = {}
    for cmd in (["scripts/truth", "list", "--json"],
                ["scripts/truth", "issues", "--json"]):
        try:
            rows = json.loads(subprocess.run(
                cmd, cwd=REPO, capture_output=True, text=True,
                timeout=60).stdout or "[]")
            out.update({r["id"]: r["status"] for r in rows})
        except (json.JSONDecodeError, OSError, KeyError):
            pass
    return out


def claim_paths() -> dict[str, list[str]]:
    """id -> evidence_paths, from claim records (last record wins)."""
    paths: dict[str, list[str]] = {}
    ledger = REPO / ".truth" / "claims.jsonl"
    if not ledger.exists():
        return paths
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("kind") == "claim":
            ep = ev.get("payload", {}).get("evidence_paths") or []
            paths[ev.get("id", "")] = ep
    return paths


def specs() -> list[Path]:
    out = []
    for f in sorted(REPO.rglob("docs/specs/*.md")):
        rel = f.relative_to(REPO)
        if any(p in {"attic", "node_modules", ".venv", "archive"}
               for p in rel.parts):
            continue
        out.append(f)
    return out


def main() -> int:
    status = ledger_status()
    id_paths = claim_paths()
    rows, _ = coverage_audit.audit()
    inventory = set(rows)

    # 1 · backward: component rollup of coverage-audit verdicts
    comp: dict[str, dict[str, int]] = defaultdict(
        lambda: {"TRACED": 0, "MENTIONED": 0, "DARK": 0})
    for rel, r in rows.items():
        comp[component(rel)][r["verdict"]] += 1

    # 2 · forward: spec -> ids -> live evidence_paths -> modules
    spec_rows = []
    for f in specs():
        text = f.read_text(encoding="utf-8", errors="replace")
        ids = sorted(set(ID_RE.findall(text)))
        live = [i for i in ids if status.get(i) in LIVE]
        dead = [i for i in ids if status.get(i) in DEAD or
                (i not in status and i.startswith("tr-"))]
        reached: set[str] = set()
        for i in live:
            for pat in id_paths.get(i, []):
                g = coverage_audit._glob_re(pat)
                reached |= {rel for rel in inventory if g.match(rel)}
        spec_rows.append({
            "spec": str(f.relative_to(REPO)),
            "uc": UC_RE.search(text).group(1) if UC_RE.search(text) else "",
            "ids": len(ids), "live": len(live), "dead": len(dead),
            "modules": sorted(reached),
            "components": sorted({component(r) for r in reached}),
        })

    if "--json" in sys.argv:
        print(json.dumps({"components": comp, "specs": spec_rows},
                         indent=2, sort_keys=True))
        return 0

    print("spec-coverage: backward (component) + forward (spec) trace\n")
    print(f"{'component':<24} {'mods':>4} {'TRACED':>7} {'MENT':>5} "
          f"{'DARK':>5}  traced%")
    for c in sorted(comp):
        v = comp[c]
        n = sum(v.values())
        pct = 100 * v["TRACED"] / n if n else 0
        print(f"{c:<24} {n:>4} {v['TRACED']:>7} {v['MENTIONED']:>5} "
              f"{v['DARK']:>5}  {pct:5.0f}%")

    print(f"\n{'spec':<44} {'uc':<6} {'ids':>3} {'live':>4} {'dead':>4} "
          f" reaches")
    for s in spec_rows:
        name = Path(s["spec"]).name
        tgt = ",".join(s["components"]) or "-"
        flag = " ⚠DEAD" if s["dead"] else ""
        print(f"{name:<44} {s['uc'] or '—':<6} {s['ids']:>3} "
              f"{s['live']:>4} {s['dead']:>4}  {len(s['modules'])} module(s)"
              f" in {tgt}{flag}")

    orphans = [s for s in spec_rows if s["ids"] and not s["modules"]]
    if orphans:
        print("\nspecs whose live claims reach no source module "
              "(evidence anchored in docs/tests only):")
        for s in orphans:
            print(f"  {s['spec']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
