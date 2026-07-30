# Spec: Screens — kitchen-erp interaction spec

> Reader: whoever implements or reviews a kitchen-erp screen (Canvas,
> comparison board, purchasing, project record, admin) | Enables: judging
> a screen's state/error/NFR coverage without re-deriving it from
> `use-cases.md`'s prose scenarios | Update-trigger: a screen ships/changes
> state, an error/empty state is discovered, or an NFR is set/renegotiated

Serves: UC-1 (Canvas, comparison board), UC-4 (purchasing), UC-6 (project
record). UC-2's BOM/pricing correctness underlies the comparison board's
data layer but UC-2 itself has no screen — it is the production-pack
pipeline, not a UI.

## Intent

`docs/specs/use-cases.md` dresses UC-1/UC-2/UC-4/UC-6 as user-goal
scenarios — actor, preconditions, main success scenario, extensions. It
does not describe the screens themselves: entry/exit state, what a user
sees on a validation failure, or the latency a screen must hit to stay
usable at a client's table. That's this spec's job — the two are meant to
be read together, this one narrower and screen-shaped.

**Scope**: every kitchen-erp screen with real interaction (Canvas,
comparison board, purchasing, project record, admin material form).
**Non-goals**: visual design (color/layout) — not this project's
concern per prior gap analysis; the use-case-level main scenario/
extensions (owned by `use-cases.md`, referenced not restated); hb5's UI
(external, out of repo, ADR-009).

### Screen inventory

| Screen | Entry state | Core actions | Error / empty states | Exit |
|---|---|---|---|---|
| **Canvas** (threshold 1, UC-1 steps 1-4) | Project open, canvas blank or partially filled | Add module (type + rough W×H×D); remove module; view live od-do widelek priced twice (tier standard/komfort) | Module type has no price-book entry → line flagged unpriced, widelek marked incomplete, never silently omitted (UC-1 ext 2a, `wk-224f3712`). Prices older than TTL → range renders with visible ages and widens rather than faking precision (UC-1 ext 3a, `tr-4afef6fb` badge; widening itself `wk-224f3712`). **Empty canvas (no modules added yet)** → OPEN, no state defined. | Client agrees to range; widelek stored on project spine as first calibration datapoint (`tr-e51ef4fd`); advances toward threshold 2 |
| **Comparison board** (threshold 2, UC-1 steps 5-7, `wk-593a317b`) | Post-pomiar design decomposed from hb5 | 2-3 variants side by side across decor/drawer-system/hinge/worktop axes (`tr-6692cbe7`); tweak an axis → re-derive from one decomposition (`tr-ff8a5110`, worktop `tr-17905dae`); owner-only cost-without-labor view toggle (`wk-59b943b1`) vs. client-facing totals-only | Budget below "od" → walk substitution axes live until it fits (UC-1 ext 1a). Unpriced line surfaces (shared UC-2 ext 8a). **Recompute failure / partial pricing mid-tweak** → OPEN, no state defined. **Client sees materials-vs-labor split accidentally** → must be structurally impossible, not just policy (`wk-59b943b1`); no UI enforcement described yet. | Client's YES locks the finalist variant and triggers UC-4; the ACCEPT that locks price waits for the recorded offer (`tr-c87a68f9`) |
| **Purchasing** (UC-4, `wk-593a317b`) | Variant selected from comparison board | Send package (rozrys+DXF, one email, out-of-system); record offer (bare total OR itemized, `tr-c87a68f9`); ACCEPT; generate per-dealer hardware CSVs | Decor unavailable in needed thickness / no matching edge-band → substitution registry, back to board (UC-4 ext 2a). Unknown/unmapped supplier SKU → line flagged, never silently passed through (ext 2b). Offer exceeds estimate beyond tolerance → back to board or explicit margin call, never silent absorption (ext 4a). Change-order after ACCEPT → explicit redo-cost boundary shown (ext 5a). **ACCEPT button's enabled/disabled state before an offer is recorded** → state machine exists in the domain (`tr-c87a68f9`); whether the button itself reflects that state, or can be clicked and fail server-side, is OPEN. | Deliveries arrive, stock updates, stage advances 5→6 (`tr-e51ef4fd` `transition_stage`) |
| **Project record** (UC-6, `wk-02a62298` — closed) | Create or open a project | View/edit customer, status, dates; artifact references thread stages 1-11 (`tr-e51ef4fd`) | Never specified — UC-6 itself is still undressed per `use-cases.md`'s own inventory. **What this screen shows for a project with no artifacts yet, or a broken artifact reference** → OPEN. | Archived at handover (UC-10) |
| **Admin — material mirror** | Mirror row priced at 0.0 (new catalog variant, not yet priced locally) | Set `price_per_unit` on a mirror row (`kitchen-erp/docs/specs/material-mirror.md`) | **Invalid price entry, or editing a field the mirror doesn't own (identity fields are catalog-owned, not ERP-owned)** → OPEN, no validation behavior described. | Row priced, available to BOM/cost flow |

