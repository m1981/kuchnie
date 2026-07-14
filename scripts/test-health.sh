#!/usr/bin/env bash
# test-health: judge the pinned-test convention by the ledger status of the
# ids tests cite (R4, ISO/IEC/IEEE 29119 — spec: docs/specs/conformance-join.md,
# concept: docs/reviews/two-ledger-concept-2026-07-15.md I.6).
# Sibling of spec-health.sh (cited ids in specs) and doc-health.sh (prose
# fabric): this one closes the family's last ungated convention — a test
# citing a tr-/wk- id is only evidence while that id exists and holds.
#
# FAIL (exit 1): a cited id that does not exist in the ledger — a fabricated
#   or mistyped citation is a broken traceability link, not a style issue.
# WARN: a citation whose claim is retracted or diverged (the test pins a
#   fact the ledger no longer believes — re-point or re-verify);
#   inverse check: a wk- item closed in the last 14 days with no citing
#   test in the swept directories (claim-at-death without a pin).
# Totals reported: citations / distinct ids / suites citing / files swept.
#
# Sweep roots (test files = *.py under these): the four component suites,
# the exercise harness, and scripts/tests (pinned tests for repo tooling).
# Fixture override: TEST_HEALTH_ROOTS="dir1:dir2" (colon-separated) — the
# ledger side always comes from scripts/truth (the canonical fold).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEFAULT_ROOTS="kuchnie-core/tests:kitchen-cam/tests:kitchen-erp/tests:home-builder-adapter/tests:exercises/harness/tests:scripts/tests"
ROOTS="${TEST_HEALTH_ROOTS:-$DEFAULT_ROOTS}"

CLAIMS_JSON="$(scripts/truth list --json)"
if ! ISSUES_JSON="$(scripts/truth issues --json 2>/dev/null)"; then
  echo "test-health: 'truth issues --json' failed; treating issue records as absent (wk- ids will report missing)" >&2
  ISSUES_JSON='[]'
fi

export ROOTS CLAIMS_JSON ISSUES_JSON

python3 - <<'PY'
import json, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ID_RE = re.compile(r"\b(?:tr|wk)-[0-9a-f]{8}\b")
BAD_CLAIM = {"retracted", "diverged"}

claims = {r["id"]: r for r in json.loads(os.environ["CLAIMS_JSON"])}
issues = {r["id"]: r for r in json.loads(os.environ["ISSUES_JSON"])}
known = set(claims) | set(issues)
roots = [Path(r) for r in os.environ["ROOTS"].split(":") if r.strip()]

# ── sweep test files for cited ids ────────────────────────────────────
failures = warnings = 0
cited_total = 0
cited_ids: set[str] = set()
suites_citing: set[str] = set()
files_swept = 0
for root in roots:
    if not root.is_dir():
        continue
    for f in sorted(root.rglob("*.py")):
        if "__pycache__" in f.parts:
            continue
        files_swept += 1
        ids = ID_RE.findall(f.read_text(encoding="utf-8", errors="replace"))
        if not ids:
            continue
        suites_citing.add(str(root))
        cited_total += len(ids)
        hits = []
        for rid in sorted(set(ids)):
            cited_ids.add(rid)
            if rid not in known:
                hits.append(f"  FAIL  {rid}  cited but missing from the ledger -- fabricated or mistyped citation")
                failures += 1
            elif rid in claims and claims[rid]["status"] in BAD_CLAIM:
                hits.append(f"  WARN  {rid}  {claims[rid]['status']} -- the test pins a fact the ledger no longer believes")
                warnings += 1
        if hits:
            print(f)
            print("\n".join(hits))

# ── inverse check (WARN-only): recent wk closes without a citing test ─
# Timestamps come from the raw append-only file (the fold's derived views
# do not expose close times); file order is append order (ADR-008).
closed_at: dict[str, str] = {}
ledger = Path(".truth/claims.jsonl")
if ledger.exists():
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("kind") != "issue_event":
            continue
        p = ev.get("payload", {})
        if p.get("event") == "closed":
            closed_at[p.get("issue", "")] = ev.get("ts", "")
        elif p.get("event") == "reopened":
            closed_at.pop(p.get("issue", ""), None)
cutoff = datetime.now(timezone.utc) - timedelta(days=14)
for wk, ts in sorted(closed_at.items()):
    if not wk.startswith("wk-") or wk in cited_ids:
        continue
    if issues.get(wk, {}).get("status") != "closed":
        continue
    try:
        when = datetime.fromisoformat(ts)
    except ValueError:
        continue
    if when >= cutoff:
        title = issues.get(wk, {}).get("title", "")[:60]
        print(f"  WARN  {wk}  closed {when.date()} with no citing test in the swept suites -- {title}")
        warnings += 1

print(f"test-health: {failures} failure(s), {warnings} warning(s) -- "
      f"{cited_total} citation(s), {len(cited_ids)} distinct id(s), "
      f"{len(suites_citing)}/{len(roots)} suite(s) citing, "
      f"{files_swept} test file(s) swept")
sys.exit(1 if failures else 0)
PY
