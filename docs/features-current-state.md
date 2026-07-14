# What the system actually does today — designer & CAM inventory

> Reader: Michał deciding what to trust on a real project | Enables: knowing
> which outputs are production-grade, which need hand-checking, and which
> don't exist yet — without marketing | Update-trigger: a wk closes that
> changes a status below (ledger-grade statuses live in
> `docs/pattern-conformance.md`)

Status vocabulary, used strictly:
**Works** — tested end-to-end, trusted output. **Partial** — works with
listed caveats. **Model-only** — data structures exist, nothing consumes
them. **Not built** — don't plan a project around it.

---

## 1. Designer perspective (planning a kitchen)

### Cabinet catalogue — Works, 5 types

`TYPE_REGISTRY` decomposers, each covered by hand-computed dimension tests:

| Type | Produces | Caveats |
|---|---|---|
| `dolna_drzwiowa` (base, doors) | sides, bottom, back, shelves, doors, hinges/pins/handles | **no top stretchers** — carcass list is incomplete for a real build (only `dolna_legrabox`/`narozna` got the round-1 fix) |
| `dolna_szufladowa` (base, drawers) | carcass + drawer fronts + runner accessories | box parts NOT decomposed (runner accessory only); same stretcher caveat |
| `dolna_legrabox` (base, LEGRABOX) | full reference carcass: 2 trawersy, plinth, drawer box parts, runner pilot drills, confirmats, HDF grooves | the walking-skeleton-validated flagship — matches a carpenter reference to the millimetre |
| `dolna_narozna_slepa` (blind corner) | carcass + blind front + 50 mm filler + door, full machining | new (ADR-014); not yet exercised end-to-end against a golden |
| `gorna_drzwiowa` (wall, doors) | sides, top+bottom, back, shelves, doors | no machining ops emitted yet |

Seven typed configs exist (`SinkConfig`, `CargoConfig`, `OvenConfig`,
`CornerInternalConfig`…) — **model-only**: no decomposer behind them yet.
Sink, cargo, oven and carousel cabinets cannot be produced today.

### Construction rules — Works

`ConstructionMethod` (the Polyboard pattern): swap dowel/confirmat/camlock,
16 vs 18 mm board, groove depths — without touching any cabinet type. Back
panels are groove-seated with 2 mm assembly clearance (fixed 2026-07-12;
never taller than the sides). Doors/fronts use the gap formula (3 mm
default — your 2 mm shop reveal is a known open convention, G12).

### Drawer systems — Partial

**LEGRABOX: end-to-end.** Blum height codes (N/M/K/C/F), NL availability,
LW width chain (verified identical to Blum planner output), box part
cutting sizes, runner pilot drills (Ø5×12 at the Blum X positions), 40 kg
runner accessories. Single-sourced in `legrabox.py` (ADR-006).
**TANDEMBOX / MERIVOBOX: data tables only** (heights, back panel heights) —
no base-cabinet decomposer consumes them yet.
**Order contract (G8, closed at loader/schema):** the drawer list is
consumed bottom-up; YAML input may declare `kolejnosc_szuflad: od_gory`
(normalized by reversal) and an ambiguous unequal stack without a
declaration is rejected at load. Hand-built `CabinetInstance` lists must
honor bottom-up themselves (documented on the model).

### Materials & decor — Partial

Catalog service (SQLite, schema 1.5.0): 148 decors with families, pairing
suggestions, producer SKUs; deliberately price-free. ERP mirrors it as its
material master (offline-tolerant, price-preserving — tested). Panels carry
material codes and **grain** (`pion`/`poziom`/`brak`) — decor fronts can no
longer be silently rotated at the saw. Gaps: 90/148 decors have no
miniature image (all 35 wood decors), color-family assignments partially
wrong (K522), and nothing resolves hb5 scene materials to catalog decors —
decor assignment is a hand step after extraction.

### Drawing in 3D (hb5 + adapter) — Partial

home_builder_5 is the committed layout path; it runs headless and the
adapter extracts **cabinet envelopes**: W×H×D + toe-kick height, per wall.
Everything else is re-entered by hand today: cabinet type (everything BASE
arrives as `dolna_drzwiowa`), drawer stack, materials, front heights. The
e2e exercise proved the drawer stack IS stored in the scene (opening cages)
— extraction round 2 (wk-81a47ab8) is queued, not done. Know also: hb5
thinks in inches and opening-sizes; your 140 mm front intent needs manual
translation until the adapter write path exists.

### Validation — Partial

Per-cabinet `validate()` catches dimensional nonsense (LEGRABOX height/NL
fit included), but checks are scattered across five modules with no ordered
gate runner — there is no single "this kitchen is buildable" verdict yet.

---

## 2. CAM / production perspective (making it)

### Cut list (rozrys) — Works, one contract decision pending

Panels aggregate by (material, thickness, dims, edging, grain) and export
semicolon CSV for e-rozkrój, Usłojenie included. BOM areas verified against
hand math (HDF 0.403 m² = reference exactly). Pending decision: which
dimension goes in Długość for lying panels (generated always writes
height-first; harmless for grain-free panels, but pin it before the first
paid e-rozkrój upload). Nesting itself: **permanent non-goal** — the
optimizer service owns it.

### Machining — Partial, strong where it counts

