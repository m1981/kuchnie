# DOC-GOVERNANCE KIT — preventing doc creep after the freeze

Three layers. Each catches what the previous can't. Keep the layer count at
three — governance creep is the doc creep of automation.

═══════════════════════════════════════════════════════════════════════════
LAYER 0 — When the charter's rules fire (policy, goes into AGENTS.md)
═══════════════════════════════════════════════════════════════════════════

The AGENT-CHARTER + Appendix A are a SOURCE, not a second rulebook. On
resume, merge these deltas into root AGENTS.md (one commit,
"docs: merge charter governance rules into AGENTS.md"):

1. EVIDENCE PROTOCOL — every repo-state claim in any doc or review is
   tagged VERIFIED(cmd) / INFERRED(basis) / UNVERIFIED. Hedging is not
   a substitute for the tag.
2. NEW-DOC GATE (A.9) — no new .md without three answers stated in the
   file's header: Reader, Enables, Update-trigger. Empty answer = don't
   write the doc. (Enforced by Layer 1, check 3.)
3. NEW-COMPONENT GATE (§4.1) — no new top-level package/component
   without an accepted ADR stating purpose, why existing components
   can't absorb it, and lifespan. Run a duplication scan (grep domain
   nouns across components) first. This is the rule that would have
   prevented the kitchen-cad fork.
4. REVIEW OUTPUT CONTRACT (§6) — audits/reviews are: 3-line TL;DR →
   2–4 P0 findings with evidence → one matrix → unknowns → one question.
   No praise without a named trade-off.
5. DIAGRAM LABELS (§2) — every architecture diagram is captioned
   OBSERVED (each arrow grep-verified) or PROPOSED. No unlabeled arrows.
6. FRESHNESS RITUAL — at every freeze or quarter boundary, rerun the
   trust audit (docs/freeze/FREEZE-PLAN.md, Prompt 1 pattern) and
   re-stamp. STALE stamps are removed only by rewriting against code.

Trigger moments, in one line each:
  session start → read order (RESUME.md) · new .md → gate 2 ·
  new component → gate 3 · any review → contract 4 · new diagram →
  rule 5 · freeze/quarter → ritual 6.

═══════════════════════════════════════════════════════════════════════════
LAYER 1 — Deterministic pre-commit (husky; already installed via
package.json "prepare": "husky")
═══════════════════════════════════════════════════════════════════════════

File: .husky/pre-commit
------------------------------------------------------------------
#!/usr/bin/env sh
sh scripts/check-governance.sh || exit 1
------------------------------------------------------------------

File: scripts/check-governance.sh
------------------------------------------------------------------
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
------------------------------------------------------------------

═══════════════════════════════════════════════════════════════════════════
LAYER 2 — LLM semantic gate (pre-push or on demand; NOT pre-commit)
═══════════════════════════════════════════════════════════════════════════

Catches what grep can't: a new doc that duplicates an existing one in
different words, state claims without evidence tags, scope drift. Uses
Claude Code print mode (claude -p) with --bare so local config can't
alter the verdict. Costs cents per run; keep it at push time.

File: scripts/llm-doc-gate.sh
------------------------------------------------------------------
#!/usr/bin/env sh
# Semantic doc-governance review of .md changes vs main.
# Usage: sh scripts/llm-doc-gate.sh   (or wire into .husky/pre-push)
# Requires: claude CLI authenticated; jq.
set -eu
DIFF=$(git diff origin/main...HEAD -- '*.md' ':!docs/archive/**' \
       ':!attic/**' ':!**/docs/archive/**')
[ -z "$DIFF" ] && { echo "no .md changes — gate skipped"; exit 0; }
DOCLIST=$(git ls-files '*.md' | grep -Ev '^(docs/archive|attic)/' )

