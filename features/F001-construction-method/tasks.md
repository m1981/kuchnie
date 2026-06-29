# F001 Tasks — Construction Method

> Pick the next unchecked box in **Implementation — Must**. Do not skip ahead.

---

## Pre-flight

- [x] `spec.md` Open Questions all answered.
- [x] `adr.md` written and `Accepted`.
- [x] Primary bounded context confirmed: Core.
- [x] New terms identified: `ConstructionMethod`, `JoineryType`, `BackType`, `ConstructionMethodRegistry`.

---

## Implementation — Must (gate-blocking)

### 1. Enums

- [ ] Create `src/kuchnie_core/construction.py`.
- [ ] Define `class JoineryType(str, Enum)` with values: `DOWEL_CAMLOCK`, `CONFIRMAT`, `DADO`, `BUTT_GLUE`.
- [ ] Define `class BackType(str, Enum)` with values: `GROOVE`, `NAILED`, `RABBET`, `SCREWED`.
- [ ] Define `class DrillingSystem(str, Enum)` with values: `SYSTEM_32`, `NONE`.

### 2. ConstructionMethod model

- [ ] Define `class ConstructionMethod(BaseModel)` with fields:
  - `id: str` (slug, e.g., `dowel_camlock_18`)
  - `name: str` (human label)
  - `side_thickness_mm: int`
  - `top_thickness_mm: int`
  - `bottom_thickness_mm: int`
  - `back_thickness_mm: int`
  - `shelf_thickness_mm: int`
  - `front_thickness_mm: int`
  - `joinery: JoineryType`
  - `back_attachment: BackType`
  - `back_recess_mm: int`
  - `front_overlay_mm: int`
  - `front_gap_mm: int`
  - `cabinet_gap_mm: int`
  - `drilling_system: DrillingSystem`
  - `system32_offset_mm: int`
  - `system32_spacing_mm: int` (default 32)
- [ ] Use `model_config = ConfigDict(frozen=True)` (immutable).
- [ ] Add `Field(..., gt=0)` validators where appropriate.

### 3. Registry

- [ ] Define `class ConstructionMethodRegistry` in same file.
- [ ] Method `load_from_directory(path: Path) -> None` — scan `*.yaml`, load each.
- [ ] Method `get(method_id: str) -> ConstructionMethod` — raises `KeyError` if missing.
- [ ] Method `list_all() -> list[ConstructionMethod]`.
- [ ] Method `reload()` — clear and re-load.
- [ ] Module-level singleton: `default_registry = ConstructionMethodRegistry()`.

### 4. YAML data

- [ ] Create `src/kuchnie_core/construction_methods/dowel_camlock_18.yaml`:
  ```yaml
  id: dowel_camlock_18
  name: "Dowel + Cam-lock, 18mm carcass"
  side_thickness_mm: 18
  top_thickness_mm: 18
  bottom_thickness_mm: 18
  back_thickness_mm: 3
  shelf_thickness_mm: 18
  front_thickness_mm: 19
  joinery: DOWEL_CAMLOCK
  back_attachment: GROOVE
  back_recess_mm: 10
  front_overlay_mm: 2
  front_gap_mm: 2
  cabinet_gap_mm: 0
  drilling_system: SYSTEM_32
  system32_offset_mm: 37
  system32_spacing_mm: 32
  ```
- [ ] Create `src/kuchnie_core/construction_methods/confirmat_18.yaml` (use `joinery: CONFIRMAT`, `back_attachment: NAILED`, other values as appropriate).

### 5. Model updates

- [ ] Edit `src/kuchnie_core/model.py`:
  - [ ] Add `construction_method_id: str` to `CabinetInstance`.
  - [ ] Add `default_construction_method_id: str` to `Kitchen`.
- [ ] Edit `src/kuchnie_core/loader.py`:
  - [ ] On load, if `construction_method_id` missing on a cabinet, fall back to `kitchen.default_construction_method_id`.
  - [ ] If kitchen YAML predates v1.0 (no `default_construction_method_id`), inject `dowel_camlock_18` and log a warning.
