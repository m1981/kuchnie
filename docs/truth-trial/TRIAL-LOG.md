# Truth-Ledger Efficacy Trial — Log

> Reader: anyone assessing whether the truth ledger *helps* (not merely runs) on a real repo | Enables: comparing ledger behavior against the hand-maintained freeze docs over time | Update-trigger: any trial event — staleness firing, verdict filed, hand-audit run, upstream defect found

**Trial question:** does the ledger keep migration-state facts honest better
than hand-maintained status docs (`docs/freeze/*`, the deleted `RESUME.md`)?

**Started:** 2026-07-08 · **Repo:** kuchnie monorepo · **Regime:** solo dev + agent sessions, trunk
**Roles:** developer + monitor = Claude agent sessions; human judgments (retraction, divergence triage, monthly audit) = Michal

---

## Protocol

1. **Day-0 baseline** — 10 claims (tr-ec698a92 … tr-8ed0a7ff) filed from
   *re-verified current reality*, not from the freeze docs. Statuses start
   `unverified`; independent verification via `truth dispatch` is the next step.
2. **During development** — agents check `truth list --live` before trusting,
   file claims after verifying (AGENTS.md snippet), and let hooks demote.
3. **Metrics collected here:**
   - staleness events: tripwire fired vs. did the fact actually change
     (tripwire *precision*);
   - facts that changed with NO tripwire firing (tripwire *recall* — found
     only by hand-audit);
   - claims filed per agent session (discovery compliance);
   - queue latency: days from demotion to human resolution.
4. **Monthly hand-audit** — sample claims, compare to ground truth by hand,
   count false-VERIFIED. Day-0 baseline for comparison: the freeze docs'
   error rate (see "Prior decay evidence" below).

## Prior decay evidence (why the trial exists)

`MIGRATION-STATUS-2026-07.md` — immutable snapshot, ~2 weeks old — already
contains **2 rows contradicted by code** at trial start:

| Doc said | Reality at day 0 |
|---|---|
| ADR-010 deletion trio "still present, deletion pending" | all three files deleted; machining.py imports `kuchnie_core` |
| ADR-009 pyproject "drifted (`kitchen-generator`, deps=[])" | fixed: `name = "home-builder-adapter"`, real deps |

That is the baseline error rate hand-maintained docs produce in ~2 weeks.
The ledger must beat it to earn its rent.

## Wiring decisions (2026-07-08)

- **husky owns `core.hooksPath`** (`"prepare": "husky"` re-seizes it on every
  `pnpm install`); truth hooks are chained from `.husky/pre-commit` /
  `post-commit` / `post-merge`, delegating to the same scripts as `.githooks/`.
  `.githooks/` kept as copier-managed reference — do not wire it directly.
- Gate verified **live** (not by reading): malformed staged ledger line →
  commit blocked (INV-B) through the actual `$hooksPath` chain.

## Upstream findings (defects in truth-ledger itself, found by this trial)

| ID | Severity | Finding | Status |
|---|---|---|---|
| TL-1 | High | `doctor` reported hooks OK while hooks were dead: it checks hook *file contents*, not the effective `core.hooksPath` chain (husky had seized it). Doctor's one job is "your repo is wired" and it failed open on day 0. Fix: doctor must resolve `git config core.hooksPath` and trace what actually executes. | reported here; not yet fixed upstream |
| TL-2 | Low | `check-truth.sh` on macOS/BSD: `head -n 0` is illegal when the committed ledger is empty; outcome accidentally correct (cmp empty-vs-empty). Guard `OLD_N -gt 0`. First macOS datapoint (paper claims Linux-only reproduction). | reported here; not yet fixed upstream |

## Event log

| Date | Event |
|---|---|
| 2026-07-08 | Hooks wired via husky; gate live-verified; doctor 7/7 OK. TL-1, TL-2 found. |
| 2026-07-08 | Day-0 baseline filed: 10 claims (C1–C10), actor `claude-fable-dev`. 2 freeze-doc rows found already decayed. |
