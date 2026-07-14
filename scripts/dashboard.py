#!/usr/bin/env python3
"""Generate STATUS.md — the project dashboard. NEVER hand-edit STATUS.md.

Views (docs/development-process.md; design: five moments, one question each):
  V4 health strip   — gates, claims by state, verdict queue, toolchain
  V2 ready lane     — truth ready joined with bd priorities
  V3 roadmap        — L1-stage swimlanes + bd dependency arrows (mermaid)
  V1 capability     — docs/capability-map.csv, evidence ids checked live
  V5 delta log      — work closed in the last 14 days (from claims.jsonl)

Usage:
  .venv/bin/python scripts/dashboard.py           # (re)generate STATUS.md
  .venv/bin/python scripts/dashboard.py --check   # exit 1 if STATUS.md is
                                                  # stale vs current data
The --check mode ignores the volatile "Generated:" line, so committing the
dashboard does not immediately stale it.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATUS = REPO / "STATUS.md"
VOLATILE = "> Generated:"
STAGE_NAMES = {
    "0": "Process/infra",
    "1": "First visit (decors)",
    "2": "Pomiar + project record",
    "3": "Layout & design (hb5)",
    "4": "Decomposition",
    "5": "Purchasing",
    "6": "Cutting & edging (external)",
    "7": "CAM / drilling",
    "8": "Assembly outputs",
    "9": "Worktops",
    "11": "Handover archive",
}


def run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                              timeout=60).stdout
    except Exception:  # noqa: BLE001
        return ""


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


# ── data gathering ───────────────────────────────────────────────

def truth_list() -> list[tuple[str, str]]:
    """[(tr-id, status)] from `truth list`."""
    out = []
    for line in run(["scripts/truth", "list"]).splitlines():
        m = re.match(r"(tr-[0-9a-f]+)\s+(\S+)", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def issue_titles() -> dict[str, str]:
    """wk-id -> title, from the ledger's issue events."""
    titles: dict[str, str] = {}
    for line in (REPO / ".truth/claims.jsonl").read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("kind") == "issue":
            titles[ev["id"]] = ev["payload"].get("title", "")
    return titles


def truth_ready() -> list[dict]:
    """READY + HELD items from `truth ready`."""
    titles = issue_titles()
    items = []
    for line in run(["scripts/truth", "ready"]).splitlines():
        held = line.startswith("HELD")
        m = re.search(r"(wk-[0-9a-f]+)\s+(.*)", line)
        if m:
            title = m.group(2).strip()
            note = ""
            if "[warn:" in title:
                title, _, note = title.partition("[warn:")
                note = "warn: " + note.rstrip("]").strip()
            if held:
                # HELD lines carry the dead premise, not the title
                mm = re.search(r"broken premises: (.*)", line)
                note = "HELD — " + (mm.group(1) if mm else "premise dead")
                title = titles.get(m.group(1), "")
            items.append({"wk": m.group(1), "title": title.strip(),
                          "held": held, "note": note})
    return items


def bd_open() -> dict[str, dict]:
    try:
        data = json.loads(run(["bd", "list", "--status=open", "--json"]) or "[]")
    except json.JSONDecodeError:
        data = []
    return {i["id"]: i for i in data}


def bd_deps(bd_id: str) -> list[str]:
    """Ids this issue depends on (queried only when the count says so)."""
    try:
        info = json.loads(run(["bd", "show", bd_id, "--json"]) or "{}")
    except json.JSONDecodeError:
        return []
    if isinstance(info, list):
        info = info[0] if info else {}
    out = []
    for d in info.get("dependencies") or []:
        out.append(d["id"] if isinstance(d, dict) else str(d))
    return out


def gate_tail(script: str) -> tuple[bool, str]:
    lines = run(["bash", f"scripts/{script}"]).strip().splitlines()
    tail = lines[-1] if lines else "(no output)"
    return (" 0 failure" in tail), tail


def manifest() -> dict:
    p = REPO / "exercises/e2e-d60-legrabox/generated/run-manifest.json"
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {}


def closed_recently(days: int = 14) -> list[dict]:
    titles: dict[str, str] = {}
    closed: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for line in (REPO / ".truth/claims.jsonl").read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("kind") == "issue":
            titles[ev["id"]] = ev["payload"].get("title", "")
        elif (ev.get("kind") == "issue_event"
              and ev["payload"].get("event") == "closed"):
            ts = datetime.fromisoformat(ev["ts"])
            if ts >= cutoff:
                wk = ev["payload"]["issue"]
                closed.append({"wk": wk, "ts": ts.date().isoformat(),
                               "basis": ev["payload"].get("basis", "")})
    for c in closed:
        c["title"] = titles.get(c["wk"], "")
    return closed


# ── rendering ────────────────────────────────────────────────────

_SYM = {"ok": "✅", "partial": "◐", "none": "✗", "model-only": "✗"}


