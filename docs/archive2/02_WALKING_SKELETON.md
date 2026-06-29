# 02 — Walking Skeleton

> **Purpose.** Smallest end-to-end slice that exercises every architectural boundary in `01_DECISIONS.md`. **Not a prototype** — it becomes the foundation. Subsequent features add meat to these bones; they never restructure them.
>
> **Done definition.** One pre-defined kitchen (one base-door cabinet) flows from YAML → live JPG preview → photoreal PNG → cut-list CSV, with every subsystem touched and every cross-boundary contract proven. **Time: ~1 week.**

---

## 1. The Skeleton Journey (the slice)

```
examples/skeleton_kitchen.yaml
   1 cabinet: base-door 600×720×560
   2 decor slots: body=K8685, front=K8685
        │
        ▼
   kuchnie_core.loader.load_kitchen()          ← parses YAML
        │
        ▼
   Kitchen (in memory)
        │
        ├──▶ kuchnie_core.recipe.decompose(kitchen)
        │    └─▶ kitchen_cad.panel_calculator.calculate_panels()
        │        └─▶ list[Panel] (sides, top, bottom, back, door, shelf)
        │           │
        │           ├──▶ kitchen_cad.csv_generator.generate_cutting_csv()
        │           │    └─▶ output/skeleton/cuts.csv               ✓ UC3 (partial)
        │           │
        │           └──▶ kitchen_cad.drill_engine.apply_all_drilling()
        │                └─▶ list[Panel] with DrillPoints
        │
        ├──▶ kuchnie_core.render.bake_scene(kitchen)
        │    └─▶ subprocess: krono-compositor-mvp/gen_kitchen.py
        │        └─▶ 5 passes in assets/scenes/skeleton/main/      (cached ~30s)
        │           │
        │           └──▶ kuchnie_core.render.composite(kitchen, decors)
        │                └─▶ HTTP POST localhost:8000/api/v1/render
        │                    └─▶ JPG bytes (~500ms)                 ✓ UC1
        │
        ├──▶ kuchnie_core.render.photoreal(kitchen)
        │    └─▶ subprocess: blender --background --python kitchen-plugin/src/main.py
        │        └─▶ output/skeleton/photoreal.png                  ✓ UC2 step 7-10
        │
        ├──▶ kuchnie_core.materials.MaterialResolver.resolve_role("front", cabinet)
        │    └─▶ reads catalog/db/catalog.db
        │        └─▶ ResolvedMaterial(decor_id, name, paired_edge_id, texture_path...)
        │
        └──▶ kitchen-app/ skeleton route
             └─▶ Reflex page: title, JPG preview, decor picker (2 options),
                  "Export CSV" button, "Generate photoreal" button
```

**Six subsystems exercised. Three outputs produced. One YAML in.**

---

## 2. The Shared YAML Schema (v0.1, deliberately minimal)

`examples/skeleton_kitchen.yaml`:

```yaml
schema_version: "0.1"
project_name: skeleton

# Just one run with one cabinet — no walls, no corners, no plinth in v0.1.
runs:
  - id: run_0
    cabinets:
      - id: cab_001
        type: base_door
        width_mm: 600
        height_mm: 720
        depth_mm: 560
        doors: 1
        shelves: 1

# Kitchen-level material slots. Cabinets reference slot names; slots reference decor ids.
material_slots:
  body: K8685
  front: K8685
  back: HDF_WHITE   # placeholder decor for back panel

# Single construction method for the whole kitchen (registry expanded in F001).
construction_method: dowel_18  # not yet a registry; placeholder string
```

This is **deliberately thinner** than the eventual full schema. Walls, corners, plinth, multiple runs, cabinet-level overrides — all deferred to Phase 1+.

---

## 3. Files To Create (exhaustive list)

### Glue layer in `src/kuchnie_core/`

