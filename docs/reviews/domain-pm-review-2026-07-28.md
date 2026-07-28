# Review: kuchnie vs the L-Kitchen Playbook, from the kitchen-design-software PM chair (2026-07-28)

> Reader: Michał deciding the feature set and roadmap toward
> `docs/l-kitchen-design-playbook.md`, or anyone writing the specs it names |
> Enables: knowing per playbook phase what exists, what to build, what to
> refuse, in which order, and how visibility rides the existing dashboard |
> Update-trigger: a stage below completes, a listed decision is taken, or a
> named spec ships (then its row here is history, not plan)

Perspective applied: 15 years of PRO100 / Polyboard / Winner Flex /
TopSolid'Wood / PaletteCAD product management, plus carcass manufacturing
(32mm system, Blum hardware, postformed worktops, CNC handoff). Commissioned
2026-07-28; full component inventory read (catalog, kuchnie-core,
kitchen-cam, kitchen-erp, krono-compositor-mvp, home-builder-adapter,
exercises), plus use-cases.md, STATUS.md, roadmap-map.csv, capability-map.csv,
spec-convention.md, development-process.md, question-bank.md.

**The one-sentence verdict up front:** this repo has a production back half
that most small shops would envy — a Polyboard-grade parametric decomposer, a
TopSolid-lite CAM handoff, and an ERP purchasing loop with better
price-freshness discipline than Winner Flex — but the playbook's front half
(Phases 0–5: survey, heights, zones, corner, run composition) has **no data
model at all**. The live domain `Kitchen` is a flat list of `Row`s of
`CabinetInstance`s with no positions, no corner, no adjacency, no appliances;
the adapter even collapses a whole hb5 scene into one `Row`
(`home-builder-adapter/src/extract.py`, `cabinets_to_kitchen`: "wall
dimensions are inferred from the cabinets"). That single missing model is why
buildability gates G2/G3/G4/G5/G7 sit permanently SKIPPED. Everything below
flows from closing that one hole cheaply, without building a CAD editor.

---

## A. Gap map — playbook phases vs repo capabilities

**The three cross-cutting answers first:**

1. **Room/wall/layout/zone model:** none in the live domain.
   `kuchnie_core.model.Kitchen/Row` is flat (`Row` = label + wall W/H +
   cabinet list; no position, no corner link). Two ghosts exist: (a)
   `kuchnie_core.validator.check_run_continuity` validates a **geometry
   manifest** (runs with `start/end_position_mm`, `direction`, `turn`,
   L/I-shape) that *nothing in the repo produces*; (b)
   `home-builder-adapter/src/kitchen/__pycache__/` holds **bytecode-only**
   `Wall`/`Run`/`Layout`/`LayoutEngine` classes whose source lives in the
   external, retired plugin-era project (pre-ADR-009; its name is on the
   forbidden list — deliberately not written here). The manifest contract
   is the resurrection point — the validator half already exists and is
   tested.
2. **Elevation/plan drawing output:** none. Closest artifacts: kitchen-erp's
   on-screen "CAD elevation" module boxes (Reflex CSS, not exportable) and
   kitchen-cam's per-panel machining DXF. No dimensioned wall elevation or
   plan sheet exists anywhere.
3. **Client-facing quote document:** none. The widelek range, SZACUNEK badge
   and comparison board are on-screen only; no PDF/print library in the repo.

Per phase:

| Phase | Repo today | Missing | What the pro tools teach |
|---|---|---|---|
| **0 Discovery** | `kitchen-erp` Project spine, stage `2_pomiar`, `ArtifactRef` (tr-e51ef4fd); boundary is deliberately "attachments only" (process-coverage stage 2) | A *structured* survey pack: wall dims + diagonals, media points, appliance model sheets, user height/handedness, budget bracket — and a gate that stage 3 can't start without it (the playbook's Phase-0 rule) | Winner Flex's room wizard forces dims before design; none of the tools capture elbow height/handedness — the playbook is *stricter* than commercial tools here. A checklist schema beats an app |
| **1 Heights** | `ConstructionMethod` (720 carcass, reveals, plinth math) — the Polyboard-manufacturing-rules analog, genuinely good; `ProjectDefaults` table exists in ERP | A project-level **height parameter set** (worktop = elbow−100..150, wall-unit line, tall line) as a first-class entity consumed by layout and by gate G1-across-legs | PRO100/Winner both have global installation heights set once per job; Polyboard's job parameters cascade. Trivial to add, high leverage |
| **2 Zones** | Nothing. No appliance entities, no positions, no sink/hob/fridge concept | Zone map + appliance positions on a leg model; triangle/landing math (G5) | Even Winner only *draws* the triangle; it doesn't gate on it. The playbook's decision tree is automatable as a checklist over a leg model — no pro tool does this, it's your differentiator |
| **3 Corner** | `decompose_dolna_narozna_slepa` (tr-591aa208, filler + blind front — production side solved!) but **unreachable from a scene** (capability-map); no diagonal/dead corner, no corner *decision* artifact | Corner strategy record (blind/diagonal/dead + mechanism + filler widths on BOTH runs) feeding gate G2; corner width consumption from both legs | Polyboard's corner assemblies auto-consume width from both runs — that arithmetic is exactly what your flat model can't express |
| **4 Base runs** | ERP canvas rows (quick-estimate only, per ADR-009 boundary); `validate_rows` WSTD (standard widths) + FIT gates live | Appliances-first composition (no appliance model exists at all), one-filler-per-run-at-wall-end rule, two legs sharing the corner | PRO100's "place appliances first" is just practice; Winner encodes filler rules. Cheap once legs + appliances exist |
| **5 Wall + tall** | `gorna_drzwiowa` partial (ok rozrys/BOM, no machining ops from decomposer); **no tall/column type at all** (oven/fridge column absent — sink/cargo/oven/karuzela are model-only) | Tall column type (or enforced estimate-line exclusion), hood-on-duct check, top-line continuity gate | Every pro tool has tall units day one; a bespoke L-kitchen almost always has a fridge/oven column at the open end (the playbook mandates it) — this is a real coverage hole, not a nice-to-have |
| **6 Worktop + services** | `WorktopSegment` per-lm with cutout *count* (tr-17905dae, wk-4c37f4ee); comment in model.py: "L-shape geometry comes in CAM stage" | Cutout *positions*, corner joint (mason's mitre) modeling, joint-clear-of-cutouts (G7); electrical plan — nothing | TopSolid does full worktop CAD — overkill. What you need is Winner's *worktop order sheet*: 2 segments, joint type, cutout positions, grain. Electricals: annotate a plan by hand forever |
| **7 Fronts/decors** | Strongest sales asset: catalog (variants/pairings/edges, schema 1.5.0), 6-endpoint configurator wizard, builder GUI, krono-compositor 2.5D swap (~500ms) | Krono renders a **linear strip on a bare floor** — no L preset despite the vision doc promising I/L/U; 90/148 decor images missing (wk-6716e9c8); UC-3 undressed | PRO100/PaletteCAD do photoreal-in-minutes with room context. Your 500ms decor swap is actually *faster* than PRO100's re-render for the decor-choosing job — don't chase photoreal, chase the L preset |
| **8 Validation gate** | Genuinely strong: `evaluate_buildability` ordered-gate verdict (tr-65aa5969), M1–M5 + FIT/WSTD/G1/G6, emission refuses FAIL (tr-409f4aab). G2/G3/G4/G5/G7 explicitly SKIPPED "model carries no L-run adjacency / no appliance positions / no cutout positions" | The parked gates — blocked solely on the layout model | No pro tool has a *refusing* gate that blocks artifact emission — PRO100 lets you export nonsense. This architecture is better than commercial; it's just starved of input data |
| **9 Production handoff** | The crown jewel: `decompose()` → rozrys CSV with Usłojenie (tr-15d48651), CNC drilling + DXF, priced BOM from one decomposition (tr-b485d74c), walking-skeleton golden validated. Flagship `dolna_legrabox` full; corner-blind full-but-no-golden; `dolna_drzwiowa`/`szufladowa` partial | Type completion (stretchers/ops for door type, box parts for szufladowa), G11 edge-band-by-thickness + G13 hardware completeness (wk-593a317b, tracked), ext-2a exclusion enforcement (non-decomposable types not yet *excluded with a marker*) | This is TopSolid'Wood's CAM handoff territory and you're honestly ~70% there for the covered types — with the anti-scrap golden discipline TopSolid doesn't have |

---

## B. Realistic feature set — the honest cut

Design principle: **hb5 stays the layout editor (ADR-009), the repo owns the
extracted truth.** No feature below is a drawing/editing surface; they are
data models, gates, and emitted documents.

### B1. Must-have — complete ONE real L-kitchen through the playbook

| # | Feature | Serves phase | Extends existing / genuinely new |
|---|---|---|---|
| 1 | **L-layout model**: `Run` gains position/direction + a corner link; `Kitchen` gains leg adjacency; produces the manifest `check_run_continuity` already validates | 2,3,4,8 | Extends `kuchnie_core.model` + the *existing* validator manifest contract. The keystone; ~a value-object's worth of code, not a CAD kernel |
| 2 | **Adapter position extraction** (r4): read per-cabinet world position + wall assignment from hb5, emit two Runs + corner instead of one flattened Row | 2–5 | Extends the extraction-fidelity lineage (wk-81a47ab8 → wk-cd815fba); zero new machinery |
| 3 | **Survey pack**: named `ArtifactRef` kinds + a completeness checklist; `transition_stage` 2→3 refuses an incomplete pack | 0 | Extends kitchen-erp spine (tr-e51ef4fd). Days, not weeks |
| 4 | **Height parameter set** on `ProjectDefaults` (worktop/wall-line/tall-line, elbow formula), consumed by G1-across-legs | 1 | Extends kitchen-erp + `validate_rows` |
| 5 | **Appliance modules**: typed fixed-size config with model-sheet reference; enforced estimate-line **exclusion with marker** (closes UC-2 ext 2a); enables gate G4 (cutout vs sheet) | 2,4,8 | Extends `model.py` typed configs — sink/oven/cargo configs already exist model-only |
| 6 | **Corner strategy object**: blind/diagonal/dead + mechanism + filler widths both runs; unparks G2; diagonal flags the worktop order | 3,8 | Extends core; production side (corner-blind decomposer) already shipped |
| 7 | **Unpark gates G2/G3/G5/G7** on the new model; SKIP only when data genuinely absent | 8 | Extends `buildability.py` — the SKIP slots were designed for exactly this |
| 8 | **Type coverage for a real kitchen**: finish `dolna_drzwiowa` (top stretchers + ops), `dolna_szufladowa` box parts, one tall-column type | 5,9 | Extends `catalog.py` decomposers + capability-map rows |
| 9 | **Worktop order sheet**: cutout positions + corner joint on `WorktopSegment`; emit an order document | 6,9 | Extends wk-4c37f4ee / wk-3141488c lineage |
| 10 | **Purchasing artifacts** G11/G13 (already wk-593a317b) | 9 | Existing, already P2 — just don't let the layout work starve it |

### B2. Strong-second (repeatability/speed)

- **Elevation + plan sheets** (SVG per wall, dimensioned) generated from the
  layout model — the single highest-value *client + installer* artifact once
  positions exist; every pro tool has it one click away. (Phases 2–5
  approval, installation.)
- **Client quote document** — print-CSS HTML from the existing
  widelek/comparison board, archived as `ArtifactRef`. (Phase 7/UC-1.)
- **Krono I/L/U presets** — the vision doc already promises them; the
  compositor's zone-mask machinery carries it. (Phase 0/7, UC-3.)
- **Triangle/landing calculator** (G5 full form) with walkway check.
  (Phase 2.)
- **Playbook phase tracker** on the project spine — phases as recorded
  checkpoints. (All phases; this is also the visibility mechanism, §E.)

### B3. Explicitly NOT build — the brutal list

- **Photoreal rendering.** hb5/Blender renders (or, bluntly, keeping a
  PRO100 seat for presentation) beat months of render pipeline. Krono stays
  a 2.5D decor picker — its job is Phase 0/7 decor choice, where it already
  outperforms PRO100's workflow on speed.
- **A drag-drop room editor. Ever.** ADR-009 settled it: hb5 owns placement;
  the ERP canvas stays a sketchpad. Building even a "simple" 2D editor is
  the classic bespoke-shop death spiral (three companies watched trying to
  out-edit PRO100; all failed).
- **Nesting** — already a permanent non-goal; the CNC service owns it.
  Correct call.
- **Electrical/lighting CAD** (Phase 6 services) — hand-annotate the
  generated plan sheet. Winner's electrics module is used by <10% of its
  users for a reason.
- **Stone/quartz worktops** — external quote line, as decided.
- **Auto-layout / AI placement, VR/panorama (PaletteCAD territory),
  bidirectional hb5 write-back, assembly sheets before the stage-8
  milestone, decomposers for karuzela/cargo mechanisms** — estimate lines
  with enforced exclusion are cheaper than modeling a Magic Corner, and the
  mechanism arrives as a boxed SKU anyway.

---

## C. Roadmap — four stages, each ending in a playbook artifact

Anchor: **pick one real signed L-kitchen project ("Project P1") now** and run
every stage against it. L1 stage numbers refer to roadmap-map.csv semantics
(2 pomiar, 3 layout, 4 decomposition, 5 purchasing, 9 worktops, 1
first-visit).

**Stage 1 — "One real L-kitchen, hand-stitched" (L1 stages 2,3)**
Survey pack + height set entities; adapter r4 keeps positions and emits two
Runs + corner for P1's hb5 scene; run the existing pipeline on the covered
types; parked gates checked *by hand against the playbook, results recorded*.
**DoD:** P1's survey pack blocks/passes the 2→3 transition; a two-leg
`Kitchen` JSON exists extracted without hand re-entry; buildability verdict
on P1 lists its SKIPs explicitly. *Demonstrable on a real client in weeks.*

**Stage 2 — "Layout truth + the full gate" (L1 stages 3,4)**
L-layout model + corner strategy + appliance modules in core; unpark
G2/G3/G4/G5/G7; new golden exercise `walking-skeleton-L` (two legs,
corner-blind + flagship + one appliance) alongside d60.
**DoD:** Phase 8 gate runs G1–G7 with zero SKIPs on the L golden;
corner-blind becomes reachable from a scene (clearing its capability-map
caveat).

**Stage 3 — "Full cabinet list out" (L1 stages 4,9,5)**
Type completion (door type ops, szufladowa box parts, tall column); ext-2a
exclusion enforcement; worktop order sheet with joint + cutout positions (G7
fed by real data); wk-593a317b lands (G11/G13).
**DoD:** P1's *entire* cabinet list either decomposes or is an
explicitly-marked estimate line; rozrys + DXF + BOM + worktop order accepted
by the cutting service and CNC shop for P1. This is the playbook's A10
artifact, complete.

**Stage 4 — "Client surfaces + repeatability" (L1 stages 1,3,5)**
Elevation/plan SVG sheets; quote print document; krono L-preset; playbook
phase tracker on the spine; dress UC-3.
**DoD:** a second project (P2) runs Phase 0→9 with no hand-stitched step,
client approval recorded on generated artifacts.

---

## D. Specs to write (house system: six-section ledger-wired, archetype blanks A–F, ADR-014 `--accept-cmd` oracles)

Specs are born per stage, when the work is first seriously discussed — not
batch-written up front (spec-convention lifecycle; Ground truths must cite
LIVE ids). In roadmap order. All names kebab, living in the component that
changes most per spec-convention.

| # | Spec | Home | Archetype | SC- assertion subjects (candidates) | ADR-014 acceptance oracle |
|---|---|---|---|---|---|
| 1 | `survey-pack` | `kitchen-erp/docs/specs/` | **B** (data service) | required artifact-kind enumeration on the spine; 2→3 transition refuses incomplete pack; appliance-sheet rows carry model + cutout dims; pack completeness renders in project record | pytest: fixture project, transition refusal then pass |
| 2 | `l-layout-model` | `kuchnie-core/docs/specs/` (create dir) | **A** (domain library) | Run carries position/direction/corner link; corner consumes width from both legs; produced manifest passes `validate_manifest`; flat-Kitchen loads stay back-compatible | hand-computed L-geometry test suite (Meyer-contract style, like ConstructionMethod's) |
| 3 | `adapter-position-extraction` | `home-builder-adapter/docs/specs/` | **D** (adapter/ACL) | per-cabinet world position + wall assignment read from cages; two-wall scene → two Runs + corner; golden L-scene field-mapping table each row test-cited | `exercises/harness/runner.py <L-scenario> --strict` (validation-kind oracle) |
| 4 | `height-parameter-set` | `kitchen-erp/docs/specs/` | **B** | elbow-formula derivation stored on ProjectDefaults; wall/tall lines present; G1-across-legs consumes the set; 850–910 default band | pytest fixture asserting derived heights + gate consumption |
| 5 | `appliance-modules` | `kuchnie-core/docs/specs/` | **A** | typed appliance config with fixed dims + sheet ref; decomposition excludes with explicit marker (UC-2 ext 2a); G4 finding on sheet mismatch; rozrys/CNC never emit appliance rows | buildability test: kitchen with appliance → marker present, G4 fires on bad sheet |
| 6 | `corner-strategy` | `kuchnie-core/docs/specs/` | **A** | corner decision value object (blind/diagonal/dead + mechanism + filler both runs); G2 unparked; diagonal flag propagates to worktop order; "never sink/hob/dishwasher in corner" invariant | gate test on golden L kitchen: G2 PASS, seeded violation → BLOCKING |
| 7 | `design-legality-gates` | `kuchnie-core/docs/specs/` | **F** (cross-cutting gate) | G2/G3/G5/G7 report findings, not SKIP, when model data present; SKIP only on absent data with named reason; blocking-first ordering preserved | `evaluate_buildability` on L golden expecting PASS with 0 skips (wrapper script, accept-allow listed) |
| 8 | `full-run-decomposition` | `kuchnie-core/docs/specs/` | **E** (pipeline) | dolna_drzwiowa emits stretchers + machining ops; szufladowa box parts decomposed; tall column type in TYPE_REGISTRY; zero silent exclusions per kitchen (count check) | `walking-skeleton-L` golden diff via exercise-gate |
| 9 | `worktop-order-sheet` | `kuchnie-core/docs/specs/` | **E** | cutout positions with ≥50mm web check; joint-clear-of-cutout (G7); two segments + joint type + grain on the emitted sheet; per-lm price line matches wk-4c37f4ee output | golden order-sheet diff for P1 |
| 10 | `elevation-sheets` | `kitchen-cam/docs/specs/` (it owns drawing output) | **E** | per-wall SVG with dimension lines from layout model; plan view with triangle overlay; deterministic (run-twice-same-bytes) | golden SVG diff |
| 11 | `quote-document` | `kitchen-erp/docs/specs/` | **C** (GUI) | print view renders widelek/variant totals with SZACUNEK grade; labor split never in client view; archived as ArtifactRef on emit | snapshot test + attestation (UNVERIFIED, --ttl-days) for the visual walkthrough |
| 12 | `krono-l-preset` | `krono-compositor-mvp/docs/specs/` | **C** | I/L/U layout.json presets; zone masks correct on the L return leg; swap latency budget held | rendered-mask pixel test + human attestation |

**Extend, don't duplicate:** dress **UC-11** in `docs/specs/use-cases.md`
(it already exists casually as *the playbook UC*) rather than minting a new
UC for design; extend the extraction-fidelity work lineage (wk-cd815fba)
rather than a parallel adapter spec family; extend wk-4c37f4ee/wk-3141488c
for worktops; `process-coverage.md` needs only a one-line stage-3 boundary
amendment ("adapter now carries positions") — its in/out decisions all
survive. `kitchen-cam/docs/specs/overview.md` is already banner-marked
stale; spec 10 should supersede-with-pointer rather than revive it.

---

## E. Visibility plan — feed the existing dashboard, build nothing new

**1. roadmap-map.csv rows** (schema `bd_id;wk_id;stage;label;uc;axis`; bd
placeholders until twins exist — rows without a bd_id are inert in the
swimlanes until the bd twin is created at work start):

```
;;2;Survey pack (artifact kinds + 2->3 gate);UC-12;product
;;3;L-layout model (runs+corner+positions);UC-11;product
;;3;Adapter position extraction r4 (two-leg scene);UC-2;product
;;3;Height parameter set (ProjectDefaults);UC-11;product
;;4;Appliance modules + ext-2a exclusion enforcement;UC-2;product
;;4;Corner strategy object (G2 unpark);UC-11;product
;;4;Design gates G3/G5/G7 unpark;UC-11;product
;;4;dolna_drzwiowa/szufladowa completion + tall column;UC-2;product
;;9;Worktop order sheet (joint + cutout positions);UC-11;product
;;7;Elevation/plan sheets (SVG);UC-11;product
;;5;Quote print document;UC-1;product
;;1;Krono I/L/U presets;UC-3;product
```

**2. use-cases.md:** today's inventory covers quoting, production pack,
decor session, ordering, spine — but the playbook itself is only UC-11,
*casual*. Two changes: (a) **dress UC-11 fully**, with the main success
scenario's steps = playbook Phases 0–9 and extensions = the Phase-8
fail-back edges (heights→P1, clearance→P2, corner→P3, cutout→P6 — they're
already drawn in the playbook's gate diagram, ready-made Cockburn
extensions); (b) add **UC-12 (Surveyor: capture a measurement visit into a
survey pack)** — the Surveyor actor exists in the actor table with *no UC of
its own*, which is exactly the Phase-0 hole.

**3. STATUS.md:** no new section needed. Dressing UC-11 makes §1's existing
UC progress-bar machinery render a **playbook phase coverage bar for free**
— each step-supported/step-open marker is a phase. §4's note "Buildability's
parked design gates (playbook G2–G5, G7) count inside the UC-2 bar" already
shows the dashboard knows how to carry playbook gates; the parked-gate
burn-down will surface there as they unpark. The only hand-maintained inputs
remain the three CSVs — this respects the "feed the existing dashboard"
constraint completely.

---

## F. Top 5 risks / operator decisions

1. **Resurrect vs rebuild the layout model.** A full
   `Wall`/`Run`/`Layout`/`LayoutEngine` once existed — it survives only as
   bytecode in `home-builder-adapter/src/kitchen/__pycache__/`, source in
   the external retired plugin-era repo. Decide: recover that source (if it
   still exists on disk) and port the minimal subset into `kuchnie_core`, or
   rebuild clean against the manifest contract the validator already tests.
   PM lean: rebuild minimal in core (the old model was plugin-era,
   pre-ADR-009), but only the operator knows if the old source is reachable
   and trustworthy.
2. **Where the pro-tool boundary sits permanently.** Recommendation to
   ratify explicitly (as a non-goal line in process-coverage): *photoreal
   client presentation stays in hb5/Blender renders forever; krono stays
   2.5D decor choice; no built rendering.* If Blender render turnaround ever
   hurts sales, the answer is a PRO100/PaletteCAD seat for presentation only
   — never a build.
3. **How much CAM to trust, per type.** The scrap-severity doctrine (wrong
   drill row > missing BOM line) implies a hard rule only the operator can
   set: **no DXF leaves for a cabinet type without a committed golden**
   (today only d60-legrabox has one; corner-blind ships DXF with none).
   Ratifying that rule may slow Stage 3 — scrap risk vs speed.
4. **Decomposer coverage vs permanent estimate lines.** Tall column: build
   it (playbook mandates a column in nearly every L-kitchen). Sink cabinet:
   borderline. Cargo/karuzela/oven housings: keep as enforced estimate-line
   exclusions — mechanisms arrive as boxed SKUs and the margin doesn't repay
   a decomposer. Only the operator knows the job mix.
5. **G5 (triangle/landings): mechanize or checklist?** Full automation needs
   room doors, walkways and traffic paths — a slippery slope back toward a
   room editor. The cheap alternative: G5 stays a human gate executed on the
   generated plan sheet, recorded as a TTL'd attestation per project. Decide
   before spec #7 is written, because it sets that spec's scope.

**Sixth, unnumbered because it's not a risk but a commitment:** Stage 1 only
works anchored to a real signed project. Choosing P1 — and accepting that
its first run through the playbook will be half-manual — is the single
decision that turns this roadmap from a plan into a schedule.
