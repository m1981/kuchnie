#!/usr/bin/env python3
"""Scaffold a new golden-first e2e exercise.

Usage:  .venv/bin/python exercises/harness/scaffold.py <scenario-name>

Creates exercises/<scenario-name>/ with GOLDEN.md, golden/panels.csv,
blender_leg.py, run_production_leg.py, GAP-REPORT.md and generated/ —
pre-wired to exercises/harness. Refuses to overwrite an existing exercise
(goldens are immutable per run; a new design gets a new directory).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
EXERCISES = HERE.parent


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    name = sys.argv[1]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        print(f"scaffold: name '{name}' must be kebab-case ([a-z0-9-])")
        return 2
    target = EXERCISES / name
    if target.exists():
        print(f"scaffold: {target} already exists — goldens are immutable "
              f"per run; pick a new scenario name")
        return 1

    (target / "golden").mkdir(parents=True)
    (target / "generated").mkdir()
    for tmpl in TEMPLATES.iterdir():
        if not tmpl.name.endswith(".tmpl"):
            continue
        rel = tmpl.name[:-len(".tmpl")]
        dest = target / rel.replace("__", "/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tmpl.read_text().replace("{{NAME}}", name))
        print(f"  created {dest.relative_to(EXERCISES.parent)}")
    print(f"\nNext (docs/e2e-exercise-convention.md):")
    print(f"  1. file the wk issue (scripts/truth issue ... --premise ...)")
    print(f"  2. author GOLDEN.md + golden/panels.csv BY HAND, before any tool")
    print(f"  3. blender leg:  /Applications/Blender.app/Contents/MacOS/Blender"
          f" --background --enable-autoexec --python exercises/{name}/blender_leg.py")
    print(f"  4. verify:       home_builder_5 dev_tools/inspection --open ...")
    print(f"  5. production:   .venv/bin/python exercises/{name}/run_production_leg.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
