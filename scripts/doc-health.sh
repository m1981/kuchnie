#!/usr/bin/env bash
# doc-health: judge the live markdown corpus for the two decay modes the
# 2026-07-09 doc sweep actually found — dead component names and broken
# relative links. Sibling of spec-health.sh (which judges cited ledger ids);
# this script judges the prose fabric around them.
#
# Scope: git-tracked *.md only. History is exempt (archive/, attic/, ADRs,
# docs/freeze/, CHANGELOGs) — old names and dead paths are the POINT there.
# ADR rename files are cited by wildcard (docs/adr/009-*.md) per convention,
# so a live doc never needs to spell a dead component name.
#
# Checks:
#   A  dead component names (ADR-009/010/011) on any live line
#   B  relative markdown links whose target does not exist (anchors stripped;
#      http/mailto/anchor-only/wildcard targets skipped)
# Backtick path mentions are NOT checked — shorthand like `kuchnie_core/x.py`
# is endemic and legitimate; links are the load-bearing references.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Same exemption surface as check-governance.sh Check 1.
FILES="$(git ls-files '*.md' | grep -vE '^(docs/archive/|attic/|docs/adr/|catalog/docs/adr/|docs/freeze/|features/archive/)' | grep -vE '(^|/)(docs/archive/|docs/archived/)' | grep -vE '(^|.*)CHANGELOG' || true)"

export FILES

python3 - <<'PY'
import os, re, sys
from pathlib import Path

DEAD = re.compile(r'kitchen[-_](cad|plugin|app)\b', re.IGNORECASE)
LINK = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)\)')

failures = 0
files = [f for f in os.environ["FILES"].splitlines() if f.strip()]
for f in files:
    text = Path(f).read_text(encoding="utf-8")
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        m = DEAD.search(line)
        if m:
            hits.append(f"  FAIL  dead component name '{m.group(0)}' (line {i}) -- renamed per ADR-009/010/011; cite ADRs as docs/adr/NNN-*.md")
        for lm in LINK.finditer(line):
            target = lm.group(1).split('#', 1)[0]
            if not target or '://' in target or target.startswith('mailto:') or '*' in target:
                continue
            # leading / means repo-root-relative in this repo's docs
            resolved = Path(target.lstrip('/')) if target.startswith('/') else Path(f).parent / target
            if not resolved.exists():
                hits.append(f"  FAIL  broken link '{lm.group(1)}' (line {i}) -- target missing")
    if hits:
        print(f)
        print("\n".join(hits))
        failures += len(hits)

print(f"doc-health: {failures} failure(s) across {len(files)} live doc(s)")
sys.exit(1 if failures else 0)
PY
