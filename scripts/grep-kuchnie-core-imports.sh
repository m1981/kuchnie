#!/usr/bin/env sh
# Track kuchnie_core imports across the monorepo — guards the hub-and-spoke
# rule: spokes import the hub, never the reverse (README "Dependency direction").
#
# Usage:
#   scripts/grep-kuchnie-core-imports.sh          # consumers only (outside kuchnie-core/)
#   scripts/grep-kuchnie-core-imports.sh --all    # include kuchnie-core's own code/tests
set -eu

cd "$(dirname "$0")/.."

MODE="${1:-consumers}"

EXCLUDES="--exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.git \
--exclude-dir=__pycache__ --exclude-dir=.web --exclude-dir=htmlcov \
--exclude-dir=.pytest_cache --exclude-dir=attic"

# shellcheck disable=SC2086
hits=$(grep -rn $EXCLUDES --include='*.py' -E \
  '^[[:space:]]*(from[[:space:]]+kuchnie_core|import[[:space:]]+kuchnie_core)' . || true)

if [ "$MODE" != "--all" ]; then
  hits=$(printf '%s\n' "$hits" | grep -v '^\./kuchnie-core/' || true)
fi

if [ -z "$hits" ]; then
  echo "no kuchnie_core imports found"
  exit 0
fi

printf '%s\n' "$hits"
echo
echo "── imports per component ──"
printf '%s\n' "$hits" | sed 's|^\./||; s|/.*||' | sort | uniq -c | sort -rn
