# Changelog

All notable changes to `kuchnie-core` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased] — 2026-08-01 — Edge-band identity by thickness (G11, wk-593a317b)

### Added
- `kuchnie_core.model.EdgeBand` gains `catalog_edge_code: str = ""` —
  supplier SKU for ordering (e.g. `K-8685-SM/BS/PD`), empty when unknown.
- `kuchnie_core.bom._edge_material_key(band)` — builds the BOM grouping
  key for `edge_band` items as `{material}_{thickness_mm:.1f}`, with
  `_{catalog_edge_code}` appended when a code is present. `BOMItem.material`
  for `category="edge_band"` now carries this composite key instead of the
  plain material name, so a 0.8×22 carcass ABS band and a 2.0×23 front ABS
  band price and purchase as distinct lines instead of collapsing into one.
  Price lookup falls back to the plain material name when no price is keyed
  under the composite (backward compatible with existing `edge_prices`
  tables keyed on material alone).
- `kuchnie_core.export.edging_csv.EdgingRow` gains `catalog_edge_code: str`
  and the CSV output gains a trailing `Kod_krawedzi` column. `EdgingRow.material`
  itself is unchanged (still the plain `band.material`) — only the BOM's
  material key is composite; the edging worklist keeps material and
  thickness as separate columns.
- `kuchnie-core/tests/test_G11_edge_band_identity.py` — 15 tests covering
  the key format, price fallback, and CSV column.
- `kuchnie_core.model.EdgeBand` gains `width_mm: float = 0.0` — purchase-
  identity width (e.g. Egger 23mm vs a Kronospan-partner 22mm band for the
  same 18mm board). Width is supplier/decor-dependent so it is **not**
  derived by core; it defaults to `0.0` ("unknown") and is only populated
  by a caller that knows the specific supplier roll (the ERP catalog
  layer). `_edge_material_key` appends `x{width_mm:.0f}` when known, so
  same-material/same-thickness bands with different purchase widths now
  price and purchase as distinct lines; the key format is byte-identical
  to before when width is unset.
- `kuchnie_core.model.CabinetInstance` gains
  `front_edge_banding_thickness_mm: float = 2.0`, alongside the existing
  `edge_banding_thickness_mm: float = 0.8` (now corpus/carcass-only).
  Both defaults are owner-confirmed: 0.8mm ABS on carcass edges, 2.0mm ABS
  on fronts. `kuchnie_core.catalog._front_eb` now sources
  `front_edge_banding_thickness_mm`; `_body_eb` is unchanged.
  `kuchnie_core.loader.load_cabinet` reads the new optional YAML key
  `oklejanie.grubosc_frontu` (via `.get`, default `2.0`) into the new
  field; `oklejanie.grubosc` keeps mapping to the corpus field as before.
- `kuchnie_core.export.edging_csv.EdgingRow` gains `width_mm: float = 0.0`
  and the CSV gains a `Szerokosc_obrzeza_mm` column, placed right after
  `Grubość_mm` and before `Kod_krawedzi`; empty string when width is
  unknown.
- New end-to-end tests in `test_G11_edge_band_identity.py` load
  `fixtures/K01.yaml` through the real `load_cabinet`/`decompose`
  pipeline (no hand-built shortcuts) and assert drawer-front panels carry
  `thickness_mm == 2.0` on their bands, carcass panels `0.8`, and that
  `calculate_bom` on that decomposition emits at least two distinct
  `edge_band` material keys differing by thickness. Loader tests cover
  `oklejanie.grubosc_frontu` present (overrides) and absent (defaults to
  `2.0`).

### Notes
- Real decompositions now emit distinct thicknesses: `kuchnie_core.catalog`
  sources corpus bands from `edge_banding_thickness_mm` (0.8mm, owner-
  confirmed) and front bands from the new `front_edge_banding_thickness_mm`
  (2.0mm, owner-confirmed), so a stock K01/G01 decomposition already
  produces separate 0.8mm carcass and 2.0mm front `edge_band` BOM lines —
  this is no longer plumbing-only. `catalog_edge_code` and `EdgeBand.width_mm`
  remain unpopulated by the core decomposer/loader (both default empty/0.0)
  — populating them from real supplier SKUs and purchase widths is a catalog
  DB lookup that belongs to the ERP layer, not core. `legrabox.py` still
  emits no `EdgeBand` at all.
- No downstream impact found: kitchen-erp's BOM views (`domain_adapter.py`,
  `variant_derivation.py`) bucket by `BOMItem.category`/`role`/`measure`,
  never `BOMItem.material`, and its own `EdgingRow.material` usage reads
  the unchanged plain field. kitchen-cam and home-builder-adapter don't
  touch either field. `exercises/walking-skeleton-d60/run_production_leg.py`
  hand-rolls its own BOM/rozrys writers directly off `EdgeBand.material`
  and never calls `calculate_bom`/`export_edging_csv`, so the flagship
  exercise baseline is unaffected (re-ran the production leg: `generated/`
  output byte-identical to the pre-change committed copy).

---

## [Unreleased] — 2026-07-14 — Dashboard increment 1: by-goal roadmap + Serves: UC- warn (wk-a9212b40)

### Added
- `docs/roadmap-map.csv` gains a `uc` column mapping work items to use
  cases (assignments from the `docs/specs/use-cases.md` inventory).
- `scripts/dashboard.py` renders a second roadmap view grouped by use
  case (V3b) beside the by-stage view; UC goal labels parsed from the
  use-cases inventory table; unrouted items land in a visible "no UC"
  bucket.
