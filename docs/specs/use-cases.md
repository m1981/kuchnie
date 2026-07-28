# Spec: Use cases — actors, goals, and the dressed flows

> Reader: anyone (human or agent) deciding where a feature belongs or what
> a piece of work is FOR | Enables: routing every feature discussion
> through "which use case does this serve?" and reading the open backlog as
> unfinished steps of named user goals | Update-trigger: an actor's goal
> changes, a use case changes dress level, or a dressed scenario's step
> gains/loses system support

This is the system's Cockburn **sea level** — the layer between the L1
stage map (kite: `process-coverage.md` owns stages, boundaries, in/out) and
feature specs (fish). Use cases span stages; they do not duplicate them.
Born from `docs/reviews/requirements-assessment-2026-07-14.md`.

## Intent

Give every work item an upward trace to a user goal, and give failure-path
requirements a home *before* they are discovered at the saw (the review's
finding: G8 was an extension clause nobody wrote). **Non-goals:** no
separate SRS document (the union of this file + L1 + feature-spec
Acceptance sections + capability-map IS the requirements specification);
no bd epic hierarchy (the feature spec plays the epic role — two homes
fork); no full dress beyond the flows whose extensions carry real
money/scrap risk.

## Decisions

- ADR-009 — hb5 owns layout/placement; the adapter is the ACL (shapes
  UC-2 step 1–2 and keeps hb5 an external actor).
- ADR-011 — kitchen-erp owns ops artifacts (UC-1, UC-4, UC-6 live there).
- ADR-001 — panel is the atom (every dressed scenario's outputs are flat
  panel lists a carpenter can audit).

## Actors (Michał's hats) and their goals

| Actor | Goal the system serves | L1 stages |
|---|---|---|
| **Salesperson** | leave a client visit with a decor selection set, chosen on a realistic preview | 1 |
| **Surveyor** | capture a measurement visit (photos, appliance sheets, dimensions) attached to a project | 2 |
| **Designer** | turn a measured room into a cabinet layout production can consume without re-typing | 3–4 |
| **Production engineer** | turn a frozen design into a trusted cut list, drilling list and DXF pack | 4, 6–8 |
| **Purchaser** | order exactly the boards, edging and hardware a job needs, at current prices | 5, 9 |
| **Assembler** | assemble each cabinet from a per-cabinet sheet without consulting the designer-self | 8 (later milestone) |

Secondary actors: **Client** (approves decors and quote), **cutting &
edging service** (its interest is the pinned stage-6 rozrys contract),
**board/hardware supplier** (receives orders, emits price files), **AI
agent** (maintenance actor; served by the ledger/gates).

## Use-case inventory

Dress rule: full Cockburn template only where extensions carry scrap- or
margin-risk. Everything else stays casual (one line) until it earns more.

| UC | Actor | Goal | Dress | Stages | Work today |
|---|---|---|---|---|---|
| UC-1 | Salesperson/Designer | Quote a kitchen (two thresholds: iPad canvas widelek → hb5 comparison board; estimate-grade always) | **full — below** (dressed 2026-07-18) | 2–5 | wk-224f3712, wk-59b943b1, wk-593a317b |
| UC-2 | Production engineer | Produce the production pack | **full — below** | 3–8 | wk-81a47ab8 |
| UC-3 | Salesperson + Client | Run a first-visit decor session ending in a selection set | **full — to write** | 1 | wk-6716e9c8, wk-c67ffaa1 |
| UC-4 | Purchaser | Order materials for a job (cutting-service package + hardware CSVs to dealers) | **full — below** (dressed 2026-07-16) | 5, 9 | wk-593a317b, wk-39ed9155, wk-4c37f4ee |
| UC-5 | Assembler | Assemble a cabinet from its per-cabinet sheet | casual (defer until stage-8 milestone) | 8 | — |
| UC-6 | all hats | Open a project and thread its artifacts through stages 1→11 | **full — to write** | 1–11 | wk-02a62298 |
| UC-7 | Purchaser | Import a supplier price file into the ERP material mirror | casual | 5 | wk-39ed9155 |
| UC-8 | AI agent / Purchaser | Refresh the material mirror from the catalog | casual — already spec'd (`kitchen-erp/docs/specs/material-mirror.md`) | 5 | — |
| UC-9 | Salesperson | Maintain the decor catalog (images, families, pairings) | casual | 1 | wk-6716e9c8, wk-c67ffaa1 |
| UC-10 | all hats | Archive a handover (project record references kitchen JSON + cut lists + decor set) | casual | 11 | — |
| UC-11 | Designer | Design an L-kitchen (heights → zones → corner → widths), governed by `docs/l-kitchen-design-playbook.md`, executed mostly in hb5 | **full — below** (dressed 2026-07-28) | 2–4 | — |
| UC-12 | Surveyor | Capture a measurement visit into a structured survey pack on the project spine | **full — below** (dressed 2026-07-28) | 2 | — |

