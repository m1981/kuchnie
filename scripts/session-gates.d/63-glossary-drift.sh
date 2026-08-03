#!/usr/bin/env bash
# Ubiquitous-language watch: WARN when the domain vocabulary drifts from
# docs/GLOSSARY.md — a NEW domain-surface class without a glossary entry,
# a glossary File-of-record that stopped existing, or a cross-context
# name collision without a "Not to be confused with" disambiguation.
# Checker: scripts/glossary-check.py; accepted debt lives in
# docs/glossary-baseline.txt (regenerate: glossary-check.py --write).
# WARN-only, same posture as 50/60/61/62/70. Never exits non-zero.
# BLIND-SPOT: it checks that domain-surface names HAVE glossary entries.
#   It cannot check that an entry still describes what the code does, so a term whose meaning drifted while its name held is silently fine.
cd "$(git rev-parse --show-toplevel)"
if [ ! -f docs/glossary-baseline.txt ]; then
    echo "glossary-drift: WARN baseline missing — run" \
         "python3 scripts/glossary-check.py --write and commit it"
    exit 0
fi
new="$(comm -23 <(python3 scripts/glossary-check.py) \
    <(sort docs/glossary-baseline.txt))"
accepted="$(grep -c . docs/glossary-baseline.txt || true)"
if [ -z "$new" ]; then
    echo "glossary-drift: no new findings (${accepted} accepted in baseline)"
else
    count="$(printf '%s\n' "$new" | grep -c .)"
    echo "glossary-drift: WARN ${count} NEW finding(s) — add the glossary" \
         "entry (GLOSSARY.md contract) or accept via glossary-check.py --write:"
    printf '%s\n' "$new" | sed 's/^/  WARN  /'
fi
exit 0
