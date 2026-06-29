# ADR — F004 — Four Validation Gates with Pluggable Checks and Stable Issue Codes

**Date:** 2026-06-28
**Status:** `Proposed`
**Feature:** F004
**Author:** solo dev

---

## Context

TopSolid'Wood, the most engineering-oriented of the five reference CAD systems, validates at four distinct stages: single cabinet, row layout, whole kitchen, CAM-ready. Each gate has different inputs and different consequences for failure. The other four systems do various subsets of this; TopSolid is the cleanest.

The Blender plugin has its own `manifest_validator.py` that checks scattered concerns (dimensions, overlaps, walkway clearance) but is plugin-internal and not callable from our Web or CLI. The existing `kitchen-plugin/src/config_parser.py` validators are similar — plugin-local, not reusable.

For our system, validation lives in **Core** (`03_implementation_placement.md` § Pattern 8): every consumer — Web UI, CAD CLI, render adapter — must get the same answer. Inventing per-consumer validation is the path to a CNC company calling at 6pm Friday saying "this DXF has a cutout that exceeds the worktop".

The decision needs to be made **now** because: (1) F005 needs an extension API to add material-resolution checks; (2) F006 (Web) needs the gate API to surface errors in the sidebar; (3) F008 (CLI) refuses to export without a passing Gate 4 — the contract has to be stable before exporters are written.

---

## Decision

We will introduce a `src/kuchnie_core/validation/` package with:

1. **Four stateless gate classes**, one per validation stage:
   - `CabinetValidationGate.validate(cabinet, ctx) → ValidationResult`
   - `RowValidationGate.validate(row, ctx) → ValidationResult`
   - `KitchenValidationGate.validate(kitchen, ctx) → ValidationResult`
   - `CAMReadinessGate.validate(decomposition, ctx) → ValidationResult`

2. **Per-gate `ValidationContext` dataclasses**, each carrying only the registries and ambient data that gate needs (Cabinet → registries; Row → wall_length_mm; Kitchen → all registries; CAM → catalog + decomposition).

3. **Pluggable check registry** per gate. Each gate has a class-level `_checks: list[Check]` populated at module load with built-in checks. F005 (and any future extension) calls `Gate.register_check(MyCheck)` to append. Gates ship their built-ins on import; extensions are explicit.

4. **Stable issue codes** of the form `<GATE>-<NNN>` (e.g., `CAB-001`, `ROW-003`). Codes are registered in `validation/codes.py` with title, description, and default severity. F004 ships ~30 codes; reserves `KIT-100` and `CAM-100` for F005's material-resolution checks.

5. **`ValidationResult` as a dataclass** (not Pydantic) holding `list[ValidationIssue]` plus computed `is_valid`, `errors`, `warnings`, `infos`. Issues are values, not exceptions. Always collect all issues; never stop on first error.

6. **Three severities** — `ERROR`, `WARNING`, `INFO`. Gate 4 (CAM Readiness) treats WARNING as ERROR by default; lower gates allow warnings to pass.

7. **Gate 3 aggregates lower gates** — `KitchenValidationGate` re-runs Gate 1 over every cabinet (`KIT-008`) and Gate 2 over every row (`KIT-009`), so calling Gate 3 alone yields a full kitchen-level picture without requiring callers to loop.

8. **English messages, stable codes**. Localization is a future layer keyed by code; F004 doesn't bake Polish into messages.

The four gate classes and the extension API become Core's published validation surface. The issue code catalog (`docs/validation_codes.md`) becomes a stable reference for carpenters and LLM agents.

---

## Alternatives Considered

