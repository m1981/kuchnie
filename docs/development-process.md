# Development process — how gold survives sessions

> Reader: anyone (human or agent) starting or ending a work session in this
> repo | Enables: knowing where every kind of knowledge must land, what
> "ready" and "done" mean mechanically, and which gate refuses what |
> Update-trigger: a gate script changes, or a knowledge kind gains/loses
> its home

**Principle: chat is a scratchpad; only artifacts survive.** Every piece of
gold (fact, decision, finding, golden, open work) lands in exactly ONE
durable home, addressed by a greppable id, guarded by a mechanical check
that notices when it dies. Two homes fork; zero homes vanish at context
compaction; no gate means silent rot.

The ledger mechanics behind everything below (fold, claim lifecycle,
premise gating, union-merge, the immune system) are illustrated in
**`docs/truth-ledger-machinery.md`** — this page does not duplicate them,
it tells you which lever to pull when.

## 1. One home per kind of gold

| Kind | Home | Id | Kept alive by |
|---|---|---|---|
| Fact about code/world | truth claim (+ evidence cmd) | `tr-` | evidence re-run; commit-time invalidate-scan (machinery §2) |
| Work item | truth issue + bd twin | `wk-` / `kuchnie-x` | `truth ready` premise gate (machinery §3–4) |
| Decision | ADR — immutable, superseding only | `ADR-NNN` | governance hook |
| Scope | L1 + feature specs, ledger-wired | spec file | `spec-health.sh` |
| Designer intent | exercise golden — immutable per run | `exercises/<n>/golden/` | claim-watched paths; `exercise-gate.sh` |
| Finding | GAP-REPORT + filed claim | G/E/P/B → `tr-` | exercise reruns |
| Fixed behavior | pinned test in owning suite | test cites the id | every suite run |
| Convention | `docs/*-convention.md` | file | doc-health + implementing tools |
| Capability status | `features-current-state.md`, `pattern-conformance.md` | file | update-trigger on wk close |
| **Priority / next order** | **bd priority + deps; ordered Work list in the owning spec** | — | `bd ready` ordering |

Filing rule: if you cannot say which row a piece of gold belongs to, you
have not finished thinking about it. **Priorities are data, never handoff
prose** — "do X next" is expressed as `bd update --priority` / `bd dep add`,
so `truth ready` / `bd ready` IS the plan after any compaction.

## 2. Session lifecycle (a session is a sprint)

**Open** — recover context mechanically, never from memory:

```bash
bd prime                      # tracker context (hook runs it automatically)
scripts/truth ready           # the plan: READY / HELD with dead premises named
bash scripts/spec-health.sh   # do any specs stand on dead facts?
scripts/truth queue           # what needs re-verification first
```

