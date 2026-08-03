#!/usr/bin/env bash
# auto-reaffirm: heal the mechanically-healable half of the ledger, unasked.
#
# WHY. `invalidate-scan` runs on every commit and merge, so staling is
# automatic. Healing was not: someone had to remember `truth reaffirm`, and a
# knowledge base whose upkeep is a remembered chore is the FIT maintenance
# curve -- the death mode the 2026-08-03 doctrine names in L3. Estler et al.
# (2014) make it structural rather than incidental: specifications change an
# order of magnitude less than implementations, so "path touched -> STALE"
# guarantees a high false-stale rate by construction. The right response is
# to make the false half heal itself, not to stale less.
#
# WHAT IT CANNOT DO. `truth reaffirm` only re-confirms claims whose evidence
# command still produces the recorded output. Everything else it refuses to
# touch and reports: a hash mismatch becomes a divergence for a human, a
# claim with no evidence command stays manual, and -- the seam that matters --
# a claim THIS session filed is never auto-agreed, because ADR-010's
# author-verifier separation is reused verbatim here. Automating the
# mechanical half is safe precisely because the judgment half is refused.
#
# WHY POST-COMMIT AND NOT ONLY POST-MERGE. The doctrine says post-merge, but
# this repo pushes trunk-style: staling overwhelmingly happens at commit, and
# a healer wired only to merges would almost never fire. Both hooks call it.
#
# NEVER BLOCKS. post-* hooks run after the fact; a failure here must not look
# like a failed commit. Escape hatch for a session that wants the stale
# records left alone: TRUTH_NO_AUTO_REAFFIRM=1.
set -u
cd "$(git rev-parse --show-toplevel)" || exit 0

[ "${TRUTH_NO_AUTO_REAFFIRM:-0}" = "1" ] && exit 0

out=$(scripts/truth reaffirm 2>&1); rc=$?
if [ $rc -ne 0 ]; then
    # F1 rule: a healer that could not run must say so rather than leave
    # silence that reads as "nothing needed healing".
    echo "auto-reaffirm: SENSOR FAILED -- 'truth reaffirm' exited $rc; no claim was re-confirmed" >&2
    printf '%s\n' "$out" | tail -2 >&2
    exit 0
fi

summary=$(printf '%s\n' "$out" | grep '^reaffirm:' | tail -1)
# Silent when there was nothing to do: this runs on EVERY commit, and an
# unconditional line here would spend the whole whisper budget (ADR-005) on
# the most common case.
case "$summary" in
    *"0 stale claim(s)"*) exit 0 ;;
esac
[ -n "$summary" ] && printf '%s\n' "$summary"
exit 0
