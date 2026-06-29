#!/bin/bash
# Doc Freshness Analyzer
# Uses git diff filters to determine true file origin and modification history
# Handles renames, moves, and re-creation correctly
#
# Usage: bash scripts/analyze_doc_freshness.sh [--project <name>]

set -euo pipefail

FILTER=""
if [ "${1:-}" = "--project" ] && [ -n "${2:-}" ]; then
  FILTER="$2"
fi

echo "FILE|TRUE_ORIGIN|LAST_MODIFY|LIFECYCLE|NOTES"
echo "---|---|---|---|---"

for file in $(git ls-files | grep -E '\.md$' | grep -v node_modules | grep -v .venv | grep -v .pytest_cache | grep -v __pycache__); do
  # Apply project filter if specified
  if [ -n "$FILTER" ] && ! echo "$file" | grep -q "^$FILTER"; then
    continue
  fi

  # Follow renames to find TRUE origin
  true_origin=$(git log --follow --diff-filter=A --format="%ai" -- "$file" 2>/dev/null | tail -1)
  # Last content modification
  last_mod=$(git log --format="%ai" --diff-filter=M -- "$file" 2>/dev/null | head -1)
  # Last any change (including renames)
  last_any=$(git log -1 --format="%ai" -- "$file" 2>/dev/null)

  # Check if there were renames
  rename_count=$(git log --follow --diff-filter=R --summary -- "$file" 2>/dev/null | grep -c "rename" || true)

  # Check if it was deleted and re-created
  add_count=$(git log --diff-filter=A --format="x" -- "$file" 2>/dev/null | wc -l | tr -d ' ')
  del_count=$(git log --diff-filter=D --format="x" -- "$file" 2>/dev/null | wc -l | tr -d ' ')

  notes=""
  lifecycle="ADDED_ONLY"

  if [ "$del_count" -gt 0 ] && [ "$add_count" -gt 1 ]; then
    lifecycle="RECREATED"
    notes="deleted+recreated"
  elif [ "$rename_count" -gt 0 ]; then
    lifecycle="RENAMED"
    notes="renamed ${rename_count}x"
  elif [ -n "$last_mod" ]; then
    lifecycle="MODIFIED"
    notes="modified"
  fi

  echo "$file|$true_origin|$last_mod|$lifecycle|$notes"
done
