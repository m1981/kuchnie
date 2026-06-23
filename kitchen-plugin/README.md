# Kitchen Plugin Documentation

## What Is This?

This plugin generates 3D kitchen cabinets in Blender from a JSON config file.
You describe your kitchen layout in JSON — which cabinets, what sizes, where
they go — and the plugin builds the 3D geometry.

But here's the key question: **how do you know Blender built the right thing?**

That's what the **geometry manifest** is for.

## How It Works

The flow is simple:

```
JSON config (your blueprint)
    │
    ▼
Blender builds 3D meshes (geometry_builder.py)
    │
    ├──▶ manifest.json  ← report card: exact measurements, pass/fail
    └──▶ .blend file    ← optional: open in Blender to look at
```

The manifest is **not** the input — it's the output. Blender builds the
geometry first, then the manifest reads what Blender built and reports
whether it matches your config.

Think of it like building a house:

| Step                          | Kitchen Plugin                                  |
| ----------------------------- | ----------------------------------------------- |
| **Blueprint**                 | JSON config file                                |
| **Building the house**        | `geometry_builder.py` creates meshes in Blender |
| **Walking through the house** | Opening `.blend` in Blender                     |
| **Inspector's report**        | The manifest (exact measurements, pass/fail)    |

The manifest doesn't build anything. It **inspects** what was built and
reports whether it matches the blueprint.

## Why Not Just Use OBJ or glTF?

OBJ and glTF are rendering formats — they answer "how do I draw this?" They
don't carry units, coordinate system info, or object names. Every parser has
to guess.

The manifest carries everything explicitly:

- `"units": "meters"` — no guessing
- `"coordinate_system": "Z-up"` — no heuristic detection
- `"name": "run0_base_0_base-door"` — you know what each object is
- `"validation": { "width_ok": true }` — self-checking

OBJ and glTF exports have been removed. The manifest replaced them.

## Quick Start

### Run Tests (No Blender Needed)

```bash
.venv/bin/python -m pytest tests/ -v
```

### Generate a Kitchen

```bash
# Build in Blender + export manifest
blender --background --python src/main.py -- configs/ref_l_shape.json

# Build + validate (prints pass/fail report)
blender --background --python src/main.py -- configs/ref_l_shape.json --validate

# Build + save .blend for visual inspection
blender --background --python src/main.py -- configs/ref_l_shape.json --export-blend
```

### Validate a Manifest (No Blender Needed)

```bash
# Detailed validation report
python scripts/validate_manifest.py output/meshes/ref_l_shape_manifest.json

# Human/LLM-friendly summary
python scripts/summarize_manifest.py output/meshes/ref_l_shape_manifest.json
```

### CLI Flags

```
blender --background --python src/main.py -- configs/kitchen.json
    --validate              Run manifest validation after export
    --no-manifest           Skip manifest export (not recommended)
    --no-materials          Skip Cycles materials (faster)
    --export-blend          Save .blend to output/meshes/
    --render-wireframe      PNG wireframe render
```

## Reading Guide

### For New Developers (Start Here)

1. **[architecture.md](docs/architecture.md)** — Layer architecture, manifest
   schema, validation pipeline, module overview
2. **[config-syntax.md](docs/config-syntax.md)** — JSON config reference: settings,
   cabinet types, layout examples (I, L, U shape)
3. **[wall-centric-model.md](docs/wall-centric-model.md)** — How cabinets are
   positioned relative to walls, corner handling

### For LLM Agents / AI Assistants

1. **[architecture.md](docs/architecture.md)** — Architecture, manifest schema,
   validation pipeline
2. **[ROADMAP.md](ROADMAP.md)** — Current status and what's next
3. **[3d-format-strategy.md](docs/3d-format-strategy.md)** — Why manifest is
   primary output

### For CAD/Kitchen Domain Reference

1. **[european-kitchen-standards.md](docs/european-kitchen-standards.md)** — Kitchen
   standards (dimensions, 32mm system)
2. **[cad-principles.md](docs/cad-principles.md)** — CAD principles and conventions
3. **[roadmap-production-cad.md](docs/roadmap-production-cad.md)** — Production CAD
   roadmap (renders, BOM, CNC)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 5: main.py            CLI entry point                     │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: adapters/          Blender integration                 │
