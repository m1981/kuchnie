# F007 — Blender Render Adapter (Headless PNG + .blend Generation)

## Job Story

**When** I am preparing renders for a Wrocław customer — first-visit preview after material selection, or final-acceptance render after layout approval — and I have a validated `Kitchen` and a resolved material chain (F005),
**I want to** run `kitchen-cli render kitchen.yaml --preset perspective` and get back a PNG image plus a `.blend` file showing the kitchen with construction-method-correct geometry, Kronospan/Egger texture-mapped materials, and a sensible camera/lighting setup — without involving the interactive `home_builder_5/` addon,
**So I can** ship presentation images to the customer in minutes, and so I can open the `.blend` in Blender (optionally with the `home_builder_5/` addon enabled) to manually tweak lighting/camera/materials if the auto-render needs polish.

---

## Bounded Context

- **Primary (the one that OWNS this):** **Render Adapter** — a new bounded context. Code location: `kitchen-render/` (sibling to `kitchen-cad/`, `kitchen-app/`, `catalog/`).
- **Touched (consumers / dependencies, must have explicit reason):**
  - `kuchnie_core` — read-only consumer of `Kitchen`, `CabinetInstance`, `MaterialResolver`, `ResolvedMaterial`, validation gates.
  - `catalog/` — indirectly via `MaterialResolver` (F005). Adapter does not import catalog directly.
  - **NOT touched:** `home_builder_5/` (the interactive Blender addon). F007 does not import, drive, or modify it.

> **Change Locality Test result:** one new bounded context (Render Adapter). All cross-context calls are read-only consumption of Core's published API. ✅ Passes.

> **Critical architectural pivot:** This spec rejects the earlier prescription (in `03_implementation_placement.md` § "What goes INTO the Blender plugin") to extend the plugin with a headless entry point. That prescription was written when "the Blender plugin" referred to an older, simpler `kitchen-plugin/` from a different project directory. The actual target — `home_builder_5/` — has **no headless API**, **no config-driven entry**, and **no documented automation interface**. Extending it would mean forking a 50,000-LOC interactive addon. F007 takes the cleaner path: a standalone Blender-Python script that uses `bpy` directly and never touches `home_builder_5/`. See ADR § Alternative A.

---

## Subdomain Classification

- [x] **Supporting** — necessary but commoditized. We use Blender as a "bought" rendering engine. Our value-add is the scene assembly logic (which knows our domain), not the renderer itself.
- [ ] Core
- [ ] Generic

**Reasoning:** Photoreal kitchen rendering is a solved problem (Blender, V-Ray, Cycles, every CAD vendor ships one). What's unique is that our renders use the *exact* dimensions our cut-list will use — same `ConstructionMethod`, same `Recipe`, same `ResolvedMaterial`. Carpenters value "what you see is what gets manufactured" more than they value photorealism. Blender + texture lookup is enough.

---

## Data Ownership

- **Canonical writes happen in:**
  - Adapter code: `kitchen-render/src/kitchen_render/`.
  - Render presets (camera, lighting, resolution): `kitchen-render/presets/*.yaml`.
- **Read-only consumers / inputs:**
  - `Kitchen` from `kuchnie_core` (full domain model).
  - `ResolvedMaterial` from F005 (per-panel texture path, color, grain).
  - F004 `KitchenValidationGate` — must pass before render runs.
- **Outputs:**
  - PNG file at `--output` path.
  - `.blend` file at `--output` path with `.blend` extension (free side effect of saving the scene).
  - Exit code 0 on success, non-zero on validation or render failure.

---

## Scope — MoSCoW

### Must (do not ship without)

#### CLI entry point

- [ ] `kitchen-cli render <kitchen.yaml> --preset <preset_name> --output <path.png>` — top-level command.
- [ ] Internally: `subprocess.run(["blender", "--background", "--python", script.py, "--", ...args])`.
- [ ] Detect Blender installation; clear error if missing or version too old.
- [ ] Pass `kitchen.yaml` and preset path to the Blender subprocess.
- [ ] Capture stdout/stderr from Blender; surface errors to user without dumping 200 lines of bpy noise.

#### Adapter package

