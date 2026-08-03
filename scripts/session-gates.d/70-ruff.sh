#!/usr/bin/env bash
# Ruff correctness gate: WARN-only, same posture as 50/60/61 — promoting
# to FAIL is Michał's call once the baseline is burned down. Config is
# ruff.toml at repo root (correctness-only; NO style rules — see the
# note there about reformat staling path-watched claims). Never exits
# non-zero.
# BLIND-SPOT: the rule set is correctness-only by deliberate choice (ruff.toml).
#   Style, formatting and typing findings are not merely unreported -- they are not computed, so a clean run says nothing about them.
# BLIND-SPOT-PROBE: scripts/tests/probes/70-ruff-blind.sh
cd "$(git rev-parse --show-toplevel)"
RUFF=".venv/bin/ruff"
[ -x "$RUFF" ] || RUFF="$(command -v ruff || true)"
if [ -z "$RUFF" ] || [ ! -x "$RUFF" ]; then
    echo "ruff: WARN not installed — uv pip install --python .venv/bin/python ruff"
    exit 0
fi
out="$("$RUFF" check --quiet --output-format concise \
    kuchnie-core/src kitchen-erp/kitchen_erp kitchen-cam \
    home-builder-adapter/src catalog 2>&1 | grep -v '^warning:')"
count="$(printf '%s\n' "$out" | grep -c ':' || true)"
if [ "$count" -eq 0 ]; then
    echo "ruff: 0 findings"
else
    echo "ruff: WARN ${count} finding(s) (correctness-only rule set):"
    printf '%s\n' "$out" | sed 's/^/  WARN  /' | head -30
    [ "$count" -gt 30 ] && echo "  WARN  ... ($((count - 30)) more; run: $RUFF check <components>)"
fi
exit 0
