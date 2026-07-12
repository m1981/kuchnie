# home_builder_5 — headless scripting reference

> Reader: anyone driving hb5 from `blender --background` (walking-skeleton
> legs, future extraction-fidelity work) | Enables: building rooms and
> cabinets programmatically without rediscovering the modal-operator dead
> ends | Update-trigger: hb5 registration, type-class API, or property
> storage changes

Established empirically 2026-07-12 (walking-skeleton D60; working example:
`exercises/walking-skeleton-d60/blender_leg.py`). hb5 lives at
`/Users/michal/PycharmProjects/home_builder_5`; Blender 5.1.2.

## Enabling (legacy-addon path — the one that works)

```python
import sys, addon_utils
sys.path.append("/Users/michal/PycharmProjects")   # parent of the repo dir
addon_utils.enable("home_builder_5", default_set=True, persistent=True)
```

- Do NOT `import` + `register()` bare: `get_user_preferences` needs the
  `preferences.addons["home_builder_5"]` entry that only `addon_utils.enable`
  creates (walls crash without it).
- Do NOT install as a Blender extension: `blender_manifest.toml` lists
  Pillow wheels under `./wheels/` which don't exist in the repo — wheel
  validation fails. The legacy path ignores the manifest.
- The `load_post` handler doesn't fire headless (no file load) — call
  manually: `hb_project.ensure_main_scene()` and
  `main.hb_frameless.ensure_default_style()`.

## Building geometry (type classes, never modal operators)

Placement operators (`hb_frameless_OT_place_cabinet`, `draw_walls`) are
modal + VIEW_3D-bound — unusable headless. The non-modal path used by hb5's
own elevation templates (`props_elevation_templates.py:663-714`):

```python
from home_builder_5 import hb_types, hb_utils, units
from home_builder_5.product_libraries.frameless import types_frameless

w = hb_types.GeoNodeWall(); w.create("Wall")
w.set_input("Thickness", units.millimeter(100))
w.set_input("Height", units.millimeter(2400))
w.set_input("Length", units.millimeter(3000))
w.obj.location = (0, 0, 0); w.obj.rotation_euler.z = 0

cab = types_frameless.BaseCabinet()
cab.default_exterior = "3 Drawers"        # -> add_drawer_stack(3)
cab.width  = units.millimeter(600)        # all units METERS internally
cab.depth  = units.millimeter(560)
cab.height = units.millimeter(820)        # includes toe kick
cab.create("Base 600 3-Drawer")           # sets cage markers + CABINET_TYPE
cab.obj.location = (units.millimeter(600), 0, 0)
hb_utils.run_calc_fix(bpy.context, cab.obj, passes=3)  # force driver eval
```

## What the cage object actually stores (extraction contract)

Verified via `exercises/walking-skeleton-d60/generated/raw-cage-dump.json`:

- ID props present: `IS_FRAMELESS_CABINET_CAGE`, `CABINET_TYPE`,
  `Toe Kick Height` (meters), `Material Thickness` (0.01905 imperial
  default), `Base Top Construction`, `Stretcher Width`.
- **NOT ID props:** `Dim X/Y/Z` (geometry-node modifier inputs — read the
  evaluated `obj.dimensions` bbox instead) and `opening_sizes` (transient
  Python attribute on the SplitterVertical wrapper; never persisted —
  drawer stacks are currently unextractable from a saved scene, see
  wk-81a47ab8 extraction fidelity round 2).
- Cabinets are generated procedurally — there is no "3 drawer base" .blend
  asset to append; `.blend` assets are geo-node groups + materials only.

## Gotchas

- `run_calc_fix` (2–3 passes) is mandatory before reading dimensions —
  grandchild drivers lag (Blender bug referenced in hb5 source).
- Viewport/HUD helpers (`save_view_state`, `frame_all_objects`) need a
  screen — skip them headless.
- Room scenes: `operators/rooms.py` only manages Scene objects; actual wall
  geometry comes from `GeoNodeWall` as above.
