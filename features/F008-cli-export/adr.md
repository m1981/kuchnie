# ADR — F008 — `kitchen-cli` Binary, MachiningFeature Model, Data-Driven Pattern Resolution

**Date:** 2026-06-28
**Status:** `Proposed`
**Feature:** F008
**Author:** solo dev

---

## Context

F008 is the manufacturing closer. It is where the kitchen domain becomes CSV rows the CNC company accepts, DXF panels the saw operator loads, drill coordinates the boring machine reads, and a PLN cost estimate the carpenter uses to negotiate. Three structural pressures shape it:

1. **Polish CNC pricing model is one-shot.** Vendors require material commitment *before* quoting. We must produce our own cost estimate (with waste factor) prior to vendor contact — otherwise we lose negotiation leverage and risk over-ordering.

2. **F002 deferred drill-pattern resolution.** F002's `Recipe` emits `DrillPatternRef` strings (`"system32"`, `"hinges_3"`); the actual hole positions remained unresolved. F008 is where named patterns become concrete `MachiningFeature` instances with coordinates derived from formula evaluation against the panel's actual dimensions and the project's `ConstructionMethod`.

3. **Existing CAD code is partly built.** `kitchen-cad/src/kitchen_cad/csv_generator.py`, `drill_engine.py`, and `generators/legrabox_side_panel.py` already exist — code-driven, ad-hoc, not data-driven. F008 reconciles them: same outputs, new data-driven framework.

The legacy `MachiningOp` in `src/kuchnie_core/model.py` is structurally inadequate for what F008 needs (no tool spec, no operation order, no provenance). A new `MachiningFeature` belongs in CAD because it carries CAD-specific concerns (CNC tool specs, machining order, cutter diameter); Core only ever needs the pattern *reference* string.

The decision needs to be made **now** because: (1) F007 already committed to contributing its `render` subcommand to F008's CLI binary; the subcommand registry contract must be stable; (2) the MachiningFeature/MachiningOp split affects the v1.0 schema commitments locked in by F001; (3) every export-format choice (CSV columns, DXF layers, encoding) needs to be set before the carpenter validates with a sample upload to their CNC company.

---

## Decision

We will introduce `kitchen-cli` as a single binary owned by F008, with subcommands `cut-list`, `drill-pattern`, `dxf`, `bom`, `cost-estimate`, `export-all` (plus `render` registered by F007). The binary lives at `kitchen-cad/src/kitchen_cad/cli/main.py` and uses `typer` (or `click`) as the CLI framework.

`MachiningFeature` is introduced as an immutable dataclass in `kitchen-cad/src/kitchen_cad/features/feature.py`, carrying tool spec, face, position, operation order, and pattern provenance. It **replaces** `kuchnie_core/model.py::MachiningOp` in new code. Legacy `MachiningOp` is **deprecated** (warning, not removed) and the glossary entry is marked legacy with a pointer to `MachiningFeature`.

Patterns are stored as YAML in `kitchen-cad/patterns/*.yaml` (matching the recipe/template/method storage pattern). `PatternResolver` reads pattern definitions, evaluates position formulas using F002's safe `asteval` evaluator, and emits `list[MachiningFeature]` for a given panel + construction method. Five patterns ship in F008: `system32`, `hinges_2`, `hinges_3`, `handle_center`, `dowel_camlock_side`.

Three exporters ship: `CutListExporter` (CSV; e-rozkroj-compatible columns subject to implementation-time verification), `DrillPatternExporter` (CSV), `DXFExporter` (one DXF per panel using `ezdxf`, with layer conventions for outline, drilling per face, grooves, rabbets, edge banding, and annotation text).

Every exporter subcommand invokes F004's `CAMReadinessGate` (Gate 4) before writing files. ERROR refuses output; a `--force` flag overrides with stderr warning and `_OVERRIDE` filename annotation.

`CostEstimator` (Should-have) ships waste-factor-aware cost calculation per material category, in PLN, net only, defaulting to 0.18 sheet / 0.10 edge / 0.05 hardware.

Existing legacy generators (`csv_generator.py`, `drill_engine.py`, `generators/legrabox_side_panel.py`) are **subsumed** with thin wrappers + deprecation warnings, not removed. Full removal is backlog.

