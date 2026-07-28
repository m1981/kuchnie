# ADR-035: Playbook operating decisions — pro-tool boundary, golden-before-DXF, G5 as human checklist, decomposer coverage cut

> Reader: anyone scoping rendering, CAM output, gate G5 or a new decomposer
> against `docs/l-kitchen-design-playbook.md` | Enables: refusing the four
> classic scope creeps (built rendering, ungoldened DXF, mechanized triangle
> math, mechanism decomposers) with an operator decision to point at |
> Update-trigger: the operator revisits one of the four decisions below (each
> is independently revisitable; supersede per decision, not wholesale)

## Status

Accepted 2026-07-29 (operator decisions, review §F risks 2/3/5/4 of
`docs/reviews/domain-pm-review-2026-07-28.md`). Sibling of ADR-034 (the
build decision); this one records the refusals and cuts around it. The
pro-tool boundary line lands in `docs/specs/process-coverage.md`
non-goals; the CAM refusal rule binds the Stage 3 type-completion work.

## Decision 1 — pro-tool boundary ratified (review §F.2)

**Context.** Every failed bespoke-shop trajectory in the PM review runs
through trying to out-render or out-edit the commercial tools. Krono's
2.5D decor swap already beats PRO100's re-render loop for the one job it
has (decor choice), and hb5/Blender covers presentation.

**Decision.** Photoreal client presentation stays in hb5/Blender renders
**permanently**. krono-compositor stays a 2.5D decor-choice surface. No
rendering pipeline is built in this repo. If Blender render turnaround
ever hurts sales, the answer is a commercial-seat purchase for
presentation, never a build.

**Consequence.** Ratified as a non-goal line in
`docs/specs/process-coverage.md` (citing this ADR), so future feature
discussions hit a written boundary instead of a fresh debate. Krono
investment stays pointed at the I/L/U presets and decor coverage.

## Decision 2 — no DXF leaves for a cabinet type without a committed golden (review §F.3)

**Context.** The scrap-severity doctrine: a wrong drill row costs more
than a missing BOM line. Today the flagship d60-legrabox has a committed
golden; the corner-blind type ships DXF with none. Trusting per-type CAM
output without a golden is exactly how a saw eats a board.

**Decision.** **Hard refusal rule for the CAM lane:** DXF emission for a
cabinet type is refused until that type has a committed golden exercise.
No golden, no DXF — the type stays at rozrys/BOM coverage until its
golden lands. This is a gate on the emission path, not a review-time
convention.

**Consequence.** Stage 3 type completion slows by one golden per type —
accepted: scrap risk outranks speed. The rule gives the capability map a
crisp per-type boundary (DXF column implies golden committed) and makes
"corner-blind ships DXF with no golden" a defect to close, not a state
to tolerate.

## Decision 3 — G5 (work triangle / landings) stays a human checklist (review §F.5)

**Context.** Mechanizing G5 fully needs room doors, walkways and traffic
paths — a slippery slope back toward the room editor ADR-009 forbids.
The playbook's triangle and landing numbers are design-practice values a
human can check on a plan sheet in a minute.

**Decision.** G5 is executed by a human on the generated plan sheet and
is **never mechanized**. The result is recorded per project as a TTL'd
attestation: an UNVERIFIED claim with an explicit `--ttl-days`, filed
when the checklist is walked, expiring so a stale walkthrough cannot
pass silently for a changed layout. The buildability verdict keeps
reporting G5 as a named non-mechanized gate (SKIP with reason pointing
here) rather than pretending coverage.

**Consequence.** The design-legality-gates spec (Stage 2) scopes G5 out
of automation from birth. What the layout model must still supply is the
**data** a plan sheet needs (positions, appliance markers) — that part
stays in scope per ADR-034.

## Decision 4 — decomposer coverage cut: build the tall column, the rest are estimate lines (review §F.4)

**Context.** The playbook mandates a fridge/oven column in nearly every
L-kitchen, so its absence is a real coverage hole. Mechanism cabinets
(cargo, karuzela) arrive as boxed SKUs whose margin does not repay a
decomposer; the sink cabinet is dominated by the cutout and plumbing,
not by panel geometry.

**Decision.** Build: **tall column** gets a decomposer (Stage 3).
Permanent estimate lines with enforced, explicitly-marked exclusion:
**sink cabinet, cargo, karuzela, oven housing** — the sink cabinet's
borderline status is resolved to the estimate side.

**Consequence.** UC-2 ext-2a exclusion enforcement covers the estimate
list with a marker (never a silent drop), so a full cabinet list always
partitions into decomposed + explicitly-excluded. Revisiting any line of
the cut (e.g. sink cabinet later earning a decomposer) supersedes this
decision alone, not the ADR.
