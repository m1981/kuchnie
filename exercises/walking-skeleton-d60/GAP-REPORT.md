# Walking skeleton D60 — gap report

> Reader: owner deciding what to fix next in the pipeline | Enables: reading
> the measured distance between a carpenter's reference and what the tools
> produce today, gap by gap | Update-trigger: a listed gap is resolved (move
> it to the resolved table with its commit) or the exercise is re-run

Exercise: wk-9f1ad053 / kuchnie-4uo · spec `docs/specs/walking-skeleton-d60.md`
Reference: `reference/` (hand-computed) · Output: `generated/` (pipeline)

## Verdict in one paragraph

The production core (decompose → panels) is real: 13 panels, LEGRABOX
formulas to-the-millimeter identical with the Blum-derived reference
(drawer parts 0.919 m² in both), runner drill positions present on both
sides. But the cabinet it produces **could not be built and invoiced as-is**:
no top stretchers, no plinth, no confirmat drilling, no HDF groove, wrong
runner-screw depth, and a back panel taller than the sides. The ergonomic
cost is front-loaded: everything LEGRABOX-specific had to be re-entered by
hand after extraction.

## Gaps — carcass & machining (reference vs generated)

| # | Gap | Reference | Pipeline | Severity |
|---|---|---|---|---|
| G1 | **No top stretchers (trawersy)** — drawer carcass has nothing holding the top; would rack on assembly | 2× 564×100×18 | absent | build-blocking |
| G2 | **No confirmat ops** despite `joinery_type="dowel_confirmat"` in ConstructionMethod — the declared joinery produces zero drillings | 10 szt + Ø7/Ø5 pattern | absent | build-blocking |
| G3 | **No HDF groove** — `MachiningOp` supports `groove` but no decomposer emits it | frez 4×8 @10 in boki/dno/trawers | absent (generator prints warning) | build-blocking |
| G4 | **Runner screw depth = 0** with note "through-hole" — euro 6.3×13 needs a Ø5×12 blind hole; through an 18 mm side is a visible hole in the cabinet side | Ø5 gł. 12 | D5 gł. 0 przelot | scrap-risk |
| G5 | **Runner axis Y at zone bottom** (code TODO admits missing Blum offset) and zone stacking ignores the 3 mm front gaps | Y = 55/342/629 | Y = 18/158/445 | scrap-risk |
| G6 | **Back panel taller than sides**: `back_panel_height = side_h + 8` gives 728 for a 720 side with no top groove receiver; width 580 leaves no assembly clearance | 578 × 698 (2 mm luz, pod trawers) | 580 × 728 | scrap-risk |
| G7 | **No plinth panel** — `PanelRole.PLINTH` is declared aspirational; cokół missing from cut list and BOM | 596×97×18 + klipsy | absent | quote-understates |
| G8 | **Drawer list order semantics undocumented** — list is consumed bottom-up; entering fronts top-down puts the M drawer at the bottom | M on top | M at bottom | silent wrong build |
| G9 | **Drawer-box material not configurable** — `CabinetInstance` has no field; decomposer hard-defaults `plyta_16mm` | PLYTA_BIALA_16 (named) | `plyta_16mm` literal | BOM naming drift |
| G10 | **No grain axis on Panel** — `GrainAxis` exists in the model but `Panel` has no such field; rozrys "Usłojenie" column cannot be filled; decor fronts risk 90° rotation at nesting | pion for K5307 fronts | empty | scrap-risk (decor) |
| G11 | **Edge banding undifferentiated** — one derived name `abs_<board>`, no thickness/width; 0.8 carcass vs 2.0 front cannot be ordered from the BOM | ABS 0.8×22 / ABS 2×23 | `abs_PLYTA_BIALA_18` 2.00 mb | order-blocking |
| G12 | **Front margin convention** — decomposer default 3 mm/side (594) vs shop standard 2 mm reveal (596) | 596 | 594 | convention (settable) |
| G13 | **BOM hardware incomplete** — runners only; no konfirmaty, euro screws, nóżki, klipsy, HDF fasteners | 5 hardware lines | 3 runner lines | quote-understates |

## Gaps — design leg & flow ergonomics