The `kitchen-cli` binary, the `MachiningFeature` model, the pattern YAML format, and the export file formats become CAD's published surface.

---

## Alternatives Considered

| Option | Why rejected |
|---|---|
| **A. No CLI; export from Reflex (Web app) only** | Web app is for design; manufacturing pipeline runs headless. Carpenter wants `kitchen-cli export-all` to produce a folder, ready to ship. Coupling to a UI loop is the wrong abstraction. |
| **B. Each export format as its own binary** (`kitchen-cut-list`, `kitchen-drill`, `kitchen-dxf`) | More binaries to install, more code duplication for argument parsing, more friction. Single binary with subcommands is the standard pattern. |
| **C. Keep `MachiningOp`; extend it instead of introducing `MachiningFeature`** | `MachiningOp` is a Core type; growing it with tool diameter, operation order, formula provenance bloats Core with CAM concerns. `MachiningFeature` belongs in CAD; clear separation. |
| **D. Hardcode patterns in Python** (extend `drill_engine.py::apply_system32`, etc.) | Already the current pattern — code-driven, hard to extend without a release, opaque to carpenters who want to tune drilling for their CNC machine. Data-driven YAML matches our other choices (recipes, templates, methods). |
| **E. Compute MachiningFeatures at recipe-emit time and store on `Panel`** | Couples F002 (engine) to F008 (machining). F002 specifically deferred this. Panel stays serializable; features computed on demand. |
| **F. SVG instead of DXF** | CNC vendors don't accept SVG. DXF is the established interchange format. |
| **G. STEP / IGES / glTF output** | 3D solid formats for assembly review. Sheet-goods CNC uses 2D DXF. STEP is post-v1.0 if needed. |
| **H. Generate G-code directly** (skip DXF, send to CNC machine) | We don't run the CNC; the vendor does. G-code is their CAM software's output, not ours. |
| **I. Use openpyxl / XLSX as the cut list format** | CSV is the universal exchange format CNC software accepts. XLSX is a Could (for carpenter-friendly review). |
| **J. Combine cut list + drill + DXF into a single ZIP / archive** | CNC vendors expect separate files for separate tools (saw operator gets CSV; CNC operator gets DXF). Separation is functional, not arbitrary. |
| **K. Auto-upload to CNC vendor's web portal** | Out of scope. Manual upload is the workflow; automation requires per-vendor APIs that don't exist. |
| **L. Replace `ezdxf` with custom DXF writer** | `ezdxf` is mature, maintained, and already used in legacy `legrabox_side_panel.py`. Custom writer is reinvention. |
| **M. Cost estimator in `kuchnie_core/` (Core)** | Pricing knowledge (PLN, waste factors, sheet rounding, edge meters) is manufacturing-specific. Core stays domain-only. CAD owns the estimator; F006 imports it for UI display. |
| **N. Cost estimator with VAT / multi-currency** | Out of scope. Net PLN only in v1.0. Backlog when serving non-Polish customers or generating invoices. |
| **O. Cache exported files keyed by kitchen hash** | Re-export is cheap (seconds). Cache invalidation depends on inputs across multiple contexts (decor texture, pattern YAML, recipe YAML, gate output) — not worth tracking. |
| **P. Move `kuchnie_core/bom.py` into CAD** | BOM (panels + materials + accessories list) is domain truth, not CAM. Core owns it; CAD's CLI just formats and prints. |
| **Q. Remove legacy `csv_generator.py`, `drill_engine.py`, `generators/legrabox_side_panel.py` in F008** | Deprecation + subsume now, removal as backlog. Removing them is a separate cleanup feature; mixing it with F008 risks breaking F002's quarantined fallback path. |
| **R. CLI library: custom argparse instead of typer/click** | Custom argparse for ~10 subcommands is tedious. typer is the modern choice; click is the established choice. Either works; argparse is unnecessary friction. |
| **S. JSON instead of CSV for cut list** | CNC vendor software reads CSV. JSON is a Could (for tooling integration). |
| **T. Hardcode waste factors** | Different cabinet styles have different cutting losses (corner cabinets waste more; simple bases waste less). Configurable per category with defaults is the right balance. |
| **U. PatternResolver detects collisions** (two drills at the same position) | Real bug, but rare. Adds graph-traversal complexity. Backlog as a Gate 4 check rather than a resolver responsibility. |
| **V. Strict CAM `--force` flag does NOT mark filenames** | Then "override" runs leak into vendor uploads with no trace. `_OVERRIDE` annotation in filenames + stderr warning is cheap insurance. |
| **W. Allow rolling back from CSV edits to YAML** | One-way pipeline. YAML is truth; CSV is output. Round-trip would require either YAML regeneration logic (complex) or accepting CSV as a second truth (worse). |
| **X. Per-vendor DXF dialect presets in v1.0** (HOMAG, Felder, Holzma) | Premature optimization. Ship generic R2018 DXF; the carpenter validates with their actual vendor. If a dialect difference is found, address with a config override. Per-vendor presets is Could. |
| **Y. F008 owns the `render` subcommand too** (full ownership inside CAD) | Renders use Blender; Blender belongs to the Render context (F007). F007 contributes the subcommand registration; F008 just provides the binary's plugin point. Bounded contexts stay clean. |

