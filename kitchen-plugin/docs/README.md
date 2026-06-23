# Kitchen Plugin Documentation

## Overview

This directory contains documentation for the kitchen cabinet 3D generator.
The plugin reads JSON config files and generates kitchen cabinet models in Blender.

**Primary output:** Structured JSON geometry manifest for validation.
Visual exports (OBJ, glTF, .blend) are optional.

---

## Reading Guide

### For New Developers (Start Here)

Read in this order:

1. **[architecture.md](architecture.md)** — Start here!
    - Layer architecture
    - Manifest-first pipeline
    - Dependency rules
    - Module overview

2. **[implementation-plan.md](implementation-plan.md)** — Migration plan
    - Phased implementation
    - New modules (geometry_manifest, manifest_validator)
    - Test strategy

3. **[config-syntax.md](config-syntax.md)** — JSON config reference
    - Schema overview
    - Settings (dimensions, gaps, tolerances)
    - Cabinet types and properties
    - Layout examples (I, L, U shape)

4. **[wall-centric-model.md](wall-centric-model.md)** — Positioning model
    - How cabinets are positioned relative to walls
    - Wall-local vs world coordinates
    - Corner handling

### For LLM Agents / AI Assistants

Read:

1. **[architecture.md](architecture.md)** — Architecture, manifest schema, validation pipeline
2. **[../ROADMAP.md](../ROADMAP.md)** — Current status and what's next
3. **[3d-format-strategy.md](3d-format-strategy.md)** — Why manifest is primary output

### For CAD/Kitchen Domain Reference

Read:

1. **[european-kitchen-standards.md](european-kitchen-standards.md)** — Kitchen standards
2. **[cad-principles-part1.md](cad-principles-part1.md)** — CAD principles (part 1)
3. **[cad-principles-part2.md](cad-principles-part2.md)** — CAD principles (part 2)
4. **[3d-format-strategy.md](3d-format-strategy.md)** — Format comparison & rationale

---

## File Index

| File                    | Purpose                        | Audience          |
| ----------------------- | ------------------------------ | ----------------- |
| `README.md`             | This file — reading guide      | Everyone          |
| `architecture.md`       | SOLID architecture overview    | Developers        |
| `config-syntax.md`      | JSON config syntax reference   | Developers, Users |
| `wall-centric-model.md` | Wall-centric positioning model | Developers        |

| `european-kitchen-standards.md` | European kitchen standards | Domain Experts |
| `cad-principles-part1.md` | CAD principles (reference) | Developers |
| `cad-principles-part2.md` | CAD principles (reference) | Developers |

---

## Quick Reference

### Running Tests

```bash
# All tests (no Blender required)
.venv/bin/python -m pytest tests/ -v

# Manifest tests only
.venv/bin/python -m pytest tests/test_manifest_*.py -v
```

### Generating 3D Models

```bash
# Generate with manifest (primary output)
blender --background --python src/main.py -- configs/ref_u_shape.json

# Generate with manifest + validation
blender --background --python src/main.py -- configs/ref_u_shape.json --validate

# Generate with visual exports
blender --background --python src/main.py -- configs/ref_u_shape.json --export-blend --export-obj

# Open in Blender
open output/meshes/ref_u_shape.blend
```

### Validating Manifests (No Blender Required)

```bash
# Validate a manifest
python scripts/validate_manifest.py output/meshes/ref_u_shape_manifest.json

# Summarize a manifest (LLM-friendly)
python scripts/summarize_manifest.py output/meshes/ref_u_shape_manifest.json
```

### Key Directories

```
kitchen-plugin/
├── src/
│   ├── core/              # Pure math (Vector, BoundingBox, Transform)
│   ├── kitchen/           # Domain logic (Wall, Cabinet, Layout)
│   ├── geometry_manifest.py  # Manifest export (PRIMARY output)
│   ├── manifest_validator.py # Manifest validation
│   ├── geometry_builder.py   # Blender mesh creation
│   ├── exporters.py          # OBJ, glTF, .blend (optional)
│   └── ...
├── schemas/               # JSON Schema for manifest format
├── scripts/               # Standalone tools (no bpy needed)
├── tests/                 # Test suite (332+ tests)
├── configs/               # Example JSON configs
├── output/                # Generated manifests, .blend, .obj
└── docs/                  # This directory
```

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: core/          Pure math, no dependencies          │
│ Layer 2: kitchen/       Domain logic (Wall, Cabinet, Layout)│
│ Layer 3: builder/       Config parsing, validation          │
│ Layer 4: adapters/      Blender integration                 │
│ Layer 5: main.py        CLI entry point                     │
└─────────────────────────────────────────────────────────────┘

Dependency Rule: core/ ← kitchen/ ← builder/ ← adapters/
                 (Never reverse arrows)
```

---

## Contributing

When adding new documentation:

1. Use descriptive filenames (e.g., `config-syntax.md` not `f02-kitchen-config-syntax.md`)
2. Add entry to this README.md
3. Include mermaid diagrams for complex concepts
4. Keep docs in sync with code changes

---

## Current Status

Run `make test` to verify all tests pass.

See [ROADMAP.md](../ROADMAP.md) for what's done and what's next.
See [CHANGELOG.md](../CHANGELOG.md) for recent changes.

- **Architecture:** Manifest-first with SOLID layered design
- **Config Version:** 1.1 (with backward compatibility for 1.0)
- **Manifest Version:** 2.0 (primary validation output)
