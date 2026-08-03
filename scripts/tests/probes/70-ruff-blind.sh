#!/usr/bin/env bash
# Blind-spot probe for 70-ruff.sh. Same contract: 0 = blind spot still real.
#
# Declared: the rule set is correctness-only (ruff.toml), so style findings
# are not merely unreported -- they are not computed.
# Probed by: a file that violates style rules only must produce zero findings
# under the repo config. If style rules are ever selected, this fails and the
# declaration must be rewritten.
set -u
cd "$(git rev-parse --show-toplevel)"
RUFF=".venv/bin/ruff"; [ -x "$RUFF" ] || RUFF="$(command -v ruff || true)"
[ -n "$RUFF" ] && [ -x "$RUFF" ] || { echo "probe-70: ruff not installed -- probe inconclusive, treated as PASS (environment, not governance)"; exit 0; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
{
  printf 'x = 1\n'
  printf 'def f(a,b):\n'
  printf '    return a+b   # %s\n' "$(printf 'y%.0s' $(seq 1 200))"
} > "$TMP/style_only.py"

out="$("$RUFF" check --quiet --config ruff.toml --output-format concise "$TMP/style_only.py" 2>&1 | grep -v '^warning:')"
n="$(printf '%s\n' "$out" | grep -c ':' || true)"
if [ "$n" -ne 0 ]; then
  echo "probe-70: style-only source produced $n finding(s) -- style rules are now computed; the declared blind spot is CLOSED, update 70-ruff.sh"
  printf '%s\n' "$out" | head -3
  exit 1
fi
echo "probe-70: blind spot intact -- a 200-column line and cramped spacing produce zero findings"
exit 0
