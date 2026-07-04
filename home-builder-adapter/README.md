> Type: F | Status: frozen 2026-07 (see /MIGRATION-STATUS.md) | Role: Blender scene → kuchnie_core.Kitchen extractor | ADRs: 009

# home-builder-adapter

Blender adapter that extracts kitchen data from a `home_builder_5` scene and
produces a `kuchnie_core.Kitchen`.

**Role:** Anti-Corruption Layer between the external, licensed `home_builder_5`
Blender addon and the pure-Python `kuchnie_core` domain model.
See [ADR-009](../docs/adr/009-kitchen-plugin-becomes-home-builder-adapter.md).

---

## One-sentence flow

```
.blend scene ── walk IS_FRAMELESS_*_CAGE tree ──▶ kuchnie_core.Kitchen JSON
```

## Contract

- **Input:** a `.blend` file authored with `home_builder_5`
- **Output:** `kuchnie_core.Kitchen` (via `serialize.kitchen_to_dict` → JSON)
- **Dependency direction:** `extract.py` → `kuchnie_core` (never reverse)
- **Requires:** `bpy` (Blender's Python) — either run inside Blender or
  `pip install bpy`

## Layout

```
home-builder-adapter/
├── src/
│   ├── extract.py         Scene walker → Kitchen (all bpy calls live here)
│   └── cli.py             CLI entry point
├── AGENTS.md              Read this before making changes
├── ROADMAP.md             What's next
├── CHANGELOG.md           What changed
└── docs/
    ├── archive/           Historical docs from the old kitchen-plugin scope
    └── reference/         Cheatsheets (SketchUp, etc.)
```

## Usage

Inside Blender:

```bash
blender --background scene.blend --python-expr "from home_builder_adapter.cli import main; main()"
```

Standalone (requires `pip install bpy`):

```bash
python -m home_builder_adapter.cli
```

Outputs `kuchnie_core.Kitchen` JSON to stdout.

## What lives elsewhere

| Concern | Where |
|---|---|
| Domain model (Kitchen, Row, CabinetInstance) | `kuchnie-core/src/kuchnie_core/model.py` |
| Cabinet geometry, panels, standards, validator | `kuchnie-core/src/kuchnie_core/` |
| CAM output — cut list CSV, drilling DXF | `kitchen-cam/` |
| Rendering, decor swap, sales screenshot | `krono-compositor-mvp/` |
| BOM, cost, purchasing | `kitchen-erp/` (formerly `kitchen-app/`) |

See [ADR-009](../docs/adr/009-kitchen-plugin-becomes-home-builder-adapter.md)
for the full boundary rationale.

## History

This project was previously `kitchen-plugin/` — a full generator that built
geometry, walls, layouts, materials, and rendered `.blend` files from a JSON
config. That scope moved elsewhere (`home_builder_5` now owns geometry,
`kuchnie_core` owns the domain model, `krono-compositor-mvp` owns rendering).
The old design docs are preserved in [`docs/archive/`](docs/archive/).
