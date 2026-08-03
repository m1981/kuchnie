#!/usr/bin/env bash
# impact-check: make the BLAST RADIUS of what is about to be pushed visible.
#
# WHY THIS EXISTS. The recorded failure is L5 in the verification doctrine:
# a change was verified in isolation and shipped without anyone enumerating
# what depended on it, and /admin then crashed on every legacy database. The
# ledger already knows the dependency edges -- every claim declares the paths
# its evidence watches, and every work item declares the claims it stands on
# -- but nothing ASKED that question at the moment of shipping. This arm asks
# it: for the paths the outgoing commits touch, which claims does the next
# commit endanger, and which OPEN work items sit on top of those claims.
#
# WHY IT REUSES `scripts/truth impact`. The path/glob matching contract lives
# in one place (truthlib.advisory.match_paths, shared by the scan, the forward
# impact verb and the inverse trace -- ADR-005 says so explicitly). A second
# matcher here would drift from the first and then quietly disagree about what
# "watched" means. This script computes the CHANGE SET and renders; it does no
# matching of its own.
#
# WHY ADVISORY, NEVER BLOCKING. This is information for a human deciding
# whether the radius is acceptable. A blast radius is not, by itself, a
# defect: touching a widely-watched file is normal, legitimate work. A gate
# that refuses legitimate work teaches its own bypass (ADR-014), and the
# bypass would disable the blocking arms next to it too.
#
# WHAT IT EXAMINED IS ALWAYS PRINTED, and examining nothing is a FAILURE, not
# a pass: the comparison range, the commit count, the path count and a sample
# of the paths appear on every run. A silent green here would be
# indistinguishable from a broken range computation, which is precisely the
# failure mode that has already produced three published-and-wrong findings in
# this repo (QB-013).
#
# BLIND-SPOT: it matches PATHS, not the call graph. A change inside a watched
#   file whose real damage lands in a caller that no claim watches is invisible
#   here -- and that is the shape of the /admin regression this arm was written
#   for. The ledger's watch globs are DECLARED coupling; nothing computes the
#   import graph, so the radius is only as wide as somebody remembered to
#   declare. Two consequences, both real today:
#   (a) a changed path watched by no active claim reports ZERO dependents,
#       which reads identically to "nothing depends on it" -- silence here
#       means UNWATCHED, not SAFE (717 of 1096 tracked files are dark;
#       `scripts/truth impact --inverse`);
#   (b) the work items named under a claim come from `truth impact`, which
#       filters wk- ids to open/claimed but lists foreign tracker ids (bd
#       twins) unconditionally, because their status lives tracker-side where
#       the ledger fold cannot see it. A closed bd twin can still appear.
# BLIND-SPOT-PROBE: scripts/tests/probes/impact-check-blind.sh
#
# Exit codes: 0 examined >=1 path / 1 examined nothing (dark) / 2 sensor failed.
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$ROOT" ] || ! cd "$ROOT"; then
  echo "impact-check: SENSOR FAILED -- not inside a git work tree; 0 path(s) examined"
  exit 2
fi

if ! git rev-parse -q --verify HEAD >/dev/null 2>&1; then
  echo "impact-check: DARK -- HEAD is unborn (no commits yet); 0 path(s) examined, so this arm proves nothing"
  exit 1
fi

# --- 1. what is about to be pushed --------------------------------------
# Three cases, all reachable in this repo's normal life:
#   A. a tracking branch      -> merge-base(upstream, HEAD)..HEAD
#   B. a branch with no upstream (worktree branches are created this way)
#      -> everything not reachable from ANY remote-tracking ref, bounded
#         below by the parent of the oldest such commit
#   C. first push of a repo with no remote ancestry at all -> the whole tree
MODE=range; BASE=""; LABEL=""; NCOMMITS=0
UP="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
if [ -n "$UP" ] && git rev-parse -q --verify "$UP^{commit}" >/dev/null 2>&1; then
  NCOMMITS="$(git rev-list --count "$UP..HEAD" 2>/dev/null || echo 0)"
  BASE="$(git merge-base "$UP" HEAD 2>/dev/null || true)"
  if [ -n "$BASE" ]; then
    LABEL="$UP (upstream tracking ref)"
  else
    MODE=whole
    LABEL="$UP (no common ancestor with HEAD -- treating the whole tree as new)"
  fi