Emitted by decomposers (LEGRABOX + corner types): runner pilots, confirmat
through-drills (3 into bottom, 2 into trawersy per side, joinery-gated),
HDF grooves 4×8 @ 10 mm from rear on sides/bottom/rear trawers.
Applied downstream by kitchen-cam: System 32 rows (37/32 raster), hinge cup
drilling, handle pilots, shelf-pin holes — role-routed so a hinge cup can
never land on a fixed blind front (`PanelRole`, ADR-012/013/014).
**DXF per panel exists** (layers by drill type; LEGRABOX side panel drawing
with dims and edge-band marks). No machine-specific post-processor — DXF +
the CNC text list is the handoff format.

### BOM & pricing (ERP) — Works for materials, understates hardware

Quantities fold from the decomposition by panel role: corpus / front /
back / drawer-box m² priced separately (drawer-box board no longer hides in
corpus), edging lm split corpus vs front. Purchasing strategies add sheet
waste factors (woodgrain-aware). Hardware comes from a tag-driven rules
engine (hinges, brackets, bumpers, handles) — but **konfirmaty, nóżki,
klipsy, HDF fasteners are missing** (G13): quotes understate hardware by a
few zł per cabinet. Edge banding is one derived name per board — you cannot
order 0.8 vs 2.0 ABS from today's BOM (G11).

### What production cannot get yet — Not built

Project/Order tracking (customer, status, dates), supplier price-file
import, worktop per-lm BOM positions (WorktopSegment is model-only),
assembly drawings/instructions (later milestone), labels/barcodes,
delivery/install (permanently out of scope).

### Quality system around all of it — Works

Every closed gap is pinned by a test (852 across four suites). The e2e
harness diffs three oracles against hand goldens — panels, machining
coordinates, hardware — with a one-command runner that records the
toolchain (repo/hb5/Blender versions) per run. This is why the statuses
above can say "verified" and mean it.

---

## 3. Commercial CAD/CAM patterns in the codebase — and what each buys you

Ledger-grade status per pattern: `docs/pattern-conformance.md`. This table
adds the "so what" for project work.

| Pattern (where the industry uses it) | Status here | How it helps YOUR projects |
|---|---|---|
| **Construction Method separated from cabinet type** (Polyboard) | Built | Switch a whole kitchen 18→16 mm board or confirmat→dowel by swapping one method — no per-cabinet rework, no forgotten panel |
| **Panel as the atom** (ADR-001, vs Winner-style bay/opening trees) | Built | Every output (rozrys, BOM, DXF, CNC) is a flat panel list — easy to check by hand against your own math, nothing hides in a hierarchy |
| **Part roles for CAM routing** (Cabinet Vision-style part typing) | Built (13 roles) | "Hinge cups only on FRONT_DOOR" is enforced by type, not by name matching — a blind corner front can't get drilled for hinges; drawer-box board prices separately from decor board |
| **Feature-based machining ops** (TopSolid Wood) | Mostly built | Drills/grooves are data (face, type, coords), so the same decomposition feeds the CNC text list, DXF layers, and future post-processors without re-derivation |
| **Manufacturer hardware library, single-sourced** (Blum data in 2020/Insight) | Built for LEGRABOX | Box part sizes and pilot positions come from one Blum-verified table — when Blum revises a height code, one file changes and every cabinet follows |
| **System 32** | Built | Shelf pins and hinge plates land on the 37/32 raster automatically — carcasses stay compatible with standard hardware and re-drilling |
| **Design frontend ≠ construction engine** (IMOS/imos-iX split) | Built (hb5 ↔ core seam, ADR-009) | You sketch in a comfortable 3D tool; the shop truth (Polish construction, metric, joinery) is computed by code you control and test — the US-centric tool can't corrupt a cut list |
| **Material master + mirror** (ERP material master, imos/2020 catalogs) | Built | One decor list feeds design, rendering and pricing; supplier discontinues a board → discontinued flag flows everywhere; local prices survive catalog refreshes |
| **Cutting-contract handoff to an optimizer** (industry-standard CSV/PTX seam) | Built (column map pending) | You never maintain a nesting engine; the rozrys CSV is the stable contract any Polish rozkrój service accepts |
| **Grain constraint on parts** (nesting inputs in every serious CAM) | Built | Wood-decor fronts are pinned `pion` — the optimizer can rotate white carcass parts for yield but can never turn your fronts 90° |
| **Golden-sample regression** (vendor QA farms; our e2e harness) | Built | Before a formula change reaches a paid job, it's diffed to the millimetre against a hand-computed cabinet — the 728 mm back-panel class of error now dies in CI, not at the saw |
| **Rules engine for hardware completion** (2020 attach rules) | Partial | Doors automatically pull hinges/bumpers into the quote; extend the same rules to konfirmaty/nóżki and G13 closes without touching decomposers |

### Patterns deliberately NOT adopted

- **Nesting/optimization engine** — permanent non-goal; the seam is the CSV.
- **Bay/opening/splitter product hierarchy** (Winner Flex) — panel-is-atom
  keeps outputs auditable; revisit only if openings must become first-class.
- **Monolithic all-in-one suite** — six small components around one domain
  hub, each testable alone; the price is the seams, which the e2e exercises
  measure on purpose.

---

## 4. The honest bottom line

Today you can take a **base LEGRABOX or blind-corner cabinet** from typed
parameters to a millimetre-correct cut list, drilling list, DXF and priced
material BOM — with grain, edging flags and groove-seated backs — and trust
it, because each of those numbers is pinned against hand math. A **door
base / wall cabinet** gives you correct panels but an incomplete carcass
(stretchers) and no drilling. **Sink, cargo, oven, carousel** cabinets and
**order/worktop/price-import** workflows do not exist yet. The 3D path
saves you envelope re-typing today and is one queued work item away from
carrying the drawer stack too.
