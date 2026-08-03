#!/usr/bin/env bash
# pre-push-checks: the content gates, run at the push boundary.
#
# WHY THIS EXISTS. A 2026-08-03 control-flow audit of this repo found that
# `.beads/hooks/pre-push` invoked nothing from this project's machinery, and
# that no GitHub workflow ran a single domain test. 1,434 tests across four
# components — kuchnie-core, kitchen-erp, catalog, kitchen-cam — plus the
# flagship byte-identical golden had NO automatic trigger of any kind. The
# only thing that ran them was a human or an agent remembering to.
#
# WHY PUSH AND NOT COMMIT. These cost ~30-60s together. At pre-commit they
# would tax every edit and train `--no-verify`, which is worse than manual
# because it disables the fast ledger gates too. Push is where drift starts
# reaching others, and with agents merging worktree branches locally it is
# also the natural integration boundary: one run per batch, not per merge.
# This is the same siting argument the upstream template makes for its own
# release battery.
#
# WHY BLOCKING. A gate that only warns gets ignored — the normalisation
# mechanism this project has already documented. `git push --no-verify` is
# the honest emergency exit and it is loud in the reflog. No second, softer
# bypass, deliberately: that would be this hook teaching its own workaround.
#
# EVERY ARM REPORTS WHAT IT EXAMINED. A check that examined nothing is a
# FAILURE, never a pass. Two gates in the upstream reported "clean" for weeks
# while checking zero files; that is the failure this rule exists to stop.
#
# Exit codes: 0 ok / 1 governance (a real finding) / 2 environment.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2

PASS=0; FAIL=0
say()  { printf '%s\n' "$*"; }
pass() { PASS=$((PASS+1)); say "  ok    $1 -- $2"; }
bad()  { FAIL=$((FAIL+1)); say "  FAIL  $1 -- $2"; }

say "pre-push-checks: content gates at the push boundary"

# --- 1. ledger-facing gates (fast, and they gate the specs) --------------
OUT=$(bash scripts/spec-health.sh 2>&1); RC=$?
N=$(printf '%s' "$OUT" | sed -n 's/.*across \([0-9]*\) spec(s).*/\1/p')
if [ "${N:-0}" -eq 0 ]; then
  bad "spec-health" "examined 0 specs -- the arm is dark, not clean"
elif [ $RC -eq 0 ]; then
  pass "spec-health" "$N specs judged"
else
  bad "spec-health" "$(printf '%s' "$OUT" | tail -1)"
fi

OUT=$(bash scripts/doc-health.sh 2>&1); RC=$?
N=$(printf '%s' "$OUT" | sed -n 's/.*across \([0-9]*\) live doc(s).*/\1/p')
if [ "${N:-0}" -eq 0 ]; then
  bad "doc-health" "examined 0 docs -- the arm is dark, not clean"
elif [ $RC -eq 0 ]; then
  pass "doc-health" "$N docs judged"
else
  bad "doc-health" "$(printf '%s' "$OUT" | tail -1)"
fi

# --- 2. the flagship golden ---------------------------------------------
# Byte-identical or it is a deliberate roll, and a deliberate roll is a
# decision someone should make on purpose rather than discover later.
OUT=$(bash scripts/exercise-gate.sh 2>&1); RC=$?
if [ $RC -eq 0 ]; then
  pass "exercise-gate" "$(printf '%s' "$OUT" | tail -1)"
else
  bad "exercise-gate" "flagship outputs differ from the committed baseline -- if the roll is intended, regenerate and commit it as its own change"
fi

# --- 3. the domain suites — the whole reason this file exists ------------
run_suite() {  # name, dir, interpreter
  local name="$1" dir="$2" py="$3"
  [ -x "$py" ] || { bad "$name" "interpreter missing: $py (environment)"; return; }
  local out rc n
  out=$(cd "$dir" && "$py" -m pytest tests/ -q 2>&1); rc=$?
  # NB: the count may start the line ("819 passed in 1.48s"), so no
  # leading-character class here -- an earlier version required one and
  # reported two live suites as dark. The dark-arm rule caught it.
  n=$(printf '%s' "$out" | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '^[0-9]+')
  if [ "${n:-0}" -eq 0 ]; then
    bad "$name" "ran 0 tests -- the arm is dark"
  elif [ $rc -eq 0 ]; then
    pass "$name" "$n tests"
  else
    bad "$name" "$(printf '%s' "$out" | tail -2 | tr '\n' ' ')"
  fi
}

run_suite "kuchnie-core"  kuchnie-core           "$ROOT/.venv/bin/python"
run_suite "kitchen-erp"   kitchen-erp            "$ROOT/kitchen-erp/.venv/bin/python"
run_suite "catalog"       catalog                "$ROOT/.venv/bin/python"
run_suite "kitchen-cam"   kitchen-cam            "$ROOT/.venv/bin/python"

# --- 4. what the system needs FROM YOU (printed, never blocking) ---------
# The control-flow audit's other finding: nothing surfaced the human queue at
# any boundary, so items needing judgment waited on someone opening a file.
say ""
QUEUE=$(scripts/truth queue 2>/dev/null | grep -cE "^tr-" || true)
HUMAN=$(bd human list 2>/dev/null | grep -cE "^  kuchnie-" || true)
say "  note  needs your judgment: ${QUEUE:-0} claim(s) in the verdict queue, ${HUMAN:-0} bead(s) flagged human"
say "        (printed, not blocking -- 'scripts/truth queue' and 'bd human list')"

say ""
if [ $FAIL -eq 0 ]; then
  say "pre-push-checks: all $PASS arms green"
  exit 0
fi
say "pre-push-checks: BLOCKED ($FAIL failing, $PASS green)."
say "  These had no automatic trigger before 2026-08-03; a failure here is"
say "  drift that would otherwise have shipped unnoticed."
say "  Emergency exit is 'git push --no-verify' -- loud, and in the reflog."
exit 1
