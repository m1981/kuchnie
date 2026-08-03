#!/usr/bin/env bash
# Evidence-subset watch (doctrine L1 Adopt 1): WARN when a claim declares an
# evidence_path its own recipe never reads. Staling there demotes the claim
# while the evidence stays blind to whether the fact actually moved -- the
# tr-ce5c7845 defect, where two grep counts stood in for a sentence about a
# mapping in a third file.
#
# Accepted debt lives in docs/evidence-subset-baseline.txt (regenerate:
# python3 scripts/evidence-subset.py --write). WARN-only, same posture as
# 50/60/61/62/63/70 -- promoting to FAIL is Michał's call, and per ADR-047
# that needs an adoption metric this gate is now producing.
#
# BLIND-SPOT: a recipe that names a path and never reads it -- `grep X a.py
#   b.py` where b.py is only in the argv of a command whose output does not
#   depend on it -- counts as READ here. This gate is textual, not semantic:
#   it proves the path is mentioned, not that the output depends on it. The
#   semantic version is the mutation harness (doctrine L1 Adopt 3).
# BLIND-SPOT-PROBE: scripts/tests/probes/65-evidence-subset-blind.sh
cd "$(git rev-parse --show-toplevel)"

if [ ! -f docs/evidence-subset-baseline.txt ]; then
    echo "evidence-subset: WARN baseline missing — run" \
         "python3 scripts/evidence-subset.py --write and commit it"
    exit 0
fi

fresh="$(python3 scripts/evidence-subset.py)" || {
    echo "evidence-subset: SENSOR FAILED — the checker did not run; nothing was checked"
    exit 1
}
new="$(comm -23 <(printf '%s\n' "$fresh" | sort) \
                <(grep -v '^#' docs/evidence-subset-baseline.txt | grep . | sort))"
accepted="$(grep -vc '^#' docs/evidence-subset-baseline.txt || true)"

if [ -z "$new" ]; then
    echo "evidence-subset: no new unread evidence paths (${accepted} accepted in baseline)"
    exit 0
fi

count="$(printf '%s\n' "$new" | grep -c .)"
echo "evidence-subset: WARN ${count} NEW claim/path pair(s) — the recipe never reads a path it watches; widen the command or drop the path:"
printf '%s\n' "$new" | sed 's/^/  WARN  /'
exit 0