Worktop BOM position (wk-4c37f4ee) is a subfunction of UC-1/UC-4, not a
goal. The catalog **configurator** flow (sessions/steps/templates in
`catalog/`) is an implementation candidate for UC-3 — adopting or atticing
it is decided when UC-3 gets dressed, not before.

## UC-1 — Quote a kitchen (fully dressed, interview 2026-07-18)

**Primary actor:** Michał as Salesperson (threshold 1) / Designer
(threshold 2)
**Scope:** kitchen-erp (canvas, variants, prices) + kuchnie-core
(decomposition) + hb5 (threshold 2 only). The client is an external
actor sitting at the same table. **Level:** sea (user goal)
**Goal in context:** the client needs a number they can decide on, at two
moments with two precisions: a same-evening RANGE at the first visit
(iPad with ERP only — hb5 happens later at the office), then per-variant
prices at the comparison board after the design exists. Both are
ESTIMATE-grade; only a cutting service's recorded offer is offer-grade
(purchasing-variants.md, permanent display rule).

**Stakeholders & interests:**
- Michał/owner — never quotes below cost unknowingly: a private
  cost-without-labor view shows the margin room at the table
  (wk-59b943b1); the widelek from the first visit converges on reality
  via the calibration loop
- Client — a decidable number the same evening; the range they said yes
  to is the range the design lands in; trade-offs happen WITH them at
  the comparison board
- Cutting service — uninvolved at this stage; their eventual offer is
  the calibration ground truth
- Assembler-Michał — the quote's labor component reflects real per-type
  effort (drawer > corner > door), not a flat multiplier

**Preconditions:** material prices present (any age — age visible,
tr-4afef6fb freshness machinery); flat-rate estimate-line price book per
module type for non-decomposable modules (⚠ wk-224f3712); per-type labor
weights (⚠ wk-59b943b1). Threshold 2 additionally: pomiar done, kitchen
laid out in hb5.
**Minimal guarantees:** every displayed figure carries its grade —
SZACUNEK badge with per-line price ages (tr-4afef6fb); an estimate is
never displayed as an offer; unpriced (0.0) lines are flagged, never
silently under-quoted (shared with UC-2 ext 8a — ⚠ open); the client
never sees the materials-vs-labor split (owner-only view, wk-59b943b1).
**Success guarantees:** the client leaves threshold 1 with an od–do
range and threshold 2 with per-variant prices; the widelek and the
chosen variant's estimate are stored on the project spine as
calibration datapoints; ACCEPT hands over to UC-4 with the variant
locked (tr-c87a68f9).
**Trigger:** first client conversation with dimensions on the table
(threshold 1); design ready in hb5 (threshold 2).

