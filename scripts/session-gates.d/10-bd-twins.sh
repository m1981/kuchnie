#!/usr/bin/env bash
# bd twin audit: no in-progress bd issues may survive a session
# (A/B trial: bd runs alongside the truth ledger's native kernel).
#
# This gate ALWAYS prints a summary line, including when it is happy. Two
# reasons, both learned the hard way in this repo:
#   * silence is indistinguishable from a broken gate. pre-push-checks.sh
#     treats an arm that emits nothing as DARK, not clean, and it caught
#     this gate's own silence the first time the tree was actually clean.
#   * a sensor that cannot run must scream rather than read as zero. The
#     old form piped bd's stderr to /dev/null and counted matches, so a bd
#     that failed outright looked exactly like "no twins in progress" —
#     the F1 rule that session-close.sh's own header cites.
# BLIND-SPOT: it reads bd's status field only.
#   A bead left `open` but abandoned mid-edit is indistinguishable from one nobody started, and work tracked solely in the truth kernel as a claimed wk- item is invisible here -- that half is session-close.sh's job.
set -u
cd "$(git rev-parse --show-toplevel)"

out=$(bd list --status=in_progress 2>&1); rc=$?
if [ $rc -ne 0 ]; then
    echo "bd-twins: SENSOR FAILED — 'bd list --status=in_progress' exited $rc; nothing was checked"
    printf '%s\n' "$out" | head -3 | sed 's/^/  /'
    exit 1
fi

prog=$(printf '%s\n' "$out" | grep -c 'kuchnie-')
if [ "${prog:-0}" -gt 0 ]; then
    echo "bd-twins: $prog in_progress — close them, or hand back with 'truth start --release'"
    printf '%s\n' "$out" | grep 'kuchnie-' | head -5 | sed 's/^/  /'
    exit 1
fi
echo "bd-twins: 0 in_progress"
exit 0
