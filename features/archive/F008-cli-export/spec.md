# F008 — CLI Manufacturing Export (Cut List, Drill, DXF) + Cost Estimator

## Job Story

**When** the customer has accepted the layout and decors, and I have tweaked the kitchen YAML for obstacles, vent holes, and LED grooves,
**I want to** run `kitchen-cli cut-list`, `kitchen-cli drill-pattern`, and `kitchen-cli dxf` to produce files my Wrocław CNC company accepts (e-rozkroj / e-rozrys CSV, panel DXFs with edge banding and machining layers), plus `kitchen-cli cost-estimate` for a waste-adjusted estimate I can use to negotiate before committing materials,
**So I can** ship a complete production package in one command, refuse to ship anything that doesn't pass CAM-Readiness Gate 4, and get my own cost estimate before the CNC company quotes — without using their system back-and-forth.

---

## Bounded Context

- **Primary (the one that OWNS this):** `CAD` (`kitchen-cad/`).
- **Touched (consumers / dependencies, must have explicit reason):**
  - `kuchnie_core` — read-only consumer of `Kitchen`, `CabinetInstance`, `DecompositionResult` (via F002 engine), `MaterialResolver` (via F005), and `CAMReadinessGate` (F004).
  - **Owns** the `kitchen-cli` binary entry point (F007 contributes the `render` subcommand here).
  - **Owns** the `MachiningFeature` concept and `PatternResolver` (resolves F002's `DrillPatternRef`s).
  - **Deprecates** legacy `kuchnie_core/model.py::MachiningOp` (kept with deprecation warning; replaced by `MachiningFeature` in CAD).

> **Change Locality Test result:** one bounded context (CAD). Deprecating `MachiningOp` is a Core touch but is **additive** (annotation + warning, no removal). The CLI binary is a single entry point owned here, contributed to by F007. ✅ Passes.

---

## Subdomain Classification

- [x] **Core** — competitive advantage. The format compatibility with Polish CNC vendors (e-rozkroj, e-rozrys, HOMAG-friendly DXF), the cost estimator that runs *before* the CNC quote, and the associative MachiningFeature model are exactly the leverage points where a solo Wrocław carpenter beats PRO100's import/export workflow.
- [ ] Supporting
- [ ] Generic

**Reasoning:** Polish CNC vendors enforce a one-shot pricing model (carpenter commits material before quote). Owning the cost estimator lets the carpenter negotiate. Owning the file formats means zero "convert this for me" friction. This is core competitive advantage.

---

## Data Ownership

- **Canonical writes happen in:**
  - CLI entry: `kitchen-cad/src/kitchen_cad/cli/main.py`
  - Subcommand implementations: `kitchen-cad/src/kitchen_cad/cli/<cmd>_cmd.py`
  - MachiningFeature model: `kitchen-cad/src/kitchen_cad/features/feature.py`
  - PatternResolver: `kitchen-cad/src/kitchen_cad/features/pattern_resolver.py`
  - Pattern definitions: `kitchen-cad/patterns/*.yaml`
  - Cut list CSV exporter: `kitchen-cad/src/kitchen_cad/exporters/cut_list_csv.py`
  - Drill pattern CSV exporter: `kitchen-cad/src/kitchen_cad/exporters/drill_pattern_csv.py`
  - DXF exporter: `kitchen-cad/src/kitchen_cad/exporters/dxf_exporter.py`
  - Cost estimator: `kitchen-cad/src/kitchen_cad/cost/estimator.py`
- **Read-only consumers:**
  - F006 (Web Sidebar) imports the cost estimator module to display cost in the UI; it does NOT import exporters (Web doesn't show CSVs).
  - F007 (Render Adapter) registered its `render` subcommand with the same CLI binary.
- **Storage:** Pattern definitions are YAML in git. CLI outputs are files at user-specified paths. No persistent storage in F008 itself.

---

## Reconciliation with Existing Code

> **F008 is partly a consolidation feature.** Existing code in `kitchen-cad/` (per the `all.md` snapshot):

- `kitchen-cad/src/kitchen_cad/csv_generator.py` — has `generate_cutting_csv` and `generate_edging_csv` (legacy format).
- `kitchen-cad/src/kitchen_cad/drill_engine.py` — has `apply_system32`, `apply_hinges`, `apply_handles`, `apply_all_drilling`.
- `kitchen-cad/generators/legrabox_side_panel.py` — one-off DXF generator for legrabox sides.
- `kitchen-cad/example_generate.py` — example script using the above.

**F008's reconciliation strategy:**

| Legacy file | Action in F008 |
|---|---|
| `csv_generator.py` | Subsume into `exporters/cut_list_csv.py` with the verified e-rozkroj column schema. Old function names kept as thin wrappers with deprecation warnings. |
| `drill_engine.py` | Subsume `apply_system32` / `apply_hinges` / `apply_handles` into `features/pattern_resolver.py`. The new resolver is data-driven (YAML patterns) rather than code-driven (hardcoded functions). |
| `generators/legrabox_side_panel.py` | Becomes one of the pattern YAMLs (legrabox profile) + the new generic DXF exporter handles it. Old one-off script kept as reference. |
| `example_generate.py` | Refactor into `tests/cad/integration/test_full_export_pipeline.py`. Same scenario, now a test. |

This reduces ad-hoc generators to YAML data + one generic exporter per format.

---

## Scope — MoSCoW

### Must (do not ship without)

#### CLI binary (F008 owns)

- [ ] `kitchen-cli` entry point at `kitchen-cad/src/kitchen_cad/cli/main.py`.
- [ ] Library choice: `typer` (modern, type-driven; alternative `click`). Decide at implementation time; final choice is local to F008.
- [ ] Subcommand registry pattern so F007 can register `render` without F008 importing render code.
- [ ] Global flags: `--verbose`, `--quiet`, `--no-color`, `--config-dir`.
- [ ] Standard exit codes: 0 success, 1 validation error, 2 user error (bad args), 3 system error (missing file, no Blender, etc.).

#### MachiningFeature model

- [ ] `kitchen-cad/src/kitchen_cad/features/feature.py`:
  - [ ] `FeatureType` enum: `DRILL`, `GROOVE`, `RABBET`, `NOTCH`, `POCKET`, `CUTOUT`.
  - [ ] `Face` enum: `FRONT`, `REAR`, `LEFT`, `RIGHT`, `TOP`, `BOTTOM`, `INNER`, `OUTER`.
  - [ ] `MachiningFeature` dataclass (frozen): `id: str`, `feature_type: FeatureType`, `face: Face`, `position_mm: tuple[float, float]`, `tool_diameter_mm: float`, `tool_depth_mm: float`, `operation_order: int`, `pattern_ref: str | None` (provenance — which pattern generated it).
- [ ] `kitchen-cad/src/kitchen_cad/features/pattern_resolver.py`:
  - [ ] `Pattern` Pydantic model: `pattern_id`, `description`, `operations: list[OperationSpec]`.
  - [ ] `OperationSpec`: `feature_type`, `face`, `position_formula`, `tool_spec`.
  - [ ] `PositionFormula`: declarative — either `grid` (x_offsets + y_spacing) or `points` (list of x/y formulas).
  - [ ] `PatternRegistry` — loads YAMLs from `kitchen-cad/patterns/`.
  - [ ] `PatternResolver.resolve(pattern_ref: str, panel: Panel, context: ConstructionMethod) -> list[MachiningFeature]` — evaluates position formulas against panel dims + construction params.
  - [ ] Reuses F002's safe formula evaluator (`asteval` already a CAD dependency).

#### Pattern YAMLs (at least 5)

- [ ] `kitchen-cad/patterns/system32.yaml` — System 32 grid for cabinet sides.
- [ ] `kitchen-cad/patterns/hinges_2.yaml` — 2-hinge boring for short doors.
- [ ] `kitchen-cad/patterns/hinges_3.yaml` — 3-hinge boring for tall doors.
- [ ] `kitchen-cad/patterns/handle_center.yaml` — center-mounted handle (configurable spacing).
- [ ] `kitchen-cad/patterns/dowel_camlock_side.yaml` — joinery drilling for sides (matches `JoineryType.DOWEL_CAMLOCK`).

#### Cut list CSV exporter

- [ ] `kitchen-cad/src/kitchen_cad/exporters/cut_list_csv.py`:
  - [ ] `CutListExporter.export(decomposition: DecompositionResult, output: Path) -> Path`.
  - [ ] Columns (placeholder schema; **verify against actual e-rozkroj docs at implementation time** — see Open Q1):
    - `panel_id`, `length_mm`, `width_mm`, `thickness_mm`, `quantity`,
    - `material_decor_id`, `material_name`, `material_sheet_size_mm`,
    - `edge_top`, `edge_bottom`, `edge_left`, `edge_right` (`edge_id` from `ResolvedMaterial.paired_edge_id`, or empty for no banding). **Resolution:** the recipe (F002) declares edges per panel side as role strings (e.g., `front_color`, `body_color`). F005's `MaterialResolver.resolve_role("front_color", cabinet)` resolves to a `ResolvedMaterial` whose `paired_edge_id` is the value written here. See F005 spec § Role String Conventions for the `_color` suffix convention.
    - `grain_direction` (longitudinal / transverse / none),
    - `cabinet_id`, `cabinet_template_id`, `recipe_role`,
    - `comment` (free text).
  - [ ] UTF-8 encoding with BOM (Excel compatibility).
  - [ ] Aggregation: identical panels (same material × dim × edges) combined with `quantity > 1`.

#### Drill pattern CSV exporter

- [ ] `kitchen-cad/src/kitchen_cad/exporters/drill_pattern_csv.py`:
  - [ ] `DrillPatternExporter.export(features: list[MachiningFeature], panels: list[Panel], output: Path) -> Path`.
  - [ ] Columns:
    - `panel_id`, `feature_id`, `feature_type`, `face`,
    - `x_mm`, `y_mm`, `depth_mm`, `diameter_mm`,
    - `operation_order`, `pattern_ref`.
  - [ ] One row per `MachiningFeature` (one drill = one row; groove and rabbet = one row with `feature_type` indicating).
  - [ ] Sorted by `panel_id`, then `face`, then `operation_order`.

#### DXF exporter

- [ ] `kitchen-cad/src/kitchen_cad/exporters/dxf_exporter.py`:
  - [ ] Library: **`ezdxf`** (already used in legacy `legrabox_side_panel.py`).
  - [ ] `DXFExporter.export_panel(panel: Panel, features: list[MachiningFeature], output: Path) -> Path` — one DXF per panel.
  - [ ] `DXFExporter.export_all(decomposition: DecompositionResult, output_dir: Path) -> list[Path]` — batch.
  - [ ] DXF layers:
    - `OUTLINE` — panel cut outline (closed polyline).
    - `DRILL_FRONT`, `DRILL_REAR`, `DRILL_INNER`, `DRILL_OUTER` — per-face drilling marks (circles with diameter).
    - `GROOVE` — groove paths.
    - `RABBET` — rabbet paths.
    - `EDGE_BAND_TOP`, `EDGE_BAND_BOTTOM`, `EDGE_BAND_LEFT`, `EDGE_BAND_RIGHT` — edge banding markers.
    - `TEXT_INFO` — panel name, material, cabinet ID as annotation text.
  - [ ] DXF block attributes: drill diameter, drill depth.
  - [ ] Configurable units (default mm; verify CNC vendor expectation).
  - [ ] R2018 DXF format (modern, broadly compatible).

#### BOM CLI

- [ ] `kitchen-cad/src/kitchen_cad/cli/bom_cmd.py`:
  - [ ] Reuses `kuchnie_core/bom.py` (existing).
  - [ ] Formats: `--format table` (default, human-readable), `--format json`, `--format csv`.
  - [ ] Groups: by material, by cabinet, flat.

#### CAM-Readiness gate invocation

- [ ] Every exporter command runs `CAMReadinessGate.validate(decomposition, ctx)` (F004 Gate 4) before writing files.
- [ ] On any ERROR (including promoted WARNINGs per F004's strict CAM rule): refuse to export, print issues, exit non-zero (1).
- [ ] On strict-CAM WARNING: refuse to export (Gate 4 has already promoted them to ERROR-equivalent).
- [ ] Override flag `--force` available for emergencies — **logs to stderr that override was used and embeds an OVERRIDE annotation in output filenames** (`cuts_OVERRIDE.csv`).

#### Legacy MachiningOp reconciliation

- [ ] `src/kuchnie_core/model.py::MachiningOp` annotated:
  ```python
  import warnings
  @dataclass
  class MachiningOp:
      """Legacy. Deprecated by kitchen_cad.features.feature.MachiningFeature.
      See ADR F008."""
      ...
      def __post_init__(self):
          warnings.warn(
              "MachiningOp is deprecated. Use kitchen_cad.features.MachiningFeature.",
              DeprecationWarning,
              stacklevel=2,
          )
  ```
- [ ] Glossary entry for `MachiningOp` updated with `Status: ⚠️ legacy — superseded by MachiningFeature (F008)`.
- [ ] `kuchnie_core/catalog.py` legacy decomposers (quarantined by F002) continue using MachiningOp — they're already deprecated paths; no double-migration needed.

#### Tests

- [ ] Unit tests:
  - [ ] `tests/cad/features/test_feature_model.py` — MachiningFeature construction, immutability.
  - [ ] `tests/cad/features/test_pattern_registry.py` — load patterns, lookup, missing pattern raises.
  - [ ] `tests/cad/features/test_pattern_resolver.py` — resolve System32 against a fixture panel, assert correct DrillPoint positions.
  - [ ] `tests/cad/exporters/test_cut_list_csv.py` — exports correct columns; aggregation works.
  - [ ] `tests/cad/exporters/test_drill_pattern_csv.py` — sorted output; correct face values.
  - [ ] `tests/cad/exporters/test_dxf_exporter.py` — DXF loads back with `ezdxf` and has expected layers + counts.
  - [ ] `tests/cad/cli/test_main.py` — CLI argument parsing, subcommand registration.
- [ ] Integration tests:
  - [ ] `tests/cad/integration/test_full_export_pipeline.py` — `examples/kitchen_nowak.yaml` → cut list + drill + DXF; all gates pass; files match committed expected fixtures.
  - [ ] `tests/cad/integration/test_cam_gate_blocks_export.py` — intentionally-invalid kitchen refuses to export, exit code 1.
  - [ ] `tests/cad/integration/test_force_override.py` — `--force` produces `_OVERRIDE` files and prints warning to stderr.

### Should (do if time permits)

- [ ] `kitchen-cli cost-estimate <kitchen.yaml> [--waste-factor 0.18] [--output cost.json]`:
  - [ ] `CostEstimator` in `kitchen-cad/src/kitchen_cad/cost/estimator.py`.
  - [ ] Material cost: panel area / sheet area × sheet price × (1 + waste factor), rounded up to whole sheets.
  - [ ] Edge banding cost: linear meters × per-meter price.
  - [ ] Accessory cost: from `cabinet.accessories` × catalog prices.
  - [ ] Configurable waste factor per material category (default 0.18 for sheet, 0.10 for edge, 0.05 for hardware).
  - [ ] Output in PLN (Polish złoty); net only (no VAT in v1.0).
  - [ ] Breakdown by category + total.
- [ ] `kitchen-cli export-all <kitchen.yaml> --output-dir output/`:
  - [ ] Batch: cut list + drill + DXFs + BOM + cost estimate, all in one directory.
- [ ] `kitchen-cli validate <kitchen.yaml>` (F004 Should-have surfaced here):
  - [ ] Run all four gates; print issues; exit code reflects severity.
- [ ] `kitchen-cli list-decors [--producer kronospan]` (F005 Should-have surfaced here).
- [ ] `kitchen-cli list-templates [--category base]` (F003 Should-have surfaced here).
- [ ] Configurable encoding per format (Windows-1250 for some legacy CNC software).
- [ ] Per-cabinet DXF aggregation: one DXF per cabinet (multi-panel layout).

### Could (almost certainly defer)

- [ ] HOMAG-specific DXF dialect support (additional layer naming conventions).
- [ ] XLS/XLSX output (using `openpyxl`) for non-technical readers.
- [ ] STEP / IGES export (3D solid format) for assembly review.
- [ ] Auto-upload to CNC vendor's portal (out of scope for solo dev).
- [ ] Watermarked customer-facing PDF summary.
- [ ] Multi-vendor preset bundles ("e-rozkroj profile", "Felder profile").
- [ ] Live recalculation watcher (`kitchen-cli watch <kitchen.yaml>`).

### Won't (this iteration — explicit cuts)

- ❌ **Nesting optimization.** The CNC company runs e-rozkroj's nesting on their end. We provide cut-list input; they produce the cut plan. Our waste factor is a *pre-nest* estimate, not a layout.
- ❌ **Material purchasing.** F008 estimates cost; the carpenter calls the supplier. No procurement integration.
- ❌ **CNC machine control / G-code generation.** Out of scope; DXF goes to the vendor, vendor's CAM software produces G-code.
- ❌ **Inventory management.** Out of scope.
- ❌ **Supplier API integration.** No automated quotes from Kronospan/Egger.
- ❌ **VAT / tax computation.** Net only in v1.0.
- ❌ **Multi-currency.** PLN only.
- ❌ **Customer-facing invoice generation.** Accounting concern.
- ❌ **3D STEP/IGES output.** Sheet goods only; no need for 3D assembly format.
- ❌ **Cloud submission to CNC.** Manual file upload is the established workflow.
- ❌ **Writing back to recipes from CAM** ("optimize this recipe based on cut history"). One-way pipeline.
- ❌ **Custom DXF dialects per CNC vendor.** Generic R2018 DXF first; vendor-specific dialects (HOMAG, Felder, Holzma) are Could.
- ❌ **Reflex UI for export.** F006's call; F008 ships CLI only.
- ❌ **Replacing `ezdxf` with custom DXF writer.** Mature library; no reason.
- ❌ **Combining cut list + drill + DXF into single file.** CNC vendors expect separate. Different tools consume different files.
- ❌ **`openpyxl` / XLS as the Must format.** CSV is the standard; XLS is Could.

---

## Change Locality Test

- [x] Editing **one bounded context** (CAD).
- [x] **One published contract change**: the `kitchen-cli` binary entry point + subcommand registry. The MachiningOp deprecation in Core is additive (warning only, no removal).
- [x] **Passes.**

---

## Glossary Impact

**New terms** (must be added to `docs/GLOSSARY.md` in the implementation commit):

- `MachiningFeature` — promote placeholder → concrete. Replaces legacy `MachiningOp`. Carries tool spec, face, position, operation order.
- `FeatureType` — new enum: DRILL / GROOVE / RABBET / NOTCH / POCKET / CUTOUT.
- `Face` — new enum: face of a panel where machining applies.
- `Pattern` — new. Reusable machining definition stored as YAML.
- `PatternRegistry` — new. Loads pattern YAMLs.
- `PatternResolver` — new. Evaluates pattern formulas against a panel to produce `MachiningFeature` list.
- `OperationSpec` — new. One operation inside a Pattern.
- `PositionFormula` — new. Declarative position calculator (`grid` or `points` form).
- `CutListExporter` — new.
- `DrillPatternExporter` — new.
- `DXFExporter` — new.
- `CostEstimator` — new (if Should-have lands).
- `WasteFactor` — new term: percentage of additional material to account for nesting/cutting losses.
- `CutPiece` — promote placeholder → concrete (was already in glossary; refine to point to exporter output).

**Existing terms refined:**

- `MachiningOp` — mark as `⚠️ legacy`. Direct readers to `MachiningFeature`.
- `DrillPatternRef` — clarify: emitted by F002 recipes; resolved by F008's `PatternResolver` to concrete `MachiningFeature`s.
- `CAM Readiness` — confirm: F008 invokes the gate before every export command.

---

## Acceptance Criteria

The feature is **done** when:

- [ ] `kitchen-cli` binary installed and runnable.
- [ ] All Must subcommands work: `cut-list`, `drill-pattern`, `dxf`, `bom`.
- [ ] `MachiningFeature` model + `PatternResolver` + 5 pattern YAMLs shipped.
- [ ] `MachiningOp` annotated with deprecation warning; glossary entry updated.
- [ ] Gate 4 invoked before every export; ERROR refuses output; `--force` flag works with override annotation.
- [ ] All unit tests pass.
- [ ] All integration tests pass against `examples/kitchen_nowak.yaml`.
- [ ] Round-trip CSV diff matches committed expected fixtures.
- [ ] No `eval(` calls anywhere in the repo (Phase 2 invariant preserved).
- [ ] `docs/GLOSSARY.md` updated with ~14 new/refined entries.
- [ ] `docs/01_architecture.md` Context Map updated to show CLI binary entry + F007 contribution.
- [ ] `docs/cli.md` published — subcommand reference for the carpenter.
- [ ] ADR `features/F008-cli-export/adr.md` status = `Accepted`.
- [ ] `status.md` set to `done`.
- [ ] `features/INDEX.md` updated.
- [ ] Phase 8 gate criteria in `docs/PHASES.md` ticked.

---

## Out of Scope (anti-drift)

- ❌ **Plugin modification.** `home_builder_5/` untouched (Rule 4).
- ❌ **Nesting optimization.** CNC company's job.
- ❌ **Cloud / HTTP submission.** Manual file upload to vendor portal is the workflow.
- ❌ **Material purchasing automation.**
- ❌ **G-code / direct CNC control.**
- ❌ **Reflex UI changes.** F006's call.
- ❌ **3D STEP / IGES / glTF output.**
- ❌ **Inventory tracking.**
- ❌ **Tax / VAT computation.**
- ❌ **Multi-currency.**
- ❌ **Customer invoice generation.**
- ❌ **Live edit-on-CSV / reverse import.** YAML is the truth.
- ❌ **Replacing existing kuchnie_core BOM module.** F008 reuses it.
- ❌ **Caching exporter output.** Re-export is cheap.
- ❌ **Removing legacy `csv_generator.py`, `drill_engine.py`, `generators/legrabox_side_panel.py`.** They're subsumed via thin wrappers + deprecation; full removal is backlog.

---

## References

- **Pattern source:** `docs/02_pattern_analysis.md` § Pattern 6 (Feature-based Operations, from TopSolid'Wood) — associative MachiningFeatures.
- **Placement decision:** `docs/03_implementation_placement.md` § Pattern 6 — Feature-based Ops (CAD owns).
- **Process rules:** `docs/04_solo_dev_process.md`.
- **Related ADRs:**
  - `features/F001-construction-method/adr.md` — pattern resolver reads `system32_offset_mm` etc. from `ConstructionMethod`.
  - `features/F002-recipe-engine/adr.md` — F008 fills the `DrillPatternRef` resolution that F002 deferred.
  - `features/F004-validation-gates/adr.md` — every exporter calls Gate 4 (CAMReadinessGate); strict-CAM rule (WARNINGs promoted to ERRORs) is the export gatekeeper.
  - `features/F005-material-resolver/adr.md` — exporters read `ResolvedMaterial.sheet_size_mm` for waste calculation; `paired_edge_id` for edge banding linear-meter calculation.
  - `features/F007-blender-adapter/adr.md` — F007 contributes the `render` subcommand to F008's CLI binary.
  - `features/F008-cli-export/adr.md` — this feature's ADR.
- **Related features:**
  - **Depends on:**
    - F001 (ConstructionMethod fields for pattern resolution).
    - F002 (recipes emit `DrillPatternRef`s; engine produces `DecompositionResult`).
    - F004 (Gate 4 invoked before export).
    - F005 (`MaterialResolver` for sheet sizes, edge specs, paired edges).
  - **Indirect dependencies:**
    - F003 (templates are the source of cabinet defaults; F008 reads instances, not templates).
    - F007 (registers `render` subcommand; F008 must publish a subcommand registry that F007 can use).
  - **Enables:**
    - **The actual manufacturing workflow.** This is the feature that ships kitchens.
    - F006 (web sidebar imports `CostEstimator` to show price).
  - **Conflicts with:**
    - Legacy `kitchen-cad/src/kitchen_cad/csv_generator.py`, `drill_engine.py`, `generators/legrabox_side_panel.py`, `example_generate.py` — subsumed via wrappers + deprecation; full removal is backlog.

---

## Worked Example — Full Export Run (for spec clarity)

### CLI invocation

```bash
$ kitchen-cli export-all examples/kitchen_nowak.yaml --output-dir /tmp/nowak/

Validating kitchen against Gates 1-4...
  Gate 1 (Cabinet):       ✓ all 12 cabinets pass
  Gate 2 (Row):           ✓ all 3 rows pass
  Gate 3 (Kitchen):       ✓ aggregated; 1 warning surfaced
    [WARN] KIT-003: Worktop segment doesn't cover wall 'wall_west' (no base row).
  Gate 4 (CAM-Readiness): ✓ all panels validated

Decomposing kitchen into panels...
  Loaded 12 recipes from src/kuchnie_core/recipes/
  Loaded 5 patterns from kitchen-cad/patterns/
  Emitted 84 panels, 47 sub-assemblies, 218 machining features

Exporting cut list...
  /tmp/nowak/cuts.csv (84 rows; 38 distinct after aggregation)

Exporting drill patterns...
  /tmp/nowak/drills.csv (218 rows)

Exporting DXF panels...
  /tmp/nowak/dxf/cab_001_side_left.dxf
  /tmp/nowak/dxf/cab_001_side_right.dxf
  ...
  84 files total

Exporting BOM...
  /tmp/nowak/bom.csv

Estimating cost (waste_factor=0.18)...
  Materials: 4,820 PLN
  Edge banding: 380 PLN
  Hardware: 1,250 PLN
  ────────────────────
  Total estimate: 6,450 PLN (net)
  /tmp/nowak/cost_estimate.json

Done in 4.7 seconds.
```

### Internal flow

```python
# cli/main.py
@app.command()
def export_all(
    kitchen_path: Path,
    output_dir: Path,
    waste_factor: float = 0.18,
):
    # 1. Load + validate
    kitchen = load_kitchen(kitchen_path)
    catalog = YamlCatalogReader(catalog_dir())
    resolver = MaterialResolver(catalog, kitchen)
    
    for gate in [CabinetGate, RowGate, KitchenGate, CAMGate]:
        result = gate().validate_all(kitchen, ctx)
        print_result(result)
        if not result.is_valid:
            sys.exit(1)
    
    # 2. Decompose
    decomposition = decompose_kitchen(kitchen)  # uses kuchnie_core
    
    # 3. Resolve patterns into concrete MachiningFeatures
    pattern_resolver = PatternResolver(load_patterns())
    features = []
    for panel in decomposition.panels:
        for ref in panel.drilling_refs:
            features.extend(pattern_resolver.resolve(ref, panel, kitchen.construction_method))
    
    # 4. Export
    CutListExporter().export(decomposition, output_dir / "cuts.csv")
    DrillPatternExporter().export(features, decomposition.panels, output_dir / "drills.csv")
    DXFExporter().export_all(decomposition, output_dir / "dxf/")
    BOMExporter().export(decomposition, output_dir / "bom.csv")
    
    # 5. Cost estimate
    estimator = CostEstimator(catalog, waste_factor=waste_factor)
    cost = estimator.estimate(decomposition)
    write_json(cost, output_dir / "cost_estimate.json")
```

### Pattern YAML example

```yaml
# kitchen-cad/patterns/system32.yaml
pattern_id: system32
description: "System 32 grid drilling for cabinet sides"
applies_to_roles: [side_left, side_right]

operations:
  - feature_type: DRILL
    face: INNER
    tool:
      diameter_mm: 5
      depth_mm: 13
    position_formula:
      grid:
        x_offsets: [37, "panel.width - 37"]   # front column + rear column
        y_spacing: 32
        y_start: "construction.system32_offset_mm"
        y_end: "panel.height - construction.system32_offset_mm"
    operation_order: 100
```

---

## Open Questions

> All must be answered before coding begins.

- [x] **Q1:** What's the exact e-rozkroj / e-rozrys CSV column schema? → **A:** Placeholder schema in spec; **verify against actual e-rozkroj documentation at implementation time** (the developer will obtain a sample CSV from their CNC company). The exporter is built with the column set as a config (not hardcoded) so adjustments at implementation are localized.
- [x] **Q2:** One DXF per panel, or one DXF per cabinet, or one DXF for the whole kitchen? → **A:** One DXF per panel for Must. Per-cabinet aggregation is Should.
- [x] **Q3:** Where do patterns live? → **A:** `kitchen-cad/patterns/*.yaml` (data); `kitchen-cad/src/kitchen_cad/features/pattern_resolver.py` (engine). Same separation as recipes (F002) and templates (F003).
- [x] **Q4:** Reuse `kuchnie_core/bom.py` or rewrite? → **A:** Reuse. CLI subcommand wraps the existing BOM logic with formatting options. No domain logic in CAD.
- [x] **Q5:** Cost estimator: Core or CAD? → **A:** CAD. It uses CNC vendor conventions (waste factors, sheet sizes), which are manufacturing concerns, not domain. F006 imports from CAD when displaying.
- [x] **Q6:** Waste factor: hardcoded, configurable, or per material? → **A:** Configurable per material category (`sheet`, `edge`, `hardware`) with sensible defaults. CLI flag `--waste-factor` is shorthand for sheet only.
- [x] **Q7:** Are MachiningFeatures stored on Panel, or computed on demand? → **A:** Computed on demand by PatternResolver. Stored Panel has only `drilling_refs: list[DrillPatternRef]`. This matches F002's intent and keeps Panel serialization-friendly.
- [x] **Q8:** Strict CAM gate — does `--force` truly bypass? → **A:** Yes, but with explicit `_OVERRIDE` annotation in filenames and stderr warning. Use case: a known-acceptable WARN-level issue (e.g., a panel slightly exceeds standard sheet, but customer agreed to use oversize stock).
- [x] **Q9:** Encoding for Polish characters in CSV? → **A:** UTF-8 with BOM (Excel compatible). Optional alternate encoding (Windows-1250) is Should.
- [x] **Q10:** CLI library — typer or click? → **A:** Lean towards typer (type-driven, modern, Pydantic-friendly). Final choice deferred to implementation; both are acceptable.
- [x] **Q11:** What does F007 need from F008 to register `render`? → **A:** F008's CLI binary exposes a `register_subcommand(name, callable)` function in `kitchen_cad/cli/main.py`. F007's `cli.py` imports and calls it at module load. No circular dependency (F008 doesn't import F007).
- [x] **Q12:** How does F008 know which formats the carpenter's CNC company accepts? → **A:** At implementation time, the carpenter validates output against a sample. If the CNC accepts CSVs as-is, ship. Otherwise the column schema config (Q1) is the tunable. Backlog: per-vendor presets.
- [x] **Q13:** DXF coordinate origin? → **A:** Per-panel local origin at lower-left corner (CNC convention). Position formulas use the same coordinate system. The DXF exporter does NO transformations.
- [x] **Q14:** What about cabinets without a `recipe_id` (legacy)? → **A:** F002's recipe engine has the fallback path (legacy `decompose_*` in `catalog.py`, quarantined). F008 consumes whatever `DecompositionResult` the engine emits. If panels lack `drilling_refs` (legacy MachiningOps), F008 logs a WARN and exports without machining for those panels. Forward path: migrate the legacy cabinet types to YAML recipes (backlog).
- [x] **Q15:** Pattern conflict resolution — what if two patterns target the same position? → **A:** PatternResolver does NOT detect conflicts. Each pattern emits independent features. If two drills collide at the same x/y, it's a recipe authoring bug. Backlog: collision detection check (could go into Gate 4).

**All Open Questions resolved.** Spec is **ready** for implementation.