RESULT=$(printf '%s\n\n=== EXISTING DOC PATHS ===\n%s\n' "$DIFF" "$DOCLIST" | \
  claude --bare -p \
  --allowedTools "Read,Bash(git diff *),Bash(git ls-files *)" \
  --max-turns 6 --model sonnet --output-format json \
  --append-system-prompt "You are a documentation-governance reviewer for a \
monorepo. Input: a git diff of markdown changes, then a list of existing doc \
paths. Rules to enforce: (R1) a NEW doc must not substantially duplicate the \
purpose of an existing doc — flag likely overlaps by path+topic; (R2) claims \
about code/repo state must carry VERIFIED(...)/INFERRED(...)/UNVERIFIED tags \
or be clearly non-state content; (R3) docs must not describe components by \
their pre-rename names (kitchen-cad/kitchen-plugin/kitchen-app) as current; \
(R4) a doc that mixes tutorial+reference+explanation in one file is creep — \
flag it; (R5) roadmap/status claims belong in MIGRATION-STATUS.md or \
ROADMAP.md, not scattered in new files. Output STRICT JSON only: \
{\"verdict\":\"PASS\"|\"FAIL\",\"findings\":[{\"rule\":\"R1..R5\",\
\"file\":\"...\",\"line_hint\":\"...\",\"why\":\"one sentence\"}]}. \
FAIL only on R1/R2/R3 violations; R4/R5 are warnings (verdict PASS, \
finding listed)." )

VERDICT=$(echo "$RESULT" | jq -r '.result' | jq -r '.verdict' 2>/dev/null || echo "PARSE_ERROR")
echo "$RESULT" | jq -r '.result' 2>/dev/null || echo "$RESULT"
[ "$VERDICT" = "PASS" ] && exit 0
[ "$VERDICT" = "PARSE_ERROR" ] && { echo "gate output unparseable — treat as warning"; exit 0; }
echo "✗ LLM doc gate: FAIL"; exit 1
------------------------------------------------------------------

Optional wiring — File: .husky/pre-push
------------------------------------------------------------------
#!/usr/bin/env sh
sh scripts/llm-doc-gate.sh || exit 1
------------------------------------------------------------------

Notes:
- --bare skips local hooks/CLAUDE.md/MCP discovery so the verdict depends
  only on the prompt — deterministic across machines. Auth in bare mode
  needs ANTHROPIC_API_KEY (or wire it without --bare and accept local
  context). If runs feel slow/costly, swap --model sonnet → haiku alias.
- PARSE_ERROR is deliberately non-blocking: a flaky gate that blocks
  pushes gets deleted within a week. Fail only on clear verdicts.
- Never let this gate EDIT anything. Review-only. An auto-fixing hook is
  an ungoverned agent session.

═══════════════════════════════════════════════════════════════════════════
ROLLOUT — paste to your agent (one commit per part)
═══════════════════════════════════════════════════════════════════════════

Part A: create scripts/check-governance.sh and .husky/pre-commit exactly
as specified in docs/DOC-GOVERNANCE-KIT.md Layer 1; chmod +x both; verify
husky is active (package.json prepare script). Test: stage a scratch .md
without the three-question header and confirm the commit is blocked; then
remove the scratch file. Commit: "chore: pre-commit doc-governance checks".

Part B: create scripts/llm-doc-gate.sh per Layer 2; chmod +x. Do NOT wire
pre-push yet — run it manually for two weeks first; wire it only if its
verdicts prove useful. Commit: "chore: LLM doc gate (manual for now)".

Part C: add Layer 0's six rules to root AGENTS.md under a new
"Documentation governance" section (merge, don't duplicate what AGENTS.md
already says). Commit: "docs: merge charter governance rules into AGENTS.md".
NOTE: Part C is a RESUME-time task, not a freeze-time task, unless you're
actively creating docs during the pause.

═══════════════════════════════════════════════════════════════════════════
> Reader: future dev/agent sessions | Enables: enforcing doc-governance
> gates | Update-trigger: a gate misfires twice, or AGENTS.md governance
> rules change