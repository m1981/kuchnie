#!/usr/bin/env bash
# session-close — mechanical end-of-session survival gate.
#
# Convention: docs/development-process.md § Session lifecycle.
# Gold survives sessions only as committed artifacts with ledger ids;
# this script refuses to let a session end with knowledge still in flight.
#
# FAIL (exit 1) on survival holes: dirty tree, claimed/in-progress work,
# spec/doc gate failures, flagship-exercise regression.
# WARN (exit 0) on triage debt: unverified claims, verdict queue size.
#
# Usage: bash scripts/session-close.sh [--skip-exercise-gate]
set -u
cd "$(dirname "$0")/.."

fails=0
warns=0
fail() { printf '  FAIL  %s\n' "$*"; fails=$((fails + 1)); }
warn() { printf '  WARN  %s\n' "$*"; warns=$((warns + 1)); }
ok()   { printf '  ok    %s\n' "$*"; }

echo "session-close checklist"

# 1 — working tree: nothing survives uncommitted
dirty=$(git status --porcelain | wc -l | tr -d ' ')
if [ "$dirty" -gt 0 ]; then
    fail "uncommitted changes: $dirty file(s) — commit (or stash with a wk id) before closing"
    git status --porcelain | head -5 | sed 's/^/          /'
else
    ok "working tree clean"
fi

# 2 — truth ledger: no work left claimed (finish, or 'truth start --release')
claimed=$(scripts/truth issues 2>/dev/null | grep -cE '\b(claimed|in_progress)\b' || true)
if [ "${claimed:-0}" -gt 0 ]; then
    fail "$claimed truth work item(s) still claimed — 'truth done --claim' or 'truth start --release'"
    scripts/truth issues 2>/dev/null | grep -E '\b(claimed|in_progress)\b' | head -5 | sed 's/^/          /'
else
    ok "no claimed truth work items"
fi

# 3 — bd twins: nothing in_progress
bd_prog=$(bd list --status=in_progress 2>/dev/null | grep -c 'kuchnie-' || true)
if [ "${bd_prog:-0}" -gt 0 ]; then
    fail "$bd_prog bd issue(s) in_progress — close or release them"
else
    ok "no in-progress bd issues"
fi

# 4 — unverified claims: filed this session but nobody agreed yet (warn:
#     filer != verifier is by design, but they should not accumulate)
unver=$(scripts/truth list 2>/dev/null | grep -c 'unverified' || true)
if [ "${unver:-0}" -gt 0 ]; then
    warn "$unver claim(s) unverified — dispatch verifiers or expect ready-gate warnings"
else
    ok "no unverified claims"
fi

# 5 — verdict queue: stale/diverged facts awaiting triage (warn + count)
queue=$(scripts/truth queue 2>/dev/null | wc -l | tr -d ' ')
if [ "${queue:-0}" -gt 0 ]; then
    warn "verdict queue holds $queue claim(s) — re-verify what your session staled"
else
    ok "verdict queue empty"
fi

# 6 — spec gate
if bash scripts/spec-health.sh 2>/dev/null | tail -1 | grep -q ' 0 failure'; then
    ok "spec-health: 0 failures"
else
    fail "spec-health has failures — a spec stands on a dead fact"
fi

# 7 — doc gate
if bash scripts/doc-health.sh 2>/dev/null | tail -1 | grep -q ' 0 failure'; then
    ok "doc-health: 0 failures"
else
    fail "doc-health has failures"
fi

# 8 — flagship exercise regression (fast lane; skippable when Blender-less)
if [ "${1:-}" = "--skip-exercise-gate" ]; then
    warn "exercise-gate skipped by flag"
elif bash scripts/exercise-gate.sh >/dev/null 2>&1; then
    ok "exercise-gate: flagship outputs identical to committed baseline"
else
    fail "exercise-gate: flagship exercise outputs changed — inspect 'git diff exercises/'"
fi

echo
echo "session-close: $fails failure(s), $warns warning(s)"
if [ "$fails" -gt 0 ]; then
    echo "NOT SAFE to end the session — the items above will not survive."
    exit 1
fi
echo "Safe to close. Conservative profile: report status; push only with authority:"
echo "  git log --oneline origin/main..HEAD | cat    # what would be pushed"
echo "  git push && bd dolt push                     # only if authorized"
exit 0
