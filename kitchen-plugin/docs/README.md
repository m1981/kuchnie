# Kitchen Plugin Documentation

## Overview

This directory contains documentation for the kitchen cabinet 3D generator.
The plugin reads JSON config files and generates kitchen cabinet models in Blender.

---

## Reading Guide

### For New Developers (Start Here)

Read in this order:

1. **[architecture.md](architecture.md)** — Start here!
   - Layer architecture with mermaid diagrams
   - Dependency rules
   - Module overview
   - File structure

2. **[config-syntax.md](config-syntax.md)** — JSON config reference
   - Schema overview
   - Settings (dimensions, gaps, tolerances)
   - Cabinet types and properties
   - Layout examples (I, L, U shape)

3. **[wall-centric-model.md](wall-centric-model.md)** — Positioning model
   - How cabinets are positioned relative to walls
   - Wall-local vs world coordinates
   - Corner handling

### For LLM Agents / AI Assistants

Read:

1. **[llm-context.md](llm-context.md)** — Project context for AI
   - Current architecture
   - Coordinate system
   - Key rules and conventions
   - Test validation pipeline

### For CAD/Kitchen Domain Reference

Read:

1. **[european-kitchen-standards.md](european-kitchen-standards.md)** — Kitchen standards
   - 32mm system
   - Standard dimensions
   - Cabinet types
   - Handle types
   - Material system

2. **[cad-principles-part1.md](cad-principles-part1.md)** — CAD principles (part 1)
   - Coordinate system discipline
   - Separation of concerns
   - Units and precision
   - Constraint-based layout

3. **[cad-principles-part2.md](cad-principles-part2.md)** — CAD principles (part 2)
   - B-rep topology
   - Parametric modeling
   - Performance patterns
   - Export/interop

---

## File Index

| File | Purpose | Audience |
|---|---|---|
| `README.md` | This file — reading guide | Everyone |
| `architecture.md` | SOLID architecture overview | Developers |
| `config-syntax.md` | JSON config syntax reference | Developers, Users |
| `wall-centric-model.md` | Wall-centric positioning model | Developers |
| `llm-context.md` | LLM persona and project context | AI Assistants |
| `european-kitchen-standards.md` | European kitchen standards | Domain Experts |
| `cad-principles-part1.md` | CAD principles (reference) | Developers |
| `cad-principles-part2.md` | CAD principles (reference) | Developers |

---

## Quick Reference

### Running Tests

```bash
# All tests (no Blender required)
.venv/bin/python -m pytest tests/ -v

# Specific test suite
.venv/bin/python -m pytest tests/test_kitchen.py -v
```

### Generating 3D Models

```bash
# Generate .blend file
blender --background --python src/main.py -- configs/ref_u_shape.json --export-blend

# Open in Blender
open output/meshes/ref_u_shape.blend
```

### Key Directories

```
kitchen-plugin/
├── src/
│   ├── core/        # Pure math (Vector, BoundingBox, Transform)
│   ├── kitchen/     # Domain logic (Wall, Cabinet, Layout)
│   ├── adapters/    # Blender integration
│   └── ...
├── tests/           # Test suite (218 tests)
├── configs/         # Example JSON configs
├── output/          # Generated .blend and .obj files
└── docs/            # This directory
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

- **Tests:** 218 passing, 17 skipped (bpy required)
- **Architecture:** SOLID with layered design
- **Config Version:** 1.1 (with backward compatibility for 1.0)
