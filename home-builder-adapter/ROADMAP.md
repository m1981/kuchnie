# home-builder-adapter Roadmap

Thin Blender adapter (~200 LOC). Extracts kitchen data from `home_builder_5`
`.blend` scenes → `kuchnie_core.Kitchen` JSON.

---

## Current (extract.py + cli.py)

- ✅ Walk `IS_FRAMELESS_*_CAGE` objects
- ✅ Extract cabinet dimensions, positions, types
- ✅ Produce `kuchnie_core.Kitchen` via `cabinets_to_kitchen()`
- ✅ CLI entry point: `blender --background scene.blend --python -m home_builder_adapter`

---

## Next

- 📋 Verify against real `.blend` file (extract.py was written from cold-review doc)
- 📋 Adjust `_PROP_*` constants if home_builder_5 uses different property names
- 📋 Handle edge cases: empty scenes, missing properties, non-cabinet objects

---

## Not in scope

Geometry building, wall layout, validation, rendering, material management —
these live in `home_builder_5`, `kuchnie_core`, or `krono-compositor-mvp`.
See ADR-009 for the full boundary.
