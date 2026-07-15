# Spec: Conformance join — Phase 1 of the two-ledger architecture

> Reader: any agent or human implementing or auditing the standards-shaped
> satellites (test-health, completeness view, backward trace, upstream
> drafts) | Enables: knowing what each Phase 1 increment must produce, in
> what order, and the exact done-claim sentence that closes it |
> Update-trigger: an increment ships (its Acceptance line becomes a tr-
> claim), an upstream draft is posted or rejected, or the concept doc gains
> a superseding revision

Serves: UC-2, UC-3, UC-4, UC-6 — the dressed flows whose acceptance
coverage the join measures and whose pinned tests it protects; the direct
beneficiary is the AI-agent maintenance actor (`docs/specs/use-cases.md`
§ Actors, secondary). L1 wiring: stage 0 (process/infra) in
`docs/roadmap-map.csv`; no saw-facing stage changes.

## Intent

Implement Phase 1 of the Two-Ledger Architecture — the migration step the
design doc defines as "no core changes" — as satellites around the
existing truth ledger: a test-citation gate (R4, ISO/IEC/IEEE 29119), an
acceptance-completeness view (proto-R1/R7, ISO/IEC/IEEE 29148 + ISO/IEC
25023), and a backward-trace slice (R2-lite, ISO/IEC/IEEE 24765), plus
draft (unposted) upstream filings for Phases 2–3. Design authority:
`docs/reviews/two-ledger-concept-2026-07-15.md` (tr-7e0b27d6) — this spec
does not re-derive the design, it schedules and gates its Phase 1 slice.

**Non-goals:** no `nd-` record kind, no `satisfies` edge, no `accept-cmd`,
no `truth baseline` verb, no `contradicts` edge (those are Phases 2–3 and
belong upstream — increment 4 drafts them, never posts them); no changes
to template-owned files (`scripts/truth`, `scripts/check-truth.sh`,
`scripts/truth-canary.sh`, `.truth/schema/*`); no DARK-module triage —
adopt/attic/delete is a product-owner verb, this spec only produces the
list; no new dependencies; no changes to decomposers, harness oracles, or
exercise goldens.

**Increments, strictly in order** (deps chained in the ledger):

| # | Work | Deliverable | Join rule |
|---|---|---|---|
| 0 | wk-382ddd32 | this spec | — (requirements analysis) |
| 1 | wk-0d7a80d2 | `scripts/test-health.sh` + `session-gates.d/40-test-health.sh` | R4 test coverage |
| 2 | wk-9d77de94 | `Completeness (R7)` section in `scripts/dashboard.py` | proto-R1/R7 completeness |
| 3 | wk-9fb28a32 | `scripts/code-inventory.py` + `scripts/coverage-audit.py` + `docs/code-inventory.json` + `session-gates.d/50-new-dark.sh` | R2 backward trace |
| 4 | wk-3894b44c | five draft issue bodies in `docs/reviews/upstream-drafts-2026-07/` | Phases 2–3 filings |

Mechanism notes fixed here so implementations cannot drift:

- **R4 sweep scope** — the four component test suites plus
  `exercises/harness/tests` and `scripts/tests` (the home of pinned tests
  for repo tooling, created by increment 1). FAIL only on a cited id that
  does not exist in the ledger; retracted/diverged citations WARN; the
  inverse check (recently closed wk- without a citing test) WARNs, never
  FAILs.
- **R7 matching** — an Acceptance item "matches" a claim by deterministic
  token overlap of the item's significant words against the claim text
  (no NLP, no model — the gate stays lexical, concept §II.9); grouping is
  by the UC ids the item's text mentions, spec-wide items grouped
  separately.
- **R2 verdicts** — TRACED needs at least two trace sources of which one
  is a test file; a single source is MENTIONED; zero is DARK. Trace
  sources: claim `evidence_paths`, spec mentions, the capability/roadmap
  CSVs, test files. "Leave it dark" is not an emittable state — the list
  goes to the product owner.
- **New-dark gate posture** — WARN-only until Michał promotes it to FAIL
  (concept §II.7 R2 "refuses when a *new* module arrives DARK" is the
  target posture, not the shipped one).

