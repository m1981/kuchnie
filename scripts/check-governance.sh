#!/usr/bin/env sh
# Doc-governance pre-commit checks. Fast, deterministic, no network.
# Bypass a single check consciously: ADR_AMEND=1 git commit ...
set -eu
fail=0
say() { printf '%s\n' "$*" >&2; }

STAGED=$(git diff --cached --name-only --diff-filter=ACMR)
[ -z "$STAGED" ] && exit 0

# Paths where historical names are legitimate
EXEMPT='^(docs/archive/|attic/|docs/adr/|catalog/docs/adr/|docs/freeze/|features/archive/|.*/docs/archive/|.*/docs/archived/|CHANGELOG|.*CHANGELOG)'

# ── Check 1: dead component names in newly added lines ──────────────
for f in $STAGED; do
  echo "$f" | grep -Eq "$EXEMPT" && continue
  case "$f" in *.md|*.py|*.toml|*.json|*.yaml|*.yml) ;; *) continue ;; esac
  hits=$(git diff --cached -U0 -- "$f" \
    | grep -E '^\+' | grep -Ev '^\+\+\+' \
    | grep -En 'kitchen-cad|kitchen-plugin|kitchen-app|kitchen_cad|kitchen_app([^_]|$)' \
    || true)
  if [ -n "$hits" ]; then
    say "✗ dead component name added in $f (ADR-009/010/011 renames):"
    say "$hits"
    fail=1
  fi
done

# ── Check 2: ADR immutability (modifications, not additions) ────────
if [ "${ADR_AMEND:-0}" != "1" ]; then
  mods=$(git diff --cached --name-only --diff-filter=M \
    | grep -E '^(docs/adr|catalog/docs/adr)/[0-9]{3}-' || true)
  if [ -n "$mods" ]; then
    say "✗ accepted ADR modified (write a superseding ADR instead):"
    say "$mods"
    say "  conscious amend (typo/status line): ADR_AMEND=1 git commit ..."
    fail=1
  fi
fi

# ── Check 3: new-doc three-question gate (charter A.9) ───────────────
news=$(git diff --cached --name-only --diff-filter=A | grep '\.md$' || true)
for f in $news; do
  echo "$f" | grep -Eq "$EXEMPT" && continue
  # component README headers + freeze artifacts are format-governed already
  echo "$f" | grep -Eq '(^|/)(README|RESUME|MIGRATION-STATUS|AGENTS)\.md$' && continue
  if ! git show ":$f" | head -15 | grep -q 'Reader:' \
     || ! git show ":$f" | head -15 | grep -q 'Enables:' \
     || ! git show ":$f" | head -15 | grep -q 'Update-trigger:'; then
    say "✗ new doc $f lacks the three-question header (first 15 lines):"
    say "  > Reader: <who> | Enables: <what decision/action> | Update-trigger: <event>"
    say "  Can't answer all three? Don't write the doc (AGENTS.md gate 2)."
    fail=1
  fi
done

# ── Check 4: component README keeps its Type header ──────────────────
for f in $STAGED; do
  case "$f" in
    catalog/README.md|kitchen-erp/README.md|kitchen-cam/README.md|\
    home-builder-adapter/README.md|krono-compositor-mvp/README.md|src/README.md)
      git show ":$f" | head -8 | grep -q '> Type:' || {
        say "✗ $f lost its '> Type: ... | Status: ...' header block"; fail=1; } ;;
  esac
done

[ $fail -eq 0 ] || { say ""; say "governance checks failed — see above."; exit 1; }
exit 0