- `scripts/spec-health.sh` warns (never fails) on specs lacking a
  `Serves: UC-` line — upward trace to a user goal (upstream-candidate;
  the check is generic, the UC- id pattern is this repo's).

---

## [Unreleased] — 2026-07-12 — Compositor catalog routed to catalog service (ADR-008, wk-03434168)

### Added
- `krono-compositor-mvp/src/compositor/presentation/catalog_source.py` —
  stdlib-only catalog source replacing the hardcoded CATALOG dict: pages
  `GET /catalog/decors`, folds variant rows into one material per decor
  (allowed_zone from the role union, swatch hex from `/catalog/full`'s
  color-family approximations, `img_url` from decor miniatures), caches
  in memory and to a disk snapshot for offline sales visits. Local
  presentation-owned tables: texture tiling widths and price grouping
  (spec: `krono-compositor-mvp/docs/specs/catalog-routing.md`).
- `krono-compositor-mvp/tests/test_catalog_source.py` — 16 tests against
  a faked catalog client: row mapping, zone derivation, discontinued
  filtering, contract shape, offline degradation to snapshot / to empty.
  Live smoke: 145 real decors served, render 200 with K5307/K552,
  worktop-only decor correctly refused on a FRONT zone.

### Changed
- `presentation/api.py`: `/api/v1/catalog` and `/render` material lookup
  go through `CatalogSource`; response shape unchanged.
- `assets/textures/*.jpg` renamed from invented slugs to real decor codes
  (K5307, K9103, K552, K190, K7031, K9561); `static/index.html` default
  zone materials updated to match.

### Fixed
- `static/index.html`: Alpine crash on first paint — `catalog.price_groups`
  evaluated while `catalog` was still null (`x-show` hides, it does not
  stop evaluation); now null-safe. Latent pre-existing bug.
- Materials without a tileable texture on disk no longer 500 on click:
  the payload carries an additive `renderable` flag (server checks
  `assets/textures/<id>.jpg`), the sidebar greys those decors out, and
  the click is guarded with a message instead of a failed render.

### Removed
- `presentation/catalog_db.py` (the hardcoded CATALOG dict, tr-88dc0d9a).

---

## [Unreleased] — 2026-07-09 — ADR-011 phase 3: Material mirror (kitchen-erp ← catalog)

### Added
- `kitchen-erp/kitchen_erp/core/catalog_client.py` — stdlib-only read
  client for the catalog service's paginated `/catalog/decors` endpoint
  (flat decor-variant rows, v_decors_full shape); typed
  `CatalogUnavailable` failure contract.
- `kitchen-erp/kitchen_erp/core/material_mirror.py` —
  `refresh_material_mirror()` converges Material rows onto catalog
  identity, keyed by new `Material.catalog_variant_id`. Identity (name,
  brand, category, sheet size, `has_woodgrain` from the catalog's
  `wood_grain` structure type) is catalog-owned; `price_per_unit` is
  ERP-owned — never touched on existing rows, new rows arrive at 0.0.
  Local-born rows (NULL key: admin-created, utility) are never touched.
- `tests/test_material_mirror.py` — 6 tests against a faked catalog
  client: populate, price preservation, idempotency, local-row isolation,
  role/discontinued filtering, typed offline failure. Live smoke against
  the real service: 134 variants mirrored, 24 woodgrain, second pass
  0 added / 134 unchanged.
- `AdminState.refresh_from_catalog()` + `mirror_status` — manual mirror
  refresh from the Admin panel.

### Changed
- `kitchen_erp/ui/state.py` seed: the ~25-row hand-seeded board catalog is
  gone; boards arrive via the mirror (populated once when empty; offline
  catalog degrades with a warning, never blocks boot). Demo project picks
  its default board from the mirror and is skipped gracefully when no
  boards exist yet. Named survivors: 3 utility materials (HDF back, 2 ABS
  edges) that catalog/ does not model.
- `Material` schema: `catalog_variant_id` column (indexed, nullable;
  ALTER-TABLE migration for existing databases).

---

## [Unreleased] — 2026-07-09 — truth-ledger v0.5.3: issue-fold first-wins hardening (ADR-006)

### Changed
- `scripts/truth`'s `fold_issues` is now first-wins on duplicate `wk-`
  issue ids, matching `fold()`'s claim handling (the F6 fix). Closes a
  gap found during a documentation-accuracy audit of the template: the
  prior last-wins rule protected an "update-by-refile" verb the CLI never
  actually implements (`truth issue` always mints a fresh id), so it was
  pure attack surface — a raw appended duplicate carrying `premises: []`
  could silently strip an open issue's ADR-001 protection, no backdated
  timestamp needed. This repo had three open issues with live premise
  links (`wk-03434168`, `wk-6716e9c8`, `wk-c67ffaa1`) exposed to it before
  this sync. Canary 48→49 (`FAULT R9`).
- `scripts/truth-canary.sh`, `scripts/test-truth-core.py` upstreamed via
  `copier update` (byte-identical pre-align, zero-conflict).
- `docs/adr/002-native-work-kernel.md` — canary-requirement wording
  correction (stale vs. diverged premise) carried in from the template.
- `docs/adr/003–006-*.md` added: satellite-placement doctrine,
  tracker-adapter seam, pre-edit whisper (Proposed, unimplemented),
  issue-fold first-wins.
- Standing claim filed as tr-e1b14049, citing the version and the fix.

---

## [Unreleased] — 2026-07-09 — truth-ledger v0.5.2: doc-health upstreamed

### Changed
- `scripts/doc-health.sh` now the generic template version (byte-identical
  pre-align, zero-conflict copier update): forbidden names config-driven
  via `scripts/doc-health.patterns` (kitchen dead names live there),
  exemptions generalized to path segments. Canary 45→48 (FAULT D1–D3).
- `.truth/README.md` — doc-health section + "Claim discipline" earned
  lessons (scope text to evidence; pin gate evidence output stable;
  commit-first ordering).
- Standing claim re-filed as tr-94a98135: tr-3591aae0's `--paths` were
  space-separated (stored as one nonexistent literal → tripwire dead);
  successor uses comma-separated paths + covers the patterns file.
  tr-3591aae0 queued for human retraction.

---

## [Unreleased] — 2026-07-09 — Doc cleanup: pre-ledger prose archived, doc-health gate

### Added
- `scripts/doc-health.sh` — corpus-wide tripwire for the two measured decay
  modes: dead component names (ADR-009/010/011) and broken relative links in
  live (non-archive) markdown. Fault-injection tested both checks.
- `check-governance.sh` Check 6 — any staged `.md` must leave the whole live
  corpus doc-health-clean (complements Check 1, which only gates added lines).

### Changed
- Entry-point repairs from the 2-detector sweep (dead links + routing
  coverage over 105 live docs): kitchen-erp/README (title, archived-doc
  links, now routes `docs/specs/`), root README (dead RESUME.md refs →
  `scripts/truth ready`), doc-routing.md (5 dead rows fixed; now routes
  GLOSSARY, kitchen-cam ROADMAP, kitchen-erp specs), kitchen-cam README
  (docs/ tree added), kitchen-cam architecture (Polish archive filenames),
  krono README (underscore link), catalog configurator-design (spec path).
- Dead component names reworded to ADR citations in 7 live docs
  (AGENTS.md roster, file-naming-convention, vision/01-user-journeys,
  home-builder-adapter AGENTS+README, kitchen-cam architecture, GLOSSARY).
- `docs/GLOSSARY.md` — ~25 stale file references repaired against disk.

### Removed (archived, tombstoned in place)
- → `docs/archive/`: 00-brief-understanding.md, home-build-5-external-plugin.md
- → `features/archive/TEMPLATE_spec.md` (F-system template; superseded by
  spec-convention) — `features/` is now archive-only
- → `catalog/docs/archive/ROADMAP.md` (phases 1–4 complete; ❄️ price calc noted)
- → `krono-compositor-mvp/docs/archive/ROADMAP.md` (all steps referenced an
  already-archived doc)
- → `kitchen-cam/docs/archive/design.md` (described modules deleted by ADR-010/012)

---

## [Unreleased] — 2026-07-09 — Feature-spec convention: ledger-wired specs

### Added
- `docs/spec-convention.md` — specs cite truth-ledger ids instead of
  restating facts; section contract, ADR-001 health semantics.
- `scripts/spec-health.sh` — tripwire judging every `*/docs/specs/*.md`
  by the ledger status of the ids it cites; wired into pre-commit
  (`check-governance.sh` Check 5: no unwired new specs, no silent spec
  deletion, staged spec changes must be healthy).
- `kitchen-erp/docs/specs/material-mirror.md` — pilot spec (ADR-011
  phase 3), fully wired (wk-d5df7e30 + 3 live ground-truth premises).
- AGENTS.md "Feature specs" entry-point section + component
  artifact-ownership routing; CLAUDE.md pointer.

---

## [Unreleased] — 2026-07-08 — ADR-011 phase 2: BOM geometry from kuchnie_core

### Added
- `kitchen-erp/kitchen_erp/core/domain_adapter.py` — `to_kuchnie_core()`
  maps `Cabinet` rows onto `kuchnie_core.CabinetInstance`;
  `quantities_from_decomposition()` folds panels back into the m2/lm
  quantities the BOM prices. `BASE_CABINET`/`WALL_CABINET`/`DRAWER_BASE`
  route to `dolna_drzwiowa`/`gorna_drzwiowa`/`dolna_szufladowa`.
- `kitchen-erp` now depends on `kuchnie-core` (editable path source).
- `tests/test_domain_adapter.py` (9 tests) — mapping contracts + panel
  quantities hand-computed from the construction method.

### Changed
- `BOMGenerator.generate()`: panel quantities and banded-edge lengths come
  from `kuchnie_core.decompose()` for supported module kinds; recipe
  formulas remain the fallback for kinds the hub cannot build yet
  (appliances, fillers, panels). Reference wall-cabinet price is now
  $141.05 (real panels) instead of $155.80 (formula estimates).

### Fixed
- Ghost front costs: a doorless/drawerless cabinet no longer pays front
  edging and front CNC cutting for a front part that was never added.

---

## [Unreleased] — 2026-07-08 — ADR-011: old BOM path deleted (kitchen-erp)

### Removed
- `kitchen-erp`: `Cabinet.calculate_cost()` (the pre-recipe direct cost path),
  the `use_new_bom` runtime toggle + UI switch, and the `*_new` method
  suffixes — the recipe-based `BOMGenerator` is now the only cost path.
  `CabinetCostResult` deleted (orphaned). `scripts/validate_migration.py`
  retired to `attic/` (its old-vs-new comparison job is done).

### Fixed
- `kitchen-erp` test suite repaired from 38 pass / 15 broken to 66 pass:
  fixtures updated for schema drift (`Material.unit`,
  `ProjectDefaults.edge_band_mat_id`, `Cabinet.type`,
  `Project.customer_name`), rules tests pinned to
  `get_default_hardware_rules()` instead of the app database, hardware
  names updated (`Drawer slides` → `Drawer System (Blum/Hettich)`).

### Added
- `kitchen-erp/tests/test_adr011_canonical_bom.py` — pins the deletion.
- `kitchen-erp/tests/test_calculations.py` — deterministic hand-computed
  pricing math for the canonical path (WALL_CABINET recipe, $155.80).

---

## [Unreleased] — 2026-07-03 — Trust audit freeze actions

### Changed
- `pyproject.toml`: declared `pydantic>=2,<3` (was imported but undeclared)
- `docs/doc-routing.md`: rewritten — `kitchen-cad/` → `kitchen-cam/`, `kitchen-plugin/` → `home-builder-adapter/`, added `kitchen-erp/` routing
- `.pi/doc-routing-prompt.md`: rewritten — same name substitutions
- `package.json`: trimmed dead `kitchen-agent/frontend` reference from `fix-all` script

### Added
- `docs/00-brief-understanding.md`: tombstone linking to `docs/vision/00-mission.md` (fixes ADR-009/011 dangling refs)
- `docs/freeze/DOC-TRUST-REPORT.md`: full trust audit of all 109 tracked `.md` files
- `docs/freeze/RESUME-MENU.md`: deferred items for post-freeze resumption (absorbed into RESUME.md, deleted)

### Stamped
- `kitchen-cam/README.md`, `kitchen-cam/ROADMAP.md`, `kitchen-cam/docs/specs/overview.md`, `docs/session-handoff-2026-07-02.md`: `> ⚠️ STALE` markers pointing to authoritative docs

---

## [Unreleased] — 2026-07-01 — Architecture decisions codified

### Added — ADR-012 Extension 6: `CabinetInstance.config` discriminated union

Sixth and final `kuchnie_core.model` extension required by ADR-012.
With this landed all six extensions are complete and Workstream 3
(ADR-010 completion — deleting `kitchen_cam.models`,
`panel_calculator`, `csv_generator`, and rewriting `machining.py`) is
fully unblocked.

Purely additive: `config` defaults to `None`, legacy loose fields
(`drawers`, `shelves`, `fronts`) remain in place, and the loader
synthesises `config` from them on load. No existing decomposer, test,
or fixture required changes.

- `kuchnie_core.model` — seven typed variant dataclasses (ADR-012 §6):
  * `BaseDoorConfig(shelves: list[float], doors: list[int])`
  * `BaseDrawerConfig(drawers: list[DrawerSlot])`
  * `CornerBlindConfig(corner_side, second_width_mm, shelves, doors)`
  * `CornerInternalConfig(carousel, shelves, doors)`
  * `SinkConfig(has_sorting_drawer, sorting_drawer, doors)`
  * `CargoConfig(cargo_type, cargo_colour, doors)`
  * `OvenConfig(cavity_height_mm, has_ventilation, reinforced_shelf)`
- `DrawerSlot` — English-fielded replacement for the legacy drawer dict
  (`id`, `system`, `height_mm`, `height_code`, `nl_mm`, `capacity_kg`).
- `CabinetConfig = Union[...]` — discriminated by concrete dataclass
  (`isinstance`), no explicit `type: Literal[...]` tag needed. Keeps the
  model plain-dataclass (no Pydantic dependency).
- `CabinetInstance.config: CabinetConfig | None = None` — new field.
  Legacy `drawers` / `shelves` / `fronts` fields kept until callers migrate.
- `loader._synthesise_config(cab) -> CabinetConfig | None` — mirrors
  `kitchen_cam.models.CorpusSpec._sync_config_from_legacy`. Maps every
  Polish cabinet type (`dolna_szufladowa`, `gorna_drzwiowa`,
  `dolna_legrabox`, plus forward-compatible corner/sink/cargo/oven
  aliases) to the correct variant. Unknown types return `None` (no
  false variant).
- `loader._apply_synthesised_config(cab)` — idempotent guard called from
  both `load_cabinet` (Polish YAML) and `_cabinet_from_schema` (English
  schema YAML). Preserves an explicitly-set `config` (no clobber).
- Loader helpers `_shelf_positions`, `_door_hinge_counts`,
  `_drawer_slot_from_dict` extract values from loose fields, accepting
  both Polish and English key names for robustness.
- Re-exported at package root: `from kuchnie_core import (CabinetConfig,
  DrawerSlot, BaseDoorConfig, BaseDrawerConfig, CornerBlindConfig,
  CornerInternalConfig, SinkConfig, CargoConfig, OvenConfig)`.
- 37 new tests in `tests/test_cabinet_config.py`: variant defaults,
  `default_factory` isolation, `CabinetConfig` union membership,
  `CabinetInstance.config` field, loader helper unit tests, dispatch
  table for all nine recognised Polish types + unknown, `_apply_...`
  guard (populate-when-None + preserve-explicit), and fixture round-trip
  for K01 / G01 / K02_legrabox.

Test posture: `kuchnie_core` **626 → 663 pass** (+37). `kitchen-erp`
(38/3/12/1) and `kitchen-cam` (292/35/13) baselines verified unchanged.

### Cleanup — post-ADR-012 §1/§2 audit follow-ups

From the 2026-07-02 `code-sum-kitchen.md` audit; low-risk documentation
and ordering polish, no behaviour change.

- `CabinetInstance.plinth_height_mm` moved from **after** the `validate()`
  method to be with the other dimensional fields (between
  `edge_banding_thickness_mm` and the interior-element collections).
  Pre-existing code smell from commit `35f6927` (walking skeleton):
  Python dataclasses accept field annotations after methods, but a
  reader scanning top-to-bottom would see the methods and assume the
  field list ended above — silently defaulting `plinth_height_mm` to
  100 mm. Dataclass field order verified stable; both default and
  keyword-override construction still work.
- `PanelRole` enum docstring gained a coverage note: 8 values are emitted
  today by `catalog.py`; `PLINTH` is aspirational (reserved for the
  future plinth-panel decomposition, locked in the enum so downstream
  CAM can pattern-match exhaustively without a follow-up model change).
- `docs/session-handoff-2026-07-02.md` updated:
  - Landed-commits table extended with `5e03187` and `1603017`.
  - Test baseline: `kuchnie_core` 533 → **565** pass.
  - Workstream 2 table now shows §1 and §2 as ✅ done; §3–§6 ⏳ remaining.
  - Workstream 3 gained two warnings from the audit:
    * **Atomic-commit warning** — after §1, `PanelRole` exists in BOTH
      namespaces (`kuchnie_core.model` English vs `kitchen_cam.models`
      Polish, deprecated). The `machining.py` rewrite MUST land in the
      same commit as `kitchen_cam.models` deletion.
    * **Runner-op `drill_type` back-fill** — `legrabox.decompose_drawer_box`
      and `DrawerSystem._runner_screw_ops` emit `drill_type=""` today.
      Classification decision (probably `"minifix"` from ADR-012 §2
      vocabulary) is deferred to the ADR-010 machining rewrite; back-
      fill at origin and update the LEGRABOX regression test.

Test posture: `kuchnie_core` **565 pass** (unchanged — all edits are
documentation, field ordering, or handoff-doc updates).

### Added — ADR-012 Extension 5: `ShelfPinSpec` on `CabinetInstance`

Fifth of the six `kuchnie_core.model` extensions ADR-012 requires.
Purely additive — default factory means every cabinet gets a spec
without opt-in, and every existing YAML fixture keeps working unchanged.

- `kuchnie_core.model.ShelfPinSpec` — new dataclass with the ADR-012 §5
  fields (`diameter_mm`, `depth_mm`, `front_offset_mm`, `back_offset_mm`,
  `max_per_row`) and default values matching standard European 5mm
  shelf-pin drilling (5mm × 8mm depth, 50/80 offsets, 3 positions per
  row per side).
- `CabinetInstance.shelf_pins: ShelfPinSpec = field(default_factory=ShelfPinSpec)`
  — default_factory (not mutable default) so each cabinet gets its own
  spec instance (regression-guarded by
  `test_shelf_pin_spec.py::TestCabinetInstanceShelfPinsField::test_each_cabinet_gets_its_own_spec`).
- `loader.py` — two new optional adapter helpers:
  * `_shelf_pins_from_polish(dict) -> ShelfPinSpec` translates the
    optional Polish YAML `kolki_polkowe` block (`srednica`, `glebokosc`,
    `odsuniecie_przod`, `odsuniecie_tyl`, `maks_na_rzad`) into the
    English spec. Missing block returns the ADR-012 default.
  * `_shelf_pins_from_schema(dict) -> ShelfPinSpec` lifts the schema-
    format English dict directly. Both always return a `ShelfPinSpec`
    (never `None`) so the field is always populated.
- `catalog.py` — the shelf-pin accessory name now builds from
  `cab.shelf_pins.diameter_mm` (`f"Kołek półkowy {int(...)}\ mm"`).
  For the default 5mm case, BOM output is byte-identical to pre-ADR-012
  (`"Kołek półkowy 5 mm"`). Non-default diameters reflect in the label.
  Quantity math (`4 × n_shelves`) is unchanged.
- Re-exported at package root: `from kuchnie_core import ShelfPinSpec`.
- 21 new tests in `tests/test_shelf_pin_spec.py`: dataclass defaults,
  default_factory isolation, Polish/schema loader translation, partial
  override semantics, real-fixture round-trip (all 3 fixtures use
  defaults), BOM name stability + non-default reflection, YAML override
  end-to-end.

Test posture: `kuchnie_core` **605 → 626 pass**. No pre-existing test
touched. `kitchen-erp` (38/3/12) and `kitchen-cam` (292/35/13) baselines
verified unchanged.

### Changed — ADR-012 Extension 4: `HandleSpec` replaces `handles: dict`

Fourth of the six `kuchnie_core.model` extensions ADR-012 requires.
Breaking type change on `CabinetInstance.handles` (dict → dataclass),
kept safe by the YAML loader (adapter) and by a display-map in
`catalog.py` that preserves BOM Polish output verbatim.

- `kuchnie_core.model.HandleSpec` — new dataclass with the ADR-012 §4
  fields (`type`, `spacing_mm`, `hole_diameter_mm`, `position`).
  English values (AGENTS.md rule).
- `CabinetInstance.handles: HandleSpec | None = None` — replaces
  `handles: dict = field(default_factory=dict)`. Default `None`
  short-circuits every `if cab.handles is not None:` branch in the
  4 catalog decomposers.
- `loader.py` — two new adapter helpers:
  * `_handle_spec_from_polish(dict) -> HandleSpec | None` translates
    the Polish YAML block (`typ: 'relingowy'`, `rozstaw: 256`,
    `srednica_otworu: 5`, `pozycja: 'srodek_frontu'`) into English
    (`type='bar'`, `spacing_mm=256.0`, `hole_diameter_mm=5.0`,
    `position='center'`). Handles 4 Polish handle types (relingowy,
    kulisty, profilowy, wpuszczany) and 3 positions.
  * `_handle_spec_from_schema(dict) -> HandleSpec | None` lifts the
    schema-format English dict directly. Both return `None` on empty
    input so cabinets without handles carry `handles=None` cleanly.
- `catalog.py` — `_HANDLE_TYPE_EN_TO_PL` + `_handle_accessory_name()`
  build the user-facing Polish BOM accessory name from the English
  `HandleSpec.type`. BOM output byte-identical to pre-ADR-012
  ("Uchwyt relingowy (rozstaw 256mm)") — regression guarded by
  `test_handle_spec.py::TestBOMAccessoryNamePolish`.
- Re-exported at package root: `from kuchnie_core import HandleSpec`.
- 27 new tests in `tests/test_handle_spec.py`: dataclass defaults,
  field-type replacement, Polish↔English loader translation (both
  formats), K01/G01/K02 fixture round-trip, BOM Polish-name stability,
  cabinet-without-handles behaviour.

Test posture: `kuchnie_core` **578 → 605 pass**. No pre-existing test
touched. `kitchen-erp` (38/3/12) and `kitchen-cam` (292/35/13) baselines
verified unchanged.

### Added — ADR-012 Extension 3: `HingeGeometry` on `BlumHinge`

Third of the six `kuchnie_core.model` extensions ADR-012 requires.

- `kuchnie_core.blum_hinges.HingeGeometry` — frozen dataclass carrying
  every drilling parameter a CAM stage needs for one hinge: cup drill
  (diameter, depth), plate-screw geometry (spacing, offset, pilot
  diameter and depth), edge-to-cup-centre offset, and first cup position
  from door top. Field defaults match Blum CLIP top 110° standard
  European geometry from ADR-012 §3.
- `BlumHinge.geometry` — concrete `@property` on the abstract base.
  Combines each subclass's already-implemented `cup_diameter_mm` /
  `cup_drill_depth_mm` with the ADR-012 default plate-screw geometry.
  Zero changes to `BlumClipTop110` / `95` / `155`; they inherit the
  property. Subclasses can override the property if a hinge in the
  catalog has non-standard drilling.
- Re-exported at package root: `from kuchnie_core import HingeGeometry`.
- 13 new tests in `tests/test_blum_hinges.py` covering: direct
  construction defaults, frozen-immutability guard, concrete-hinge
  round-trip (cup values propagate, plate-screw defaults preserved),
  factory-produced hinges expose `geometry`, package-root re-export.

Test posture: `kuchnie_core` **565 → 578 pass**. No pre-existing test
touched. `kitchen-erp` / `kitchen-cam` unaffected.

### Added — ADR-012 Extension 2: `MachiningOp.face` + `MachiningOp.drill_type`

Second of the six `kuchnie_core.model` extensions ADR-012 requires.

- `MachiningOp.face: str = "inside"` — which face of the panel the
  operation is applied to (`inside` | `outside` | `front` | `back`).
  Default `"inside"` matches every operation kuchnie_core produces
  today (LEGRABOX runner-mount screws are drilled from the inside face
  of the carcass side panel).
- `MachiningOp.drill_type: str = ""` — CAM discriminator with the
  ADR-012 §2 vocabulary (`system32`, `hinge_cup`, `hinge_screw`,
  `hinge_dowel`, `dowel_connector`, `minifix`, `handle`, `shelf_pin`).
  Open string, not enum, so kitchen-cam can extend the vocabulary
  without a core dependency inversion. Default `""` = unclassified;
  classifying LEGRABOX runner ops belongs in the ADR-010 rewrite of
  `kitchen-cam.machining`.
- Both new fields are additive with safe defaults — every existing
  `MachiningOp(...)` call site keeps working unchanged. The LEGRABOX
  ops in `legrabox.py` and `blum_drawers.py` are not touched;
  `test_machining_op.py::TestLegraboxRunnerOpDefaults` locks in that
  they carry `face="inside"` via the default.
- 7 new tests in `tests/test_machining_op.py` covering: field defaults,
  full ADR-012 vocabulary acceptance, open-string extensibility, and
  the LEGRABOX-decomposer real-output regression guard.

Test posture: `kuchnie_core` **558 → 565 pass**. No pre-existing test
touched.

### Added — ADR-012 Extension 1: `PanelRole` enum + `Panel.role` field

First of the six `kuchnie_core.model` extensions ADR-012 requires to unblock
the ADR-010 deletion queue (`kitchen_cam.models` / `panel_calculator` /
`csv_generator`, plus the `machining.py` rewrite).

- `kuchnie_core.model.PanelRole` — str-Enum with the 9 structural roles
  from ADR-012 §1 (`LEFT_SIDE`, `RIGHT_SIDE`, `BOTTOM`, `TOP`, `SHELF`,
  `BACK`, `FRONT_DOOR`, `FRONT_DRAWER`, `PLINTH`). English values keep
  the model layer English-only per the AGENTS.md rule.
- `Panel.role: PanelRole | None = None` — optional structural marker.
  Default `None` preserves every existing constructor call site.
  Populated on all carcass panels by the 4 decomposers in `catalog.py`
  (`dolna_szufladowa`, `dolna_drzwiowa`, `dolna_legrabox`, `gorna_drzwiowa`).
  LEGRABOX drawer-box back/base panels intentionally keep `role=None`
  — those are intermediate parts, not carcass roles (documented in
  `tests/test_panel_role.py::TestLegraboxRoles::test_drawer_box_panels_have_no_role`).
- Re-exported at package root: `from kuchnie_core import PanelRole`.
- 25 new tests in `tests/test_panel_role.py` covering: enum vocabulary,
  default value, per-decomposer role assignment (K01 / G01 / K02 LEGRABOX),
  role-based filtering (the primary downstream use case).

Test posture: `kuchnie_core` **533 → 558 pass**. No pre-existing test
touched. `kitchen-erp` and `kitchen-cam` unaffected (model layer is
additive, `role=None` is the safe default).

### Restructured — ADR-011 Commit B.ii: internal package unification

Single top-level ``kitchen_erp/`` package with ``ui/`` + ``core/``
subpackages, replacing the previous two-siblings layout
(``kitchen_app/`` + inner ``kitchen_erp/``).

**Moves (14 files, history preserved by git rename detection):**

- ``kitchen_app/kitchen_app.py`` → ``kitchen_erp/kitchen_erp.py`` (Reflex entry — matches Reflex convention: ``app_name="kitchen_erp"`` → ``kitchen_erp/kitchen_erp.py``).
- ``kitchen_app/{state,admin_state,admin_ui,__init__}.py`` → ``kitchen_erp/ui/*``.
- ``kitchen_erp/{models,database,schemas,bom_generator,purchasing,recipe_loader,rules_engine,recipes.json,__init__.py}`` → ``kitchen_erp/core/*``.

**New:** ``kitchen_erp/__init__.py`` describing the package layout.

**Import rewrites** (25 files touched):

- Within ``kitchen_erp/core/``: absolute ``from kitchen_erp.X`` → relative ``from .X`` (5 files: ``models``, ``bom_generator``, ``database``, ``rules_engine`` + lazy imports inside those).
- Within ``kitchen_erp/ui/``: absolute ``from kitchen_erp.X`` → relative ``from ..core.X`` (state, admin_state + lazy imports).
- Reflex entry ``kitchen_erp/kitchen_erp.py``: ``from .state`` → ``from .ui.state``, ``from .admin_ui`` → ``from .ui.admin_ui``, ``from .admin_state`` → ``from .ui.admin_state``.
- Tests, examples, scripts (13 files): ``from kitchen_erp.X`` → ``from kitchen_erp.core.X`` (models, database, schemas, bom_generator, purchasing, rules_engine, recipe_loader).
- ``database.py``: replaced the unusual ``import kitchen_erp.models`` side-effect line with ``from . import models`` (same behaviour, package-relative).

**Config:** ``rxconfig.py`` ``app_name = "kitchen_app"`` → ``"kitchen_erp"``.

**Style choice:** within-package uses relative imports (``.X`` inside ``core/``, ``..core.X`` inside ``ui/``), cross-package (tests/examples/scripts) uses absolute. Matches Python community convention (PEP 8) and makes the package internally movable.

Test posture identical to pre-restructure: 38 pass / 3 fail / 12 errors / 1 collect error. Same 15 test names in the failing set (all pre-existing: ``HARDWARE_RULES`` symbol missing, SQLAlchemy fixture issues, oven-cabinet backward-compat check). ``kuchnie_core`` unaffected (533 pass).

### Renamed — ADR-011 Commit A: directory rename

- `kitchen-app/` → `kitchen-erp/` (43 files moved via `git mv`; history preserved).
- `kitchen-erp/pyproject.toml` — package name `kitchen-app` → `kitchen-erp`.
- `kitchen-erp/uv.lock` — package name updated to match.
- `kitchen-erp/README.md` — shell snippet `cd kitchen-app` → `cd kitchen-erp`.
- `docs/GLOSSARY.md` — file-of-record paths updated (4 entries: CabinetUI, HardwareSet, Material, Project).
- `docs/vision/01-user-journeys.md` — heading `kitchen-app` → `kitchen-erp` (fixed adjacent typo `refinemnt` → `refinement`).

**Deliberately deferred to follow-up commits:**

- Internal package restructure `kitchen_app/` + `kitchen_erp/` → `ui/` + `core/` (or `kitchen_erp_ui/` + `kitchen_erp_core/`). `rxconfig.py` `app_name="kitchen_app"` remains — refers to the internal package, not the directory.
- Delete old BOM path (`Cabinet.calculate_cost`, `use_new_bom` toggle, `_new`-suffix normalisation, backward-compat tests). Semantic change, distinct from the rename.
- `kuchnie_core` integration (`BOMGenerator` → `kuchnie_core.decompose`). Explicitly deferred by ADR-011 itself.

ADRs 003 and 009 still mention `kitchen-app` — not edited per the AGENTS.md rule "Don't edit an old ADR"; ADR-011 supersedes.

### Added — ADR-010 partial execution (safe, additive)

- `kuchnie_core.export.edging_csv` — per-edge banding worklist CSV. One row per banded edge across the kitchen. Same Polish CNC format as `cutlist_csv` (UTF-8-SIG BOM, `;` delimiter, Polish headers). Migrated semantically from `kitchen_cam.csv_generator.generate_edging_csv` but rewritten against `kuchnie_core.model.Panel.banded_edges` (dict-keyed) instead of the deprecated `kitchen_cam.models.Panel.edges` (list-with-side).
- `tests/test_edging_csv.py` — 8 tests covering row collection, edge-length rule (front/back → width; left/right → height), Polish header, UTF-8-SIG BOM, semicolon delimiter, round-trip. Also a regression guard for `cutlist_csv` Polish format.
- Deprecation banners on `kitchen-cam/src/kitchen_cam/{models,panel_calculator,csv_generator,machining}.py` pointing at ADR-012 as the unblocking work.

### Decided — ADR-012

- **ADR-012**: enumerates the `kuchnie_core.model` extensions required to execute the remaining ADR-010 steps (delete `kitchen_cam.models` / `panel_calculator` / `csv_generator`, rewrite `machining.py`). Extensions: `PanelRole` enum, `MachiningOp.face`/`drill_type`, `HingeGeometry`, `HandleSpec`, `ShelfPinSpec`, discriminated `CabinetInstance.config` union. Migration is BLOCKED on this — attempted mechanical rewrite fails to import.

### Decided (documented, not yet executed)

- **ADR-009**: `kitchen-plugin/` → `home-builder-adapter/`. Ports & Adapters pattern. Pure code (geometry, standards, construction math, manifest validator) migrates into `kuchnie_core/`. `bpy`-dependent extraction stays isolated as an anti-corruption layer against `home_builder_5` (external, licensed).
- **ADR-010**: `kitchen-cad/` → `kitchen-cam/`. Downstream consumer of `kuchnie_core`. Duplicate Panel / CabinetInstance / Hinge / Drawer models deleted. Package keeps System32 drilling and DXF generation only; CSV cut list merges into `kuchnie_core.export`. **Partially executed**: CSV merge done (see above). Model migration blocked on ADR-012.
- **ADR-011**: `kitchen-app/` → `kitchen-erp/`. Accept ERP scope (BOM, purchasing, rules, admin). Sales-tool role explicitly reassigned to `krono-compositor-mvp/`. Old (non-recipe) BOM path deleted; `use_new_bom` flag removed.

Execution plan: phases B–F in session handoff notes. Rename phase (Phase C, commit `8e85da1`) complete. Model migration deferred to ADR-012.

---

## 2026-06-30 — Catalog consolidation

### Moved

- `data/materials/` → `catalog/data/materials/` (YAML source data + build pipeline)
- `docs/materials-boards/` → `catalog/docs/materials/` (source PDFs + markdown specs)
- `scripts/convert-global-collection.js` → `catalog/scripts/` (conversion script)

### Updated

- `catalog/package.json` — build/test scripts now run from catalog/ directly
- `catalog/data/materials/build.js` — fixed output path to `catalog/public/`
- `catalog/AGENTS.md` — updated directory structure diagram
- `catalog/Makefile` — simplified paths (no more `cd ..`)
- `catalog/docs/architecture/` — updated path references

### Verified

- 78/78 catalog validation tests pass
- 110/110 root tests pass
- `make build`, `make test`, `make validate` all pass

---

## 2026-06-24 — Walking skeleton + LEGRABOX + Kitchen model

### Architecture decisions

See `docs/adr/` for full rationale:

- ADR-001: Panel is the atomic manufacturing unit
- ADR-002: Construction method separated from cabinet instance (Polyboard pattern)
- ADR-003: Kitchen is the unit of work flowing through the system
- ADR-004: Intermediate format is logical description, not physical panels
- ADR-005: MachiningOp is a first-class object on Panel
- ADR-006: LEGRABOX LW = KB − 2×13mm runner clearance
- ADR-007: LEGRABOX drawer box panels are 16mm chipboard

### Added

**Core engine** (`src/kuchnie_core/`):

- `model.py` — Panel, EdgeBand, MachiningOp, Accessory, CabinetInstance, DecompositionResult
- `model.py` — Kitchen, Row, WorktopSegment (kitchen-level models)
- `catalog.py` — 3 cabinet types: `dolna_szufladowa`, `gorna_drzwiowa`, `dolna_legrabox`
- `decomposer.py` — thin dispatcher from CabinetInstance → panels via catalog
- `bom.py` — per-cabinet costed BOM (panels + edge banding + accessories)
- `kitchen.py` — kitchen-level aggregation (all_panels, kitchen_bom, validate_rows)
- `loader.py` — YAML → CabinetInstance, YAML → Kitchen
- `serialize.py` — Kitchen ↔ JSON round-trip (intermediate format)
- `export/cutlist_csv.py` — aggregated cut list CSV (semicolon-separated)
- `legrabox.py` — LEGRABOX catalog (heights, NL matrix, formulas, validation, drawer box decomposition, runner mounting drill ops)

**Fixtures** (`fixtures/`):

- `K01.yaml` — base cabinet with 2 metabox drawers
- `G01.yaml` — wall cabinet with 2 doors
- `K02_legrabox.yaml` — base cabinet with 2 LEGRABOX C drawers (NL=500)
- `kitchen_01.yaml` — minimal test kitchen (1 row, 2 cabinets)

**Tests** (`tests/`):

- 84 tests passing across 6 test files
- Decomposition tests (K01: 16 tests, G01: 19 tests)
- LEGRABOX tests (24 tests — formulas, validation, full cabinet integration)
- Kitchen model tests (10 tests — loading, aggregation, row validation)
- Serialize tests (8 tests — JSON round-trip, self-contained format)
- Cut list tests (7 tests — aggregation, CSV output, total quantity)

### Fixed

- Drawer box panel thickness: was 3mm/12mm, corrected to **16mm** per Blum spec (ADR-007)
- LW formula: was subtracting `2 × side_thickness`, corrected to `2 × 13mm` runner clearance (ADR-006)

### Design patterns applied

- **Polyboard pattern**: Construction method as first-class entity (ADR-002)
- **Winner Flex pattern**: Material decoupled from construction
- **Anti-corruption layer**: Intermediate format isolates design from manufacturing (ADR-004)

---

## 2026-06-27 — Material Master Catalog (Kronospan + Swiss Krono)

### Architecture decisions

- ADR-008: Material Master Catalog — separate bounded context from project domain
- ER diagram: `catalog/docs/architecture/04-er-diagram.md` (32 entities, 2 bounded contexts)
- Schema: 6 incremental migrations (`01-schema.sql` through `05-phase4b-property-flags.sql`)

### Added

**Catalog schema** (`catalog/docs/architecture/`):

- 21 tables: producers, structures, collections, subcollections, materials,
  material_types, decors, variants, worktop_constructions, worktop_profiles,
  worktop_specs, sheet_formats, edges, edge_suppliers, variant_edges,
  decor_structures, pairings, variant_availability, property_flags,
  color_families, tags, decor_tags
- 9 views: v_decors_full, v_pairings_full, v_worktops_full,
  v_synchro_variants, v_variants_availability, v_property_flags,
  v_decor_structures_full
- 13 indexes

**Catalog importer** (`catalog/scripts/`):

- `importer.py` — CatalogImporter class (11 import methods, FK validation, idempotent)
- `generate_kronospan_yaml.py` — YAML generator from Kronospan data
- `generate_kronoswiss_yaml.py` — YAML generator from Swiss Krono data

**Catalog data** (`catalog/data/`):

- `kronospan_full.yaml` — 62 decors, 11 variants, 6 worktops, 69 junction rows,
  5 pairings, 11 availability, 10 property flags
- `kronoswiss_full.yaml` — 40 decors, 10 variants, 6 worktops, 40 junction rows,
  4 pairings, 5 availability, 12 property flags

**Material analysis** (`docs/materials-boards/`):

- Kronospan: 20 markdown spec files (Global Collection, MDF, Acrylic, Mirror,
  Metal, HDF, HPL, Emporio, Kaindl, Focus, Rocko Tiles, blaty 4 collections)
- Swiss Krono: 3 markdown spec files (laminated boards, worktops, BE Velvet)
- PDF page exports for visual reference

**Tests** (`catalog/tests/`):

- 177 tests passing across 7 test files (catalog schema + import)
- Phase 1: 32 tests — worktop specs, sheet formats, subcollections
- Phase 2: 28 tests — decor_structures junction, pairings expansion
- Phase 3: 33 tests — importer (per-entity + full import + validation)
- Import: 45 tests — Kronospan + KronoSwiss + cross-catalog
- Phase 4a: 21 tests — variant availability (Express 24h, konfekcja)
- Phase 4b: 18 tests — property flags (antibacterial, waterproof, etc.)

**Materials bridge** (`src/kuchnie_core/materials/`):

- `models.py` — 5 frozen DTOs: VariantInfo, EdgeInfo, WorktopInfo, PropertyFlag, AvailabilityInfo
- `exceptions.py` — 3 domain exceptions: MaterialNotFoundError, EdgeNotFoundError, CatalogUnavailableError
- `protocol.py` — MaterialCatalog Protocol (runtime_checkable, 4 methods)
- `sqlite_repository.py` — SqliteMaterialCatalog (lazy connection, PRAGMA query_only)
- `resolver.py` — MaterialResolver (cached facade, LRU-style dict cache)
- `__init__.py` — public API with __all__ exports
- 26 tests: protocol conformance, SQLite reads, caching, FakeCatalog for engine tests

**ADR** (`docs/adr/`):

- ADR-008: Material Master Catalog — 7 decisions (bounded contexts, EAV, junction tables, Protocol pattern)

### Fixed

- `structures.code UNIQUE` column-level constraint blocked same code per producer
  (e.g. Kronospan SM vs KronoSwiss SM). Removed column-level UNIQUE,
  kept only `UNIQUE(code, producer_id)` composite.

### Key entities

| Entity | Kronospan | KronoSwiss | Total |
|--------|-----------|------------|-------|
| Decors | 62 | 40 | 102 |
| Variants | 11 | 10 | 21 |
| Worktop specs | 6 | 6 | 12 |
| Structures | 26 | 23 | 49 |
| Pairings | 5 | 4 | 9 |
| Availability | 11 | 5 | 16 |
| Property flags | 10 | 12 | 22 |

### Design patterns applied

- **Bounded contexts**: Catalog (material master) vs Project (customer kitchen)
- **EAV pattern**: property_flags table prevents schema bloat
- **Junction table**: decor_structures replaces CSV multi_structures column
- **Bridge by business_id**: Project references Catalog via string codes, not FK
- **Idempotent migrations**: CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE

---

## Next (planned)

- [ ] Add remaining cabinet types from taxonomy (corner blind, corner internal, sink, cargo, oven)
- [ ] Fill in complete runner screw position table (all NL values from Blum PDF)
- [ ] Confirm M and F back panel heights from Blum PDF sheets
- [ ] Shelf pin System32 drill operations on side panels
- [ ] Handle boring drill operations on front panels
- [ ] DXF export (panels + machining ops → DXF files for CNC)
- [ ] Dimension constraints per cabinet type (min/max, auto-correction)
- [ ] Blender render service (FastAPI + headless Blender)
- [ ] kitchen-plugin web app (Svelte layout editor)
- [ ] ADR-008: Material Master Catalog decision record  ✅ DONE
- [ ] ADR-009: Worktop construction types
- [ ] Full YAML data: expand to 174 Kronospan + 174 KronoSwiss decors
- [x] Bridge module: `src/kuchnie_core/materials/` — Python API over catalog SQLite  ✅ DONE
- [ ] Catalog REST API (FastAPI) — parallel agent in progress
- [ ] Catalog frontend (Svelte) — parallel agent in progress