**Main success scenario** (⚠ = the id IS the requirement's tracker):

1. At the client's table Michał lays out modules on the ERP canvas
   (iPad): types + rough W×H×D from the client's tape — canvas exists
   (KitchenState rows), sizing survives today.
2. Non-decomposable modules (cargo, karuzela, sink, oven) enter as
   estimate lines from the flat-rate per-type price book, TTL-aged like
   every price — **⚠ wk-224f3712**.
3. System prices the canvas twice — tier "standard" (melamine,
   Tandembox, standard hinges) and tier "komfort" (upper decors,
   LEGRABOX, soft-close) — widens by the pre-pomiar uncertainty margin,
   and shows the od–do widelek with the SZACUNEK badge — **⚠
   wk-224f3712** (badge machinery live: tr-4afef6fb).
4. Client agrees to the range; the widelek is stored on the project
   spine as the first calibration datapoint — **⚠ wk-224f3712**
   (spine: tr-e51ef4fd).
5. After pomiar Michał designs in hb5; decomposition prices the real
   kitchen through the single BOM fold — supported (tr-ff8a5110,
   tr-b485d74c); worktop enters per-lm with priced cutouts — supported
   (tr-17905dae).
6. System presents the comparison board: 2–3 variants of the same
   kitchen side by side (decor/drawer-system/hinge/worktop axes), each
   re-derived and re-priced from one decomposition — variants live
   (tr-6692cbe7); the board itself **⚠ wk-593a317b**; labor per module
   type, owner-only split view — **⚠ wk-59b943b1**.
7. Client picks a variant (possibly after axis tweaks recomputed in
   minutes). The client's YES at the board chooses the finalist and
   triggers UC-4 (send the package, get the binding offer); the recorded
   ACCEPT that locks the variant happens once that offer confirms the
   price — the state machine refuses an ACCEPT with no recorded offer by
   design (tr-c87a68f9), so an estimate can never be locked in as if it
   were the price.

**Extensions** (where the margin lives):

- 1a. Client's budget is below "od" → walk down the substitution axes
  live at the board (cheaper decor tier, Tandembox, shorter run) until
  it fits — re-derivation is minutes (tr-6692cbe7); margin concession is
  Michał's call, informed by the private cost-without-labor view (⚠
  wk-59b943b1).
- 2a. A module type has no entry in the estimate-line price book → line
  flagged unpriced, widelek marked incomplete — never silently omitted
  (⚠ wk-224f3712).
- 3a. Prices older than TTL → the range renders estimate-grade with
  ages visible and widens instead of faking precision — badge live
  (tr-4afef6fb), widening ⚠ wk-224f3712.
- 5a. Post-pomiar design lands outside the quoted widelek → the client
  hears it from Michał with the board open, not from a surprise final
  number — process rule, no mechanism owed.
- 7a. Client walks away → project stays at the quote stage with the
  widelek archived; no artifacts were promised (stage spine
  tr-e51ef4fd).

Reading: threshold 2 stands almost entirely on shipped machinery
(variants, single BOM fold, worktop per-lm, freshness badge,
offer/ACCEPT); the genuinely new work is threshold 1 (wk-224f3712) and
the labor model (wk-59b943b1). The comparison board (wk-593a317b) is the
quoting surface. Handoff: the client's board-YES is UC-4's trigger; the
locking ACCEPT is UC-4 step 5, after the binding offer — one decision,
two recorded moments.

## UC-2 — Produce the production pack (fully dressed)

**Primary actor:** Michał as Production engineer
**Scope:** kuchnie system (adapter + kuchnie-core + kitchen-cam +
kitchen-erp). hb5 and the cutting service are external actors.
**Level:** sea (user goal)
**Goal in context:** the client accepted the design; Michał needs the
complete, mutually consistent artifact set — cut list, drilling data,
priced BOM — to order cutting/edging and CNC drilling without hand-deriving
a single dimension.

**Stakeholders & interests:**
- Michał/owner — no scrap (severity order: wrong drill row > missing BOM
  line, per `e2e-exercise-convention.md` §16); margin not eroded by
  understated hardware
- Cutting service — parsable rozrys per the stage-6 column contract,
  Usłojenie respected
- Client — the kitchen designed is the kitchen delivered
- Supplier — order lines resolvable to producer SKUs

**Preconditions:** kitchen laid out in hb5 (.blend on disk); decors
selected and present in the catalog; ConstructionMethod configured.
**Minimal guarantees:** no partial artifact can be mistaken for a complete
one; every hand re-entry / extraction loss is gap-logged; nothing is
emitted for cabinet types that cannot be decomposed.
**Success guarantees:** rozrys CSV, CNC ops + per-panel DXF, and priced BOM
all derived from ONE decomposition of ONE Kitchen object; validation
passed.
**Trigger:** design freeze (client acceptance).