### Interaction NFRs

| Screen | Constraint | Status |
|---|---|---|
| Canvas | Runs live at the client's table on an iPad (UC-1 threshold 1) — implies an offline-tolerance and responsive-layout requirement | **OPEN** — no latency budget, offline behavior, or responsive/mobile spec exists; `catalog`'s `builder-gui.md` explicitly parked "Responsive/mobile" as out of scope and it was never revisited for this screen either |
| Comparison board | Axis tweaks must recompute "in minutes" per the design intent behind `tr-6692cbe7` | **OPEN** — no numeric budget; "minutes" is prose, not a fit criterion |
| Purchasing | Local iteration should be "minutes, not a 1-3 day service round-trip" (UC-4 stakeholder interest) | **OPEN** — same gap, prose not a number |
| All screens | Accessibility (keyboard nav, screen reader) | **OPEN** — not addressed anywhere in the repo for any UI surface |

None of these are contradicted by anything shipped — they're simply requirements nobody has stated as a testable number yet. Until they are, "is this screen fast enough" has no fit criterion to check against.

### Test strategy

No visual-regression or browser-level test convention exists for any kitchen-erp screen today (the harness discipline in `docs/e2e-exercise-convention.md` covers geometry goldens, not UI). The error/empty states marked OPEN above are exactly the states most likely to ship untested, per the same pattern `catalog/docs/specs/builder-gui.md` fell into (Playwright tests listed, never written). Recommendation, not yet committed: a per-screen state-transition test (manual checklist first, Playwright later) that specifically exercises every row in the Error/empty column above — the happy path is already exercised implicitly by use; the error paths are not.

## Decisions

- `docs/adr/011-*.md` — kitchen-erp owns
  ops artifacts (canvas, comparison board, purchasing, project record all
  fall inside this role).

## Ground truths

- `tr-6692cbe7` — kitchen-erp Variants hold parameter overrides and
  re-derive rozrys/CNC/BOM from one decomposition (comparison board's
  data layer).
- `tr-c87a68f9` — Offers record against variants; ACCEPT is refused
  without a recorded offer (purchasing screen's state machine).
- `tr-4afef6fb` — the ERP quote header renders an estimate-grade marker
  with per-line price age (Canvas + comparison board's freshness badge).
- `tr-e51ef4fd` — kitchen-erp's Project model carries stage, customer
  contact, lifecycle dates, and ArtifactRef (project record screen).
- `tr-17905dae` — kitchen_bom includes a worktop position from
  WorktopSegment per-lm (comparison board pricing correctness).
- `tr-ff8a5110` — BOM quantity folds consolidated per ADR-015, single
  decomposition feeds every downstream artifact (comparison board's
  re-derivation guarantee).
- `tr-b93c22bf` — kitchen-erp consumes `kuchnie_core` as domain hub
  (every screen's pricing/BOM numbers trace to one source).

## Work

- `wk-224f3712` — rough-quote canvas (Canvas screen, UC-1 progress 1).
- `wk-59b943b1` — labor pricing per module type + owner-only split view
  (comparison board's cost-without-labor toggle).
- `wk-593a317b` — purchasing artifacts incl. edge-band identity (G11) and
  hardware BOM completeness (G13) (comparison board's remaining steps +
  the entire purchasing screen).

## Acceptance

Pre-written `done --claim` texts, scoped to evidence commands:

- "the Canvas screen flags a module line with no price-book entry as
  unpriced rather than omitting it, and renders the od-do widelek with
  a SZACUNEK badge showing per-line price age, covered by a test
  exercising both a priced and an unpriced module" (`wk-224f3712`)
- "the comparison board's owner-only cost-without-labor view is gated
  behind a role/permission check the client-facing view cannot reach,
  covered by a test asserting the client-facing endpoint/component never
  returns the labor-split fields" (`wk-59b943b1`)
- "the purchasing screen's ACCEPT control is disabled (not merely
  advisory) until an offer is recorded against the variant, covered by a
  test driving the UI state machine through record-offer → ACCEPT and
  asserting ACCEPT is unreachable before that step" (`wk-593a317b`)
- "the purchasing screen surfaces an unknown/unmapped supplier SKU as a
  flagged line rather than passing it through silently, covered by a
  test with a fixture containing one unmapped SKU" (`wk-593a317b`)

The four OPEN items with no citation above (empty Canvas state, board
recompute-failure state, project-record broken-artifact state, admin
mirror validation) have no work item yet — they surfaced while drafting
this spec, not from prior planning. Filing `wk-`/Beads twins for them is
a decision for whoever picks this spec up next, not assumed here.