---

## Consequences

### Positive
- **One binary, one workflow.** `kitchen-cli export-all` is the carpenter's daily verb.
- **MachiningFeature is associative.** Pattern resolution is re-runnable; resizing a cabinet automatically gets new drill coordinates. This is the TopSolid pattern realized.
- **Patterns are data, not code.** A carpenter switching CNC machines (different drilling system) tunes a YAML, not a Python file.
- **MachiningOp deprecation is graceful.** Existing fixtures continue to work with a warning; new code uses `MachiningFeature`. No flag day.
- **Cost estimator preserves negotiation.** Carpenter knows the floor before the vendor names a number.
- **Gate 4 is the export gatekeeper.** Strict-CAM rule (WARNINGs as ERRORs) prevents the 6pm-Friday-from-CNC phone call.
- **CLI binary supports future subcommands.** F007's `render` is the proof; new tools (e.g., `kitchen-cli pack-for-customer` producing a customer summary) slot in via the same registry.
- **e-rozkroj column schema is config, not code.** Implementation-time adjustment is localized.

### Negative
- **CSV column schema is provisional at planning time.** Requires the carpenter to verify against their CNC company's sample before integration testing passes. Mitigated by structuring the exporter to accept the column set as config.
- **Two parallel CAM code paths exist transiently.** Legacy `drill_engine.py` and new `pattern_resolver.py` coexist. Forward path: legacy callers migrate; removal is backlog. Risk: a maintainer might add a check to one path and not the other. Mitigated by deprecation warnings on every legacy call.
- **`--force` is a foot-gun.** Override exists for known-acceptable warnings, but a careless `--force` could ship invalid files. Mitigated by `_OVERRIDE` filename annotation + stderr warning.
- **Cost estimator depends on catalog prices being accurate.** If catalog YAMLs lack price fields, the estimator returns partial results. F005 didn't make prices a Must (out of scope); F008 estimator handles missing prices gracefully (logs WARN, returns partial cost).

### Neutral
- **CLI binary becomes the install surface.** Solo dev installs once via pip / pipx; subcommands are discovered automatically.
- **`ezdxf` becomes a hard CAD dependency.** Lightweight and mature; no concern.
- **Polish-character encoding is UTF-8-BOM** for CSV. Standard Excel-compatible choice; verified against typical Polish CNC vendor expectations.
- **`MachiningOp` lives on as legacy.** Glossary marks it; new code shouldn't see it; removal is backlog.

---

## Affected Files (canonical)