- [ ] `kitchen-render/src/kitchen_render/`:
  - [ ] `__init__.py` — package marker.
  - [ ] `cli.py` — outer CLI (the one that spawns Blender subprocess).
  - [ ] `blender_entry.py` — the script that runs **inside** Blender's Python. Loads kitchen, validates, builds scene, renders, saves `.blend`, exits.
  - [ ] `scene_builder.py` — top-level: takes a `Kitchen` + `MaterialResolver`, returns a configured `bpy.context.scene`.
  - [ ] `geometry.py` — cabinet → `bpy.types.Object` (box geometry with fronts).
  - [ ] `materials.py` — `ResolvedMaterial` → `bpy.types.Material` (Principled BSDF + Image Texture node).
  - [ ] `placement.py` — `RowPlacement` → `WallPlacement` conversion + cabinet world transform.
  - [ ] `lighting.py` — preset-driven light placement.
  - [ ] `camera.py` — preset-driven camera placement.
  - [ ] `presets.py` — preset YAML loader + model.

#### Geometry — parametric box approach

- [ ] Cabinets rendered as **closed boxes** with visible front panels:
  - [ ] Corpus box: width × depth × height (minus plinth for base cabinets).
  - [ ] Plinth box: full-width strip below base cabinets (height from `ConstructionMethod`'s plinth height).
  - [ ] Front panels: one or more visible boxes overlaid on the corpus face (one per door / drawer / false front).
  - [ ] Front overlay gap visible (per `construction_method.front_gap_mm`).
  - [ ] Handle: simple cylinder or omitted (no detailed handle modeling in v1.0).
- [ ] Worktop: single rectangular box spanning all base cabinets in a row, with `worktop_thickness_mm` from project config.
- [ ] Walls: simple thin boxes behind cabinets, for context.
- [ ] Floor: single flat plane.
- [ ] **No interior shelves, no opening doors, no drawer animation.** The visible result is a "closed kitchen" — accurate to dimensions and materials.

#### Materials — texture-mapped via F005

- [ ] For each panel role (corpus, front, back, shelf, countertop):
  - [ ] Call `resolver.resolve_role(role, cabinet)` (F005).
  - [ ] Load texture from `ResolvedMaterial.texture_path`.
  - [ ] Build a Blender material: Principled BSDF + Image Texture, UV-mapped to the face.
  - [ ] Cache materials by `(decor_id, role)` to avoid re-creating per cabinet.
- [ ] Edge banding visualization: ignore in v1.0 (too small to matter at preview resolution).
- [ ] Wall material: solid color (light gray, configurable).
- [ ] Floor material: solid color (light wood, configurable).

#### Placement — Row → Wall conversion

- [ ] `RowPlacement` model (introduced in F005 spec; concretized here): `(row_id, slot_index)`.
- [ ] `WallPlacement` model: `(wall_id, offset_along_wall_mm, rotation_rad, z_floor_mm)`.
- [ ] Conversion algorithm:
  - For a row with wall_id W and direction D:
    - `offset_along_wall_mm = sum(cabinets[:slot_index].width_mm) + slot_index * cabinet_gap_mm`
    - `rotation_rad = wall_angle_for_direction(D)`
    - `z_floor_mm = 0` for base, `wall_mount_height_mm` for wall cabinets
- [ ] Wall geometry derived from kitchen: walls are inferred from rows. Each row implies one wall; wall length ≥ row total width.

#### Presets

- [ ] `kitchen-render/presets/`:
  - [ ] `front_view.yaml` — orthographic front projection, single wall.
  - [ ] `perspective.yaml` — 3/4 view from above, full kitchen visible.
  - [ ] `plan.yaml` — top-down orthographic, plan-view style.
- [ ] Each preset declares: camera position + target + lens, lighting setup, resolution, render engine (Eevee for speed).
- [ ] Preset YAML schema:
  ```yaml
  preset_id: perspective
  resolution: [1920, 1080]
  render_engine: BLENDER_EEVEE_NEXT  # or CYCLES if user requests photoreal
  samples: 64
  camera:
    type: perspective
    position_mm: [3000, -2000, 1800]
    target_mm: [0, 1500, 800]
    lens_mm: 35
  lighting:
    ambient_strength: 0.3
    key_light:
      type: sun
      direction: [0.3, -0.8, -0.5]
      energy: 3.0
  ```

#### Validation gate before render

- [ ] Before invoking Blender, run `KitchenValidationGate.validate(kitchen, ctx)` (F004 Gate 3).
- [ ] On any ERROR: refuse to render, print issues, exit non-zero.
- [ ] On WARNING: render but log warnings to stderr.
- [ ] On INFO: silent unless `--verbose`.

#### Blender invocation

- [ ] Locate Blender executable: `$BLENDER_PATH` env var → `which blender` → fail with help message.
- [ ] Version check: parse `blender --version`; require ≥ 3.6 (LTS). Reject older versions.
- [ ] Headless flags: `--background --factory-startup --python <script>`.
- [ ] Arguments after `--` are passed to the script.
- [ ] Capture stdout/stderr; filter "Info:" lines unless `--verbose`.
- [ ] Save `.blend` automatically before render (for carpenter's tweaking workflow).

#### Tests

- [ ] **Pure-Python unit tests (no Blender):**
  - [ ] `tests/render/test_placement.py` — `RowPlacement` → `WallPlacement` conversion correctness.
  - [ ] `tests/render/test_presets.py` — preset YAML loads and validates.
  - [ ] `tests/render/test_cli.py` — CLI argument parsing, error handling.
  - [ ] `tests/render/test_blender_detection.py` — Blender locator + version check, mocked subprocess.
- [ ] **Smoke test (invokes Blender — runs in CI optionally / manually by developer):**
  - [ ] `tests/render/integration/test_smoke_render.py` — small fixture kitchen → invoke Blender → assert PNG exists and is > 1KB.
  - [ ] Marked `@pytest.mark.blender` so it can be skipped in CI without Blender.

#### Documentation

- [ ] `kitchen-render/README.md` — install Blender, set `$BLENDER_PATH`, run a render.
- [ ] `docs/rendering.md` — explain preset structure, how to add custom presets.

### Should (do if time permits)

- [ ] Batch mode: `kitchen-cli render kitchen.yaml --all-presets` — runs all presets, writes `kitchen_front.png`, `kitchen_perspective.png`, `kitchen_plan.png`.
- [ ] Worktop cutouts visible in render (sink hole, hob hole) — geometry-only, no detailed sink/hob model.
- [ ] Splashback strip behind base row (rear wall close-up surface).
- [ ] Cycles backend option (`--engine cycles --samples 256`) for photoreal output at the cost of render time.
- [ ] `--resolution 1920x1080` CLI override.
- [ ] `kitchen-cli render --diff old.yaml new.yaml` — render both and side-by-side compare image.

### Could (almost certainly defer)

- [ ] HDRI environment maps for realistic lighting.
- [ ] Material variants (matte vs gloss based on decor's `is_gloss` flag).
- [ ] Detailed handle modeling (knob vs bar vs recessed) — currently no handles.
- [ ] Open-door / open-drawer variants ("show me with the second drawer open").
- [ ] Camera animation / fly-through video.
- [ ] Render farm support (queue multiple kitchens).
- [ ] AR-ready 3D export (USDZ, glTF).
- [ ] Real-time preview server (web-based gl viewport).

### Won't (this iteration — explicit cuts)

- ❌ **Drive `home_builder_5/` operators headlessly.** The addon is interactive-only; operators expect modal context. Forking it is out of scope.
- ❌ **Import or use `home_builder_5/`'s `GeoNode*` types, `types_frameless`, `types_face_frame`, etc.** F007 uses pure `bpy` mesh primitives. No coupling to plugin internals.
- ❌ **Photorealism.** Quick clean preview, not magazine-grade. Use Cycles via `--engine cycles` (Should) for higher quality, but it's not the default.
- ❌ **Interior visibility.** Cabinets are closed boxes. No open doors, no visible shelves, no contents.
- ❌ **People, decorations, props.** Clean architectural render only.
- ❌ **Multiple rooms in one render.** One `Kitchen` per render call.
- ❌ **Animation, video output.** Still images only.
- ❌ **Edge banding visualization.** Too small at preview resolution.
- ❌ **Live preview / hot-reload as kitchen YAML changes.** Run the CLI, get a render. Discrete, not reactive.
- ❌ **bpy as pip package** (`pip install bpy`). Adds 1GB+ to the venv and ties to a specific Blender build. Subprocess invocation is the right boundary.
- ❌ **Asynchronous / parallel render.** Solo dev workflow; renders take ~10-30 seconds; sync is fine.
- ❌ **Render output caching keyed by kitchen hash.** Re-rendering is cheap; cache invalidation is hard.
- ❌ **Texture procedural generation** (no `wood_materials.py`-style shaders). F005 produces texture paths; we load images.
- ❌ **Web service / HTTP endpoint for rendering.** Solo dev runs CLI locally.
- ❌ **Reflex UI for triggering renders.** F006's web sidebar may shell out to the CLI; that's F006's choice.
- ❌ **Bug-for-bug parity with `home_builder_5/` visual style.** We render our own way.

---

## Change Locality Test

- [x] Editing **one new bounded context** (Render Adapter at `kitchen-render/`).
- [x] **One published contract**: the render preset YAML schema. `kitchen_config.yaml` schema is **unchanged**.
- [x] **Passes.**

---

## Glossary Impact

**New terms** (must be added to `docs/GLOSSARY.md` in the implementation commit):

- `Scene` — promote placeholder → concrete. Defined as: a `bpy.context.scene` built by F007's `scene_builder.py` from a `Kitchen`. Includes geometry, materials, lighting, camera.
- `WallPlacement` — promote placeholder → concrete. `(wall_id, offset_along_wall_mm, rotation_rad, z_floor_mm)`.
- `RowPlacement` — promote placeholder → concrete. `(row_id, slot_index)`. Web app's coord model; render adapter converts.
- `Texture` — promote placeholder → concrete. An image file (JPG/PNG) at `Decor.texture_path`, loaded by F007 into a Blender Image Texture node.
- `RenderPreset` — new. YAML-defined bundle of camera, lighting, resolution, engine settings.
- `RenderResult` — new. CLI return value: `(png_path, blend_path, exit_code, warnings)`.
- `BlenderEntry` — new. The script that runs inside Blender's subprocess (`blender_entry.py`).
- `SceneBuilder` — new. The class that translates `Kitchen` → `bpy.context.scene`.

**Existing terms refined:**

- `MaterialResolver` — confirmed consumer; clarifies that F007 calls `resolve_role()` per panel.
- `WallPlacement` and `RowPlacement` — concretized.
- The plugin (`home_builder_5/`) — glossary entry can note: "Interactive Blender addon, NOT invoked by F007. Carpenter may open generated `.blend` files in Blender with this addon enabled for manual tweaking."

---

## Acceptance Criteria

The feature is **done** when:

- [ ] `kitchen-render/` package exists with all listed modules.
- [ ] `kitchen-cli render` CLI command implemented.
- [ ] Blender detection works on Linux, macOS (Windows out of scope for solo dev v1.0 unless trivially supported).
- [ ] Three presets shipped: `front_view`, `perspective`, `plan`.
- [ ] `examples/kitchen_nowak.yaml` renders successfully with each preset, producing a non-empty PNG and a loadable `.blend`.
- [ ] Validation Gate 3 runs before render; ERROR refuses render.
- [ ] All unit tests pass (no Blender required).
- [ ] Smoke test passes when Blender is installed (`pytest -m blender`).
- [ ] `docs/GLOSSARY.md` updated with 8 new/refined terms.
- [ ] `docs/01_architecture.md` Context Map shows `kitchen-render/` as a new bounded context with arrows to `kuchnie_core` (consumer) and `Blender` (subprocess).
- [ ] `docs/rendering.md` published.
- [ ] `kitchen-render/README.md` published.
- [ ] ADR `features/F007-blender-adapter/adr.md` status = `Accepted`.
- [ ] `home_builder_5/` directory and `__init__.py` are untouched in this feature's diff (verify in the close-out: `git diff --stat home_builder_5/ | wc -l` returns 0 for non-doc files).
- [ ] `status.md` set to `done`.
- [ ] `features/INDEX.md` updated.
- [ ] Phase 7 gate criteria in `docs/PHASES.md` ticked (note: `docs/PHASES.md` currently says "plugin loaded headless" — update to match F007's actual approach).

---

## Out of Scope (anti-drift)

- ❌ **Modifying `home_builder_5/`.** Rule 4. Confirmed by reading the addon's `__init__.py` — fully interactive, no headless API. F007 does not touch it.
- ❌ **Using `bpy` as a pip-installed library.** Subprocess invocation is the boundary.
- ❌ **Photorealism, animation, AR, VR.**
- ❌ **Web-based rendering or cloud render farms.** Local subprocess only.
- ❌ **Reflex UI for triggering renders.** F006's call.
- ❌ **Caching rendered images** — re-render is cheap, cache invalidation is hard.
- ❌ **Material variants beyond what `Decor` carries.** F005 publishes the material data; F007 consumes verbatim.
- ❌ **Render quality optimization beyond preset tuning.** Eevee for speed, Cycles as Should-have.
- ❌ **Multi-language preset names.** Polish-only is fine; presets are technical config not customer-facing.
- ❌ **Decor approval / "preview before commit" workflow.** Business state, not rendering.
- ❌ **Custom shaders** (procedural wood, custom roughness maps). Use F005's `ResolvedMaterial` as-is.
- ❌ **Live BPY type checking in our pure-Python tests.** We mock `bpy` for unit tests.

---

## References

- **Pattern source:** `docs/02_pattern_analysis.md` § Pattern 5 (Object-in-Room Model, from PaletteCAD) — placement separation from definition.
- **Placement decision:** `docs/03_implementation_placement.md` § Pattern 7 — Object-in-Room (Web row-based; Render wall-based; adapter converts).
- **Architecture pivot from `03_implementation_placement.md`:** the earlier "what goes INTO the Blender plugin" table referenced extending a plugin's `config_parser.py`. That prescription does NOT apply to `home_builder_5/` (which has no `config_parser.py`). F007's ADR Alternative A documents the pivot.
- **Process rules:** `docs/04_solo_dev_process.md` § Anti-Corruption Layer.
- **Related ADRs:**
  - `features/F001-construction-method/adr.md` — Adapter reads `ConstructionMethod` to build correct geometry (plinth height, front overlay, gap).
  - `features/F004-validation-gates/adr.md` — Gate 3 must pass before render.
  - `features/F005-material-resolver/adr.md` — Adapter calls `resolver.resolve_role()` per panel to get texture path.
- **Related features:**
  - **Depends on:**
    - F001 (geometry uses `ConstructionMethod` dimensions).
    - F004 (Gate 3 validates before render).
    - F005 (`MaterialResolver` provides texture paths).
  - **Indirect dependencies:**
    - F002 (recipes shouldn't be required for render — geometry is approximate boxes — but if recipes have rendered, panel breakdown is more accurate. v1.0: render from cabinet dimensions, not from panels).
    - F003 (cabinets carry `template_id`; render doesn't need it but may use it for legend labels).
  - **Enables:**
    - F006 (Web sidebar can shell out to `kitchen-cli render` to show preview).
  - **Conflicts with:** none. F007 is purely additive.

---

## Worked Example — End-to-End Render Flow (for spec clarity)

### CLI invocation

```bash
$ kitchen-cli render examples/kitchen_nowak.yaml \
    --preset perspective \
    --output renders/nowak_perspective.png

Validating kitchen against Gate 3 (Kitchen)...
  ✓ 0 errors, 1 warning
    [WARN] KIT-003: Worktop segment doesn't cover wall 'wall_west' (no base row).
            Hint: Add a base row or remove the segment.

Locating Blender...
  Found at /usr/bin/blender (version 4.2.1 LTS)

Rendering preset 'perspective' (1920x1080, Eevee, 64 samples)...
  Building scene: 6 cabinets, 1 worktop, 3 walls, 1 floor
  Loading textures: 4 unique materials cached
  Rendering...
  Saved: renders/nowak_perspective.png
  Saved: renders/nowak_perspective.blend

Done in 18.3 seconds.
```

### Internal call chain

```python
# kitchen-render/src/kitchen_render/cli.py
def render_command(args):
    # 1. Load kitchen + validate
    kitchen = load_kitchen(args.kitchen_path)
    catalog = YamlCatalogReader(catalog_dir())
    resolver = MaterialResolver(catalog, kitchen)
    
    result = KitchenValidationGate().validate(kitchen, ctx)
    if result.errors:
        print_issues(result)
        sys.exit(1)
    for warning in result.warnings:
        print_warning(warning, file=sys.stderr)
    
    # 2. Locate Blender
    blender_path = locate_blender()
    
    # 3. Spawn subprocess
    script = Path(__file__).parent / "blender_entry.py"
    subprocess.run([
        str(blender_path),
        "--background",
        "--factory-startup",
        "--python", str(script),
        "--",
        "--kitchen", args.kitchen_path,
        "--preset", args.preset,
        "--output", args.output,
    ], check=True)
```

```python
# kitchen-render/src/kitchen_render/blender_entry.py
# This runs INSIDE Blender's Python.
import bpy
import sys
# Parse args after "--"
args = parse_after_double_dash(sys.argv)

# Load kitchen (from outer process via path)
kitchen = load_kitchen(args.kitchen_path)
preset = load_preset(args.preset)

# Build scene
catalog = YamlCatalogReader(catalog_dir())
resolver = MaterialResolver(catalog, kitchen)
scene_builder = SceneBuilder(resolver, preset)
scene_builder.build(kitchen, bpy.context.scene)

# Render
bpy.context.scene.render.filepath = args.output
bpy.ops.render.render(write_still=True)

# Save .blend for carpenter's tweaking
blend_path = Path(args.output).with_suffix(".blend")
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
```

---

## Open Questions

> All must be answered before coding begins.

- [x] **Q1:** Drive `home_builder_5/` or write our own renderer? → **A:** Write our own. `home_builder_5/` has no headless API. See ADR Alternative A.
- [x] **Q2:** `bpy` pip package or subprocess? → **A:** Subprocess. Pip `bpy` is 1GB+, ties to specific Blender build, and conflicts with installed Blender. Subprocess is the standard pattern. See ADR Alternative B.
- [x] **Q3:** Where does the adapter package live? → **A:** `kitchen-render/` as a new sibling package (parallel to `kitchen-cad/`, `kitchen-app/`, `catalog/`). It is its own bounded context.
- [x] **Q4:** Eevee or Cycles as default? → **A:** Eevee (BLENDER_EEVEE_NEXT). Fast (~10-30s vs minutes), good enough for preview. Cycles available as `--engine cycles` Should-have.
- [x] **Q5:** Geometry from cabinet dimensions or from F002 recipe panels? → **A:** Cabinet dimensions in v1.0. Render is "what the kitchen looks like", not "what each panel looks like". F002 panels can be used in a future "exploded view" preset (backlog).
- [x] **Q6:** How do handles render? → **A:** Omitted in v1.0. A flush minimalist look is the visual default. Handle catalog is post-v1.0.
- [x] **Q7:** Multiple presets in one invocation? → **A:** Single preset per invocation in Must. `--all-presets` is Should.
- [x] **Q8:** What if Blender is not installed? → **A:** Clear error: "Blender not found. Install from blender.org or set $BLENDER_PATH. v1.0 requires Blender ≥ 3.6 LTS."
- [x] **Q9:** Should the `.blend` file embed the project YAML for round-tripping? → **A:** Not in v1.0. Carpenter regenerates from the YAML, doesn't edit YAML from .blend. One-way pipeline.
- [x] **Q10:** Camera position units — meters or millimeters? → **A:** Millimeters in preset YAML for consistency with the rest of our system. Adapter converts to meters internally before setting `bpy.context.scene.camera.location` (Blender's native unit).
- [x] **Q11:** How do we test the adapter without invoking Blender? → **A:** Mock `bpy` in unit tests using `sys.modules["bpy"] = MagicMock()`. The `scene_builder.py`'s logic (placement, material assignment) is testable purely. Smoke integration test invokes real Blender once.
- [x] **Q12:** Wall geometry — derived from rows or declared explicitly? → **A:** Derived. Each row implies a wall behind it; the room outline is inferred. Carpenter doesn't model walls explicitly in v1.0; the kitchen YAML doesn't have a `room` section yet (backlog).
- [x] **Q13:** Output `.blend` always, or opt-in? → **A:** Always. It's a free side effect of Blender saving the scene, and it's valuable to the carpenter for manual tweaking.
- [x] **Q14:** What's the relationship to F008's CLI (`kitchen-cli cut-list`, etc.)? → **A:** Same CLI binary, different subcommand. `kitchen-cli render`, `kitchen-cli cut-list`, `kitchen-cli dxf` all live in a common `kitchen-cli` entry point. F008 will own the entry point; F007 contributes the `render` subcommand. Coordinate at implementation time.
- [x] **Q15:** Wrocław-specific styling (Polish kitchens often have specific colors / preferences)? → **A:** Not in renderer. Style comes from the chosen decors, which the carpenter selects per project. F007 is style-neutral.

**All Open Questions resolved.** Spec is **ready** for implementation.
