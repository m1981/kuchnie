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
| TL-3 | High | **Dispatch prompt integrity is transport-dependent.** An output-compression proxy (sqz) in the agent harness silently dropped rule 3 (VERDICT RULES — including "never soften a diverge into an agree") from `truth dispatch` output in **all 10** verifier sessions. G11 scripts what the verifier receives, but nothing guarantees it *arrives* intact. Fix idea: dispatch prints a sha256 of the fixed prompt; verifier protocol step 0 = verify it against `prompts/truth-verifier.md`. | found by verifiers themselves; not yet fixed upstream |
| TL-4 | Medium | `truth verdict <id> --recheck` is not a dry-run: it silently **files an auto-`agree` verdict** ("recheck: output hash matches recorded evidence") before the verifier's interpretation step. Every protocol-obedient verifier therefore double-files; a verifier diverging at step 2 would leave contradictory verdicts; a verifier that stopped after step 1 would appear to have completed verification. Nothing in the prompt documents the write. Fix: recheck reports without filing (or files only diverge/cannot_verify). Found independently by 5 of 10 verifiers. | reported here; not yet fixed upstream |
| TL-5 | Low | Verdict/claim records carry `session: "s-unknown"` — the CLI has no session identity source in this environment, weakening the provenance envelope. | reported here |

## Event log

| Date | Event |
|---|---|
| 2026-07-08 | Hooks wired via husky; gate live-verified; doctor 7/7 OK. TL-1, TL-2 found. |
| 2026-07-08 | Day-0 baseline filed: 10 claims (C1–C10), actor `claude-fable-dev`. 2 freeze-doc rows found already decayed. |
| 2026-07-08 | Baseline committed (1bd4558) through the live gate; post-commit scan fired, 0 stale. |
| 2026-07-08 | **Verification round 1**: 10 fresh isolated agent sessions (actors `claude-verifier-1..10`), dispatch-only context. Result: **10/10 agree → all claims `live`**. Every verifier went beyond hash recheck and closed the evidence→text interpretation gap (blind-spot sweeps for absence claims, ADR cross-reads, SQLite magic-byte check, addon manifest inspection). One letter-vs-spirit note recorded in tr-8962a692's basis (bpy host-provided, not declared). |
| 2026-07-08 | Concurrency stress (incidental): 10 parallel same-machine verifier sessions, 20 appends — 30/30 records validate, no corruption. First empirical datapoint for the `O_APPEND` assumption. |
| 2026-07-08 | **Calibration caveat on round 1 unanimity**: all verifiers judged without VERDICT RULES (dropped in transit, TL-3), i.e. without the anti-sycophancy instruction. Their independent evidence work argues the agreements are sound, but round 2 must run with verified-intact prompts. |
