# F004 — Validation Gates (Four-Stage Quality Checks)

## Job Story

**When** I am working on a kitchen project at any stage — configuring a single cabinet, arranging a row, finalizing the whole kitchen, or preparing for CNC export,
**I want to** call a stage-appropriate validation gate (`CabinetValidationGate`, `RowValidationGate`, `KitchenValidationGate`, `CAMReadinessGate`) that returns a structured list of issues with stable codes (`CAB-001`, `ROW-003`, `KIT-005`, `CAM-007`), severities (ERROR / WARNING / INFO), and human-readable messages,
**So I can** catch dimensional errors, missing components, and integration mismatches before sending DXF/CSV to my CNC company in Wrocław — and so my web UI, CLI, and render adapter all get the **same answer** to "is this valid?" without each context inventing its own checks.

---

## Bounded Context

- **Primary (the one that OWNS this):** `Core` (`src/kuchnie_core/validation/`)
- **Touched (consumers, must have explicit reason):**
  - **None in F004.** Every consumer (Web F006, Render Adapter F007, CAD CLI F008) will *call* the gates, but F004 itself ships only the gate library in Core.
  - F005 will **extend** the gates by registering additional checks (`KitchenValidationGate.register_check(MaterialResolutionCheck)`). The extension API ships in F004; F005 uses it.

> **Change Locality Test result:** single bounded context (Core). The extensibility API is the published contract; consumers call gates, F005 registers checks. ✅ Passes.

---

## Subdomain Classification