| Option | Why rejected |
|---|---|
| **A. No gates; let each consumer validate ad-hoc** | Each consumer reinvents the rules. Drift guaranteed. The plugin already shows this failure mode (`manifest_validator.py` is plugin-local). |
| **B. Single mega-`validate(kitchen)` function** | Cannot validate a single cabinet during editing without re-running the whole kitchen. UX disaster for F006. |
| **C. Pydantic validators in the model classes themselves** | Pydantic can't express cross-entity rules (sum of widths ≤ wall length; sink-base required when worktop has sink cutout). Local constraints are already in F003's `dimension_constraints`. |
| **D. JSON Schema as the validation language** | Same as C — no cross-entity expressions. Also doesn't compose with our Pydantic-based domain. |
| **E. External rule engine (Drools-style)** | Massive overkill for solo dev. Adds a runtime dependency and a DSL to learn. |
| **F. Async gates** | Gates are CPU-only and millisecond-fast. Async adds complexity for zero benefit. |
| **G. Stop on first ERROR** | UX failure. Carpenter wants the full list to fix in one pass. |
| **H. Exception-per-error** | Forces try/except chains in every caller. Issues as values compose with lists, filters, and serialization trivially. |
| **I. Stop on first WARNING in Gate 4** | Reasonable interpretation but too strict at v1.0. Warnings are still useful info; we just promote them to ERROR severity for the CAM gate's `is_valid` computation. Caller can still inspect them. |
| **J. Severity binary (ERROR / OK only)** | Loses the distinction between "blocks export" and "review recommended". WARNING exists for that gap. |
| **K. Single shared `ValidationContext`** | Becomes a god object holding everything every gate might need. Per-gate contexts are clearer and prevent accidental coupling. |
| **L. Pydantic `ValidationResult`** | Pydantic adds runtime overhead and stricter construction rules without benefit here. Dataclass + computed properties is enough. |
| **M. Gates as module-level functions** | Cannot have class-level `_checks` registry. Extension API would need module-level globals, which are uglier than `Gate.register_check(...)`. |
| **N. Codes as integers** | Strings are greppable, sortable, namespaced by prefix. Integers force a lookup table for human-readable names. |
| **O. Codes embedded in messages instead of separate field** | Messages may change wording across versions; codes must stay stable for i18n and tooling. Separate fields. |
| **P. Real-time validation on every model mutation** | Pulls validation into the model layer. Couples Core to a reactive system. Web UI calls gates on edit-blur; that's enough. |
| **Q. Plugin's `manifest_validator.py` as the implementation** | Plugin-internal, calls Blender APIs, not callable from CLI/Web. Wrong location (Rule 4). |
| **R. Stateful gates with caching** | Gates are cheap. Caching would need invalidation on every model change — more code to maintain than it saves. |
| **S. Gates 1 and 2 invocable in parallel** | Solo dev; not the bottleneck. Synchronous. |
| **T. Localize messages now** | i18n is a layer above codes. Stabilizing codes first means we can translate later without touching gate code. |
| **U. Hook system / event emission** | Out of scope. Caller decides what to do with the result. |
| **V. Auto-fix engine** | `fix_hint` is a string suggestion to the human, not executable code. Auto-fix is post-v1.0 (Could). |

---

## Consequences

### Positive
- **One source of truth for "is this valid?"** — Web, CLI, render adapter all get the same answer.
- **Extension API is the seam for F005** — material checks slot in cleanly via `register_check`; F004 doesn't need to know about catalog.
- **Stable codes survive message edits** — we can rewrite a message in v1.1 without breaking tooling that grepped for `CAB-001`.
- **Aggregation in Gate 3** — calling `KitchenValidationGate` alone yields a full kitchen-level picture; callers don't have to loop.
- **`WARNING-as-ERROR` in Gate 4** matches reality — CNC export is the last chance to catch issues; permissive mode would be a foot-gun.
- **Per-gate context** keeps each gate's contract tight and testable.
- **Codes catalog (`docs/validation_codes.md`)** doubles as a carpenter-facing reference and an LLM-agent lookup.
- **No new runtime dependencies** — pure Python stdlib + Pydantic (already there).

