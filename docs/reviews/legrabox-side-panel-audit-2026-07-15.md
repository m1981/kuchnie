# Audit: is legrabox_side_panel.py a third LEGRABOX formula source?

> Reader: Michał deciding this module's fate in the dark-code triage
> (adopt / attic / delete) | Enables: deciding from measured divergences
> instead of suspicion; the ADR-006 single-source question answered with
> numbers | Update-trigger: the triage decision lands (record it here), or
> the file is modified

Audited: `kitchen-cam/src/kitchen_cam/dxf/legrabox_side_panel.py` vs
`kuchnie-core/src/kuchnie_core/legrabox.py`, `blum_drawers.py`,
`kitchen-cam/src/kitchen_cam/machining.py`, and the confirmat ops in
`kuchnie-core/src/kuchnie_core/catalog.py`. Performed by a read-only
investigation agent 2026-07-15; key numbers spot-checked independently by
the reviewing session (SYSTEM32_OFFSET 37 vs 16, runner front offset 46
vs 37, DOWEL_DIA 8.0, zero importers).

## Verdict: DIVERGED — a live, un-networked third source

Agrees with core on exactly one family (N/M/K/C/F side heights) and
diverges on every other: opening sizing, System32 raster, runner mounting
holes, and dowel/confirmat joinery. DARK per `scripts/coverage-audit.py`
(zero importers, zero tests, zero live spec wires, zero ledger citations)
— so nothing breaks today — but it remains directly executable by hand
and would hand a shop a DXF disagreeing with the real pipeline's geometry
for the same panel.

| Family | Verdict |
|---|---|
| Height-code table (N/M/K/C/F side heights) | IDENTICAL |
| Opening-height / min-install sizing | DIVERGED (self-invented heuristic, never checked against Blum minimums) |
| System32 raster | DIVERGED |
| Runner / profile mounting holes | DIVERGED (orthogonal geometry) |
| Dowel/confirmat joinery | DIVERGED (right pattern, wrong diameter/count) |

## Numeric divergences (side-panel vs core)

| Quantity | side-panel | core | Consequence if used |
|---|---|---|---|
| Side heights N/M/K/C/F | 66.5/90.5/128.5/177/241 | identical (`legrabox.py` LegraboxHeight) | none |
| Drawer-back cutting heights | absent | N=39 M=63 K=101 C=148 F=212 | cannot produce/verify the back panel at all |
| Min install height per code | absent — invents an "opening height" redistribution (`calculate_drawer_openings`) | N=50 M=68 K=106 C=155 F=220 | can silently size an opening below Blum's minimum (only warns when the SUM overflows, never per-opening) — drawer binds or won't fit |
| System32 first-hole Y | 16.0 mm | 37.0 mm (`machining.py` SYSTEM32_OFFSET) | hole columns 16/48/80… vs 37/69/101… — no hole ever coincides with the real pipeline's |
| System32 rows | 2 rows (front @ width−37, back @ 37) | 1 front row @ 37; back-side handled as shelf pins @ 80 | back row has no counterpart concept |
| Runner-hole front offset | 37.0 mm | 46 mm (`runner_screw_first_offset()`) | 9 mm off before geometry is compared |
| Runner-hole layout | vertical column every 32 mm up each opening | horizontal row per NL (e.g. NL500 → x∈{46,78,110,398}) | orthogonal patterns; screws never align |
| Pilot depth | not encoded (plain circle) | 12 mm blind, "NEVER through" | through-drill risk on an 18 mm side |
| First mounting point | 9 mm from opening bottom, asserted | ~37 mm, explicitly flagged unverified in core | two numbers, one asserted with false confidence |
| Panel joinery diameter | Ø8 dowel | Ø7 confirmat (`catalog.py` _confirmat_side_ops) | oversized hole → weak joint; count also differs (symmetric vs 3-bottom/2-top) |

## Consumer census

Zero Python importers repo-wide; no CLI (the `kitchen-cam side-panel`
entry point promised by ADR-010 was never built — its only entry is
`python legrabox_side_panel.py` by hand); zero tests; only stale doc
mentions of the pre-move path; zero ledger citations; DARK in
coverage-audit. `kitchen-cam/docs/architecture.md` already marks it
"disconnected"; `panel_dxf.py`'s docstring names it as the thing
panel_dxf was built to replace; the 2026-07-08 session handoff twice
called it a retirement candidate.

## History vs ADR-006

Written 2026-06-17 (under the component's pre-rename name, in its
`generators/` directory — see the ADR-010 rename), BEFORE ADR-006
(2026-06-25) declared `kuchnie_core.legrabox` the single source. The
2026-07-01 "Phase C" commit moved the path only; ADR-010's planned
migration (import LegraboxHeight from core) was never executed. Unedited
and unimported since, while core and panel_dxf kept evolving.

## Recommendation: attic with tombstone; port the annotation layers first

1. No unique math worth keeping — every formula either duplicates core or
   disagrees with it using uncited/invented constants.
2. Its genuinely unique capability is PRESENTATION, not geometry:
   `add_dimensions_and_notes` and `add_edgebanding_marks` (title block,
   dimension text, edge marks) are fuller than `panel_dxf.py`'s current
   outline+circles output. Port them as optional annotation layers over
   `Panel`/`MachiningOp` — reading values from core, never re-deriving.
3. Zero blast radius: DARK + zero importers + zero tests.
4. Standing risk if kept: a hand-run DXF silently disagreeing with the
   real pipeline — the exact ADR-006/ADR-010 violation, latent.

**Decision (Michał, 2026-07-16): ATTIC.** Moved to
`attic/legrabox_side_panel.py` with tombstone header; annotation-layer
port filed as its own work item (see repo tracker: "Port DXF annotation
layers into panel_dxf").