- [ ] Edit `src/kuchnie_core/serialize.py`:
  - [ ] Ensure round-trip preserves both fields.

### 6. Schema publication

- [ ] Create `docs/schemas/kitchen_config.v1.0.yaml` — export from Pydantic:
  - Either `Kitchen.model_json_schema()` dumped to YAML, or a hand-written annotated schema.
  - Include a header: `version: "1.0"`, `published: 2026-06-28`, `source: src/kuchnie_core/model.py`.

### 7. Example

- [ ] Create `examples/kitchen_nowak.yaml`:
  - Wrocław address
  - `default_construction_method_id: dowel_camlock_18`
  - 2 rows, ~6 cabinets total
  - References to decors by `decor_id` (placeholder IDs OK if catalog isn't wired yet)
- [ ] Validate it loads without warnings.

### 8. Tests

- [ ] Create `tests/core/test_construction_method.py`:
  - [ ] `test_load_registry_from_directory()`
  - [ ] `test_get_method_by_id()`
  - [ ] `test_get_unknown_method_raises_keyerror()`
  - [ ] `test_method_is_immutable()` — assert `frozen=True` works
  - [ ] `test_method_validates_positive_thicknesses()`
- [ ] Create `tests/core/test_yaml_roundtrip.py`:
  - [ ] `test_kitchen_nowak_roundtrip_byte_identical()`
  - [ ] `test_cabinet_inherits_default_method()` — cabinet without explicit method gets project default
  - [ ] `test_cabinet_explicit_method_overrides_default()` — even though we don't use it in v1.0, the model supports it (and F001 ADR commits to this future)
- [ ] All tests pass: `pytest tests/core/`.

---

## Implementation — Should

- [ ] Add `kitchen-cli list-construction-methods` command (lists all method IDs + names).
- [ ] Add `kitchen-cli show-method <id>` (prints full YAML).

---

## Cross-context Impact

- [ ] **CAD (`kitchen-cad/`):** thin read-only consumer. `panel_calculator.py` currently reads `SETTINGS["corpusThickness"]`-style flat values from a global dict. Phase 2 (F002) replaces these reads with `cabinet.construction_method.side_thickness_mm`. **F001 itself does not modify CAD code** — it just makes the new data available.
- [ ] **Render (plugin adapter):** does not exist yet (F007). F001 makes no changes to plugin or adapter.

---

## Documentation

- [ ] `docs/GLOSSARY.md` updated with 4 new terms:
  - [ ] `ConstructionMethod`
  - [ ] `JoineryType`
  - [ ] `BackType`
  - [ ] `ConstructionMethodRegistry`
- [ ] `docs/01_architecture.md` Context Map updated to show `ConstructionMethod` inside Core.
- [ ] `docs/schemas/kitchen_config.v1.0.yaml` exists.
- [ ] `examples/kitchen_nowak.yaml` exists.

---

## Validation

- [ ] All Must boxes ticked above.
- [ ] `pytest tests/core/` passes.
- [ ] No `bpy` / `reflex` / `fastapi` imports in `src/kuchnie_core/`.
- [ ] No regression in any pre-existing test.
- [ ] `examples/kitchen_nowak.yaml` loads and round-trips byte-identical.
- [ ] Manual check: `grep -r "corpusThickness" src/kuchnie_core/` returns no hits (legacy term not leaking into Core).

---

## Close-out

- [ ] `status.md` set to `done` with `completed` date.
- [ ] `features/INDEX.md` row F001 updated to ✅.
- [ ] `docs/PHASES.md` Phase 1 gate criteria all ticked.
- [ ] `docs/PHASES.md` Phase 1 Sign-off filled with date + commit hash.
- [ ] `docs/PHASES.md` Phase Overview table: Phase 1 → ✅, Phase 2 → 🔵.
- [ ] `features/INDEX.md` "Current Focus" updated to F002.
- [ ] Commit message: `feature: close F001 — Construction Method`.

---

## Notes / Scratch

> Use this section while implementing. Promote to ADR if a decision emerges.

- _(empty — fill while working)_
