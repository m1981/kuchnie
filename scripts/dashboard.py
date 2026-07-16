#!/usr/bin/env python3
"""Generate STATUS.md — the project dashboard. NEVER hand-edit STATUS.md.

v2 (wk-f6d3d2f1; design: docs/reviews/dashboard-pm-review-2026-07-17.md):
five sections = five PM questions, each with needle-moving commands:
  1 CAN I SELL IT     — UC progress bars (spec markers), all-specs
                        acceptance gauge (R7), capability board
  2 BLOCKED ON OWNER  — human-only retractions (paste-ready batch),
                        undressed UCs with dressing prompts
  3 WHAT'S NEXT       — ready lane split product|process (axis column of
                        docs/roadmap-map.csv) + proportion stat
  4 WHERE'S THE MASS  — per-stage counts, L1/UC mermaid swimlanes,
                        gap register G1-G13 (docs/gap-register.csv)
  5 MACHINE OK        — health strip, R-rule lines, delta count + top 5
Format stays MARKDOWN (dev-process §4: every status one grep from proof).

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
    FILED — best candidate exists but is not live;
    LIVE — best candidate is live.
    Ranking among candidates >= threshold: live-first, then coverage,
    then lexicographic claim id — so a live successor beats a dead
    original even at lower overlap (wk-eb7164f1).
    """
    out: list[dict] = []
    for it in items:
        sig = _sig_tokens(it["text"])
        candidates = []
        for c in claims:
            cov = len(sig & _sig_tokens(c.get("text", ""))) / len(sig) if sig else 0.0
            if cov >= threshold:
                candidates.append((c["status"] != "live", -cov, c["id"], c["status"]))
        if candidates:
            _, neg_cov, best_id, best_status = min(candidates)
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