**Work loop** — per item (Definition of Done, all six or it isn't done):

1. `truth start wk-…` + claim the bd twin (Definition of Ready: premises
   live, acceptance claim pre-written in the owning spec).
2. Implement; every fixed behavior gets a **pinned test** citing the id.
3. Suites + gates green.
4. **Commit** (message carries the wk/tr ids — `git log --grep wk-` is the
   history query).
5. `truth done wk-… --claim "<the new fact>"` — close and fact-file
   atomically (machinery §3); evidence commands **count, never point**
   (`grep -c`, no line numbers — they diverge mechanically).
6. Independent `truth verdict <tr-…> agree --basis "<fresh re-check>"`,
   and re-affirm any claims your paths staled.

**Close** — one command, refusal not reminder:

```bash
bash scripts/session-close.sh
```

FAILs (exit 1) on survival holes: dirty tree, claimed truth items,
in-progress bd twins, spec/doc gate failures, flagship-exercise
regression. WARNs on triage debt (unverified claims, queue size). A
session that ends red has left gold in flight — finish, `--release`, or
commit-with-id before walking away.

### 2a. Multi-agent sessions — supervision doctrine

Promoted 2026-07-16 after two supervised groups confirmed every
candidate (evidence:
[multi-agent-supervision-retro-2026-07-16.md](reviews/multi-agent-supervision-retro-2026-07-16.md);
Group 2: both worktrees arrived 22 commits stale and the check below
caught both, one agent stalled and resumed from its milestone commit,
and the end-of-session verifier caught the filer's own basis error).

1. **Task shapes by value/risk:** fan out read-only investigations and
   small fenced main-tree tasks freely; implementations run in
   worktrees, at most one per component at a time (Group 2's pair was
   safe because kuchnie-core and kitchen-erp are disjoint).
2. **Step-0 merge-base check is mandatory:** an implementation agent's
   first act is verifying its worktree tip matches main's; on mismatch
   it stops and reports. Distrust any baseline statement from an agent
   whose base was stale. Auto-created worktrees are not exempt — both of
   Group 2's arrived stale; when in doubt the agent cuts its own fresh
   worktree off main.
3. **Commit per milestone:** stalls are routine, resumable via message;
   a lost handoff is recoverable from commits, lost uncommitted work is
   not.
4. **Division of labor is hard-fenced:** worktree agents never run
   bd/dashboard/truth/session-close; the supervising reviewer merges,
   re-verifies on main (merge-time invalidate-scan outranks worktree
   re-affirmations), files acceptance claims, and closes twins.
5. **Every claims-heavy session ends with a verifier dispatch:**
   filer≠verifier makes it structural — a claim filed and path-staled in
   the same session cannot be repaired by its own filer, and independent
   re-runs catch the filer's basis errors.
6. **Supervisor watches proportion** (product vs process hours) — no
   gate does; expect roughly half the supervision effort to be ledger
   bookkeeping and say so to anyone adopting the regime.

## 3. Gates inventory — what refuses what

| Gate | Runs | Refuses |
|---|---|---|
| `check-truth` pre-commit + invalidate-scan | every commit | broken ledger schema; silently-stale facts (paths → stale) |
| Governance hook | every commit | edits to accepted ADRs; doc-health violations |
| `spec-health.sh` | on demand + close | specs citing dead/diverged facts |
| `doc-health.sh` | commit + close | dead component names, broken links |
| Component suites (core/cam/erp/adapter) | per change | regression on pinned behavior |
| **`exercise-gate.sh`** | per decomposer/extraction change + close | flagship outputs differing from the committed baseline — a formula drift fails at commit time, not at the saw. Intended change? Commit the new baseline WITH the code and a claim |
| **`session-close.sh`** | end of session | knowledge still in flight (see §2); project checks plug in as `scripts/session-gates.d/*.sh` (template-aligned — upstreamed to truth-ledger) |
| **`dashboard.py --check`** (session-gates.d/30) | end of session | a stale `STATUS.md` — the dashboard is GENERATED from ledger/bd/gates (`scripts/dashboard.py`, sources `docs/capability-map.csv` + `docs/roadmap-map.csv`) and its freshness is gated so it cannot lie |
| **`test-health.sh`** (session-gates.d/40) | on demand + close | a test citing a tr-/wk- id that does not exist in the ledger; WARNs on retracted/diverged pins and on recent closes with no citing test (R4 — `docs/specs/conformance-join.md`) |
| **`session-gates.d/50-new-dark.sh`** | end of session | nothing yet — WARN-only: a module absent from the committed `docs/code-inventory.json` arriving DARK per `scripts/coverage-audit.py` (R2-lite; promotion to FAIL is Michał's call) |
| Ledger intake gates | at filing | quantifier/scope mismatch (ADR-007), unsafe evidence cmds (ADR-009), duplicates, backdating (machinery §7) |

Full-fat exercise reruns (Blender leg + inspection) stay on-demand after
adapter/hb5 changes: `exercises/harness/runner.py <scenario> --strict`.

**Dashboard** (`STATUS.md`, repo root): five moment-views — health strip,
ready lane (premise health × bd priority), roadmap by L1 stage with bd
dependency arrows (plus a by-use-case rendering of the same items, from
the `uc` column of `docs/roadmap-map.csv`), capability board (cells cite
tr- ids; non-live ids are flagged in-page), and a 14-day delta log.
Hand-maintained inputs are only the two CSVs; everything else is derived.

## 4. Traceability — the "undoubtable" chain

Every status is one grep from its proof; no link is prose:

```
golden → diff → gap (G/E/P) → tr-claim (evidence cmd) → wk → commit (id
in message) → pinned test (id in comment) → spec citation → gate
```

To audit any statement in any doc: take its id, `scripts/truth list |
grep <id>` for status, run its evidence command for the fact, `git log
--grep <id>` for the code. If a statement has no id, treat it as courtesy
text — the id is authoritative (spec convention).

## 5. Writing for humans AND models (they converge)

1. **Ids in prose, always** — "fixed the back formula" dies at compaction;
   "tr-8dfe366d closed G6" is recoverable forever.
2. **Schemas over paragraphs** — CSV/frontmatter/JSON parse
   deterministically and diff cleanly.
3. **Counting evidence** — `grep -c`/`-l`, never `-n`; line numbers
   diverge without the fact changing (ADR-012's mechanical-diverge scar).
4. **Quantifier discipline** — "only/all/no/each" claims need
   `--scope-ok` or a narrower sentence (ADR-007 refuses otherwise).
5. **One fact per claim, one concern per file, absolute dates** — small
   addressable units survive summarization; "yesterday" does not.
6. **Docs state reader/enables/update-trigger** in the header — staleness
   becomes a rule, not a vibe.
7. **Immutable things stay immutable** — accepted ADRs (supersede),
   goldens (new run, new directory), ledger history (append-only fold,
   machinery §1/§6).
8. **Watch sources, never generated artifacts** — `--paths` on a claim
   must name the files that cause a fact to change, not the outputs a
   script writes from them (STATUS.md, code-inventory.json); a claim that
   watches an output restales every time the generator runs. Likewise,
   never embed a volatile foreign-tracker field (a bd priority, status,
   or assignment) inside claim text — it drifts out from under the claim
   without touching any watched path (wk-ea10d199).

## 6. Agile mapping, for the avoidance of ceremony

Planning = the open ritual · Backlog = `truth ready` (premise-filtered) ·
Sprint = session · Review = golden diffs + gate output, not opinion ·
Retro = the GAP-REPORT "natural-flow observations" section · Burndown =
`truth stats` / `bd stats`. No meeting produces gold; only artifacts do.