else
  UNPUSHED="$(git rev-list HEAD --not --remotes 2>/dev/null || true)"
  NCOMMITS="$(printf '%s\n' "$UNPUSHED" | grep -c . || true)"
  if [ "$NCOMMITS" -eq 0 ]; then
    BASE=HEAD
    LABEL="no upstream; every commit on HEAD is already on a remote-tracking ref"
  else
    OLDEST="$(printf '%s\n' "$UNPUSHED" | grep . | tail -1)"
    if BASE="$(git rev-parse -q --verify "${OLDEST}^{commit}^" 2>/dev/null)" && [ -n "$BASE" ]; then
      LABEL="no upstream; boundary is the parent of $(git rev-parse --short "$OLDEST"), the oldest commit on no remote"
    else
      MODE=whole
      LABEL="no upstream and no remote ancestry -- first push of the entire history"
    fi
  fi
fi

# core.quotepath=false keeps non-ASCII paths raw so they match the ledger's
# globs; this repo has Polish filenames under kitchen-cam/cabinet-types/.
if [ "$MODE" = whole ]; then
  PATHS="$(git -c core.quotepath=false ls-tree -r --name-only HEAD 2>/dev/null || true)"
else
  PATHS="$(git -c core.quotepath=false diff --name-only "$BASE" HEAD 2>/dev/null || true)"
fi
NPATHS="$(printf '%s\n' "$PATHS" | grep -c . || true)"

if [ "$NPATHS" -eq 0 ]; then
  # Not a clean pass. An empty change set and a broken range computation look
  # the same from the outside, so this says so out loud rather than going
  # quiet -- the dark-arm rule, which applies to advisory arms too.
  echo "impact-check: DARK -- 0 changed path(s) over ${NCOMMITS} commit(s) vs ${LABEL}; nothing was examined, so this arm proves nothing"
  exit 1
fi

# --- 2. ask the ledger, do not re-implement it ---------------------------
FILES=()
while IFS= read -r p; do
  [ -n "$p" ] && FILES+=("$p")
done <<EOF
$PATHS
EOF

JSON="$(scripts/truth impact --json -- "${FILES[@]}" 2>&1)"; RC=$?
if [ $RC -ne 0 ] && [ $RC -ne 3 ]; then
  # 0 = nothing watched, 3 = rows found; anything else means the verb itself
  # failed and NOTHING was actually checked.
  echo "impact-check: SENSOR FAILED -- 'scripts/truth impact' exited ${RC} over ${NPATHS} path(s); nothing was examined"
  printf '%s\n' "$JSON" | tail -3 | sed 's/^/  /'
  exit 2
fi

IMPACT_JSON="$JSON" IMPACT_NPATHS="$NPATHS" IMPACT_NCOMMITS="$NCOMMITS" \
IMPACT_LABEL="$LABEL" IMPACT_PATHS="$PATHS" python3 - <<'PY'
import json, os

rows = json.loads(os.environ["IMPACT_JSON"] or "[]")
npaths = os.environ["IMPACT_NPATHS"]
ncommits = os.environ["IMPACT_NCOMMITS"]
label = os.environ["IMPACT_LABEL"]
paths = [p for p in os.environ["IMPACT_PATHS"].splitlines() if p]

work = sorted({w for r in rows for w in r["holds"]})
tiers = {}
for r in rows:
    t = r["tier"] or "P?"
    tiers[t] = tiers.get(t, 0) + 1
tier_s = " ".join("%s x%d" % kv for kv in sorted(tiers.items())) or "none"

# Column-0 summary line. The arm extractor in pre-push-checks.sh keeps the
# LAST line matching ^[^space].*': ' -- so everything below stays indented.
print("impact-check: %s changed path(s) over %s commit(s) vs %s -> "
      "%d claim(s) endangered (%s), %d open work item(s) standing on them"
      % (npaths, ncommits, label, len(rows), tier_s, len(work)))

SHOW = 12
for p in paths[:SHOW]:
    print("  examined  %s" % p)
if len(paths) > SHOW:
    print("  examined  ... and %d more path(s)" % (len(paths) - SHOW))

if not rows:
    print("  IMPACT    no active claim watches any of these paths -- read that "
          "as UNWATCHED, not as SAFE (see the BLIND-SPOT header)")
else:
    for r in rows:
        text = r["text"] or ""
        if len(text) > 110:
            text = text[:107] + "..."
        print("  IMPACT    %s (%s, %s) via %s"
              % (r["claim"], r["tier"], r["status"], ", ".join(r["touched"])))
        print("            %s" % text)
        if r["holds"]:
            print("            -> if that premise dies, ready HOLDs %s"
                  % ", ".join(r["holds"]))
    if work:
        print("  IMPACT    open work standing on the above: %s" % ", ".join(work))
PY
exit 0
