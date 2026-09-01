# FROZEN — this ledger is an archive as of 2026-09-01

> Reader: anyone about to write to `.truth/claims.jsonl` or wondering
> why a truth-ledger gate is silent | Enables: knowing the freeze is a
> ruling, not rot, and where the successor lives | Update-trigger: an
> operator ruling reversing or amending the freeze

Status: **FROZEN by operator ruling of 2026-09-01** (disarm package
D2–D7, executed the same day). The ledger is append-only history and
stays exactly that: **nothing may write to it on any commit, merge, or
CI path from this date.** Reading it is encouraged — it anchors
eighteen complaint records in the successor system.

## Why — the record, not an opinion

- Of 630 stalings resolved by a later verdict, the fact had not
  changed in 555 — a false:true ratio above 3:1 (`tr-e1225a78`,
  refined by `tr-68b8b752`; the 555/630 ratio survives the whole
  correction chain).
- Fourteen spec-coverage sentinels produced 43 alarms and 57 verdict
  actions with zero caught defects (2026-07-26 → 2026-08-13).
- The engine demonstrated itself during its own disarm: the deliberate
  commit of a 19-day-old stray reaffirm verdict (8cb0ce4) triggered
  invalidate-scan, which immediately marked 3 more claims stale by TTL
  — pure upkeep, zero information.
- Last human-era record: 2026-08-13. The installation was dormant 19
  days while the weekly CI canary stayed green — ceremony outliving
  its operators.

## What was disarmed (ruling D2, D5)

- `.beads/hooks/post-commit` — replaced with a no-op (was:
  invalidate-scan + auto-reaffirm on every commit).
- `.beads/hooks/post-merge` — truth lines commented out; the beads
  integration block is untouched and beads remains fully armed.
- `.github/workflows/truth-scan.yml` (pushed bot commits to main) and
  `truth-canary.yml` (weekly, green as late as 2026-08-31) — moved to
  `.github/workflows-disabled/`.
- `package.json` `prepare` (husky re-arm path) — renamed to
  `prepare-DISARMED-2026-09-01`; a `pnpm install` no longer re-points
  `core.hooksPath`.

## What stays armed (ruling D3, D4)

- The real test gates: `pre-push-checks.sh` (five pytest suites, the
  e2e golden, doc-health, spec-health, session gates) — engineering,
  not ceremony.
- `check-truth.sh` + `check-governance.sh` on commit — check-truth
  no-ops unless the ledger is staged, which makes it the free
  integrity guard OF this freeze: any future write to the archive
  still has to pass INV-A/INV-B.
- `truth-gate.yml` in CI — same role, remote side.
- The `scripts/truth` CLI and `truthlib/` vendor copy stay runnable:
  spec-health folds the frozen ledger read-only and stays green.

## Accepted consequences (ruling D7)

- Eleven claims carrying `rg` evidence (`wk-8908bacc`) are permanently
  unverifiable — accepted as frozen history.
- The seven live sentinels (`tr-fcca2d96`, `tr-40a5beb5`,
  `tr-12b7419f`, `tr-e602c0b0`, `tr-7970e982`, `tr-a075eed2`,
  `tr-284395a9`) remain `live` in the fold but are inert: nothing
  fires them. They are not retracted, because retraction is a write.
- 126 live / 79 retracted claims stand as they were on 2026-08-13.

## Voided by ruling, tombstone pending (ruling D6)

`wk-11a1a151` ("adopt template v0.9.36") is the re-arm path and is
**void by operator ruling of 2026-09-01**. The ledger's own G12 gate
correctly refused an agent-issued cancellation during the disarm
("issue cancellation is a human tombstone decision") — a genuine catch
by this machinery, on its last day of writes, recorded here with
respect. The formal tombstone awaits the operator running, in their
own terminal:

    python3 scripts/truth done wk-11a1a151 --cancel --basis "re-arm path voided by the 2026-09-01 freeze ruling (.truth/FROZEN.md)"

That command is the single sanctioned exception to this freeze.

## Where the live value went

- Open domain defects (real work, not ceremony) remain in the work
  kernel — headline items: `wk-075803aa` (degenerate TURNS mapping in
  the validator), `wk-4fc28a19` (wrong surface-structure codes on ten
  postformed decors, amplified ×36 by U-U seeding), `wk-bca0a74b`
  (36 variants offered by the configurator, hidden by the worktops
  endpoint), `wk-c67ffaa1` (color_family misassignments),
  `wk-6716e9c8` (90 of 148 decors without miniatures), plus the domain
  epics and the UC-3 chain.
- The five `*.sc.txt` manifests, `docs/specs/sc-slugs.txt`, and both
  contract-symbol manifests are live inputs for the successor's
  `tl2 mirror` (truth-ledger2, `~/PycharmProjects/truth-ledger2`).
- The question bank (`docs/question-bank.md`) and its
  incident-to-gap ritual are untouched — they are this repository's
  own register and predate the freeze's reasons.

## Successor

truth-ledger2 (`~/PycharmProjects/truth-ledger2`) — an engine whose
constitution was priced largely by this ledger's measured history.
This repository is designated installation #2 there; installation
follows the freeze as a separate ruling.