| Path | What it does | Lines |
|---|---|---|
| `src/kuchnie_core/recipe.py` | `cabinet_to_corpus_spec(cab)` adapter; `decompose(kitchen) → list[Panel]`. Imports from `kitchen_cad`. | ~80 |
| `src/kuchnie_core/render.py` | `bake_scene(kitchen, scene_id)` (subprocess to compositor's gen_kitchen.py); `composite(kitchen, scene_id) → bytes` (HTTP to compositor); `photoreal(kitchen, path)` (subprocess to kitchen-plugin/main.py). | ~120 |
| `src/kuchnie_core/loader.py` | **Refactor existing**. Read the v0.1 YAML schema above; produce `Kitchen(runs=[Run(cabinets=[...])])`. Drop the legacy `CabinetInstance` fields. | ~60 (replacement) |
| `src/kuchnie_core/model.py` | **Refactor**. Replace `CabinetInstance`/`Panel`/`MachiningOp` with re-exports: `from kitchen_plugin.kitchen.cabinet import Cabinet`, `from kitchen_cad.models import Panel, DrillPoint, EdgeBand`. Keep `Kitchen`, `Run` (was `Row`), `WorktopSegment`. | ~50 (replacement) |
| `src/kuchnie_core/materials/__init__.py` | **Existing.** Already an adapter over `catalog/db/catalog.db`. No changes for skeleton. | 0 |
| `src/kuchnie_core/__init__.py` | Public exports: `Kitchen`, `Cabinet`, `Panel`, `load_kitchen`, `decompose`, `bake_scene`, `composite`, `photoreal`, `MaterialResolver`. | ~30 |

### Each subsystem — minimal additions

| Subsystem | What to add | Lines |
|---|---|---|
| `kitchen-cad/` | One adapter file `kitchen_cad/skeleton_adapter.py` that takes our shared `Kitchen` schema and produces a `CorpusSpec` for the one cabinet. **No changes to existing kitchen-cad code.** | ~40 |
| `kitchen-plugin/` | Update `config_parser.py` to ALSO accept YAML (today: JSON only). One new function `load_kitchen_yaml(path)` that maps our schema → kitchen-plugin's internal `Config` dict. Existing JSON loader untouched. | ~50 |
| `krono-compositor-mvp/` | Update `gen_kitchen.py` to accept `--kitchen-yaml` flag in addition to its current `layout.json` input. Map our schema → its expected dict. **No changes to compositor's `SceneCompositor` or FastAPI.** | ~30 |
| `catalog/` | **No changes.** Already provides everything via the SQLite DB. | 0 |
| `kitchen-app/` | One new route `/skeleton`. Reflex state with: skeleton kitchen loaded once, 2-decor picker, JPG `<img>` from compositor endpoint, two action buttons (Export CSV, Generate Photoreal). | ~150 |

### Build & wiring

| Path | What it does | Lines |
|---|---|---|
| `pyproject.toml` (root) | Workspace declaration. Lists each subdir as a workspace package; pins shared deps (pydantic, pyyaml). | ~40 |
| `Makefile` (root) | Targets: `setup` (creates `.envrc` with PYTHONPATH), `skeleton` (runs end-to-end), `compositor-up` (starts compositor's FastAPI), `kitchen-app-up` (starts Reflex), `bake-skeleton`, `render-skeleton`, `csv-skeleton`. | ~50 |
| `.envrc` (root) | `export PYTHONPATH=src:catalog:kitchen-cad/src:kitchen-plugin/src:krono-compositor-mvp/src:kitchen-app` | 1 |
| `scripts/check_imports.py` | AST lint: each subsystem may import `kuchnie_core` but not any other sibling. CI gate. | ~80 |
| `examples/skeleton_kitchen.yaml` | The one example. | ~20 |
| `tests/test_skeleton_e2e.py` | End-to-end: load YAML → decompose → assert panel count = 7; bake scene (mocked or real); composite → assert JPG bytes returned; export CSV → assert file exists; photoreal → assert PNG exists. | ~100 |

**Estimated new code: ~900 lines.** Mostly glue, adapters, and one CI script. Production code adds zero net lines (no domain logic written; existing prototypes do all the work).

---

## 4. The 5-Day Schedule

### Day 1 — Workspace + import wiring

- [ ] Write root `pyproject.toml` declaring workspace + shared deps (pyyaml, pydantic 2.x)
- [ ] Write root `Makefile` with `setup`, `skeleton`, dev targets
- [ ] Write `.envrc` / shell snippet for `PYTHONPATH`
- [ ] Verify `python -c "from kitchen_cad.models import CorpusSpec; from kitchen_plugin.kitchen.cabinet import Cabinet; from compositor.application.scene_compositor import SceneCompositor; from catalog.models.domain import DecorSummary; print('all imports work')"` succeeds.
- [ ] Write `scripts/check_imports.py` and run on current codebase to confirm "no cross-imports exist today" (baseline).

**Done when:** `make setup` is idempotent and `python -c "..."` proves all subsystems are importable.

### Day 2 — kuchnie_core glue

- [ ] Refactor `src/kuchnie_core/model.py`: keep `Kitchen`, rename `Row→Run`, re-export `Cabinet` from kitchen-plugin and `Panel` from kitchen-cad.
- [ ] Refactor `src/kuchnie_core/loader.py`: read the new v0.1 YAML schema (above).
- [ ] Write `src/kuchnie_core/recipe.py` with `cabinet_to_corpus_spec(cab)` and `decompose(kitchen) → list[Panel]`.
- [ ] Write `src/kuchnie_core/render.py` with subprocess+HTTP wrappers.
- [ ] Update `src/kuchnie_core/__init__.py` public surface.
- [ ] Delete files listed in `01_DECISIONS.md` § D4 retirements (move to `src/kuchnie_core/_retired/` to keep git history; remove from `__init__.py`).

**Done when:** `from kuchnie_core import load_kitchen, decompose, composite, photoreal, MaterialResolver` works.

### Day 3 — Compositor + kitchen-plugin YAML acceptance

- [ ] Add `--kitchen-yaml` flag to `krono-compositor-mvp/gen_kitchen.py` + mapper.
- [ ] Bake `examples/skeleton_kitchen.yaml` → confirm 5 passes appear in `assets/scenes/skeleton/main/`.
- [ ] Add `load_kitchen_yaml()` to `kitchen-plugin/src/config_parser.py` + mapper.
- [ ] Run `blender --background --python kitchen-plugin/src/main.py -- examples/skeleton_kitchen.yaml --validate` → confirm manifest.json emitted.
- [ ] Test: `python -m kuchnie_core` (`__main__.py` for the skeleton CLI) with `bake skeleton_kitchen.yaml` and `photoreal skeleton_kitchen.yaml` flags works.

**Done when:** both renderers accept the YAML schema and produce their outputs from CLI.

### Day 4 — kitchen-cad CSV path + kitchen-app skeleton page

- [ ] Add `kitchen_cad/skeleton_adapter.py` with `kitchen_to_corpus_specs(kitchen)`.
- [ ] In `kuchnie_core.recipe.decompose`, glue to `kitchen_cad.calculate_panels` + `apply_all_drilling`.
- [ ] Wire `kuchnie_core.export_cutlist(kitchen, path)` calling `kitchen_cad.csv_generator.generate_cutting_csv`.
- [ ] Add Reflex route `/skeleton` to kitchen-app: hardcoded skeleton kitchen, 2-decor picker, `<img>` from compositor's `/api/v1/render`, two action buttons.
- [ ] Confirm: open `http://localhost:3000/skeleton`, click "Export CSV" → CSV downloads; click "Generate photoreal" → progress, then PNG link.

**Done when:** the Reflex UI shows a JPG, exports a CSV, and triggers a photoreal render.

### Day 5 — End-to-end test + CI lint + docs

- [ ] Write `tests/test_skeleton_e2e.py` covering the full pipeline (with subprocess calls allowed; skip Blender steps if not on dev machine via `pytest.mark.requires_blender`).
- [ ] Run `scripts/check_imports.py` in CI mode → fail build on any cross-subsystem import not via `kuchnie_core`.
- [ ] Write `kitchen-app/.env.example` and `krono-compositor-mvp/.env.example` for whatever runtime config needed.
- [ ] Update `00_README.md` if any path changed during the week.
- [ ] Tag commit `skeleton-v0.1`.

**Done when:** `make skeleton` runs green end-to-end on a clean checkout; `git tag` records the milestone.

---

## 5. Acceptance Criteria (skeleton complete iff all true)

- [ ] `make setup` is idempotent.
- [ ] `python -c "from kuchnie_core import Kitchen, Cabinet, Panel, load_kitchen, decompose, composite, photoreal, MaterialResolver"` succeeds.
- [ ] `scripts/check_imports.py` passes (no cross-subsystem imports except via kuchnie_core).
- [ ] `make skeleton` does: bake → composite → CSV → photoreal, producing 4 output files.
- [ ] `tests/test_skeleton_e2e.py` passes.
- [ ] kitchen-app `/skeleton` route loads in browser, shows JPG, exports CSV, triggers photoreal.
- [ ] Each subsystem's own existing test suite still passes (no regressions).
- [ ] `01_DECISIONS.md` § D4 retired files are gone from `kuchnie_core` (in `_retired/` or deleted).
- [ ] `06_AUDIT_EVIDENCE.md` re-run: cross-imports section confirms `kuchnie_core` imports each sibling exactly once, no sibling imports any other.

---

## 6. What the Skeleton Does NOT Do (deferred to roadmap)

- ❌ Multiple cabinets / multiple runs / walls / corners
- ❌ Cabinet templates with constraints (F003 work)
- ❌ Construction method registry (F001 work — `construction_method: dowel_18` is a string placeholder)
- ❌ Validation gates with codes (F004 work — only "exception or pass" today)
- ❌ Material resolver chain `role→slot→decor→variant` (F005 — uses direct decor IDs in slots for now)
- ❌ BOM cost (kitchen-app's BOMGenerator not wired in skeleton)
- ❌ DXF (F008 work — skeleton outputs CSV only)
- ❌ Drill pattern CSV (F008)
- ❌ Cost estimate (F008)
- ❌ kitchen-cli binary (F008)
- ❌ Two-phase validation (logical pre-build + manifest geometric — F004)
- ❌ Reflex configurator (only the one skeleton page; F006)
- ❌ Decor filtering UI / picker by producer / collection (F005 + F006)

**Each ❌ is on the post-skeleton roadmap (`03_ROADMAP.md`).**

---

## 7. Risks + Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Reflex `<img>` polling kills CPU during decor swap | Medium | Use Reflex's `rx.image(src=state.preview_url)` with debounced state update. Test on Day 4. |
| Compositor's `gen_kitchen.py` not idempotent on the same scene_id | Low | Verified in audit — output dir is recreated per run. If wrong, add cache-key by kitchen hash on Day 3. |
| `PYTHONPATH` hack fails on Windows (carpenter may install on a Windows laptop later) | Medium | Use `setup.py develop` mode as fallback. For v0.1, document POSIX-only. |
| pydantic v1 vs v2 mismatch across subsystems | Medium | Audit: catalog uses pydantic v2 (FastAPI), kitchen-cad uses pydantic v2, kitchen-app uses pydantic (via SQLModel — v1 or v2 depending). **Day 1 task: pin pydantic v2 in root workspace; let each subsystem's own venv pin if conflict.** |
| Blender invocation slow (~30s) blocks skeleton tests in CI | Low | Mark Blender steps with `pytest.mark.requires_blender`; skip in CI; cover with unit-test stubs. Real run is part of `make skeleton`, not pytest. |

---

## 8. Why This Order

The skeleton is sequenced so that **each day produces something independently observable**:

1. Day 1 → "I can import everything" (proves D3 packaging)
2. Day 2 → "I have a Kitchen object with panels in memory" (proves D2 winner table for Recipe + Cabinet)
3. Day 3 → "I have a JPG and a PNG from the same YAML" (proves both render paths)
4. Day 4 → "I have a UI that shows it and exports CSV" (proves end-to-end through the user-facing surface)
5. Day 5 → "It can't drift back" (CI lint + tests freeze the architecture)

If Day N fails, Days N+1+ stop, and the failure is locally bounded (one subsystem's adapter, not the whole architecture).

---

## 9. After The Skeleton

**Hand-off to `03_ROADMAP.md`.** The skeleton is the foundation; each feature in the roadmap adds capabilities by extending one or two of the files listed in § 3 — never by introducing a new architectural pattern. If a future feature requires changing the cross-import rule (D6), that's a signal the feature is wrong, not the architecture.