### Created
- `kitchen-cad/src/kitchen_cad/cli/__init__.py`
- `kitchen-cad/src/kitchen_cad/cli/main.py` — entry point + subcommand registry
- `kitchen-cad/src/kitchen_cad/cli/cut_list_cmd.py`
- `kitchen-cad/src/kitchen_cad/cli/drill_pattern_cmd.py`
- `kitchen-cad/src/kitchen_cad/cli/dxf_cmd.py`
- `kitchen-cad/src/kitchen_cad/cli/bom_cmd.py`
- `kitchen-cad/src/kitchen_cad/cli/cost_estimate_cmd.py` (Should)
- `kitchen-cad/src/kitchen_cad/cli/export_all_cmd.py` (Should)
- `kitchen-cad/src/kitchen_cad/features/__init__.py`
- `kitchen-cad/src/kitchen_cad/features/feature.py` — `MachiningFeature`, enums
- `kitchen-cad/src/kitchen_cad/features/pattern.py` — `Pattern`, `OperationSpec`, `PositionFormula`
- `kitchen-cad/src/kitchen_cad/features/pattern_registry.py`
- `kitchen-cad/src/kitchen_cad/features/pattern_resolver.py`
- `kitchen-cad/src/kitchen_cad/exporters/__init__.py`
- `kitchen-cad/src/kitchen_cad/exporters/cut_list_csv.py`
- `kitchen-cad/src/kitchen_cad/exporters/drill_pattern_csv.py`
- `kitchen-cad/src/kitchen_cad/exporters/dxf_exporter.py`
- `kitchen-cad/src/kitchen_cad/cost/__init__.py` (Should)
- `kitchen-cad/src/kitchen_cad/cost/estimator.py` (Should)
- `kitchen-cad/patterns/system32.yaml`
- `kitchen-cad/patterns/hinges_2.yaml`
- `kitchen-cad/patterns/hinges_3.yaml`
- `kitchen-cad/patterns/handle_center.yaml`
- `kitchen-cad/patterns/dowel_camlock_side.yaml`
- `tests/cad/features/test_feature_model.py`
- `tests/cad/features/test_pattern_registry.py`
- `tests/cad/features/test_pattern_resolver.py`
- `tests/cad/exporters/test_cut_list_csv.py`
- `tests/cad/exporters/test_drill_pattern_csv.py`
- `tests/cad/exporters/test_dxf_exporter.py`
- `tests/cad/cli/test_main.py`
- `tests/cad/integration/test_full_export_pipeline.py`
- `tests/cad/integration/test_cam_gate_blocks_export.py`
- `tests/cad/integration/test_force_override.py`
- `tests/cad/integration/fixtures/expected_nowak_cuts.csv`
- `tests/cad/integration/fixtures/expected_nowak_drills.csv`
- `docs/cli.md` — carpenter-facing CLI reference

### Modified
- `src/kuchnie_core/model.py::MachiningOp` — add deprecation warning + docstring pointer to `MachiningFeature`
- `kitchen-cad/src/kitchen_cad/csv_generator.py` — thin wrapper around new exporter + deprecation warning
- `kitchen-cad/src/kitchen_cad/drill_engine.py` — thin wrapper around `PatternResolver` + deprecation warning
- `kitchen-cad/generators/legrabox_side_panel.py` — replaced by `legrabox_side.yaml` pattern + generic DXF exporter; legacy script kept with deprecation note
- `kitchen-cad/example_generate.py` — refactored into integration test
- `docs/GLOSSARY.md` — ~14 new/refined entries
- `docs/01_architecture.md` — show CLI binary + F007 contribution to subcommand registry
- `docs/03_implementation_placement.md` § Pattern 6 — link to F008 ADR

### Deleted or stubbed
- None in F008. Full removal of legacy generators is backlog.

---

## LLM Hints

> Direct instructions for future LLM sessions in this decision area.