def all_acceptance() -> list[dict]:
    """Acceptance items swept over EVERY spec, tagged with its file."""
    items: list[dict] = []
    for path in sorted(REPO.glob("docs/specs/*.md")) + \
            sorted(REPO.glob("*/docs/specs/*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for it in acceptance_items(text):
            items.append({**it, "spec": path.stem})
    return items


def uc_progress() -> tuple[list[dict], list[dict]]:
    """(dressed, undressed) use cases from the spec's own markers.

    A dressed UC's numbered steps classify by the spec convention:
    '⚠' = open (its wk-/tr- ids collected), 'out of system' = excluded,
    else supported. Extensions likewise. Undressed = inventory rows
    marked 'full — to write'.
    """
    try:
        text = (REPO / "docs/specs/use-cases.md").read_text(encoding="utf-8")
    except OSError:
        return [], []
    goals = uc_goals()
    undressed = [{"uc": m.group(1), "goal": goals.get(m.group(1), "")}
                 for m in re.finditer(
                     r"^\| (UC-\d+) \|.*full — to write", text, re.M)]
    dressed: list[dict] = []
    for m in re.finditer(r"^## (UC-\d+) — .*?fully dressed.*?$(.*?)(?=^## |\Z)",
                         text, re.M | re.S):
        uc, body = m.group(1), m.group(2)
        main = re.search(r"\*\*Main success scenario\*\*.*?$(.*?)(?=\*\*Extensions)",
                         body, re.M | re.S)
        steps = re.split(r"^\d+\. ", main.group(1), flags=re.M)[1:] if main else []
        ext_m = re.search(r"\*\*Extensions:\*\*$(.*?)(?=^[A-Z*#]|\Z)",
                          body, re.M | re.S)
        exts = re.findall(r"^- (\d+[a-z]\..*?)(?=^- \d|\Z)",
                          ext_m.group(1), re.M | re.S) if ext_m else []
        def _cls(chunks: list[str]) -> tuple[int, int, int, list[str]]:
            done = excl = 0
            open_ids: list[str] = []
            for c in chunks:
                if "out of system" in c:
                    excl += 1
                elif "⚠" in c:
                    open_ids += re.findall(r"(?:wk|kuchnie)-[0-9a-z]+", c)
                else:
                    done += 1
            return done, len(chunks) - excl, excl, sorted(set(open_ids))
        s_done, s_total, _, s_ids = _cls(steps)
        e_done, e_total, _, e_ids = _cls(exts)
        dressed.append({"uc": uc, "goal": goals.get(uc, ""),
                        "steps_done": s_done, "steps_total": s_total,
                        "ext_done": e_done, "ext_total": e_total,
                        "open_ids": sorted(set(s_ids + e_ids))})
    return dressed, undressed


def queue_split() -> tuple[list[str], list[str]]:
    """(diverged ids → human retraction, other ids → verifier sweep)."""
    human, verifier = [], []
    for line in run(["scripts/truth", "queue"]).splitlines():
        m = re.match(r"(tr-[0-9a-f]+)\s+\S+\s+(\S+)", line)
        if not m:
            continue
        (human if m.group(2) == "diverged" else verifier).append(m.group(1))
    return human, verifier


def bar(done: int, total: int, width: int = 12) -> str:
    filled = round(width * done / total) if total else 0
    return "█" * filled + "░" * (width - filled)


# ── rendering ────────────────────────────────────────────────────

_SYM = {"ok": "✅", "partial": "◐", "none": "✗", "model-only": "✗"}


def render() -> str:
    claims = truth_list()
    by_status: dict[str, int] = {}
    for _, st in claims:
        by_status[st] = by_status.get(st, 0) + 1
    live_ids = {i for i, st in claims if st == "live"}
    spec_ok, spec_tail = gate_tail("spec-health.sh")
    doc_ok, doc_tail = gate_tail("doc-health.sh")
    man = manifest()
    bd = bd_open()
    rmap = read_csv(REPO / "docs/roadmap-map.csv")
    wk2bd = {r["wk_id"]: r["bd_id"] for r in rmap if r["wk_id"]}
    wk2axis = {r["wk_id"]: r.get("axis", "") for r in rmap if r["wk_id"]}
    bd2axis = {r["bd_id"]: r.get("axis", "") for r in rmap}
    ready = truth_ready()
    dressed, undressed = uc_progress()
    human_q, verifier_q = queue_split()

    L: list[str] = []
    a = L.append
    a("# STATUS — generated dashboard (v2)")
    a("")
    a("> Reader: Michał asking one of five PM questions (can I sell it / "
      "what's on me / what's next / where's the mass / machine ok) | "
      "Enables: each section answers its question AND carries the command "
      "that moves the needle | Update-trigger: GENERATED by "
      "`scripts/dashboard.py` — never hand-edit; freshness gated by "
      "`session-gates.d/30-dashboard-fresh.sh`")
    a("")
    a(f"{VOLATILE} {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    a("")

    # ── 1 · CAN I SELL IT ────────────────────────────────────────
    a("## 1 · Can I sell it? — capability & feature progress")
    a("")
    for d in dressed:
        ids = " ".join(f"`{i}`" for i in d["open_ids"][:3])
        a(f"- **{d['uc']}** {bar(d['steps_done'], d['steps_total'])} "
          f"{d['steps_done']}/{d['steps_total']} steps · "
          f"{d['ext_done']}/{d['ext_total']} extensions — open: {ids or '—'}")
    for u in undressed:
        a(f"- **{u['uc']}** ░░░░░░░░░░░░ not dressed — {u['goal']} (see § 2)")
    a("")
    acc = classify_acceptance(all_acceptance(), claims_json())
    n_live = sum(1 for it in acc if it["state"] == "LIVE")
    a(f"**Acceptance gauge (R7, all specs): {n_live}/{len(acc)} LIVE.** "
      "Denominator = pre-written intent, numerator = demonstrated fact; "
      "it can go DOWN when a commit stales a completion claim.")
    a("")
    a("| Spec | UC | Acceptance item | State | Claim |")
    a("|---|---|---|---|---|")
    for it in acc:
        uc = ", ".join(it["ucs"]) if it["ucs"] else "—"
        short = it["text"][:70] + ("…" if len(it["text"]) > 70 else "")
        claim = f"{it['claim']} ({it['status']})" if it["claim"] else "—"
        a(f"| {it['spec']} | {uc} | {short} | {it['state']} | {claim} |")
    a("")
    a("| Type | rozrys | drills | DXF | BOM | 3D | Note |")
    a("|---|---|---|---|---|---|---|")
    cap = read_csv(REPO / "docs/capability-map.csv")
    dead: list[str] = []
    for r in cap:
        cells = [_SYM.get(r[c], r[c]) for c in
                 ("rozrys", "drills", "dxf", "bom", "extract3d")]
        a(f"| `{r['type']}` | {' | '.join(cells)} | {r['note']} |")
        for tid in re.findall(r"tr-[0-9a-f]+", r.get("evidence", "")):
            if tid not in live_ids:
                dead.append(f"{r['type']}: {tid}")
    a("")
    a("Legend: ✅ trusted (id-cited) · ◐ works with caveats · ✗ absent "
      "(`docs/capability-map.csv`).")
    if dead:
        a("")
        a("**⚠ cells citing non-live facts:** " + ", ".join(dead)
          + " — move the needle: `scripts/truth queue` then re-verify or "
            "re-map the cell.")
    a("")

    # ── 2 · BLOCKED ON MICHAŁ ────────────────────────────────────
    a("## 2 · Blocked on Michał — the owner lane")
    a("")
    if human_q:
        a(f"- **{len(human_q)} retraction(s) ready** (human-only; every "
          "diverged claim's verdict names its live successor). Paste:")
        a("")
        ids = " ".join(human_q)
        a("  ```")
        a(f"  for id in {ids}; do TRUTH_HUMAN=1 TRUTH_HUMAN_ACK=$id "
          "scripts/truth verdict $id retracted --basis "
          '"superseded; successor in verdict trail"; done')
        a("  ```")
    else:
        a("- retractions: none pending ✅")
    for u in undressed:
        a(f"- **{u['uc']} needs dressing** — {u['goal']}. "
          f"Move the needle: say *“Dress {u['uc']} with me”* "
          "(interview per docs/spec-convention.md).")
    if verifier_q or by_status.get("unverified") or by_status.get("stale"):
        n = len(verifier_q) + by_status.get("unverified", 0)
        a(f"- **{n} claim(s) for an agent verifier** (not you — but only "
          "you start sessions). Move the needle: say "
          "*“dispatch a verifier sweep”*.")
    a("")

    # ── 3 · WHAT'S NEXT ──────────────────────────────────────────
    a("## 3 · What's next — ready lane, product | process")
    a("")
    rows = []
    for it in ready:
        bd_id = wk2bd.get(it["wk"], "")
        prio = bd[bd_id]["priority"] if bd_id in bd else 9
        axis = wk2axis.get(it["wk"], "") or "?"
        rows.append((it["held"], prio, it, bd_id, axis))
    prod = [r for r in rows if r[4] == "product"]
    proc = [r for r in rows if r[4] != "product"]
    closed = closed_recently(7)
    PRODUCT_HINT = re.compile(
        r"UC-\d|G\d+\b|decompos|extract|drawer|rozrys|worktop|decor|"
        r"purchas|offer|variant|panel|runner|plinth|hinge|corner|price|"
        r"buildab|spine|catalog", re.I)
    def _axis_of(c: dict) -> str:
        mapped = wk2axis.get(c["wk"], "")
        if mapped:
            return mapped
        return "product" if PRODUCT_HINT.search(c["title"]) else "process"
    c_prod = sum(1 for c in closed if _axis_of(c) == "product")
    c_proc = len(closed) - c_prod
    n_guessed = sum(1 for c in closed if not wk2axis.get(c["wk"]))
    warn7 = " ⚠ swing back to product" if c_proc > c_prod else ""
    a(f"**Open {len(prod)} product / {len(proc)} process · closed 7d "
      f"{c_prod} product / {c_proc} process"
      + (f" ({n_guessed} classified by keyword)" if n_guessed else "")
      + f"{warn7}**")
    a("")
    for label, lane in (("PRODUCT", prod), ("PROCESS", proc)):
        a(f"### {label}")
        a("")
        a("| P | Work | Title | Premise health |")
        a("|---|---|---|---|")
        for held, prio, it, bd_id, _ in sorted(lane, key=lambda r: (r[0], r[1])):
            p = f"P{prio}" if prio != 9 else "—"
            a(f"| {p} | {it['wk']}{' / ' + bd_id if bd_id else ''} | "
              f"{it['title']} | {it['note'] or 'live'} |")
        top = sorted(lane, key=lambda r: (r[0], r[1]))
        if top:
            held, _, it, bd_id, _ = top[0]
            if held:
                a("")
                a(f"Move the needle: unblock `{it['wk']}` — re-premise onto "
                  f"the live successor: `scripts/truth premise {it['wk']} "
                  "<live-tr>` (successor named in the dead claim's last "
                  "verdict).")
            else:
                a("")
                a(f"Move the needle: `scripts/truth start {it['wk']}`"
                  + (f" · `bd update {bd_id} --claim`" if bd_id else "")
                  + f" — then say *“continue {it['title'][:40].rstrip()}…”*")
        a("")

    # ── 4 · WHERE'S THE MASS ─────────────────────────────────────
    a("## 4 · Where's the mass — concentration & won ground")
    a("")
    stages: dict[str, list[dict]] = {}
    for r in rmap:
        if r["bd_id"] in bd:  # open items only
            stages.setdefault(r["stage"], []).append(r)
    a("| L1 stage | open | weight |")
    a("|---|---|---|")
    for stage in sorted(stages, key=lambda s: (s == "0", int(s))):
        name = STAGE_NAMES.get(stage, f"Stage {stage}")
        n = len(stages[stage])
        a(f"| {stage} · {name} | {n} | {'█' * (2 * n)} |")
    a("")
    reg = read_csv(REPO / "docs/gap-register.csv")
    n_closed = sum(1 for g in reg if g["state"] == "closed")
    cells = " ".join(
        f"{g['gap']}{'✅' if g['state'] == 'closed' else '⚠(' + g['ref'] + ')'}"
        for g in reg)
    a(f"**Gap register (walking skeleton): {n_closed}/{len(reg)} closed** — "
      + cells)
    a("")
    a("Buildability's parked design gates (playbook G2–G5, G7) count inside "
      "the UC-2 bar in § 1, not here.")
    a("")
    a("### Roadmap by L1 stage (order = bd priority; arrows = bd deps)")
    a("")
    a("```mermaid")
    a("flowchart LR")
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
    a("### Roadmap by use case (goals from `docs/specs/use-cases.md`)")
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
            gid, label = "g_none", "process (axis column of roadmap-map.csv)"
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
        a(f"**⚠ unmapped open bd issues** (both views above lie by "
          f"omission until mapped): {', '.join(sorted(unmapped))} — "
          "move the needle: add a row with stage+uc+axis to "
          "`docs/roadmap-map.csv`.")
        a("")

    # ── 5 · IS THE MACHINE OK ────────────────────────────────────
    a("## 5 · Is the machine OK? — regime health")
    a("")
    a("| Signal | State |")
    a("|---|---|")
    a(f"| spec-health | {'🟢' if spec_ok else '🔴'} {spec_tail} |")
    a(f"| doc-health | {'🟢' if doc_ok else '🔴'} {doc_tail} |")
    a("| flagship baseline | guarded by `scripts/exercise-gate.sh` "
      "(runs at session-close) |")
    claims_line = " · ".join(f"{k} {v}" for k, v in sorted(by_status.items()))
    a(f"| claims | {claims_line} |")
    a(f"| verdict queue | {len(human_q)} human (§ 2) + "
      f"{len(verifier_q)} verifier |")
    r2 = run(["python3", "scripts/coverage-audit.py", "--counts"]).strip()
    if r2:
        pretty = " · ".join(p.replace("=", " ") for p in r2.split())
        a(f"| backward trace (R2) | {pretty} |")
    a("| R4 tests | `scripts/test-health.sh` — cited ids swept at close |")
    a(f"| R7 acceptance | {n_live}/{len(acc)} LIVE (§ 1) |")
    if man:
        a(f"| last exercise run | {man.get('started_utc', '?')} · "
          f"{man.get('blender_version', '?')} · repo "
          f"`{man.get('repo_sha', '')[:7]}` · hb5 "
          f"`{man.get('hb5_sha', '')[:7]}` |")
    a("")
    recent = closed_recently()
    a(f"**Closed in 14 days: {len(recent)}** — latest:")
    a("")
    for c in sorted(recent, key=lambda c: c["ts"], reverse=True)[:5]:
        title = c["title"][:80] + ("…" if len(c["title"]) > 80 else "")
        a(f"- {c['ts']} `{c['wk']}` {title}")
    a("")
    a("Full log: `git log --grep wk-` · every id above is one grep from "
      "its proof (dev-process §4).")
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
