# Roadmap

## Status Legend

| Marker | Meaning                                |
| ------ | -------------------------------------- |
| ✅     | Done — implemented, tested, documented |
| 🔨     | In Progress — actively being worked on |
| 📋     | Planned — spec exists, not started     |
| ❄️     | Parked — not abandoned, just not now   |

---

## Current Phase: Manifest Pipeline + Generator Hardening

### Manifest-First Pipeline

- ✅ `geometry_manifest.py` — JSON manifest export (primary output)
- ✅ `manifest_validator.py` — dimension, overlap, clearance checks
- ✅ `schemas/manifest_v2.schema.json` — JSON Schema for manifest format
- ✅ Standalone `scripts/validate_manifest.py` (no bpy required)
- ✅ Deprecated OBJ/glTF inspection scripts removed

### Generator Bug Fixes

- ✅ Board-based carcass rewrite (4 separate boards with technical gaps)
- 🔨 Corner handling — U-shape corner overlaps need resolution
- 📋 Countertop overhang accuracy
- 📋 Filler positioning at run ends

### Schema & Config

- ✅ Schema versioning (1.0 → 1.1 with backward compat)
- ✅ Gap system: `cabinetGap` (carcass) vs `frontGap` (fronts)
- ✅ Tolerance model (frontOffset, clearanceOffset)
- ✅ Construction parameters (corpus, front, back thickness)

---

## Next Phase: Material System + Rendering

See [docs/roadmap-production-cad.md](docs/roadmap-production-cad.md) for full detail.

### Material System

- 📋 Material catalog schema (`schemas/material_catalog.schema.json`)
- 📋 PBR texture loading (color, roughness, normal maps)
- 📋 Material assignment by component type
- 📋 Material variant generation for customer comparison

### Scene & Rendering

- 📋 Room template system (L-shaped, U-shaped, galley)
- 📋 Camera presets (front elevation, 3/4 view, top-down)
- 📋 HDRI environment lighting
- 📋 Multi-view render pipeline (batch all views in one pass)

---

## Future: Production Data

### BOM & Cut List

- 📋 Panel extraction from geometry
- 📋 BOM generation (panels + hardware)
- 📋 Cut list with 2D bin packing optimization
- 📋 DXF export for panel saws

### Design Intelligence

- 📋 Constraint-based layout (auto, remaining, fill widths)
- 📋 Corner cabinet types (blind, diagonal, L-shape, super-corner)
- 📋 Appliance integration (oven, cooktop, sink, fridge)
- 📋 Design rules engine (safety, ergonomics, construction)

### Customer Interaction

- 📋 Web configuration form
- 📋 Multi-variant comparison (side-by-side renders)
- 📋 Cost estimation
- ❄️ Interactive 2D plan editor

---

## Specs

Feature specs live in `docs/specs/`:

| Spec                             | Status                             |
| -------------------------------- | ---------------------------------- |
| `docs/roadmap-production-cad.md` | Master reference for future phases |
