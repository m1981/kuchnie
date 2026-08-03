#!/usr/bin/env python3
"""evidence-subset: find claims whose recipe never reads a path it watches.

WHY. A claim declares `evidence_paths` (what staling watches) and an evidence
command (what proves it). When a declared path is not among the things the
command actually reads, the two halves disagree: a change to that path DEMOTES
the claim, but the evidence cannot detect whether the fact itself moved. The
verifier then rechecks a hash that never depended on the change. That is the
defect the 2026-08-02 audit found in tr-ce5c7845 -- two grep counts while the
claim's sentence was about a mapping in a third file.

Doctrine reference: agentic-verification-doctrine-2026-08-03.md L1 Adopt 1,
"refuse a recipe that does not read its own evidence_paths".

MEASURED FIRST, THEN BUILT. A naive matcher (exact path or basename) reported
4 offenders; making it aware that `grep -r <dir>` legitimately covers every
file beneath <dir> dropped that to 0. The real defect is not "reads none of
its paths" but "reads only some" -- proper subset, not disjointness. On
2026-08-04 that is 12 of 109 claims (11%).

upstream-candidate: the natural home is an intake lint beside ADR-037's
recipe_lints in truthlib/evidence.py, warning at `truth claim` time when the
author is present. This script is the consumer-side audit until then.

Exit 0 always for --json/--write; the gate wrapper decides posture.
"""
from __future__ import annotations

import json
import posixpath
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "docs" / "evidence-subset-baseline.txt"


def _prefixes(p: str) -> list[str]:
    """Every directory prefix of a declared path, plus the path itself.

    A recipe that greps a directory reads everything under it; treating the
    declared file as unread there would be a false positive, and a gate that
    cries wolf is the one people learn to skip (ADR-014).
    """
    p = p.split("*")[0].rstrip("/")
    out: list[str] = []
    while p and p not in (".", "/"):
        out.append(p)
        p = posixpath.dirname(p)
    return out


def path_is_read(cmd: str, declared: str) -> bool:
    for cand in _prefixes(declared):
        if cand and cand in cmd:
            return True
    base = declared.rsplit("/", 1)[-1]
    return bool(base) and "*" not in base and base in cmd


def findings() -> list[tuple[str, str, list[str]]]:
    """(claim_id, status, unread_paths) for every active claim."""
    out = subprocess.run(
        [str(ROOT / "scripts" / "truth"), "list", "--json"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if out.returncode != 0:
        # F1 rule: a sensor that cannot run must scream, never read as zero.
        print("evidence-subset: SENSOR FAILED -- 'truth list --json' exited "
              f"{out.returncode}; nothing was checked", file=sys.stderr)
        raise SystemExit(2)
    folded = {r["id"]: r for r in json.loads(out.stdout)}

    rows = []
    with (ROOT / ".truth" / "claims.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["kind"] != "claim":
                continue
            cid = rec["id"]
            status = folded.get(cid, {}).get("status")
            if status in (None, "retracted"):
                continue
            payload = rec["payload"]
            cmd = (payload.get("evidence") or {}).get("command") or ""
            declared = payload.get("evidence_paths") or []
            if not cmd or not declared:
                continue
            unread = [p for p in declared if not path_is_read(cmd, p)]
            if unread:
                rows.append((cid, status, unread))
    return rows


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {
        ln.strip() for ln in BASELINE.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    }


def keys(rows) -> list[str]:
    return sorted(f"{cid} {p}" for cid, _st, unread in rows for p in unread)


def main() -> int:
    rows = findings()
    all_keys = keys(rows)

    if "--write" in sys.argv:
        BASELINE.write_text(
            "# evidence-subset accepted debt -- one 'tr-id path' per line.\n"
            "# Each line is a claim that watches a path its own recipe never\n"
            "# reads: staling there cannot be detected by the evidence.\n"
            "# Regenerate deliberately: python3 scripts/evidence-subset.py --write\n"
            + "\n".join(all_keys) + "\n", encoding="utf-8")
        print(f"evidence-subset: baseline written, {len(all_keys)} accepted")
        return 0

    if "--json" in sys.argv:
        print(json.dumps([{"claim": c, "status": s, "unread": u}
                          for c, s, u in rows], indent=2))
        return 0

    # default: print every key, one per line, for the gate to diff
    for k in all_keys:
        print(k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