- **When asked "should we nest panels ourselves?"** → **No.** CNC vendor does it. We provide the cut list; they produce the nest. Our waste factor is a *pre-nest estimate*, not a layout. See spec Won't list.
- **When asked "where do machining features live as data?"** → `kitchen-cad/patterns/*.yaml`. Data-driven, matches recipes/templates/methods.
- **When asked "should `MachiningFeature` live in Core?"** → **No.** Carries CAM concerns (tool diameter, operation order). Core stores only the pattern *reference* string. See Alternative C.
- **When asked "should we keep extending `MachiningOp`?"** → **No.** Deprecated. New code uses `MachiningFeature`. See Alternative C.
- **When asked "should we store MachiningFeatures on Panel?"** → **No.** Computed on demand by `PatternResolver`. Panel keeps only `drilling_refs`. See Alternative E.
- **When asked "Should F008 own the `render` subcommand?"** → **No.** F007 contributes `render` to F008's binary via a registry. Bounded contexts stay clean. See Alternative Y.
- **When asked "DXF or SVG or STEP?"** → DXF (R2018). SVG isn't accepted by CNC. STEP is 3D, not for sheet-goods cutting. See Alternatives F, G.
- **When asked "Can we replace `ezdxf` with custom DXF code?"** → **No.** Mature library. See Alternative L.
- **When asked "Should we cache exports?"** → **No.** Re-export is cheap. See Alternative O.
- **When asked "cost estimator location?"** → CAD, not Core. F006 imports it for UI display. See Alternative M.
- **When asked "should we add VAT or multi-currency?"** → Not in v1.0. PLN net only. See Alternative N.
- **When asked "single binary or one per export?"** → **Single binary, subcommands.** See Alternative B.
- **When asked "should we accept CSV edits and round-trip to YAML?"** → **No.** One-way pipeline. See Alternative W.
- **When asked "should we delete the legacy `csv_generator.py` / `drill_engine.py`?"** → **No** in F008. Deprecation + subsume only. Removal is backlog. See Alternative Q.
- **When asked "should patterns detect drill collisions?"** → Not in F008. Backlog as a Gate 4 check. See Alternative U.
- **When asked "should we add per-vendor DXF dialects (HOMAG, Felder)?"** → **No** in v1.0. Generic R2018 DXF; per-vendor is Could. See Alternative X.
- **When asked "CLI library: typer, click, argparse?"** → typer or click. Argparse is unnecessary friction. Final choice deferred. See Alternative R.
- **When asked "Should `--force` skip Gate 4 silently?"** → **No.** `_OVERRIDE` filename annotation + stderr warning. See Alternative V.
- **When asked "Should `kuchnie_core/bom.py` move to CAD?"** → **No.** BOM is domain truth. CAD's CLI is a formatter. See Alternative P.
- **When asked "Should the exporter support strict per-vendor column schemas?"** → CSV column schema is config, not code. Adjust at implementation per the carpenter's actual CNC company sample. See spec Q1.
- **Do not propose:**
  - Building a nesting optimizer.
  - Adding CNC machine control / G-code generation.
  - Adding HTTP-based vendor submission.
  - Adding inventory tracking.
  - Adding multi-currency or VAT.
  - Moving cost estimation into Core.
  - Removing legacy generators in F008 (backlog).
  - Replacing the recipe engine's `asteval` evaluator with anything else (reuse F002's choice).
- **Related ADRs:**
  - **F001 (Construction Method)** — pattern resolver reads `system32_offset_mm`, `front_overlay_mm`, etc., from the project's construction method.
  - **F002 (Recipe Engine)** — recipes emit `DrillPatternRef` strings; F008 resolves them. The contract: F002 → string reference; F008 → concrete features.
  - **F004 (Validation Gates)** — Gate 4 (CAMReadinessGate) is the export gatekeeper. Strict-CAM rule applies. F008 may register additional checks (e.g., "no two patterns at same position" — backlog).
  - **F005 (Material Resolver)** — exporters read `ResolvedMaterial.sheet_size_mm` for waste calc; `paired_edge_id` for edge meter calc.
  - **F006 (Web Sidebar)** — imports `CostEstimator` for sidebar price display. Does not import exporters.
  - **F007 (Blender Adapter)** — registers `render` subcommand into F008's `kitchen-cli` binary at install time.

---

## Sign-off

- [ ] `docs/GLOSSARY.md` updated with ~14 entries (MachiningFeature promoted; MachiningOp marked legacy).
- [ ] `kitchen-cli` binary installs and runs all Must subcommands.
- [ ] 5 pattern YAMLs shipped; `PatternResolver` evaluates each correctly against test fixtures.
- [ ] Cut list, drill, DXF exporters all produce output for `examples/kitchen_nowak.yaml`.
- [ ] Integration tests pass; expected fixtures committed.
- [ ] Gate 4 invocation blocks invalid exports; `--force` produces `_OVERRIDE` files with stderr warning.
- [ ] `MachiningOp` deprecation warning fires on construction; glossary marks legacy.
- [ ] Legacy `csv_generator.py`, `drill_engine.py`, `legrabox_side_panel.py` wrapped with deprecation; still functional.
- [ ] `docs/cli.md` published.
- [ ] `docs/03_implementation_placement.md` § Pattern 6 links to this ADR.
- [ ] F007 confirmed: `render` subcommand registers successfully into the binary.
- [ ] Status moved from `Proposed` → `Accepted` after first green integration test run.
