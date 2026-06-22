# F03 — Standalone Blender Script Approach

Status: **Implemented** · Replaces Archimesh plugin for kitchen generation

---

## Decision

**Skip the Archimesh plugin entirely.** Use a standalone Python script that
calls Blender's API directly. The plugin was designed for interactive UI
use; our workflow is config-driven (JSON in, 3D out).

## Architecture

```
JSON config → config_parser.py → geometry_builder.py → Blender scene
                                      ↓
                              exporters.py → OBJ / GLTF / wireframe PNG
                                      ↓
                              validators.py → dimension/position checks
```

## Module Responsibilities

| Module | bpy dependency | Purpose |
|---|---|---|
| `main.py` | yes | CLI entry point, orchestration |
| `config_parser.py` | no | JSON loading, validation, mm→m conversion |
| `geometry_builder.py` | yes | Mesh creation (external shell only) |
| `material_manager.py` | yes | Cycles materials |
| `exporters.py` | yes | OBJ, GLTF, wireframe export |
| `validators.py` | no | Dimension, position, gap checks |

## CLI Usage

```bash
# Full pipeline
blender --background --python src/main.py -- \
  configs/l_shape.json --export-obj --render-wireframe

# Unit tests (no Blender)
python -m pytest tests/test_config_parser.py tests/test_positions.py

# Integration tests (Blender)
blender --background --python tests/test_integration.py
```

## Design Principles

1. **External only** — model what the camera sees, skip internals
2. **Config as contract** — JSON is the single source of truth
3. **mm in config, m in Blender** — conversion happens in config_parser
4. **Pure Python where possible** — config_parser and validators have no bpy
5. **Headless by default** — `blender --background` is the primary mode
6. **Testable** — every module can be tested independently

## Iteration Loop

```
Edit src/*.py or configs/*.json
  → blender --background --python src/main.py -- configs/test.json --export-obj
  → Check output/meshes/*.obj
  → Fix, repeat
```

No plugin reload. No Blender restart. Seconds per iteration.

## File Structure

```
kitchen-plugin/
├── src/
│   ├── main.py
│   ├── config_parser.py
│   ├── geometry_builder.py
│   ├── material_manager.py
│   ├── exporters.py
│   └── validators.py
├── tests/
│   ├── test_config_parser.py
│   ├── test_positions.py
│   └── test_integration.py
├── configs/
│   ├── i_shape.json
│   ├── l_shape.json
│   └── u_shape.json
├── output/
│   ├── meshes/
│   └── renders/
├── archimesh/                   # Reference only, not used
└── docs/
```

## What We Keep From Archimesh

Only the `from_pydata()` mesh generation pattern. The rest is discarded.

## What We Lose (And Don't Need)

- Blender UI panels (config-driven)
- OpenGL hints (we export OBJ/PNG)
- Addon registration (standalone script)
- Interactive property updates (regenerate from config)