| # | Gap | Detail |
|---|---|---|
| E1 | **Adapter's Blender generation leg is dead** — Makefile targets call `src/main.py` which no longer exists (orphaned `.pyc` in `src/kitchen/` are its remains) | logged during exercise setup |
| E2 | **Extraction type map cannot express drawer cabinets** — `_TYPE_MAP` sends every BASE to `dolna_drzwiowa`; `dolna_legrabox`/`dolna_szufladowa` unreachable from a scene | must re-enter type by hand |
| E3 | **Extraction loses the drawer system** — only opening heights survive; system/height-code/NL/capacity re-entered by hand | the whole M+C+C spec is manual |
| E4 | **No material-resolution step** — adapter emits `unassigned` (ADR-008 by design) but nothing between adapter and decompose assigns decors; hand edit required | `kuchnie_core.materials` resolver exists but is unwired |
| E5 | **hb5 headless: YES, via type classes** — `BaseCabinet`/`GeoNodeWall` build fine in `--background`; the modal placement operators are the only GUI-bound path. Room + cabinet built and saved (`d60-room.blend`) | resolved-positive |
| E6/E7 | **Extraction contract dead on arrival** (`tr-e60f4fe0`) — `extract.py` reads `Dim X/Y/Z` + `opening_sizes` as ID props; the real cage stores dimensions on the evaluated bbox and no opening sizes at all (`raw-cage-dump.json`). As-is extraction returned 0×0×0 and no drawers; the exercise shim shows the fix is ~15 lines (bbox + `Toe Kick Height`) | pipeline-blocking |
| E8 | **hb5 knows more than we extract** — the cage carries `Base Top Construction`, `Stretcher Width` (0.1016 m), `Material Thickness` (19 mm imperial default): stretcher data exists upstream while G1 shows it missing downstream | design input for G1 |

## Filed ledger claims

| Claim | Covers |
|---|---|
| tr-e60f4fe0 (P1) | E6/E7 extraction contract |
| tr-3b4e0168 (P1) | G1 + G7 no stretchers / no plinth |
| tr-72e29da5 (P1) | G2 + G3 machining = runner screws only |
| tr-41acef99 (P1) | G4 + G5 runner depth/axis unbuildable |
| tr-484cf1df (P1) | G6 back taller than sides, dual formula |
| tr-4a2cd4e3 (P2) | G10 no grain axis on Panel |

Report-only (await L1 scope decisions): G8 order semantics, G9 box material
field, G11 edge-band identity (ties to catalog edge codes), G12 margin
convention, G13 hardware BOM completeness, E1–E4.

## Resolution round 1 (2026-07-12)

Fixed and re-validated by re-running BOTH legs — extraction now succeeds
with the unmodified adapter, and the generated rozrys carries 16 panels:

| Gap | Fix | Work id |
|---|---|---|
| E6/E7 (tr-e60f4fe0) | extraction reads evaluated bbox + Toe Kick ID prop; legacy Dim-props still win when present | wk-ee28c3dd |
| G1+G7 (tr-3b4e0168) | dolna_legrabox emits 2 trawersy (TOP) + cokół (PLINTH), 596×97 = reference | wk-c3d0a0f0 |
| G4+G5 (tr-41acef99) | runner pilots blind Ø5×12; axis = zone floor + 37 (single-source constant in legrabox.py) | wk-7341700c |
| G2+G3 (tr-72e29da5) | confirmat through-drills (3× dno, 2× trawersy — coordinates match reference exactly) gated on joinery_type; HDF groove ops on boki/dno/trawers tylny | wk-38c32190 |

Still open: G6 back oversize (tr-484cf1df), G10 grain (tr-4a2cd4e3),
and the report-only items above. Note the generated CNC still shows the
M-drawer at the bottom — that is G8 (input order semantics), untouched
by design.

## Resolution round 2 (2026-07-12)

Re-validated by re-running the production leg against the hand reference:

| Gap | Fix | Work id |
|---|---|---|
| G6 (tr-484cf1df) | back formula fixed in ConstructionMethod: height = side_h − bottom − top + 2×groove − 2 mm luz, width gets the same luz; Plecy 698×578 = reference, HDF area 0.403 m² = reference; third inline formula in decompose_gorna_drzwiowa consolidated into the same method | wk-090ed9f4 |
| G10 (tr-9054097f, successor of tr-4a2cd4e3) | `Panel.grain` added (GrainAxis); decomposers set HEIGHT on FRONT_DOOR/FRONT_DRAWER; cutlist aggregation keys on grain and emits Usłojenie (pion/poziom/brak); rozrys shows `pion` on K5307 fronts = reference | wk-5dc557d6 |

After round 2 the remaining gaps are all report-only/L1-scoped: G8 order
semantics, G9 box material field, G11 edge-band identity, G12 margin
convention, G13 hardware BOM completeness, E1–E4.

## Reconciliations (not gaps)

- 16 mm drawer-part areas: reference 0.919 m² = generated 0.919 m² — ADR-006
  chain (LW→back/base widths) confirmed identical.
- White-board delta 1.293 − 1.122 = 0.171 m² = exactly the missing
  trawersy (0.113) + cokół (0.058) — the formulas that DO exist agree.
- K5307 delta 0.426 vs 0.424 = the G12 margin convention only.
- Runner X positions 46/78/110/398 identical (Blum NL500 chart).

## Status

- [x] Reference authored
- [x] Production leg run (fallback input)
- [x] Blender/home_builder_5 leg (headless, room + cabinet, .blend saved)
- [x] Production leg re-run from extracted JSON (drawer spec re-entered by
      hand — E3 demonstrated live)
- [x] Gaps filed as ledger claims (6, table above); repair work items await
      owner prioritization
