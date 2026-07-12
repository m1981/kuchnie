# E2E D60 LEGRABOX — gap report (wk-641a80a8)

> Reader: owner deciding what the pipeline needs next | Enables: reading the
> measured distance between designer intent (GOLDEN.md), the hb5 design tool,
> and production output, phase by phase | Update-trigger: exercise re-run

Golden: `GOLDEN.md` (authored FIRST, independent) · Build: `blender_leg.py`
· Verify: hb5 `dev_tools/inspection` (18/18 PASS) · Production:
`run_production_leg.py` · Diff: `generated/golden-diff.txt`

## Verdict in one paragraph

The pipeline's production core reproduces the golden almost exactly — every
carcass panel, the 698×578 back, the Blum drawer-box parts to the millimetre,
confirmats and grooves at golden coordinates. The measured cost is at the
SEAMS: hb5 speaks US-imperial (¾" board, opening sizes + overlays, finish =
all exterior faces) so a Polish designer's intent needs translation both INTO
hb5 (front heights, 18 mm, decor-fronts-only) and OUT of it (extraction reads
none of the drawer stack, type, or materials the scene demonstrably stores).
One pre-existing report-only gap (G8 drawer order) produced a real
scrap-risk: runner rows drilled for the M drawer at the bottom while the
design hangs it at the top.

## Phase 2 — building in hb5 headless (designer → tool)

| # | Finding | Detail |
|---|---|---|
| B1 | `finish_colors` user-data path broken headless | ValueError "package does not name an extension" — custom-color store unreachable under `--background` legacy-addon enable; patched to empty in the leg |
| B2 | hb5 finish semantics are US | style "exterior finish" covers ALL exterior faces incl. carcass ends; Polish melamine flow (decor fronts, white carcass) needs per-part `Finish Top/Bottom` surgery (9 parts) |
| B3 | No white-melamine interior preset | interior enum = UV ply / matching / custom; "biały korpus" is only reachable via a custom material |
| B4 | `default_carcass_part_thickness` did not propagate | scene prop set to 18 mm pre-create, parts still built ¾" (19.05); forcing `Material Thickness` on the cage subtree + calc-fix works |
| B5 | Front heights not expressible | `top_drawer_front_height` is an OPENING size; US overlay model produced fronts 163.8/268.8/279.4 vs designed 140/287/287 — adapter write path needs a front-height → opening-size translation |
| B6 | Default bar pulls appear | golden is handleless; no obvious "no pulls" knob exercised — cosmetic, extraction ignores pulls |
| B7 | Saved .blend is bootstrap-fragile | reopening without the addon pre-registered breaks the `IF()` driver namespace and geometry collapses; only the inspection harness's bootstrap discipline (or `--enable-autoexec` + enable-then-open) renders it correctly |

## Phase 3 — visual verification (dev_tools/inspection)

18/18 checks PASS: overall 600×560×820, 18 mm carcass inventory, reveals,
box clearances, LEGRABOX side/NL suggestions (M/C/C, NL500) — the audit
layer independently reproduced the golden's LEGRABOX mapping from geometry.

**Reported unobservables** (things no camera angle can verify):

- Decor identity — inspector renders Workbench random per-part colors; the
  material split was verified separately (own EEVEE render + part-input dump)
- Joinery — hb5 models NO fasteners; confirmats exist only downstream
- HDF groove — hb5's back is an 18 mm panel between the sides; there is no
  groove in the scene at all (golden's wpust is a pipeline-only construct)
- Drillings (runner pilots, system 32) — not modeled in the scene
- Edge banding and grain direction — not represented visually

## Phase 4 — through the pipeline (tool → production) vs golden

Panel diff (`generated/golden-diff.txt`): boki, plecy 698×578, cokół and all
six drawer-box parts MATCH the golden exactly. Remaining deltas:

| # | Delta | Classification |
|---|---|---|
| P1 | Fronts 594 vs golden 596 | G12 margin convention (settable, still open) |
| P2 | Drawer-box material `plyta_16mm` vs `PLYTA_BIALA_16` | G9 (no box-material field) |
| P3 | Dno/trawersy listed 560×564 / 100×564 vs golden 564×560 / 564×100 | rozrys writes height_mm into Długość unconditionally; carpenter convention puts the long/grain axis in Długość — free-rotation panels are unaffected at the saw, but the contract column semantics deserve a decision |
| P4 | **Runner rows Y = 55/195/482 vs golden 55/342/629** | G8: drawer list consumed bottom-up, entered top-down (M first) → M-drawer drillings at the BOTTOM. Scrap-risk demonstrated live |
| P5 | BOM hardware: 3 runner lines only | G13 — golden lists konfirmaty ×10, nóżki ×4, klipsy, zszywki |
| P6 | Edge banding one `abs_<board>` name | G11 — golden orders ABS 0.8 white + ABS 2.0 K5307 separately |

CNC otherwise identical to golden: konfirmaty (50/280/510 @ 9; 50/510 @ 711,
Ø7), wpust HDF 4×8 @ 10 on boki/dno/trawers tylny, runner pilots Ø5×12 at
X = 46/78/110/398.

## Extraction — what the scene stores vs what the adapter reads (wk-81a47ab8)

The cage hierarchy dump (`generated/cage-hierarchy.json`) proves the drawer
stack IS headless-readable: `Bay → Splitter Vertical
(IS_FRAMELESS_SPLITTER_VERTICAL_CAGE) → Opening N (IS_FRAMELESS_OPENING_CAGE,
geo-node Dim Z = 0.140/0.254/0.254) → Drawers → Drawer Front
(IS_DRAWER_FRONT) → Drawer Box (IS_DRAWER_BOX + clearance props)`. The
adapter reads none of it — extraction returned `dolna_drzwiowa`, drawers=[],
materials unassigned. Hand re-entry needed: type, LEGRABOX spec, materials,
front heights (5 GAP lines in `run_production_leg.py`).

## Natural-flow observations

1. Golden-first is cheap and catches what tests don't: the G8 order bug is
   invisible in unit tests (formulas are consistent) but instantly visible
   against a designed cabinet.
2. hb5 is a capable GEOMETRY oracle (envelope, openings, boxes, clearances)
   and a poor CONSTRUCTION oracle (imperial defaults, no joinery, thick
   back) — matches the committed layout-path split: hb5 draws, kuchnie-core
   builds.
3. The inspection harness is a genuine second pair of eyes: it independently
   suggested M/C/C + NL500 from geometry — cross-validating the golden's
   LEGRABOX mapping without touching our code.
