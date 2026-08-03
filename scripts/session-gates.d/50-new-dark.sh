#!/usr/bin/env bash
# New-dark watch (R2): WARN when a module absent from the committed
# docs/code-inventory.json arrives DARK (zero trace sources). WARN-only by
# design — promoting this to FAIL is Michał's call (docs/specs/
# conformance-join.md, gate posture note). Never exits non-zero.
# Detail runs: python3 scripts/coverage-audit.py ; scripts/code-inventory.py
# BLIND-SPOT: it compares against the committed inventory, so a module that was already dark when the baseline was taken stays invisible.
#   It watches the derivative, not the level.
cd "$(git rev-parse --show-toplevel)"
python3 - <<'PY'
import importlib.util, json, subprocess
from pathlib import Path

committed = Path("docs/code-inventory.json")
if not committed.exists():
    print("new-dark: WARN docs/code-inventory.json missing -- run "
          "python3 scripts/code-inventory.py and commit it")
    raise SystemExit(0)
known = set(json.loads(committed.read_text(encoding="utf-8")))
verdicts = json.loads(subprocess.run(
    ["python3", "scripts/coverage-audit.py", "--json"],
    capture_output=True, text=True, timeout=120).stdout or "{}")
new_dark = sorted(m for m, v in verdicts.items()
                  if v == "DARK" and m not in known)
if new_dark:
    print(f"new-dark: WARN {len(new_dark)} new module(s) arrived DARK "
          "(no claim/spec/map/test traces; regenerate + commit the "
          "inventory after triage):")
    for m in new_dark:
        print(f"  WARN  {m}")
else:
    print("new-dark: 0 new dark module(s)")
raise SystemExit(0)
PY
