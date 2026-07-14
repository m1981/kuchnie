#!/usr/bin/env bash
# exercise-gate — flagship-exercise regression gate (fast lane).
#
# Convention: docs/development-process.md § Gates. Reruns the committed
# flagship exercise's production leg (no Blender needed) and requires the
# regenerated outputs to be byte-identical to the committed baseline —
# the committed golden-diff.txt IS the accepted state, so any decomposer
# or formula change that moves a millimetre fails HERE, not at the saw.
#
# run-manifest.json is timestamped by design and excluded + restored.
#
# Usage: bash scripts/exercise-gate.sh   (exit 0 identical, 1 regression)
set -u
cd "$(dirname "$0")/.."

FLAGSHIP="e2e-d60-legrabox"
GEN="exercises/$FLAGSHIP/generated"

if ! .venv/bin/python exercises/harness/runner.py "$FLAGSHIP" \
        --skip-blender --skip-inspect --strict >/dev/null 2>&1; then
    echo "exercise-gate: runner FAILED for $FLAGSHIP"
    exit 1
fi

# manifest is a per-run record, not a baseline — restore it
git checkout -q -- "$GEN/run-manifest.json" 2>/dev/null || true

if git diff --quiet -- "$GEN"; then
    echo "exercise-gate: OK — $FLAGSHIP outputs identical to committed baseline"
    exit 0
fi

echo "exercise-gate: REGRESSION — $FLAGSHIP outputs differ from committed baseline:"
git --no-pager diff --stat -- "$GEN" | sed 's/^/  /'
echo "  If the change is INTENDED: review 'git diff $GEN', commit the new"
echo "  baseline together with the code change and a ledger claim."
exit 1
