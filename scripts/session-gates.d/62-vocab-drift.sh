#!/usr/bin/env bash
# Vocabulary-drift watch: WARN when a NEW identifier-like string literal
# starts being shared across >= 3 production modules of one package —
# a shared constant being born as scattered copies (the dolna_* /
# module_kind / dual-LW failure family). The committed baseline
# (docs/shared-literals-baseline.txt) is today's accepted debt; after a
# deliberate vocabulary addition regenerate it:
#   python3 scripts/shared-literals.py --write
# WARN-only, same posture as 50/60/61/70. Never exits non-zero.
cd "$(git rev-parse --show-toplevel)"
if [ ! -f docs/shared-literals-baseline.txt ]; then
    echo "vocab-drift: WARN baseline missing — run" \
         "python3 scripts/shared-literals.py --write and commit it"
    exit 0
fi
new="$(comm -23 <(python3 scripts/shared-literals.py) \
    <(sort docs/shared-literals-baseline.txt))"
if [ -z "$new" ]; then
    echo "vocab-drift: no new shared literals"
else
    count="$(printf '%s\n' "$new" | grep -c .)"
    echo "vocab-drift: WARN ${count} NEW shared literal(s) — extract a" \
         "constant/enum or accept via shared-literals.py --write:"
    printf '%s\n' "$new" | sed 's/^/  WARN  /'
fi
exit 0
