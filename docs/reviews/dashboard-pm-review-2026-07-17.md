# Review: STATUS dashboard from the PM chair (2026-07-17)

> Reader: Michał deciding what the dashboard must answer, or anyone
> implementing dashboard v2 | Enables: rebuilding STATUS.md around PM
> questions instead of code taxonomies without re-deriving this critique |
> Update-trigger: dashboard v2 ships (sections below become reality or are
> explicitly rejected)

Reviewed: `scripts/dashboard.py` (478 lines) + its generated `STATUS.md`
of 2026-07-16. Trigger: the owner reported being lost despite trusting
the ledger — "limited visibility" into how much work is ahead, where it
concentrates, and what is feature vs process.

## Verdict

An excellent MACHINE status page, a poor PM status page. It answers "is
the regime healthy" and "what may I start" well; it does not answer "how
much is ahead", "product or process?", or "what waits on the owner".

## What to keep unchanged

- Capability board — the best PM artifact in the repo (client-promise
  table with evidence-cited cells).
- Ready lane's truth×bd join and HELD-with-dead-fact-named semantics.
- Health strip concept and the generated/gated discipline (rule 8).

## The five failures

1. **Product and process mixed everywhere.** Ready lane ranks purchasing
   work and glossary hygiene as peers; the "no UC" bucket lumps real
   product debt (Blum runner geometry = UC-2 quality) with true infra.
   The retro assigned "watch proportion" to the supervisor because no
   gate does — the dashboard should be that gate.
2. **No denominators.** Only gauge is R7's n/3 — and `acceptance_items`
   reads ONLY use-cases.md, ignoring purchasing-variants.md's four
   pre-written items and every other spec. The dressed UC sections
   already carry supported/⚠ markers per step; nothing renders
   "UC-2: 8/9 steps, 3 extensions open".
3. **No owner lane.** "10 awaiting triage" hides that those are
   human-only retractions; undressed UCs (UC-1/3/6 — UC-3 blocks the
   configurator decision and the decor lane) appear nowhere. The
   bottleneck moved to the owner (retro finding 6); the dashboard does
   not show the owner's queue.
4. **Hand-maintained map lags.** 8 of ~20 open items unmapped in
   roadmap-map.csv → both swimlanes lie by omission; the render-time
   chore line ("add to the CSV") is the wrong enforcement point — demand
   mapping at filing.
5. **Trivia at equal weight.** Retracted-claim rows in R7, a 90-line
   closed-items wall, maintenance warnings inside the client-promise
   board.

## Design principle (answers the owner's taxonomy question)

**Taxonomies are for finding; dashboards are for deciding.** Do NOT give
L/G/M/R/UC/P one section each. Structure by two axes only — UC (the
feature axis: value is sold in use cases) and L1 stage (the pipeline
axis: where it lands for the carpenter). Demote the rest:

| Family | Where it lives in v2 |
|---|---|
| G1–G13 | compact Gap Register — 13 rows, mostly ✅ won ground; open ones cite wk- |
| M1–M5 + parked G2–G5/G7 | folded INTO UC-2's progress line (model debt) |
| R1–R7 | one line each inside Health (process instrumentation) |
| P0–P4 | sort order within lanes, never a section |
| wk-/bd-/tr- | metadata on every card, never a grouping |

## STATUS v2 — five sections = five PM questions

1. **CAN I SELL IT?** Capability board + UC progress bars
   ("UC-2 ████████░ 8/9 steps · ext 2a/5a/8a open") parsed from dressed
   spec markers; acceptance gauge swept over ALL `*/docs/specs/*.md`.
2. **WHAT'S BLOCKED ON ME?** Owner lane: pending human retractions
   (count + ready-to-paste command), undressed UCs with what they block,
   `bd human` flags.
3. **WHAT'S NEXT?** Ready lane split Product | Process, each P-sorted,
   with the proportion stated: "open 9/8 · closed-14d 6 product /
   9 process ⚠" — the single most valuable new number.
4. **WHERE'S THE MASS?** Open-item counts per L1 stage and per UC (the
   concentration map) + the Gap Register.
5. **IS THE MACHINE OK?** Health strip as today + R-rule lines; delta
   log becomes count + top 5.

## Mechanics (all incremental; R7 classifier and ready-join untouched)

- `docs/roadmap-map.csv` gains an `axis` column (product|process);
  unmapped-at-render becomes a WARN naming the filing gap.
- Marker parser over dressed UC sections (supported / ⚠ wk- / half
  supported) → per-UC step and extension counts.
- `acceptance_items` sweeps every spec's `## Acceptance`, not one file.
- Owner lane sources: `truth queue` (diverged = human retraction),
  use-cases.md inventory (dress-marked UCs without a dressed section),
  `bd human list`.
- Proportion: closed-in-14d joined against the axis column.

## Status

Review only — no implementation. Dashboard v2 is filed as a work item
when the owner picks it up; sections above are the acceptance skeleton.