**Main success scenario** (⚠ = step the system cannot do yet — the id IS
the requirement's tracker):

1. Michał points the system at the .blend; the adapter extracts cabinet
   envelopes (W×H×D, toe kick, per wall) — tr-239065a8.
2. System identifies each cabinet's type and configuration from the scene
   — supported: extraction reads the persisted drawer stack (type, count,
   opening heights bottom-up per G8) — tr-ef90fea5.
3. Michał reviews/completes parameters; loaders normalize a declared
   top-down drawer stack and REJECT an ambiguous unequal one — supported
   (wk-844f5a9f closed G8 at loader/schema; hand-built instances follow
   the documented bottom-up contract).
4. System decomposes each cabinet to panels (dims, edging, grain,
   machining ops) — flagship types full (tr-591aa208, tr-3ef7b607,
   tr-8dfe366d); door/wall types partial (`capability-map.csv`).
5. System validates the kitchen and issues a single buildability verdict —
   supported: `kuchnie_core.buildability.evaluate_buildability` runs the
   formerly scattered checks (premise tr-00421995) as ordered gates
   M1–M5 + FIT/WSTD/G1/G6, parked gates reported as explicit skips —
   tr-65aa5969.
6. System emits rozrys CSV per the stage-6 contract, grain included —
   tr-15d48651; one contract decision open (Długość orientation for lying
   panels).
7. System emits the CNC drilling list and per-panel DXF (layers by drill
   type) — supported for flagship types.
8. System computes the priced BOM: board m² by panel role, edging lm,
   hardware from the rules engine — tr-b485d74c; **⚠** hardware
   understated (G13) and edging not orderable by thickness (G11) —
   wk-593a317b.
9. Michał uploads the rozrys to the e-rozkrój service and sends DXF to the
   CNC shop — out of system by design (stage-6 boundary).

**Extensions:**
- 2a. Scene contains a type with no decomposer (sink/cargo/oven/karuzela)
  → carried as an ERP estimate line, excluded from rozrys/CNC with an
  explicit marker — **⚠ exclusion not enforced today**.
- 3a. Drawer stack violates NL/height fit → per-cabinet `validate()`
  rejects — supported.
- 4a. Scene decor cannot be resolved to a catalog variant → hand
  assignment, gap-logged — current reality; no resolver wired.
- 5a. Buildability verdict FAIL → no artifacts emitted; findings listed by
  scrap-severity — supported: the verdict orders findings blocking-first
  (tr-65aa5969) and the core emission doorways (cutlist, edging,
  kitchen_bom) refuse a FAILED verdict via require_buildable /
  BuildabilityError (tr-409f4aab, wk-cb6a17c8).
- 6a. Wood-grain front would need rotation for yield → forbidden; grain
  pins orientation — supported (tr-15d48651).
- 8a. Material has no local price → BOM flags unpriced lines instead of
  silently under-quoting — **⚠ rows exist at 0.0 but nothing flags them**.

Reading: extensions 2a/5a/8a and step 8's G11/G13 qualifiers
(wk-593a317b) are the open backlog; the main scenario's steps all run. This
use case adds no work — it gives the existing work its requirement, and
places the buildability verdict ON the main success scenario of the
business's central flow.

## UC-4 — Order materials for a job (fully dressed)

**Primary actor:** Michał as Purchaser
**Scope:** kuchnie system (kitchen-erp + catalog). The cutting service and
hardware dealers are external actors. **Level:** sea (user goal)
**Goal in context:** the client accepted a variant within budget; Michał
must place the orders that get the job built — ONE package to the cutting
service (they supply board, cut, edge and drill from his files: single
hop, no raw-board purchase exists) and hardware top-up CSVs to dealers —
without hand-deriving a single line. Design record for the mechanisms:
`purchasing-variants.md`.

**Stakeholders & interests:**
- Michał/owner — margin survives the offer round-trip; every local
  iteration is minutes, not a 1–3 day service round-trip
- Client — the accepted budget is the delivered price; trade-offs happen
  WITH them at the comparison board, not behind their back
- Cutting service — parsable e-rozrys per the stage-6 contract, decor and
  edging codes verbatim from producer catalogs, DXF in the same package
- Hardware dealers — clean CSV keyed by producer (Blum) codes
- Assembler-Michał — hardware arrives complete (G13 understatement is a
  stakeholder wound, not a rounding error)

**Preconditions:** an ACCEPTED variant exists (UC-1/UC-2 loop); its
rozrys CSV + DXF derive from ONE decomposition; catalog resolves the
variant's decor/edging codes; price book present (any age, age visible).
**Minimal guarantees:** no order leaves with stale-price estimates
unmarked; every sent/received document is archived verbatim and attached
to the project spine (ArtifactRef); estimates and binding offers are
never displayed as the same kind of number.
**Success guarantees:** service package sent and its binding offer
recorded against the estimate (calibration datapoint stored); ACCEPT
recorded and the variant locked; per-dealer hardware CSVs emitted with
net quantities (required − stock + buffer); project stage advances.
**Trigger:** client accepts a variant (budget agreed).

**Main success scenario** (⚠ = the id IS the requirement's tracker):

1. Michał selects the accepted variant; system re-derives rozrys + DXF
   from the frozen decomposition — **⚠ wk-593a317b** (variant model:
   `purchasing-variants.md`).
2. System validates every material line against the catalog: decor
   variant exists in the needed thickness, matching edge-band exists —
   catalog data supports it (tr-0dda200b); the check itself **⚠
   wk-593a317b**.
3. Michał sends the package (rozrys CSV + DXF, one email) — out of
   system by design; system records Sent + artifacts on the spine —
   supported (tr-e51ef4fd ArtifactRef).
4. Offer arrives; Michał records it (bare total OR itemized — the schema
   tolerates both, no granularity lock-in); system shows offer vs
   estimate and stores the calibration datapoint — **⚠ wk-593a317b**.
5. Michał ACCEPTS; the variant locks; later edits become explicit
   change-orders — **⚠ wk-593a317b** (state machine on the spine).
6. System computes hardware needs per dealer (required from the variant's
   accessories − on-hand + buffer) and emits per-dealer CSVs keyed by
   producer codes — **⚠ wk-593a317b**; quantities must include the G13
   families (konfirmaty, nóżki, klipsy, zszywki), not runners alone.
7. Deliveries arrive; stock updated; stage advances 5→6 — supported
   (tr-e51ef4fd transition_stage).

**Extensions** (where the money lives):

- 1a. Prices in the book older than their TTL → estimate rendered
  stale-grade with age shown; Michał refreshes the price book first
  (wk-39ed9155) or proceeds eyes-open.
- 2a. **Decor unavailable in needed thickness, or no matching edge-band
  (G11's class)** → substitution registry proposes catalog-verified
  alternatives → back to the variant comparison board; edging is ordered
  BY thickness and decor (0.8 carcass vs 2.0 front), never as one
  generic line — **⚠ wk-593a317b**.
- 2b. **Unknown/unmapped supplier SKU** (a code the catalog cannot
  resolve) → line flagged, never silently passed through; resolution is
  a catalog fix or an explicit manual-code marker in Uwagi.
- 4a. Offer exceeds estimate beyond tolerance → back to the comparison
  board with the client (decor/hardware-tier substitutions) or conscious
  margin decision; never silent absorption.
- 4b. Offer arrives as one bare total → calibration degrades gracefully
  to total-per-job learning; itemized offers enrich it — neither format
  is required (no supplier lock-in).
- 5a. Client changes mind AFTER accept → formal change-order; the system
  shows the point-of-no-return boundary and the redo cost explicitly.
- 6a. Hardware partially in stock or dealer backorders → split order,
  delivery risk flagged against the install date.
- 6b. Hardware tier substitution (e.g. LEGRABOX→Tandembox) after
  drilling artifacts exist → system re-derives CNC/DXF from the new
  decomposition — a substitution is geometry, not a price line
  (`purchasing-variants.md` cascade rule).

## UC-11 — Design an L-kitchen (fully dressed, dressed 2026-07-28)

**Primary actor:** Michał as Designer
**Scope:** hb5 (external layout editor per ADR-009) + kuchnie system
(home-builder-adapter, kuchnie-core, kitchen-erp, krono-compositor).
Governed phase-for-phase by `docs/l-kitchen-design-playbook.md`; gap map
per `docs/reviews/domain-pm-review-2026-07-28.md` §A. **Level:** sea
(user goal)
**Goal in context:** turn a measured room into an approved L-kitchen
design by the playbook's discipline — heights → zones → corner → widths,
never cabinets-first — so the Phase-8 gate passes on real data and
production handoff (UC-2) starts from a validated layout, with two
designs made months apart coming out consistent.

**Stakeholders & interests:**
- Michał/owner — a gate failure is caught at design time, not at the
  saw; the playbook holds even under time pressure
- Client — the kitchen fits their body (elbow-derived heights), habits
  (handedness, zones) and budget bracket
- Assembler-Michał — corner fillers and clearances decided on paper mean
  no on-site improvisation
- Production engineer (UC-2) — receives a frozen design whose
  buildability verdict is already green

**Preconditions:** survey pack on the project spine (UC-12); decors
browsable in the catalog; hb5 available for placement (ADR-009).
**Minimal guarantees:** a design that failed the Phase-8 gate never
reaches production artifacts — emission refuses a FAILED verdict
(tr-409f4aab); a phase without its input artifact does not start
(playbook Phase-0 rule).
**Success guarantees:** approved design whose cabinet list either
decomposes or is explicitly excluded; rozrys, CNC/DXF and priced BOM all
derive from ONE decomposition (handoff to UC-2).
**Trigger:** survey pack complete; project enters stage 3.

**Main success scenario** (one step per playbook phase; ⚠ = phase the
system cannot carry yet, per the review's §A gap map):

1. Phase 0 — Michał confirms the survey pack (wall dims + diagonals,
   media points, appliance model sheets, user height/handedness, budget
   bracket) sits on the project spine — attachment machinery supported
   (tr-e51ef4fd ArtifactRef); the structured pack and its 2→3 gate are
   UC-12's goal.
2. Phase 1 — Michał fixes the working heights (worktop = elbow −
   100..150 mm, wall-unit line, tall line) as a project-level height
   parameter set — **⚠** no such entity; ConstructionMethod owns the
   carcass math but nothing stores per-project lines for layout or
   G1-across-legs.
3. Phase 2 — Michał draws the zone plan (supplies > cleaning > prep >
   cooking; sink leg vs hob leg, fridge column at the open end) with
   appliance positions — **⚠** no zone, appliance or position model
   exists in the live domain.
4. Phase 3 — Michał decides the corner strategy (blind + filler /
   diagonal / dead, mechanism, filler widths on BOTH runs) before any
   widths — **⚠** no corner decision artifact; the corner-blind
   production side is solved (tr-591aa208) but unreachable from a scene.
5. Phase 4 — Michał composes the base runs in hb5: appliances first,
   standard widths, one filler per run at the wall end, two legs sharing
   the corner — **⚠** the extracted Kitchen is a flat Row list with no
   positions or leg adjacency; the adapter collapses a scene into one
   Row.
6. Phase 5 — Michał adds wall and tall units (mirror the base line,
   hood on the duct route, one continuous top line) — **⚠** no
   tall/column type exists; the wall-unit decomposer is partial.
7. Phase 6 — Michał specifies the worktop (two segments + corner joint,
   cutout positions with ≥50 mm web) and annotates services — **⚠**
   WorktopSegment prices per-lm with cutout count (tr-17905dae) but
   carries no cutout positions and no joint.
8. Phase 7 — Michał fixes one decor set, 3 mm reveals and a global
   handle system, previewing decor swaps with the client — **⚠** krono
   renders a linear strip only (no L preset) and 90/148 decor images are
   missing; the catalog data itself is live (tr-0dda200b).
9. Phase 8 — Michał runs the validation gate G1–G7 — **⚠** the
   ordered-gate verdict runs and emission refuses FAIL (tr-65aa5969,
   tr-409f4aab), but design gates G2/G3/G4/G5/G7 sit SKIPPED for want of
   the layout model; only G1/G6 and the mechanical checks fire.
10. Phase 9 — Michał hands the approved design to production: decompose
    → rozrys CSV with grain, CNC drilling + per-panel DXF, priced BOM,
    all from one decomposition — supported for covered types
    (tr-15d48651, tr-b485d74c, tr-591aa208, tr-3ef7b607, tr-8dfe366d).

**Extensions:**

- 9a. G1 fails — heights inconsistent across legs → back to Phase 1
  (step 2) — the worktop-line check is encoded in validate_rows and
  fires inside the verdict (tr-65aa5969); the across-legs form waits on
  the height parameter set (step 2).
- 9b. G2 fails — corner fillers missing on either run → back to Phase 3
  (step 4) — **⚠** parked SKIP: the model carries no L-run adjacency.
- 9c. G3 fails — door/drawer collision at the corner or room door →
  back to Phase 3 or 4 (steps 4–5) — **⚠** parked SKIP.
- 9d. G4 fails — appliance cutouts do not match the actual model sheets
  → back to Phase 0 inputs (step 1; the sheets live in UC-12's pack) —
  **⚠** parked SKIP: no appliance model.
- 9e. G5 fails — work triangle or landings illegal after width changes
  → back to Phase 2 (step 3) — **⚠** parked SKIP: no positions.
- 9f. G6 fails — plinth line broken or top line discontinuous → back to
  Phase 4 or 5 (steps 5–6) — encoded in validate_rows, fires inside the
  verdict (tr-65aa5969).
- 9g. G7 fails — worktop joint lands on a cutout, or gas/hood distances
  illegal → back to Phase 6 (step 7) — **⚠** parked SKIP: no cutout
  positions.

Reading: the back half stands (step 10 and the gate machinery of step
9); the front half — phases 1–7 — has no data model, which is the one
hole the review's roadmap closes (L-layout model first: runs + corner +
positions unpark the design gates). Roadmap rows carrying uc=UC-11 in
`docs/roadmap-map.csv` are this use case's open backlog; they gain wk-
twins when each piece of work starts.

## UC-12 — Capture a measurement visit into a survey pack (fully dressed, dressed 2026-07-28)

**Primary actor:** Michał as Surveyor
**Scope:** kitchen-erp (project spine, ArtifactRef). The room and the
client are external. **Level:** sea (user goal)
**Goal in context:** one visit to the room yields the structured survey
pack the playbook's Phase 0 demands — wall dims + diagonals, media
points, appliance model sheets, user height/handedness, budget bracket —
attached to the project spine, and the 2→3 stage transition cannot
proceed without it, so design (UC-11) never starts on missing inputs.

**Stakeholders & interests:**
- Michał/owner — no second visit to re-measure; no redesign born from a
  missing input (playbook Phase-0 rule: missing input = redesign later)
- Client — measured once; budget bracket captured explicitly, not
  remembered
- Designer-Michał (UC-11) — starts Phase 1 from a complete pack, not
  from memory
- Production engineer (UC-2) — appliance cutouts trace to actual model
  sheets (gate G4's ground truth)

**Preconditions:** project exists on the spine at stage 2_pomiar
(tr-e51ef4fd).
**Minimal guarantees:** an incomplete pack is never silently promoted —
the 2→3 transition refuses and names the missing items; every captured
artifact is archived verbatim on the spine.
**Success guarantees:** complete survey pack attached to the spine;
stage advances 2→3; UC-11's Phase-0 precondition is satisfied.
**Trigger:** measurement visit, scheduled after the first-visit decor
session (UC-3) and quote range (UC-1).

**Main success scenario** (⚠ = the system cannot do it yet — review §A
Phase 0):

1. Michał opens the project at stage 2_pomiar and attaches the raw
   visit artifacts (photos, notes) to the spine — supported
   (tr-e51ef4fd ArtifactRef).
2. Michał records wall dims + diagonals and media points (water, drain,
   gas, duct, sockets) as a structured wall sheet — **⚠** no survey
   artifact kinds exist; today an attachment is a bare file.
3. Michał captures the appliance model sheets (model + cutout dims per
   appliance) — **⚠** no named artifact kind; gate G4 has nothing to
   check against.
4. Michał records user height/handedness (the elbow-formula input) and
   the budget bracket — **⚠** no home for them on the spine.
5. System evaluates pack completeness against the required-kind
   checklist and shows what is still missing — **⚠** no checklist
   exists.
6. Michał advances the project 2→3; the transition verifies the pack —
   transition machinery supported (tr-e51ef4fd transition_stage), but
   the pack-completeness gate is **⚠** open.

**Extensions:**

- 6a. Pack incomplete at the 2→3 attempt → transition refuses and lists
  the named missing items; the stage stays 2_pomiar — **⚠** the refusal
  rule is the survey-pack spec's core assertion (review §D spec 1).

## Ground truths

- tr-239065a8 — extraction reads bbox + toe kick (UC-2 step 1 works).
- tr-ef90fea5 — extraction reads the persisted hb5 drawer stack (cabinet
  type, drawer count, opening heights bottom-up); UC-2 step 2 supported.
  Supersedes the earlier reading-gap fact (diverged by design 2026-07-16
  when wk-81a47ab8's r2 slice landed; see that claim's diverge verdict in
  the ledger for the lineage).
- tr-00421995 — validation gates scattered, no orchestrator (the premise
  wk-89a668a2 stood on; the orchestrator now delegates to those same
  scattered homes — tr-65aa5969).
- tr-65aa5969 — evaluate_buildability issues the single ordered-gate
  verdict (UC-2 step 5 supported; ext 5a emission gating shipped as
  tr-409f4aab, structured findings underneath as tr-cb1dec8a).
- tr-15d48651 — Panel.grain wired, Usłojenie emitted (UC-2 step 6 / ext 6a).
- tr-8dfe366d — back formula groove-seated, matches carpenter reference
  (UC-2 step 4 trustworthy for flagship types).
- tr-591aa208 — corner-blind decomposer with filler + blind front (UC-2
  step 4 coverage).
- tr-3ef7b607 — confirmat + HDF-groove ops emitted (UC-2 step 7 input).
- tr-b485d74c — ERP BOM quantities come from core decompose() (UC-2 step 8).

## Work

- wk-81a47ab8 — extraction fidelity r2 (UC-2 step 2)
- wk-02a62298 — Project/Order spine (UC-6)
- wk-593a317b — purchasing artifacts incl. G11/G13 (UC-2 step 8 / UC-4)
- wk-39ed9155 — supplier price-file import (UC-7 / UC-4)
- wk-4c37f4ee — worktop per-lm BOM (UC-1/UC-4 subfunction)
- wk-6716e9c8, wk-c67ffaa1 — decor images + family audit (UC-3/UC-9)
- wk-89a668a2 — CLOSED 2026-07-16 (tr-65aa5969): buildability verdict
  gate runner shipped, both rule families delegated (mechanical M1–M5,
  design-legality FIT/WSTD/G1/G6 via validate_rows); G2/G3/G4/G5/G7
  stay parked pending model support (L-adjacency, appliance positions,
  cutout positions) and surface as explicit SKIPPED gates
- wk-cb6a17c8 — CLOSED 2026-07-18 (tr-409f4aab): emission doorways gated
  on the verdict, no override flag; wk-acc8e094 closed with it
  (tr-cb1dec8a — structured findings replace the string protocol)
- wk-33342f9e — this spec (migration step 1)

## Acceptance

Pre-written `done --claim` texts for the remaining migration steps:

- "docs/specs/use-cases.md defines six actor-hats with goals, marks five
  use cases for full dress with the rest casual, and dresses UC-2 with
  every NOT-YET step citing an open tracker id; spec-health passes with the
  file's cited ids live or open" (this step)
- "UC-4 (order materials) is fully dressed in docs/specs/use-cases.md
  before wk-593a317b implementation starts, with extensions covering
  unknown supplier SKUs and edge-band orderability (G11)" (step 3)
- "roadmap-map.csv carries a uc column consumed by scripts/dashboard.py as
  a by-goal roadmap view, and spec-health warns on feature specs lacking a
  Serves: UC- line" (step 3)