- [x] **Core** — competitive advantage. Validation gates are the difference between "we sent valid DXF to the CNC" and "the CNC company called us at 6pm Friday because the cutout exceeds the worktop". For a solo carpenter, every prevented mistake is real money. Owning the validation rules in code (not in a checklist on the carpenter's wall) is the leverage.
- [ ] Supporting
- [ ] Generic

**Reasoning:** Specific to our domain (cabinet/kitchen rules) and to our manufacturing pipeline (e-rozkroj / Polish CNC vendor conventions). No off-the-shelf library encodes these. We build it.

---

## Data Ownership

- **Canonical writes happen in:**
  - Gate implementations: `src/kuchnie_core/validation/gates/*.py`
  - Result types: `src/kuchnie_core/validation/result.py`
  - Issue code registry: `src/kuchnie_core/validation/codes.py`
- **Read-only consumers:**
  - `kitchen-app` (F006) — calls Gate 1 on cabinet edit, Gate 2 on row reorder, Gate 3 on "generate render".
  - `kitchen-cad` CLI (F008) — calls all four gates before any export, refuses to export on any ERROR.
  - Render adapter (F007) — calls Gate 3 before invoking Blender.
- **Storage:** No persistent storage. Gates are stateless; results are computed on demand.

---

## Scope — MoSCoW

### Must (do not ship without)

#### Core types
- [ ] `src/kuchnie_core/validation/__init__.py` — package public API.
- [ ] `src/kuchnie_core/validation/result.py`:
  - [ ] `Severity` enum: `ERROR`, `WARNING`, `INFO`.
  - [ ] `ValidationIssue` dataclass: `code: IssueCode`, `severity: Severity`, `message: str`, `entity_ref: str | None`, `fix_hint: str | None`.
  - [ ] `ValidationResult` dataclass: `issues: list[ValidationIssue]`, `is_valid: bool` (computed: True iff no ERROR-severity issues), `errors`, `warnings`, `infos` (computed filters).
- [ ] `src/kuchnie_core/validation/codes.py`:
  - [ ] `IssueCode` Pydantic model: `code: str` (e.g. `"CAB-001"`), `title: str`, `description: str`, `default_severity: Severity`.
  - [ ] Code registry: `register_code(code, title, description, default_severity)` and `get_code(code_string)`.
  - [ ] Pre-registered codes for all Must checks below (catalog in `docs/validation_codes.md`).
- [ ] `src/kuchnie_core/validation/context.py`:
  - [ ] Per-gate context dataclasses: `CabinetValidationContext`, `RowValidationContext`, `KitchenValidationContext`, `CAMValidationContext`.
  - [ ] Each context carries the registries the gate needs (`construction_registry`, `recipe_registry`, `template_registry`) and gate-specific data (e.g., `wall_length_mm` for Row context).
- [ ] `src/kuchnie_core/validation/check.py`:
  - [ ] `Check` protocol: `run(target, ctx) -> list[ValidationIssue]`.
  - [ ] Base class `BaseCheck` for convenience.

#### Gate 1 — Cabinet Validation
- [ ] `src/kuchnie_core/validation/gates/cabinet.py::CabinetValidationGate`.
- [ ] Class attribute `_checks: list[Check]` populated at module load.
- [ ] Classmethod `register_check(check)` for F005-style extension.
- [ ] `validate(cabinet: CabinetInstance, ctx: CabinetValidationContext) -> ValidationResult`.
- [ ] Built-in checks:
  - [ ] **CAB-001** — Width out of template `dimension_constraints` range.
  - [ ] **CAB-002** — Height out of template constraints.
  - [ ] **CAB-003** — Depth out of template constraints.
  - [ ] **CAB-004** — Negative or zero dimension (defensive — even before constraint check).
  - [ ] **CAB-010** — `construction_method_id` not in registry.
  - [ ] **CAB-011** — `recipe_id` not in registry.
  - [ ] **CAB-012** — `template_id` set but not in registry (warning, not error — legacy cabinets pre-F003 may have no template).
  - [ ] **CAB-020** — Sub-assembly kind in instance not declared in template `default_sub_assemblies` (warning).
  - [ ] **CAB-021** — Sub-assembly kind in template missing from instance (error if `removable: false` is documented in template; else warning).
  - [ ] **CAB-022** — Door count > 4 (sanity ceiling).
  - [ ] **CAB-023** — Drawer count > 10 (sanity ceiling).
  - [ ] **CAB-030** — `material_refs` missing a role required by the template's `material_role_defaults` (error).

#### Gate 2 — Row Validation
- [ ] `src/kuchnie_core/validation/gates/row.py::RowValidationGate`.
- [ ] `validate(row: Row, ctx: RowValidationContext) -> ValidationResult`.
- [ ] Built-in checks:
  - [ ] **ROW-001** — Sum of cabinet widths + `cabinet_gap_mm * (n-1)` exceeds `wall_length_mm` (error).
  - [ ] **ROW-002** — Same cabinet ID appears twice in the row (error).
  - [ ] **ROW-003** — Row has zero cabinets (warning — empty rows are usually a mistake).
  - [ ] **ROW-004** — Corner cabinet (`CabinetCategory.CORNER`) placed in interior position (not first or last) (error).
  - [ ] **ROW-005** — Adjacent base + tall cabinets without explicit clearance (warning — tall next to base often blocks a door).
  - [ ] **ROW-006** — Wall reference (`row.wall_id`) is empty or refers to nothing the context provides (error).

#### Gate 3 — Kitchen Validation
- [ ] `src/kuchnie_core/validation/gates/kitchen.py::KitchenValidationGate`.
- [ ] `validate(kitchen: Kitchen, ctx: KitchenValidationContext) -> ValidationResult`.
- [ ] Built-in checks:
  - [ ] **KIT-001** — Duplicate cabinet ID across rows (error).
  - [ ] **KIT-002** — `default_construction_method_id` not in registry (error).
  - [ ] **KIT-003** — Worktop segment declared but doesn't cover all base rows (warning — carpenter may intend partial coverage).
  - [ ] **KIT-004** — Worktop segment covers a wall that has no base row (warning).
  - [ ] **KIT-005** — Sink declared in worktop cutouts but no sink-base cabinet in any base row (error).
  - [ ] **KIT-006** — Hob declared in worktop cutouts but no hob-base cabinet (error).
  - [ ] **KIT-007** — Kitchen has zero rows (error).
  - [ ] **KIT-008** — Aggregate all Gate 1 issues across all cabinets (re-run Gate 1 internally).
  - [ ] **KIT-009** — Aggregate all Gate 2 issues across all rows.
- [ ] Class attribute `_checks` and `register_check` API for F005 extension (specifically, F005 will add `KIT-100` — decor IDs resolve through catalog).

#### Gate 4 — CAM Readiness
- [ ] `src/kuchnie_core/validation/gates/cam_readiness.py::CAMReadinessGate`.
- [ ] `validate(decomposition: DecompositionResult, ctx: CAMValidationContext) -> ValidationResult`.
- [ ] **WARNING is treated as ERROR** here — CAM stage is strict; nothing ships to CNC with warnings.
- [ ] Built-in checks:
  - [ ] **CAM-001** — Panel has zero or negative dimension (`width <= 0`, `height <= 0`, `thickness <= 0`).
  - [ ] **CAM-002** — Panel's `material_role` empty.
  - [ ] **CAM-003** — Edge banding side declared but no `material_role` assigned.
  - [ ] **CAM-004** — `DrillPatternRef` unresolved (no concrete `DrillPoint`s — happens if F008's pattern engine didn't run).
  - [ ] **CAM-005** — Cutout exceeds panel bounds.
  - [ ] **CAM-006** — Panel dimension exceeds standard sheet size (e.g., 2800×2070mm Kronospan) — warning by default, error in strict CAM mode.
  - [ ] **CAM-007** — Wood-grain material panel without `grain_direction` set.
  - [ ] **CAM-008** — Two panels with same role in same cabinet (likely a recipe bug).
- [ ] Class attribute `_checks` and `register_check` API for F005 extension (specifically, F005 will add `CAM-100` — material role resolves to a concrete decor).

#### Tests
- [ ] `tests/core/validation/test_result.py` — ValidationResult/Issue/Severity behavior, `is_valid` logic.
- [ ] `tests/core/validation/test_codes.py` — registry roundtrip, duplicate registration raises.
- [ ] `tests/core/validation/test_cabinet_gate.py` — pass case + at least one failure per CAB-* code listed above.
- [ ] `tests/core/validation/test_row_gate.py` — pass case + at least one failure per ROW-* code.
- [ ] `tests/core/validation/test_kitchen_gate.py` — pass case + at least one failure per KIT-* code + aggregation tests for KIT-008/009.
- [ ] `tests/core/validation/test_cam_gate.py` — pass case + at least one failure per CAM-* code + warning-as-error behavior.
- [ ] `tests/core/validation/test_extension.py` — `register_check` adds a check that fires; un-registered checks do not run.
- [ ] `tests/integration/test_full_validation_pipeline.py` — example kitchen runs through Gates 1→2→3→4 and produces a clean result.

#### Documentation
- [ ] `docs/validation_codes.md` — flat catalog of all codes with title, description, default severity, and example fix. Carpenter reference; LLM agent reference.

### Should (do if time permits)

- [ ] `kitchen-cli validate <kitchen.yaml>` — runs all gates, prints issues grouped by gate, exits non-zero on any ERROR.
- [ ] `kitchen-cli list-checks` — dumps every registered check across every gate (for documentation generation).
- [ ] Strict-CAM-mode flag on Gate 4 — turns warnings into errors (default already does this; flag is for future relaxation).
- [ ] `--format json` on `kitchen-cli validate` for tooling integration.

### Could (almost certainly defer)

- [ ] Fix-hint auto-application (`kitchen-cli fix --code CAB-001` clamps width to nearest constraint).
- [ ] Configurable severity overrides per project.
- [ ] Localized messages (Polish) — codes stay stable, messages get translated. Not in v1.0.
- [ ] Validation result caching keyed by entity hash.

### Won't (this iteration — explicit cuts)

- ❌ **Real-time / per-keystroke validation in the web app.** F006 calls gates on edit-blur or save, not on every keystroke. F004 is gate API only; UX is F006.
- ❌ **Custom rules per customer.** v1.0 has one global rule set. Per-project overrides are post-v1.0.
- ❌ **Validation in the Blender plugin.** The plugin is downstream; the render adapter (F007) calls Gate 3 *before* invoking Blender. Plugin internals untouched (Rule 4).
- ❌ **ML / anomaly detection.** ("This kitchen is unusual; are you sure?") Out of scope.
- ❌ **Cross-project validation.** ("Customer X's other kitchens use these decors; warn on deviation.") Out of scope.
- ❌ **Async gates.** Gates are fast (milliseconds for typical kitchen). No reason for async.
- ❌ **Stop-on-first-error.** Always collect all issues. Carpenter wants the full list, not a back-and-forth.
- ❌ **Exception-per-error.** Issues are values, not exceptions. Exceptions are reserved for programmer errors (e.g., calling `validate(None)`).
- ❌ **Validation result persistence.** Re-run on demand; results are cheap.
- ❌ **Material-resolution checks.** F005 owns those. F004 ships the extension API; F005 adds `KIT-100` and `CAM-100`.
- ❌ **Recipe-output validation against template sub-assemblies.** Gate 1 checks instance vs template (structural); the recipe-vs-sub-assembly check happens implicitly because F002's engine emits panels whose roles trace back to the recipe. Cross-check would be a Should at best.
- ❌ **Workflow gates** ("Has the customer signed off?") — those are business state, not validation. Web app handles them.

---

## Change Locality Test

- [x] Editing **one bounded context** (Core). Consumers (Web, CAD, Render) only *call* the published API.
- [x] **One published contract**: the four gate classes and the `register_check` extension API. `kitchen_config.yaml` schema is **unchanged**.
- [x] **Passes.**

---

## Glossary Impact

**New terms** (must be added to `docs/GLOSSARY.md` in the implementation commit):

- `ValidationGate` — promote placeholder → concrete (file of record: `src/kuchnie_core/validation/gates/`).
- `ValidationResult` — promote placeholder → concrete (file of record: `src/kuchnie_core/validation/result.py`).
- `ValidationIssue` — new structured issue type.
- `ValidationContext` — read-only per-gate context object (4 variants).
- `Severity` — new enum: ERROR / WARNING / INFO.
- `IssueCode` — new stable string identifier (e.g., `CAB-001`).
- `Check` — new protocol: pluggable validation rule unit.
- `CabinetValidationGate`, `RowValidationGate`, `KitchenValidationGate`, `CAMReadinessGate` — four concrete gates.
- `CAM Readiness` — refine glossary entry to reference Gate 4 in F004.

**Existing terms refined:**

- `Panel` — gains validation context: `material_role` and edge assignments are validated by CAM-002 / CAM-003.

---

## Acceptance Criteria

The feature is **done** when:

- [ ] `src/kuchnie_core/validation/` package exists with all listed modules.
- [ ] All four gate classes implemented with their built-in checks.
- [ ] All listed `IssueCode`s registered with title + description + default severity.
- [ ] `register_check` API works (tested in `test_extension.py`).
- [ ] `tests/core/validation/` test suite passes — every CAB/ROW/KIT/CAM code has at least one passing test.
- [ ] `tests/integration/test_full_validation_pipeline.py` passes for `examples/kitchen_nowak.yaml`.
- [ ] No regression in F001–F003 tests.
- [ ] `docs/GLOSSARY.md` updated with 9 new/refined terms.
- [ ] `docs/validation_codes.md` published — full catalog of codes.
- [ ] `docs/01_architecture.md` Context Map updated to show `validation/` package in Core.
- [ ] ADR `features/F004-validation-gates/adr.md` status = `Accepted`.
- [ ] `status.md` set to `done`.
- [ ] `features/INDEX.md` updated.
- [ ] Phase 4 gate criteria in `docs/PHASES.md` ticked.

---

## Out of Scope (anti-drift)

- ❌ **Plugin extension.** Validation runs *before* the plugin sees data. Plugin internals untouched.
- ❌ **Reflex UI for validation.** F006 surfaces results in the sidebar; F004 ships the API only.
- ❌ **Auto-fix infrastructure.** `fix_hint` is a string suggestion, not an executable repair.
- ❌ **Custom validators registered from outside Core in v1.0.** F005 is the only external registrar, and it lives in Core too.
- ❌ **Material resolution checks** (KIT-100, CAM-100) — those codes are reserved in the registry but their checks ship in F005.
- ❌ **Validation of decor pairings** (decor X requires edge Y) — Catalog-level concern handled separately when F005 wires the catalog reader.
- ❌ **Performance budgets / benchmarks.** Gates are intentionally simple; if a check becomes slow, optimize then. v1.0 has no perf gate for F004.
- ❌ **Localization.** Messages are English. Codes are stable; translation is a separate (post-v1.0) layer.
- ❌ **Web hooks / event emission on validation failure.** No event bus in v1.0.

---

## References

- **Pattern source:** `docs/02_pattern_analysis.md` § Pattern 7 (Validation Gates, from TopSolid'Wood) — the four-gate model.
- **Placement decision:** `docs/03_implementation_placement.md` § Pattern 8 — Validation Gates (Core, called by each consumer).
- **Process rules:** `docs/04_solo_dev_process.md`
- **Related ADRs:**
  - `features/F001-construction-method/adr.md` — Gate 1 checks `construction_method_id` resolves.
  - `features/F002-recipe-engine/adr.md` — Gate 1 checks `recipe_id` resolves; Gate 4 checks engine output.
  - `features/F003-template-registry/adr.md` — Gate 1 checks dimensions against template constraints, sub-assemblies against template defaults.
  - `features/F004-validation-gates/adr.md` — this feature's ADR.
- **Related features:**
  - **Depends on:**
    - F001 (read `construction_method_id` for resolution check).
    - F002 (Gate 4 consumes `DecompositionResult` from recipe engine).
    - F003 (Gate 1 reads template constraints and sub-assembly defaults).
  - **Enables:**
    - F005 (registers material-resolution checks via extension API).
    - F006 (calls Gate 1/2/3 from web UI).
    - F007 (calls Gate 3 before render).
    - F008 (calls all gates; refuses export on ERROR).
  - **Conflicts with:** none. F004 is purely additive.

---

## Worked Example — Validation Result (for spec clarity)

What a Gate 1 result looks like when a cabinet has multiple issues:

```python
result = CabinetValidationGate().validate(cabinet, ctx)

# result.is_valid → False
# result.errors → 2 issues
# result.warnings → 1 issue
# result.infos → 0 issues

for issue in result.issues:
    print(f"[{issue.severity.name}] {issue.code} ({issue.entity_ref}): {issue.message}")
    if issue.fix_hint:
        print(f"    Hint: {issue.fix_hint}")
```

```
[ERROR]   CAB-001 (cab_a3f2c1): Width 1500mm exceeds template 'base_door_60' max 1200mm
    Hint: Reduce width to 1200mm or switch to template 'base_door_120' if it exists
[ERROR]   CAB-010 (cab_a3f2c1): construction_method_id 'unknown_method' not in registry
    Hint: Use one of: dowel_camlock_18, confirmat_18
[WARNING] CAB-022 (cab_a3f2c1): Door count 5 exceeds sanity ceiling 4
    Hint: Verify this is intentional; most base cabinets have 1-2 doors
```

And the same result as machine-readable JSON for CLI `--format json` consumers:

```json
{
  "is_valid": false,
  "issues": [
    {
      "code": "CAB-001",
      "severity": "ERROR",
      "message": "Width 1500mm exceeds template 'base_door_60' max 1200mm",
      "entity_ref": "cab_a3f2c1",
      "fix_hint": "Reduce width to 1200mm or switch to template 'base_door_120' if it exists"
    },
    {
      "code": "CAB-010",
      "severity": "ERROR",
      "message": "construction_method_id 'unknown_method' not in registry",
      "entity_ref": "cab_a3f2c1",
      "fix_hint": "Use one of: dowel_camlock_18, confirmat_18"
    },
    {
      "code": "CAB-022",
      "severity": "WARNING",
      "message": "Door count 5 exceeds sanity ceiling 4",
      "entity_ref": "cab_a3f2c1",
      "fix_hint": "Verify this is intentional; most base cabinets have 1-2 doors"
    }
  ]
}
```

---

## Open Questions

> All must be answered before coding begins.

- [x] **Q1:** Collect all issues or stop on first ERROR? → **A:** Collect all. Carpenter wants the full picture, not a back-and-forth.
- [x] **Q2:** Severity levels? → **A:** Three: ERROR (blocks next stage), WARNING (review), INFO (note). Gate 4 treats WARNING as ERROR.
- [x] **Q3:** Gates as classes or functions? → **A:** Classes. Enables `register_check` extension API (F005's path in).
- [x] **Q4:** ValidationResult as Pydantic or dataclass? → **A:** Dataclass. No serialization need beyond CLI JSON output (which uses `dataclasses.asdict()`). Lighter than Pydantic.
- [x] **Q5:** Issue code format? → **A:** `<GATE>-<NNN>`, e.g., `CAB-001`. Stable strings; grep-friendly; future i18n keyed by code.
- [x] **Q6:** Localization in v1.0? → **A:** No. English messages. Codes are stable so a future i18n layer can translate without changing the gate code.
- [x] **Q7:** How does F005 add decor checks? → **A:** Via `register_check`. F005 imports the gate class, defines a `MaterialResolutionCheck`, calls `KitchenValidationGate.register_check(MaterialResolutionCheck)`. The codes `KIT-100` and `CAM-100` are **reserved** in F004's registry but their *check implementations* ship with F005.
- [x] **Q8:** Per-gate ValidationContext or shared? → **A:** Per-gate. Each gate needs different inputs (`wall_length_mm` for Row, `catalog` for Kitchen, etc.). Shared context would balloon into a god object.
- [x] **Q9:** Exceptions vs issues? → **A:** Issues for domain errors (out-of-range width). Exceptions for programmer errors (`validate(None)` → `TypeError`).
- [x] **Q10:** Do gates re-run downstream gates? E.g., does `KitchenValidationGate` call `CabinetValidationGate` internally? → **A:** Yes — `KIT-008` aggregates Gate 1 results across all cabinets; `KIT-009` aggregates Gate 2 across rows. This means calling Gate 3 alone gives a complete kitchen-level picture. Gate 4 stands alone (different target type).
- [x] **Q11:** What's the relationship between F003's `TemplateInstantiationError` and Gate 1? → **A:** `TemplateInstantiationError` is raised at *instantiation time* for clearly-out-of-range overrides. Gate 1 re-checks at *validation time* because a cabinet might have been edited post-instantiation (dimensions changed, sub-assemblies modified). Both checks coexist; the gate is the final say.
- [x] **Q12:** Where is the issue code catalog documented? → **A:** `docs/validation_codes.md`, auto-generatable from the registry (Should-have CLI `kitchen-cli list-checks`). For v1.0 we hand-write it from the registry; auto-gen is a backlog item.
- [x] **Q13:** Should checks be stateless? → **A:** Yes. Each `Check.run()` is a pure function of `(target, ctx)`. Enables parallel execution if ever needed and keeps testing simple.

**All Open Questions resolved.** Spec is **ready** for implementation.
