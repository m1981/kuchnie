# Status — F008

> **Machine-readable.** Agents can grep all `status.md` files to build a dashboard.

```yaml
feature_id: F008
title: "CLI Manufacturing Export (Cut List, Drill, DXF) + Cost Estimator"
status: proposed                  # not started — Phase 8 begins after F007 closes
phase: 8
primary_context: cad              # single bounded context
touched_contexts:
  - cad                           # owns CLI binary, MachiningFeature, exporters, cost estimator
  # MachiningOp deprecation in Core is additive (warning + docstring); not a true cross-context edit.

started: null
completed: null
blocked_by:
  - F001                          # ConstructionMethod fields drive pattern resolution
  - F002                          # F008 fills F002's DrillPatternRef resolution
  - F004                          # Gate 4 invoked before every export
  - F005                          # exporters read sheet_size_mm, paired_edge_id from ResolvedMaterial
supersedes:
  - "kitchen-cad/src/kitchen_cad/csv_generator.py (legacy, deprecated, kept as wrapper)"
  - "kitchen-cad/src/kitchen_cad/drill_engine.py (legacy, deprecated, kept as wrapper)"
  - "kitchen-cad/generators/legrabox_side_panel.py (legacy one-off, replaced by pattern YAML)"
  - "kitchen-cad/example_generate.py (legacy script, refactored into integration test)"
deprecates_but_does_not_remove:
  - "src/kuchnie_core/model.py::MachiningOp (deprecated; new code uses MachiningFeature)"
superseded_by: null

spec_status: ready                # all 15 Open Questions in spec.md answered
adr_status: proposed              # accepted on first green integration test run
adr_needed: true

owns_subcommand_registry:         # F007 contributes 'render' via this registry
  - cut-list                      # F008
  - drill-pattern                 # F008
  - dxf                           # F008
  - bom                           # F008
  - cost-estimate                 # F008 Should
  - export-all                    # F008 Should
  - render                        # F007 contributed
  - validate                      # F004 Should surfaced here
  - list-decors                   # F005 Should surfaced here
  - list-templates                # F003 Should surfaced here

fulfills_deferred_promises:
  F002:
    - "DrillPatternRef resolution to concrete MachiningFeatures (PatternResolver)"
  F004:
    - "Gate 4 invocation as export gatekeeper (strict-CAM enforcement)"
  F007:
    - "Subcommand registry for render binary contribution"

glossary_terms_introduced:
  - MachiningFeature              # promote placeholder → concrete; replaces MachiningOp
  - FeatureType                   # new enum
  - Face                          # new enum (panel face for machining)
  - Pattern                       # new
  - PatternRegistry               # new
  - PatternResolver               # new
  - OperationSpec                 # new
  - PositionFormula               # new
  - CutListExporter               # new
  - DrillPatternExporter          # new
  - DXFExporter                   # new
  - CostEstimator                 # new (if Should lands)
  - WasteFactor                   # new term
  - CutPiece                      # promote placeholder → concrete

glossary_terms_marked_legacy:
  - MachiningOp                   # legacy; new code uses MachiningFeature; not removed in F008

last_updated: 2026-06-28
last_updated_commit: "bootstrap"
```

---

## Current Activity

**Not started.** Blocked on F001, F002, F004, F005 close (Phases 1, 2, 4, 5 gates).

> Note: F003 (Template Registry) is **not** a blocker — F008 reads `CabinetInstance` directly, regardless of how it was created.
>
> Note: F006 (Web Sidebar) is a downstream consumer, not a blocker.
>
> Note: F007 (Blender Adapter) registers its `render` subcommand into F008's binary at install time. F007 and F008 are mutually independent for implementation: F008's binary must publish a subcommand registry that F007 calls. The registration is at module-import time inside the installed package, not a runtime cross-process call.

When all four direct blockers close (Phase 7 gate passed), promote this feature's status to `in_progress` and write `tasks.md`. Spec and ADR are complete and reviewed.

---

## Blockers

- **F001 — Construction Method.** Pattern resolver reads `system32_offset_mm`, `front_overlay_mm`, `back_recess_mm`, etc. from the project's `ConstructionMethod`. Without F001, formulas cannot evaluate.
- **F002 — Recipe Engine.** Recipes emit `DrillPatternRef` strings ("system32", "hinges_3") and `DecompositionResult` with panels. F008 fills F002's deferred pattern resolution. Without F002, there are no panels to export.
- **F004 — Validation Gates.** Every exporter subcommand calls Gate 4 (CAMReadinessGate) before writing files. Strict-CAM rule (WARNINGs promoted to ERRORs) is the export gatekeeper. Without F004, F008 has no validation discipline.
- **F005 — Material Resolver.** Exporters read `ResolvedMaterial.sheet_size_mm` for cut list & cost waste calculation; `paired_edge_id` for edge banding linear-meter calculation. Without F005, materials cannot be looked up.

---

## Critical Decisions Embedded in F008

> Future LLM sessions should treat these as locked, not topics to revisit.

| Decision | Locked in by |
|---|---|
| `kitchen-cli` is a single binary with subcommands | ADR Alternative B |
| F008 owns the binary; F007 contributes `render` via subcommand registry | ADR Alternative Y + spec Q11 |
| `MachiningFeature` lives in CAD; `MachiningOp` deprecated, not removed | ADR Alternative C, Q + spec § Legacy reconciliation |
| Patterns as YAML data + safe-evaluator engine | ADR Alternative D |
| MachiningFeatures computed on demand, not stored on Panel | ADR Alternative E + spec Q7 |
| One DXF per panel; per-cabinet aggregation is Should | spec Q2 |
| ezdxf library; no custom DXF writer | ADR Alternative L |
| Gate 4 is the export gatekeeper; `--force` overrides with `_OVERRIDE` filename + stderr | ADR Alternative V + spec Q8 |
| Cost estimator in CAD (not Core); F006 imports it | ADR Alternative M + P |
| PLN net only; no VAT, no multi-currency in v1.0 | ADR Alternative N |
| CSV column schema is config (not code); verify with carpenter's CNC company at impl time | spec Q1 |
| Legacy generators subsumed via wrappers + deprecation; full removal is backlog | ADR Alternative Q |
| No nesting optimization (CNC company does it) | ADR Decision + Won't list |

---

## Decision Log (in-flight)

> Promote to ADR if any decision affects more than this feature.

- _(empty until work starts)_
