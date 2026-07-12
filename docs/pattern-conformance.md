# Pattern conformance — commercial-CAD patterns vs what's built

> Reader: owner judging how far the codebase implements the five
> commercial-system patterns identified in `docs/vision/01-user-journeys.md`
> | Enables: reading each pattern's real status from live ledger claims
> instead of remembered percentages | Update-trigger: a cited claim dies or
> a pattern's implementation status changes

Facts appear only as ledger ids (spec convention); the id is authoritative,
the hook text is courtesy. Verified 2026-07-12 against source.

| # | Pattern (source system) | Status | Evidence | Gap |
|---|---|---|---|---|
| 1 | Cabinet macros (PRO100) | Delegated to plugin | ADR-009 — hb5 owns parametric cabinets; adapter is the ACL | none (by design) |
| 2 | Construction Method (Polyboard) | Mostly built | tr-56212df8 — first-class registry entity; joinery is one flat string | no per-joint `JoinerySpec` |
| 3 | Sub-product hierarchy (Winner Flex) | Deliberately flatter | tr-0e4f1897 — zero bay/opening/splitter entities; ADR-001 panel-is-atom | intentional; revisit only if openings become first-class |
| 4 | Feature operations (TopSolid) | Mostly built | tr-168bad10 — MachiningOp + face/drill_type, cam appliers, legrabox runner/confirmat/groove | groove in `dolna_legrabox` only; no drill-list export |
| 5 | Object-in-room (PaletteCAD) | Delegated to plugin | ADR-009 — placement/room stays in hb5 | none (by design) |
| 6 | Panel formula engine | Built, unwired | tr-fc74bc2e — `recipe.py` has no decomposer consumer; erp runs its own JSON recipes | wire decomposers or retire one engine |
| 7 | Material ≠ Construction | Clean | tr-9b296c35 — construction.py material-free; MaterialCatalog Protocol | none |
| 8 | Validation gates | Scattered | tr-00421995 — validate fns in 5+ modules, no ordered gate runner | pipeline-organize (candidate: L-playbook Phase-8 gate) |
| 9 | File structure | Flat, pragmatic | directly observable: `kuchnie_core/` flat modules + `export/`, `materials/` subpackages | none worth acting on |
| 10 | Plugin extension IO | Extraction only | tr-50c8f148 — no writer back into hb5 scenes | bidirectional IO is a scope decision (L1 Q10) |

Rows 6, 8 and 10 are the actionable ones; 6 and 8 are engineering debt,
10 is the Stage-2 investment fork already posed in the L1 questionnaire.
