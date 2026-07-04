#!/usr/bin/env sh
# Track kuchnie_core / kuchnie-core mentions in documentation (*.md).
#
# Usage:
#   scripts/grep-kuchnie-core-docs.sh           # mention counts per doc file
#   scripts/grep-kuchnie-core-docs.sh --stale   # only stale `src/kuchnie_core` paths
#                                               # (pre-2026-07 layout; should be
#                                               # `kuchnie-core/src/kuchnie_core`),
#                                               # excluding archives/ADRs where
#                                               # historical names are legitimate
set -eu

cd "$(dirname "$0")/.."

MODE="${1:-list}"

# Same exemptions as scripts/check-governance.sh: history stays as written.
EXEMPT='^(docs/archive/|attic/|docs/adr/|catalog/docs/adr/|docs/freeze/|features/archive/|.*/docs/archive/|.*/docs/archived/|CHANGELOG|.*CHANGELOG)'

EXCLUDES="--exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.git \
--exclude-dir=.web --exclude-dir=htmlcov"

if [ "$MODE" = "--stale" ]; then
  # A line is stale if it still says `src/kuchnie_core` after the correct new
  # prefix `kuchnie-core/src/kuchnie_core` is stripped out.
  # shellcheck disable=SC2086
  stale=$(grep -rn $EXCLUDES --include='*.md' 'src/kuchnie_core' . \
    | sed 's|^\./||' \
    | grep -Ev "^($EXEMPT)" \
    | awk -F: '{ line=$0; sub(/^[^:]*:[^:]*:/, "", line);
                 gsub(/kuchnie-core\/src\/kuchnie_core/, "", line);
                 if (line ~ /src\/kuchnie_core/) print $0 }' || true)
  if [ -z "$stale" ]; then
    echo "no stale src/kuchnie_core paths in live docs"
    exit 0
  fi
  printf '%s\n' "$stale"
  echo
  echo "✗ $(printf '%s\n' "$stale" | wc -l | tr -d ' ') stale path(s) — update to kuchnie-core/src/kuchnie_core"
  exit 1
fi

# shellcheck disable=SC2086
grep -rc $EXCLUDES --include='*.md' -E 'kuchnie_core|kuchnie-core' . 2>/dev/null \
  | awk -F: '$2 > 0' | sed 's|^\./||' | sort -t: -k2 -rn \
  | awk -F: '{ printf "%5d  %s\n", $2, $1 }'
