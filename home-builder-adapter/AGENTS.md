# Agent Guide — home-builder-adapter

Read this before making changes. It's short on purpose.

---

## Project at a glance

Adapter that extracts kitchen data from a `home_builder_5` Blender scene and
produces a `kuchnie_core.Kitchen`. This is the **Anti-Corruption Layer** between
home_builder_5's vocabulary and your domain model.

**One sentence:** `.blend` scene → walk `IS_FRAMELESS_*_CAGE` tree →
`kuchnie_core.Kitchen` JSON

---

## Architecture (3 rules)

1. **This package requires `bpy`.** It only works inside Blender's interpreter
   or with `pip install bpy`. Never import bpy in `kuchnie_core`. (`ADR-009`)

2. **home_builder_5's vocabulary stays here.** `IS_FRAMELESS_CABINET_CAGE`,
   `CABINET_TYPE`, `Dim X/Y/Z`, `opening_sizes` — these strings appear ONLY in
   `extract.py`. They never leak into `kuchnie_core`.

3. **Output is `kuchnie_core.Kitchen`.** The adapter's job ends when it produces
   a valid Kitchen model. Everything downstream (decomposition, BOM, CSV, DXF)
   consumes that Kitchen.

---

## File map

```
src/
├── __init__.py
├── extract.py    Walks Blender scene → kuchnie_core.Kitchen
├── cli.py        CLI entry point (blender --background --python ...)
```

**Dependency direction:** `extract.py` → `kuchnie_core` (imports only).
Never import downward.

---

## What was deleted (per ADR-009)

The following files were in the former `kitchen-plugin/` and were either
moved to `kuchnie_core` or deleted:

| File | Action | Destination |
|---|---|---|
| `core/geometry.py` | Moved | `kuchnie_core/geometry.py` |
| `core/types.py` | Moved | `kuchnie_core/types.py` |
| `kitchen/standards.py` | Moved | `kuchnie_core/standards.py` |
| `kitchen/cabinet_geometry.py` | Merged | `kuchnie_core/construction.py` |
| `manifest_validator.py` | Moved | `kuchnie_core/validator.py` |
| `geometry_builder.py` | Deleted | home_builder_5 builds geometry now |
| `wall_builder.py` | Deleted | home_builder_5 owns walls |
| `kitchen/wall.py` | Deleted | Replaced by kuchnie_core model |
| `kitchen/cabinet.py` | Deleted | Replaced by kuchnie_core model |
| `kitchen/layout.py` | Deleted | home_builder_5 lays out cabinets |
| `config_parser.py` | Deleted | Input is a Blender scene, not JSON |
| `validators.py` | Deleted | Validation moved to kuchnie_core |
| `material_manager.py` | Deleted | krono-compositor-mvp handles textures |
| `exporters.py` | Deleted | Rendering lives in krono-compositor-mvp |
| `main.py` | Deleted | Replaced by cli.py |

---

## Verifying against a real scene

The `extract.py` module was written from the cold-review doc
(`docs/archive/COLD-REVIEW-HOME-BUILDER-5.md`), NOT from inspecting a real
`.blend` file. Before using in production:

1. Open a kitchen `.blend` file created with home_builder_5
2. Run: `blender --background scene.blend --python -c "import bpy; print([o.name for o in bpy.data.objects if o.get('IS_FRAMELESS_CABINET_CAGE')])"`
3. Verify the property names match what `extract.py` expects
4. Adjust `_PROP_*` constants if home_builder_5 uses different names

---

## Adding a new extraction field

1. Find the property name in home_builder_5's Blender scene
2. Add a `_PROP_*` constant in `extract.py`
3. Read it in `_extract_cabinet()`
4. Map it to a `kuchnie_core` model field
5. Update `cabinets_to_kitchen()` if the Kitchen model needs extension
6. Write a test (requires bpy mock or real scene)

---

## Documentation conventions

| What | Where |
|---|---|
| "We chose X because Y" | `docs/adr/NNN-<slug>.md` (in repo root) |
| "The property is Z" | `_PROP_*` constant in `extract.py` |
| "What changed" | `CHANGELOG.md` |
| "How to use this" | Module docstring at top of file |
| "How the system works" | `AGENTS.md` (this file) |
