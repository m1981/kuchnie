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