def render() -> str:
    claims = truth_list()
    by_status: dict[str, int] = {}
    for _, st in claims:
        by_status[st] = by_status.get(st, 0) + 1
    live_ids = {i for i, st in claims if st == "live"}
    queue_n = len([l for l in run(["scripts/truth", "queue"]).splitlines() if l.strip()])
    spec_ok, spec_tail = gate_tail("spec-health.sh")
    doc_ok, doc_tail = gate_tail("doc-health.sh")
    man = manifest()
    bd = bd_open()
    rmap = read_csv(REPO / "docs/roadmap-map.csv")
    wk2bd = {r["wk_id"]: r["bd_id"] for r in rmap if r["wk_id"]}
    ready = truth_ready()

    L: list[str] = []
    a = L.append
    a("# STATUS — generated dashboard")
    a("")
    a("> Reader: Michał in any of his five moments (client call, session "
      "start, grooming, quality glance, retro) | Enables: answering each "
      "moment's question from one page instead of five commands | "
      "Update-trigger: GENERATED by `scripts/dashboard.py` — never "
      "hand-edit; freshness gated by `session-gates.d/30-dashboard-fresh.sh`")
    a("")
    a(f"{VOLATILE} {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    a("")

    # V4 — health strip
    a("## Health")
    a("")
    a("| Signal | State |")
    a("|---|---|")
    a(f"| spec-health | {'🟢' if spec_ok else '🔴'} {spec_tail} |")
    a(f"| doc-health | {'🟢' if doc_ok else '🔴'} {doc_tail} |")
    a("| flagship baseline | guarded by `scripts/exercise-gate.sh` "
      "(runs at session-close) |")
    claims_line = " · ".join(f"{k} {v}" for k, v in sorted(by_status.items()))
    a(f"| claims | {claims_line} |")
    a(f"| verdict queue | {queue_n} awaiting triage |")
    if man:
        a(f"| last exercise run | {man.get('started_utc', '?')} · "
          f"{man.get('blender_version', '?')} · repo "
          f"`{man.get('repo_sha', '')[:7]}` · hb5 "
          f"`{man.get('hb5_sha', '')[:7]}` |")
    a("")

    # V2 — ready lane
    a("## Ready lane (`truth ready` × bd priority)")
    a("")
    a("| P | Work | Title | Premise health |")
    a("|---|---|---|---|")
    rows = []
    for it in ready:
        bd_id = wk2bd.get(it["wk"], "")
        prio = bd[bd_id]["priority"] if bd_id in bd else 9
        rows.append((it["held"], prio, it, bd_id))
    for held, prio, it, bd_id in sorted(rows, key=lambda r: (r[0], r[1])):
        p = f"P{prio}" if prio != 9 else "—"
        a(f"| {p} | {it['wk']}{' / ' + bd_id if bd_id else ''} | "
          f"{it['title']} | {it['note'] or 'live'} |")
    a("")

    # V3 — roadmap swimlanes + deps
    a("## Roadmap by L1 stage (order = bd priority; arrows = bd deps)")
    a("")
    a("```mermaid")
    a("flowchart LR")
    stages: dict[str, list[dict]] = {}
    for r in rmap:
        if r["bd_id"] in bd:  # open items only
            stages.setdefault(r["stage"], []).append(r)
    node_of: dict[str, str] = {}
    for stage in sorted(stages, key=lambda s: int(s)):
        name = STAGE_NAMES.get(stage, f"Stage {stage}")
        a(f'    subgraph s{stage} ["{stage}. {name}"]')
        for r in sorted(stages[stage], key=lambda r: bd[r["bd_id"]]["priority"]):
            nid = r["bd_id"].replace("-", "_")
            node_of[r["bd_id"]] = nid
            prio = bd[r["bd_id"]]["priority"]
            a(f'        {nid}["P{prio} {r["bd_id"]}<br/>{r["label"]}"]')
        a("    end")
    for bd_id, info in bd.items():
        if info.get("dependency_count", 0) > 0 and bd_id in node_of:
            for dep in bd_deps(bd_id):
                if dep in node_of:
                    a(f"    {node_of[dep]} --> {node_of[bd_id]}")
    a("```")
    a("")
    unmapped = [i for i in bd if i not in {r['bd_id'] for r in rmap}]
    if unmapped:
        a(f"Unmapped open bd issues (add to `docs/roadmap-map.csv`): "
          f"{', '.join(sorted(unmapped))}")
        a("")

    # V1 — capability board
    a("## Capability board (what you can promise a client)")
    a("")
    cap = read_csv(REPO / "docs/capability-map.csv")
    a("| Type | rozrys | drills | DXF | BOM | 3D | Note |")
    a("|---|---|---|---|---|---|---|")
    dead: list[str] = []
    for r in cap:
        cells = [_SYM.get(r[c], r[c]) for c in
                 ("rozrys", "drills", "dxf", "bom", "extract3d")]
        a(f"| `{r['type']}` | {' | '.join(cells)} | {r['note']} |")
        for tid in re.findall(r"tr-[0-9a-f]+", r.get("evidence", "")):
            if tid not in live_ids:
                dead.append(f"{r['type']}: {tid}")
    if dead:
        a("")
        a("**⚠ capability cells citing non-live facts (re-verify or re-map):** "
          + ", ".join(dead))
    a("")
    a("Legend: ✅ trusted (id-cited) · ◐ works with caveats · ✗ absent. "
      "Source: `docs/capability-map.csv` (each row cites its evidence).")
    a("")

    # V5 — delta log
    a("## Closed in the last 14 days")
    a("")
    recent = closed_recently()
    if not recent:
        a("(nothing closed in the window)")
    for c in sorted(recent, key=lambda c: c["ts"], reverse=True):
        basis = (c["basis"][:100] + "…") if len(c["basis"]) > 100 else c["basis"]
        a(f"- **{c['ts']}** {c['wk']} — {c['title']}  \n  {basis}")
    a("")
    return "\n".join(L) + "\n"


def stable(text: str) -> str:
    return "\n".join(l for l in text.splitlines()
                     if not l.startswith(VOLATILE))


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        if not STATUS.exists():
            print("dashboard --check: STATUS.md missing — run scripts/dashboard.py")
            return 1
        if stable(STATUS.read_text()) != stable(text):
            print("dashboard --check: STATUS.md is STALE — regenerate with "
                  "scripts/dashboard.py and commit it")
            return 1
        print("dashboard --check: STATUS.md is fresh")
        return 0
    STATUS.write_text(text)
    print(f"wrote {STATUS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
