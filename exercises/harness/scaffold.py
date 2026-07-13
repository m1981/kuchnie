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


def create_exercise(name: str, exercises_dir: Path = EXERCISES) -> Path:
    """Create an exercise directory from templates.

    Pure function of (name, dest) so tests can scaffold into a tmp dir.
    Raises ValueError on a bad name, FileExistsError on an existing target
    (goldens are immutable per run — a new design gets a new directory).
    """
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise ValueError(f"name '{name}' must be kebab-case ([a-z0-9-])")
    target = exercises_dir / name
    if target.exists():
        raise FileExistsError(str(target))

    (target / "golden").mkdir(parents=True)
    (target / "generated").mkdir()
    for tmpl in sorted(TEMPLATES.iterdir()):
        if not tmpl.name.endswith(".tmpl"):
            continue
        rel = tmpl.name[:-len(".tmpl")]
        dest = target / rel.replace("__", "/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tmpl.read_text().replace("{{NAME}}", name))
    return target


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    name = sys.argv[1]
    try:
        target = create_exercise(name)
    except ValueError as e:
        print(f"scaffold: {e}")
        return 2
    except FileExistsError as e:
        print(f"scaffold: {e} already exists — goldens are immutable "
              f"per run; pick a new scenario name")
        return 1
    for f in sorted(target.rglob("*")):
        if f.is_file():
            print(f"  created {f.relative_to(EXERCISES.parent)}")
    print(f"\nNext (docs/e2e-exercise-convention.md):")
    print(f"  1. file the wk issue (scripts/truth issue ... --premise ...)")
    print(f"  2. author GOLDEN.md + golden/*.csv BY HAND, before any tool")
    print(f"  3. one-command run:  .venv/bin/python exercises/harness/runner.py"
          f" {name}   [--strict|--skip-blender]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