## Decisions

- `docs/reviews/two-ledger-concept-2026-07-15.md` — the design record this
  spec implements Phase 1 of (Part II; §II.11 migration path).
- Ledger ADR-007 (quantifier gate) and ADR-009 (evidence screen) — reused
  as-is by every claim this spec pre-writes; the separate accept-allow
  list is deliberately deferred to the upstream draft, not implemented
  locally.

## Ground truths

- tr-7e0b27d6 — the concept doc records the design (axes, R1–R7, nd-,
  two-oracle accept-cmd, baseline, migration path).
- tr-767c1632 — spec-health gate live: the satellite family (spec-health /
  doc-health) that test-health completes exists and passes.
- tr-a95ed226 — use-cases.md defines the actors and dressed UCs and
  carries the Acceptance section increment 2 parses (successor of the
  step-2 era claim that diverged by design when extraction r2 landed).
- tr-076ed1ea — the six component source trees and pyprojects sit where
  increment 3's inventory walker expects them.

## Work

- wk-382ddd32 (bd kuchnie-gfy) — increment 0, this spec.
- wk-0d7a80d2 (bd kuchnie-xdc) — increment 1, test-health satellite (R4).
- wk-9d77de94 (bd kuchnie-7ai) — increment 2, Completeness (R7) view.
- wk-9fb28a32 (bd kuchnie-31x) — increment 3, backward-trace slice (R2).
- wk-3894b44c (bd kuchnie-82w) — increment 4, upstream drafts (draft only).

## Acceptance

Pre-written `done --claim` texts, one per increment; evidence commands at
close must count, never point, and must watch sources, never generated
artifacts (STATUS.md and docs/code-inventory.json are outputs — watch
their generators).

- Increment 0 (wk-382ddd32): "docs/specs/conformance-join.md is the Phase 1
  umbrella spec of the two-ledger concept: three-question header, Serves:
  UC- lines, stage-0 roadmap wiring, mechanism notes fixing R4/R7/R2
  semantics, and an Acceptance section pre-writing the done-claim
  sentences for increments 1-4; spec-health reports 0 failures with this
  spec included"
- Increment 1 (wk-0d7a80d2): "scripts/test-health.sh sweeps the component,
  harness and scripts test directories for cited tr-/wk- ids, exits 1 on a
  cited id missing from the ledger, warns on retracted or diverged
  citations and on wk- items closed within 14 days lacking a citing test,
  prints cited/distinct/suites-covered totals, and runs at session close
  via scripts/session-gates.d/40-test-health.sh; at HEAD it reports 0
  failures and a pinned test demonstrates exit 1 on a fabricated citation
  in a fixture tree"
- Increment 2 (wk-9d77de94): "scripts/dashboard.py renders a Completeness
  (R7) section classifying the Acceptance items of docs/specs/use-cases.md
  as PRE-WRITTEN, FILED or LIVE by deterministic token-overlap match
  against ledger claim texts, grouped by the UC ids the items mention,
  with a live/total gauge; dashboard.py --check stays green and a pinned
  test covers the parser and the classifier"
- Increment 3 (wk-9fb28a32): "scripts/code-inventory.py emits a
  deterministic, sorted docs/code-inventory.json of modules with their
  classes and functions across the six component source trees;
  scripts/coverage-audit.py joins those modules against claim
  evidence_paths, spec mentions, the capability and roadmap CSVs and test
  files, printing per-module TRACED/MENTIONED/DARK verdicts whose three
  counts appear in the dashboard Health strip;
  scripts/session-gates.d/50-new-dark.sh warns without failing when a
  module absent from the committed inventory arrives DARK; pinned tests
  cover walker determinism and verdict logic"
- Increment 4 (wk-3894b44c): "docs/reviews/upstream-drafts-2026-07/ holds
  five upstream issue drafts citing the two-ledger concept doc by section
  — accept-cmd with the two-oracle shape and a separate accept allowlist,
  a truth baseline verb, a contradicts edge folding to DISPUTED, truth
  impact --inverse, and the nd- record kind with satisfies edge marked as
  a design RFC — written as drafts and not posted upstream"