### Negative
- **~30 codes to register, document, test** — significant typing. Mitigated by template-style tests (one fixture cabinet per failure code, parametrized).
- **F005 must know about F004's class API** — coupling at the import level. Acceptable; both live in Core.
- **Code registry can drift from docs** — every new check must be added to `validation_codes.md`. The `kitchen-cli list-checks` (Should-have) closes this loop later.
- **Gate 3 internally calling Gate 1/2 means a malformed Gate 1 implementation cascades into Gate 3 failures** — clearer error in the result but harder to bisect during debugging. Mitigated by unit tests covering each gate alone.

### Neutral
- **Dataclass result types vs Pydantic** — small difference, mostly stylistic. Codifies the "issues are values, not validated objects" stance.
- **English-only messages** — temporary; reasonable for a Polish solo dev who reads English code fluently. Codes preserve future-translatability.
- **The plugin's own validation continues to exist inside the plugin** — orthogonal concern; our gates run before the plugin sees data. Two parallel validation systems serve two different audiences (us and the plugin's standalone users). Rule 4 stands.

---

## Affected Files (canonical)

### Created
- `src/kuchnie_core/validation/__init__.py`
- `src/kuchnie_core/validation/result.py` — `ValidationResult`, `ValidationIssue`, `Severity`
- `src/kuchnie_core/validation/codes.py` — `IssueCode`, registry, pre-registration
- `src/kuchnie_core/validation/context.py` — 4 context dataclasses
- `src/kuchnie_core/validation/check.py` — `Check` protocol + `BaseCheck`
- `src/kuchnie_core/validation/gates/__init__.py`
- `src/kuchnie_core/validation/gates/cabinet.py` — `CabinetValidationGate` + built-in checks
- `src/kuchnie_core/validation/gates/row.py` — `RowValidationGate` + built-in checks
- `src/kuchnie_core/validation/gates/kitchen.py` — `KitchenValidationGate` + built-in checks
- `src/kuchnie_core/validation/gates/cam_readiness.py` — `CAMReadinessGate` + built-in checks
- `tests/core/validation/test_result.py`
- `tests/core/validation/test_codes.py`
- `tests/core/validation/test_cabinet_gate.py`
- `tests/core/validation/test_row_gate.py`
- `tests/core/validation/test_kitchen_gate.py`
- `tests/core/validation/test_cam_gate.py`
- `tests/core/validation/test_extension.py`
- `tests/integration/test_full_validation_pipeline.py`
- `docs/validation_codes.md` — flat catalog of all codes

### Modified
- `docs/GLOSSARY.md` — 9 new/refined entries
- `docs/01_architecture.md` — Context Map shows `validation/` in Core
- `docs/03_implementation_placement.md` § Pattern 8 — link to F004 ADR

### Deleted or stubbed
- None. F004 is purely additive.

---

## LLM Hints

> Direct instructions for future LLM sessions in this decision area.

