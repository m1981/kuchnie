#!/usr/bin/env bash
# Signature-drift watch: WARN when the architecture surface (module-level
# defs/classes/methods of kuchnie_core + kitchen_erp) differs from the
# committed baseline docs/architecture-signatures.txt. The baseline is the
# RECEIPT of the last judgment review (docs/pattern-conformance.md
# § Re-running this review): after reviewing, regenerate it with
#   python3 scripts/signature-summary.py --write
# and commit it WITH the review's claims — same discipline as
# exercise-gate baselines. WARN-only; promotion to FAIL is Michał's call.
cd "$(git rev-parse --show-toplevel)"
if [ ! -f docs/architecture-signatures.txt ]; then
    echo "signature-drift: WARN baseline missing — run" \
         "python3 scripts/signature-summary.py --write and commit it"
    exit 0
fi
fresh="$(python3 scripts/signature-summary.py)"
if diff <(printf '%s\n' "$fresh") docs/architecture-signatures.txt >/dev/null 2>&1; then
    echo "signature-drift: surface matches the reviewed baseline"
    exit 0
fi
changed="$(diff <(printf '%s\n' "$fresh") docs/architecture-signatures.txt \
    | grep -E '^[<>]' | awk '{print $2}' | sort -u)"
count="$(printf '%s\n' "$changed" | grep -c . || true)"
echo "signature-drift: WARN architecture surface drifted since the last" \
     "review — ${count} module(s) changed signatures:"
printf '%s\n' "$changed" | sed 's/^/  WARN  /'
echo "  WARN  re-run the judgment pass (pattern-conformance.md § Re-running" \
     "this review), then: python3 scripts/signature-summary.py --write + commit"
exit 0
