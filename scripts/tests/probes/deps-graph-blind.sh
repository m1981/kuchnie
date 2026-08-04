#!/usr/bin/env bash
# Blind-spot probe for scripts/deps-graph.py. Contract: 0 = blind spot REAL.
#
# Declared (clause a of the BLIND-SPOT block): every edge is a STATIC, LITERAL
# edge, so a command whose target is a shell VARIABLE is invisible. The graph
# is a lower bound on coupling; silence never means "not coupled".
#
# Probed by the sharpest instance of it in this repo. `scripts/pre-push-checks.sh`
# runs the four domain suites through
#
#     run_suite "kuchnie-core" kuchnie-core "$ROOT/.venv/bin/python"
#     ... out=$(cd "$dir" && "$py" -m pytest tests/ ...)
#
# — roughly 1,400 tests across kuchnie-core/, kitchen-erp/, catalog/ and
# kitchen-cam/, and not one of those paths appears as a literal command target.
# So the graph shows ZERO edges from pre-push-checks.sh into any of those four
# component trees. If someone later teaches the extractor to resolve run_suite
# (or any variable dispatch), those edges appear, this probe fails, and the
# BLIND-SPOT prose in scripts/deps-graph.py has to be rewritten — which is good
# news and exactly the self-maintaining property doctrine L2 is after.
#
# POSITIVE CONTROL, because an extractor that produced NO edges at all would
# satisfy the assertion above trivially (QB-013: run a control you know
# matches). The same file's literal `run_gate ... scripts/session-gates.d/*.sh`
# call sites must still yield edges in the same run.
#
# Builds into a scratch graph rather than reading docs/deps-graph.jsonl: a
# probe that asserts against a possibly-stale committed artifact proves nothing
# about today's extractor.
set -u
cd "$(git rev-parse --show-toplevel)" || exit 1

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PY=".venv/bin/python"
[ -x "$PY" ] || PY=python3

DEPS_GRAPH_PATH="$TMP/graph.jsonl" "$PY" scripts/deps-graph.py --build \
  >"$TMP/build.log" 2>&1
rc=$?
if [ $rc -ne 0 ]; then
  echo "probe-deps-graph: SENSOR FAILED -- --build exited $rc; nothing was probed"
  tail -20 "$TMP/build.log"
  exit 1
fi

DEPS_GRAPH_PATH="$TMP/graph.jsonl" "$PY" - <<'PYEOF'
import json
import os
import sys

edges = [json.loads(l) for l in open(os.environ["DEPS_GRAPH_PATH"])
         if l.strip()]
if not edges:
    print("probe-deps-graph: SENSOR FAILED -- the graph is empty; the probe "
          "examined nothing")
    sys.exit(1)

SRC = "scripts/pre-push-checks.sh"
out = [e for e in edges if e["src"] == SRC]

# --- positive control: the extractor must still be able to SPEAK -----------
control = [e for e in out
           if e["kind"] == "invokes"
           and e["dst"].startswith("scripts/session-gates.d/")]
if not control:
    print(f"probe-deps-graph: POSITIVE CONTROL FAILED -- {SRC} produced no "
          "invokes edge into session-gates.d at all. The extractor is silent "
          "everywhere, so the silence below would prove nothing.")
    sys.exit(1)

# --- the blind spot itself -------------------------------------------------
SUITES = ("kuchnie-core/", "kitchen-erp/", "catalog/", "kitchen-cam/")
leaked = [e for e in out if e["dst"].startswith(SUITES)]
if leaked:
    print(f"probe-deps-graph: {SRC} now shows {len(leaked)} edge(s) into the "
          "domain suites it runs through the run_suite variable dispatch "
          f"(e.g. {leaked[0]['dst']} at {leaked[0]['file']}:{leaked[0]['line']}"
          "). The declared blind spot -- variable/computed command targets are "
          "invisible -- is CLOSED. Rewrite the BLIND-SPOT block in "
          "scripts/deps-graph.py.")
    sys.exit(1)

print(f"probe-deps-graph: blind spot intact -- {SRC} runs ~1,400 tests across "
      f"{len(SUITES)} component trees through a shell variable, and the graph "
      f"shows 0 edges into any of them. Control: the same file's "
      f"{len(control)} literal session-gates.d invocation(s) ARE visible in "
      "the same run, so the extractor is alive.")
PYEOF
