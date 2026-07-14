#!/usr/bin/env bash
# bd twin audit: no in-progress bd issues may survive a session
# (A/B trial: bd runs alongside the truth ledger's native kernel).
set -u
cd "$(git rev-parse --show-toplevel)"
prog=$(bd list --status=in_progress 2>/dev/null | grep -c 'kuchnie-' || true)
if [ "${prog:-0}" -gt 0 ]; then
    echo "bd twins in_progress: $prog — close or release them"
    exit 1
fi
exit 0
