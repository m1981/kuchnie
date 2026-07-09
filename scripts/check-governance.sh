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
# Pure renames (R100) carry no new content; path-limited diffs can't pair
# them with their old location and would report every line as added.
PURE_RENAMES=$(git diff --cached --name-status --diff-filter=R \
  | awk '$1 == "R100" { print $NF }')
for f in $STAGED; do
  echo "$f" | grep -Eq "$EXEMPT" && continue
  printf '%s\n' "$PURE_RENAMES" | grep -Fxq "$f" && continue
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
    home-builder-adapter/README.md|krono-compositor-mvp/README.md|kuchnie-core/README.md)
      git show ":$f" | head -8 | grep -q '> Type:' || {
        say "✗ $f lost its '> Type: ... | Status: ...' header block"; fail=1; } ;;
  esac
done

# ── Check 5: feature-spec hygiene (docs/spec-convention.md) ──────────
# 5a: deleting a spec needs an explicit override (specs are superseded, not
#     deleted — mirror of the ADR-immutability rule).
if [ "${SPEC_REMOVE:-0}" != "1" ]; then
  spec_dels=$(git diff --cached --name-only --diff-filter=D \
    | grep -E '(^|/)docs/specs/.*\.md$' || true)
  if [ -n "$spec_dels" ]; then
    say "✗ feature spec deleted (supersede with a pointer instead):"
    say "$spec_dels"
    say "  conscious removal: SPEC_REMOVE=1 git commit ..."
    fail=1
  fi
fi
# 5b: a NEW spec must cite at least one ledger id (tr-/wk-) — unwired prose
#     is the decay mode the convention exists to kill. Legacy specs are
#     grandfathered (spec-health WARNs on them).
spec_news=$(git diff --cached --name-only --diff-filter=A \
  | grep -E '(^|/)docs/specs/.*\.md$' || true)
for f in $spec_news; do
  if ! git show ":$f" | grep -Eq '(tr|wk)-[0-9a-f]{8}'; then
    say "✗ new spec $f cites no ledger ids (docs/spec-convention.md):"
    say "  facts -> tr- claims, work -> wk- issues; cite the ids, don't restate."
    fail=1
  fi
done
# 5c: any staged spec change must leave the whole spec surface healthy.
spec_staged=$(printf '%s\n' "$STAGED" | grep -E '(^|/)docs/specs/.*\.md$' || true)
if [ -n "$spec_staged" ]; then
  if ! health_out=$(bash scripts/spec-health.sh 2>&1); then
    say "✗ spec-health failed (a spec stands on a dead fact):"
    say "$health_out"
    fail=1
  fi
fi

# ── Check 6: live-doc health (dead names + broken links, corpus-wide) ─
# Any staged .md must leave the whole live corpus clean — same shape as 5c.
# Complements Check 1: that gates added lines; this gates the standing state
# (catches files that arrived by merge/rename and pre-existing rot).
md_staged=$(printf '%s\n' "$STAGED" | grep '\.md$' || true)
if [ -n "$md_staged" ]; then
  if ! doc_out=$(bash scripts/doc-health.sh 2>&1); then
    say "✗ doc-health failed (live corpus carries a dead name or broken link):"
    say "$doc_out"
    fail=1
  fi
fi

[ $fail -eq 0 ] || { say ""; say "governance checks failed — see above."; exit 1; }
exit 0
