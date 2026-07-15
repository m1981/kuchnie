# Spec: Use cases — actors, goals, and the five dressed flows

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
fork); no full dress beyond the five flows whose extensions carry real
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
| UC-1 | Salesperson/Designer | Quote a kitchen (estimate-grade; ERP canvas + estimate lines for unsupported types) | **full — to write** | 2–5 | — |
| UC-2 | Production engineer | Produce the production pack | **full — below** | 3–8 | wk-81a47ab8 |
| UC-3 | Salesperson + Client | Run a first-visit decor session ending in a selection set | **full — to write** | 1 | wk-6716e9c8, wk-c67ffaa1 |
| UC-4 | Purchaser | Order materials for a job (board + hardware orders to the single supplier) | **full — write BEFORE the purchasing epic** | 5, 9 | wk-593a317b, wk-39ed9155, wk-4c37f4ee |
| UC-5 | Assembler | Assemble a cabinet from its per-cabinet sheet | casual (defer until stage-8 milestone) | 8 | — |
| UC-6 | all hats | Open a project and thread its artifacts through stages 1→11 | **full — to write** | 1–11 | wk-02a62298 |
| UC-7 | Purchaser | Import a supplier price file into the ERP material mirror | casual | 5 | wk-39ed9155 |
| UC-8 | AI agent / Purchaser | Refresh the material mirror from the catalog | casual — already spec'd (`kitchen-erp/docs/specs/material-mirror.md`) | 5 | — |
| UC-9 | Salesperson | Maintain the decor catalog (images, families, pairings) | casual | 1 | wk-6716e9c8, wk-c67ffaa1 |
| UC-10 | all hats | Archive a handover (project record references kitchen JSON + cut lists + decor set) | casual | 11 | — |
| UC-11 | Designer | Design an L-kitchen (heights → zones → corner → widths), governed by `docs/l-kitchen-design-playbook.md`, executed mostly in hb5 | casual | 2–4 | — |

Worktop BOM position (wk-4c37f4ee) is a subfunction of UC-1/UC-4, not a
goal. The catalog **configurator** flow (sessions/steps/templates in
`catalog/`) is an implementation candidate for UC-3 — adopting or atticing
it is decided when UC-3 gets dressed, not before.

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
   envelopes (W×H×D, toe kick, per wall) — tr-3bb325f8.
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
   **⚠ wk-89a668a2** (checks scattered across five modules, no gate
   runner: tr-00421995).
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
  scrap-severity — **⚠ depends on step 5**.
- 6a. Wood-grain front would need rotation for yield → forbidden; grain
  pins orientation — supported (tr-15d48651).
- 8a. Material has no local price → BOM flags unpriced lines instead of
  silently under-quoting — **⚠ rows exist at 0.0 but nothing flags them**.

Reading: steps 2, 3, 5 and extensions 2a/5a/8a are the open backlog. This
use case adds no work — it gives the existing work its requirement, and
places the buildability verdict ON the main success scenario of the
business's central flow.

## Ground truths

- tr-3bb325f8 — extraction reads bbox + toe kick (UC-2 step 1 works).
- tr-ef90fea5 — extraction reads the persisted hb5 drawer stack (cabinet
  type, drawer count, opening heights bottom-up); UC-2 step 2 supported.
  Supersedes the earlier reading-gap fact (diverged by design 2026-07-16
  when wk-81a47ab8's r2 slice landed; see that claim's diverge verdict in
  the ledger for the lineage).
- tr-00421995 — validation gates scattered, no orchestrator (UC-2 step 5
  missing).
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
- wk-89a668a2 — buildability verdict gate runner (UC-2 step 5, filed by
  this dressing). Covers TWO rule families: mechanical (panel dims,
  overlaps — validator.py) and design-legality (playbook Phase-8 gate
  G1–G7). First slice shipped: G1/G6/width rules in validate_rows
  (wk-bae72832); G2/G3/G4/G5/G7 parked pending model support
  (L-adjacency, appliance positions, cutout positions)
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