│   geometry_builder.py       bpy mesh creation                   │
│   geometry_manifest.py      JSON manifest (PRIMARY output)      │
│   manifest_validator.py     Dimension/overlap/clearance checks  │
│   exporters.py              .blend save, wireframe render       │
│   material_manager.py       Cycles materials                    │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: builder/           Config parsing                      │
│   config_parser.py          JSON loading, defaults              │
│   validators.py             Semantic validation                 │
│   wall_builder.py           Config → Wall/Cabinet objects       │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: kitchen/           Domain logic                        │
│   wall.py                   Wall, Room, CornerReference             │
│   cabinet.py                Cabinet, CabinetPlacement           │
│   layout.py                 Run, LayoutEngine                   │
│   cabinet_geometry.py       Board-level construction math       │
│   standards.py              KitchenStandards (dims + tolerances)          │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: core/              Pure math, no dependencies          │
│   geometry.py               Vector2D, Vector3D, BoundingBox     │
│   types.py                  Direction, CabinetType, Dimensions  │
│   tolerances.py             Geometric tolerance utilities                    │
└─────────────────────────────────────────────────────────────────┘

Dependency rule: core/ ← kitchen/ ← builder/ ← adapters/ ← main.py
                 (Never reverse arrows)
```

## File Index

| File                             | Purpose                        | Audience          |
| -------------------------------- | ------------------------------ | ----------------- |
| `architecture.md`                | Layer architecture, manifest   | Developers        |
| `config-syntax.md`               | JSON config reference          | Developers, Users |
| `wall-centric-model.md`          | Wall positioning model         | Developers        |
| `geometry-inspection-tools.md`   | Manifest validation workflow   | Developers, LLM   |
| `archive/implementation-plan.md` | Migration plan (completed)     | Developers        |
| `ddd-strategic-design.md`        | DDD subdomains & boundaries    | Developers        |
| `3d-format-strategy.md`          | Format comparison & rationale  | Developers        |
| `roadmap-production-cad.md`      | Production CAD roadmap         | Developers        |
| `european-kitchen-standards.md`  | Kitchen standards              | Domain Experts    |
| `cad-principles.md`              | CAD principles and conventions | Developers        |

## Project Structure

```
kitchen-plugin/
├── src/
│   ├── core/                   # Pure math (Vector, BoundingBox, Transform)
│   ├── kitchen/                # Domain logic (Wall, Cabinet, Layout)
│   ├── geometry_builder.py     # Blender mesh creation (bpy)
│   ├── geometry_manifest.py    # Manifest export (PRIMARY output)
│   ├── manifest_validator.py   # Manifest validation checks
│   ├── config_parser.py        # JSON config loading
│   ├── validators.py           # Semantic validation
│   ├── wall_builder.py         # Config → domain objects
│   ├── exporters.py            # .blend save, wireframe render
│   ├── material_manager.py     # Cycles materials
│   └── main.py                 # CLI entry point
├── schemas/                    # JSON Schema for manifest format
├── scripts/                    # Standalone tools (no bpy needed)
│   ├── validate_manifest.py    # Validate a manifest file
│   └── summarize_manifest.py   # Human/LLM-friendly summary
├── tests/                      # Test suite (401 tests, 384 pass, 17 skip)
├── configs/                    # Example JSON configs
│   ├── ref_i_shape.json        # I-shape reference kitchen
│   ├── ref_l_shape.json        # L-shape reference kitchen
│   └── ref_u_shape.json        # U-shape reference kitchen
├── output/                     # Generated manifests and .blend files
└── docs/
    ├── architecture.md         # Layer architecture, manifest schema
    ├── config-syntax.md        # JSON config reference
    ├── wall-centric-model.md   # Wall positioning model
    ├── cad-principles.md       # CAD principles and conventions
    ├── geometry-inspection-tools.md  # Validation workflow
    ├── 3d-format-strategy.md   # Format comparison & rationale
    ├── european-kitchen-standards.md # Kitchen domain reference
    ├── roadmap-production-cad.md     # Production CAD roadmap
    ├── reference/              # Cheatsheets
    └── archive/                # Completed migration plans
```

## Current Status

- **Architecture:** Manifest-first with SOLID layered design
- **Config Version:** 1.1 (with backward compatibility for 1.0)
- **Manifest Version:** 2.0 (primary validation output)
- **Tests:** 401 collected, 384 passing, 17 skipped

See [ROADMAP.md](ROADMAP.md) for what's done and what's next.
See [CHANGELOG.md](CHANGELOG.md) for recent changes.

## Contributing

When adding new documentation:

1. Use descriptive filenames (e.g., `config-syntax.md` not `f02-config.md`)
2. Add entry to this README.md
3. Include mermaid diagrams for complex concepts
4. Keep docs in sync with code changes
