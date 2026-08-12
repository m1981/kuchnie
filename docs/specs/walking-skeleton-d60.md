# Spec: Walking skeleton — D60 LEGRABOX cabinet through the full pipeline

> Reader: anyone assessing how much of the sales→CNC pipeline actually works
> end-to-end | Enables: running the thinnest real slice (one room, one
> cabinet) through every stage and reading the resulting gap list instead of
> guessing | Update-trigger: a pipeline stage the skeleton exercises changes
> its contract, or the gap report's findings are resolved

## Intent

Push ONE base cabinet — 600 mm, three LEGRABOX drawers (M+C+C), confirmat
carcass in white 18 mm chipboard, grooved 3 mm HDF back, one decor front,
no worktop — through the complete flow:

1. **Reference first**: hand-computed carpenter's cut list, BOM and CNC
   drilling list (`exercises/walking-skeleton-d60/reference/`) — the oracle.
2. **Design leg**: headless Blender + `home_builder_5` scene (room + cabinet),
   `home-builder-adapter` extraction → `Kitchen`.
3. **Production leg**: `decompose()` → cutting-service CSV (rozrys), BOM,
   CNC TXT (runner drillings + HDF groove milling).
4. **Gap report**: line-by-line diff of reference vs pipeline output plus an
   ergonomics log (manual steps, format mismatches). Confirmed gaps become
   ledger claims + beads.

The product is the gap report, not the cabinet. Non-goals: fixing the gaps
in this exercise; nesting; worktop; pricing beyond the BOM positions.

## Decisions

- ADR-006 — LEGRABOX LW formula (reference uses LW = KB − 26).
- ADR-009 — adapter is the only bpy component; scene extraction contract.
- ADR-013 — drawer-box panel roles (reference expects role-tagged box parts).

## Ground truths

- tr-bd0ba211 — home_builder_5 addon present (the design-leg input).
- tr-76d6de33 — LEGRABOX numbers single-sourced in `legrabox.py`.
- tr-0e13ba64 — drawer-box roles + separate BOM bucketing shipped.

## Work

- wk-9f1ad053 — this exercise (bead twin: kuchnie-4uo).

## Acceptance

Written now, scoped to what evidence commands can show:

- "exercises/walking-skeleton-d60/reference/ contains hand-computed
  cutlist-rozrys.csv, bom.csv and cnc-d60.txt for the D60 M+C+C cabinet"
- "exercises/walking-skeleton-d60/generated/ contains pipeline-produced
  rozrys CSV, BOM and CNC TXT for the same cabinet, plus the extracted
  kitchen JSON"
- "exercises/walking-skeleton-d60/GAP-REPORT.md lists every
  reference-vs-pipeline mismatch, each either accepted-as-convention or
  filed as a ledger claim id"
