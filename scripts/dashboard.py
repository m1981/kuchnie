#!/usr/bin/env python3
"""Generate STATUS.md — the project dashboard. NEVER hand-edit STATUS.md.

Views (docs/development-process.md; design: five moments, one question each):
  V4 health strip   — gates, claims by state, verdict queue, toolchain
  V2 ready lane     — truth ready joined with bd priorities
  V3 roadmap        — L1-stage swimlanes + bd dependency arrows (mermaid)
  V3b by-goal       — same items grouped by use case (`uc` column of
                      docs/roadmap-map.csv; goals from docs/specs/use-cases.md)
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


def uc_goals() -> dict[str, str]:
    """UC-N -> goal, parsed from the use-cases spec inventory table."""
    goals: dict[str, str] = {}
    try:
        text = (REPO / "docs/specs/use-cases.md").read_text(encoding="utf-8")
    except OSError:
        return goals
    for m in re.finditer(r"^\| (UC-\d+) \| [^|]* \| ([^|]*) \|", text, re.M):
        goal = re.sub(r"\s*\([^)]*\)", "", m.group(2)).strip()
        goals[m.group(1)] = goal
    return goals


def claims_json() -> list[dict]:
    """Full claim records (id, status, text, ...) from `truth list --json`."""
    try:
        return json.loads(run(["scripts/truth", "list", "--json"]) or "[]")
    except json.JSONDecodeError:
        return []


def acceptance_items(text: str) -> list[dict]:
    """Parse the '## Acceptance' section of a spec into pre-written items.

    Each bullet holds one quoted done-claim text; the UC ids the bullet
    mentions attribute it to use cases (empty list = spec-wide).
    Pure function — R7 classifier input (docs/specs/conformance-join.md,
    wk-9d77de94).
    """
    m = re.search(r"^## Acceptance$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    items: list[dict] = []
    bullet: list[str] = []
    for line in m.group(1).splitlines() + ["- "]:
        if line.startswith("- "):
            if bullet:
                whole = " ".join(l.strip() for l in bullet).strip()
                q = re.search(r'"(.*)"', whole)
                items.append({
                    "text": q.group(1) if q else whole.lstrip("- ").strip(),
                    "ucs": sorted(set(re.findall(r"UC-\d+", whole))),
                })
            bullet = [line[2:]]
        elif bullet and line.strip():
            bullet.append(line)
        elif bullet and not line.strip():
            pass
    return items


def _sig_tokens(text: str) -> set[str]:
    """Significant-word signature for the lexical R7 match (no NLP)."""
    return {t for t in re.findall(r"[a-z0-9][a-z0-9_.\-/]{3,}", text.lower())}


def classify_acceptance(items: list[dict], claims: list[dict],
                        threshold: float = 0.5) -> list[dict]:
    """Classify each pre-written acceptance item against the ledger.

    PRE-WRITTEN — no claim covers >= threshold of the item's tokens;
    FILED — best-covering claim exists but is not live;
    LIVE — best-covering claim is live.
    Deterministic: ties resolve live-first, then lexicographic claim id.
    """
    out: list[dict] = []
    for it in items:
        sig = _sig_tokens(it["text"])
        best_id, best_status, best_cov = "", "", 0.0
        for c in sorted(claims, key=lambda c: (c["status"] != "live", c["id"])):
            cov = len(sig & _sig_tokens(c.get("text", ""))) / len(sig) if sig else 0.0
            if cov > best_cov:
                best_id, best_status, best_cov = c["id"], c["status"], cov
        if best_cov >= threshold:
            state = "LIVE" if best_status == "live" else "FILED"
            out.append({**it, "state": state, "claim": best_id,
                        "status": best_status})
        else:
            out.append({**it, "state": "PRE-WRITTEN", "claim": "",
                        "status": ""})
    return out


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

    # R7 — completeness view (proto-R1/R7, docs/specs/conformance-join.md)
    a("## Completeness (R7) — use-cases Acceptance vs ledger")
    a("")
    a("Pre-written acceptance items of `docs/specs/use-cases.md` classified "
      "against claim texts (lexical match, no NLP): PRE-WRITTEN = no claim "
      "yet · FILED = claim exists, not live · LIVE = claim live.")
    a("")
    try:
        uc_text = (REPO / "docs/specs/use-cases.md").read_text(encoding="utf-8")
    except OSError:
        uc_text = ""
    acc = classify_acceptance(acceptance_items(uc_text), claims_json())
    a("| UC | Acceptance item | State | Claim |")
    a("|---|---|---|---|")
    for it in acc:
        uc = ", ".join(it["ucs"]) if it["ucs"] else "(spec-wide)"
        short = it["text"][:90] + ("…" if len(it["text"]) > 90 else "")
        claim = f"{it['claim']} ({it['status']})" if it["claim"] else "—"
        a(f"| {uc} | {short} | {it['state']} | {claim} |")
    n_live = sum(1 for it in acc if it["state"] == "LIVE")
    a("")
    a(f"**Gauge: {n_live}/{len(acc)} acceptance items LIVE.** "
      "The denominator is intent (pre-written claims), the numerator is "
      "demonstrated fact — the gauge can go down when a commit stales a "
      "completion claim.")
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

    # V3b — roadmap by use case (goal)
    a("## Roadmap by use case (order = bd priority; goals from "
      "`docs/specs/use-cases.md`)")
    a("")
    a("```mermaid")
    a("flowchart LR")
    goals = uc_goals()
    by_uc: dict[str, list[dict]] = {}
    for r in rmap:
        if r["bd_id"] in bd:  # open items only
            by_uc.setdefault((r.get("uc") or "").strip(), []).append(r)
    uc_node: dict[str, str] = {}
    for uc in sorted(by_uc, key=lambda u: (u == "", int(u.split("-")[1]) if u else 0)):
        if uc:
            gid = "g" + uc.replace("-", "_")
            label = f"{uc} — {goals[uc]}" if uc in goals else uc
        else:
            gid, label = "g_none", "no UC (process/infra — route or leave)"
        a(f'    subgraph {gid} ["{label}"]')
        for r in sorted(by_uc[uc], key=lambda r: bd[r["bd_id"]]["priority"]):
            nid = "u_" + r["bd_id"].replace("-", "_")
            uc_node[r["bd_id"]] = nid
            prio = bd[r["bd_id"]]["priority"]
            a(f'        {nid}["P{prio} {r["bd_id"]}<br/>{r["label"]}"]')
        a("    end")
    for bd_id, info in bd.items():
        if info.get("dependency_count", 0) > 0 and bd_id in uc_node:
            for dep in bd_deps(bd_id):
                if dep in uc_node:
                    a(f"    {uc_node[dep]} --> {uc_node[bd_id]}")
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