- **When asked "where does validation live?"** → `src/kuchnie_core/validation/`. Core, always. Never duplicate validation in Web/CAD/Render.
- **When asked "should I add a check?"** → If the rule is new and structural, add a built-in check in the appropriate gate's file. If the rule needs the catalog or other F005+ dependencies, add it in F005 (or later) using `Gate.register_check(...)`.
- **When asked "should the plugin's `manifest_validator.py` be used?"** → **No.** It's plugin-local and calls Blender APIs. Our gates are the source of truth. The plugin keeps its own checks for its own UI; we ignore it. See Alternative Q.
- **When asked "should we stop on first error?"** → **No.** Collect all. UX rule. See Alternative G.
- **When asked "should we raise exceptions?"** → **No, for domain errors.** Exceptions are for programmer errors (`validate(None)`). See Alternative H.
- **When asked "should we use Pydantic validators on the model classes?"** → **No.** Pydantic can't do cross-entity. Local Pydantic constraints already exist in F003. F004 handles the rest. See Alternative C.
- **When asked "can checks be async?"** → **No.** Gates are CPU-bound and fast. See Alternative F.
- **When asked "should I make a shared ValidationContext?"** → **No.** Per-gate contexts. God objects are out. See Alternative K.
- **When asked "where do issue codes live?"** → `validation/codes.py` (registry) + `docs/validation_codes.md` (catalog). Always add both in the same commit.
- **When asked "can I rename a code?"** → **No.** Codes are stable forever. Add a new code, deprecate the old one in the catalog (mark `superseded_by: NEW-CODE`). Tooling and i18n depend on stability.
- **When asked "should warnings block CAM export?"** → **Yes**, in Gate 4. WARNING is promoted to ERROR for `is_valid` computation in CAM stage. Carpenter can still inspect them; the rule is "no surprises at the CNC". See Alternative I (we did the opposite of strict-first-WARNING — we instead make Gate 4 strict overall).
- **When asked "should I add real-time validation in the web app?"** → **No.** Gates fire on edit-blur / save, not on keystroke. F006 owns this UX. See Alternative P.
- **When asked "should we localize messages?"** → **No** in v1.0. Codes are stable; localization is a layer added later that keys off code. See Alternative T.
- **When asked "can F005 add new codes (KIT-100, CAM-100)?"** → **Yes.** F004 reserves these codes in the registry as placeholders; F005 ships the actual check implementations. The split is intentional: F004 publishes the contract, F005 fills it.
- **When asked "should Gate 3 re-run Gates 1 and 2?"** → **Yes.** `KIT-008` and `KIT-009` aggregate. Callers don't have to loop. See Open Q10 in spec.
- **When asked "should there be a fifth gate?"** → **No.** The four-stage model from TopSolid is the design. New stages would need an ADR superseding this one.
- **Do not propose:**
  - Replacing dataclass result with Pydantic.
  - Adding a rule-engine DSL.
  - Caching validation results.
  - Adding a "lint" mode separate from gates (gates *are* the lint).
  - Embedding code lookups in messages (they're separate fields).
  - Hot-reloading rules from a remote config service.
  - ML-based anomaly detection ("this kitchen looks unusual").
- **Related ADRs:**
  - **F001 (Construction Method)** — Gate 1 verifies `construction_method_id` resolves; Gate 3 verifies project default resolves.
  - **F002 (Recipe Engine)** — Gate 1 verifies `recipe_id` resolves; Gate 4 consumes engine output.
  - **F003 (Template Registry)** — Gate 1 reads template's `dimension_constraints` and `default_sub_assemblies`. Note: `TemplateInstantiationError` is a *fast* check at instantiation; Gate 1 is the *thorough* re-check at validation time.
  - **F005 (Material Resolver)** — Adds checks via `register_check`; uses reserved codes `KIT-100` and `CAM-100`.
  - **F006 (Web Sidebar)** — Calls Gate 1 on cabinet save, Gate 2 on row reorder, Gate 3 on "generate render".
  - **F007 (Blender Adapter)** — Calls Gate 3 before invoking Blender; refuses to render on ERROR.
  - **F008 (CLI Cut List / DXF)** — Calls all four gates; refuses to export on ERROR; surfaces warnings prominently.

---

## Sign-off

- [ ] `docs/GLOSSARY.md` updated with 9 entries.
- [ ] `docs/validation_codes.md` published with ~30 codes.
- [ ] All four gates implemented with built-in checks.
- [ ] All listed `IssueCode`s registered.
- [ ] `register_check` extension API works (tested).
- [ ] Tests in place: per-gate test files + extension test + full-pipeline integration test.
- [ ] `examples/kitchen_nowak.yaml` passes all four gates cleanly.
- [ ] Reserved codes `KIT-100` and `CAM-100` exist in the registry with `default_severity: ERROR` and a description noting F005 ownership.
- [ ] Status moved from `Proposed` → `Accepted` after first green full-pipeline integration test run.
