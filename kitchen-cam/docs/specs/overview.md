> ⚠️ STALE (audit 2026-07): describes pre-ADR-010 state (deprecated modules as primary pipeline). Trust `kitchen-cam/AGENTS.md` + `docs/adr/010-*.md` instead. Do not act on this file without re-verification.

# Kitchen CAM — Overview

**Kitchen CAM** is a kitchen cabinet design and manufacturing automation system. It takes high-level cabinet specifications and generates the detailed panel cutting lists, edge banding instructions, and CNC drilling templates needed to actually build them.

## The Core Pipeline

```
CorpusSpec (cabinet design) → Panel Calculator → Drill Engine → CSV/DXF Output
```

### 1. Models (`src/kitchen_cam/models.py`)

Defines the domain: `CorpusSpec` (a cabinet with width/height/depth, shelves, drawers, doors, hinges, handles), `Panel` (individual board with dimensions, edges, drill points), and supporting enums (`PanelRole`, `DrillType`, `DrillFace`, etc.)

### 2. Panel Calculator (`src/kitchen_cam/panel_calculator.py`)

Takes a `CorpusSpec` and calculates all panels: side walls, top/bottom, shelves, back, door fronts, drawer fronts — with correct dimensions, materials, and edge banding assignments.

### 3. Machining (`src/kitchen_cam/machining.py`)

Adds drilling operations to panels:

- **System 32** holes (European cabinet standard, 32mm grid)
- **Hinge cup** holes (Blum, Hettich, Salice, GTV brands)
- **Handle** mounting holes
- **Shelf pin** holes

### 4. CSV Generator (`src/kitchen_cam/csv_generator.py`)

Exports cutting lists and edging lists as CSV for saws/edge banders.

### 5. DXF Generator (`generators/legrabox_side_panel.py`)

Generates DXF drawings for Blum Legrabox drawer side panels (CAD output).

## What It Supports

- **Base cabinets** with doors and/or drawers (2-drawer, 3-drawer Legrabox/Metabox)
- **Wall cabinets** with doors and shelves
- Multiple hinge brands (Blum Clip, Hettich, Salice, GTV)
- Edge banding on selected sides
- Back panel grooving
- Panel mirroring (left → right)

## Test Coverage

~75% of the codebase is tests — very well tested across unit, integration, and E2E layers covering drilling positions, edge banding, panel dimensions, materials, handles, hinges, grooving, mirroring, and validation.

## Summary

A parametric kitchen cabinet CAM (Computer-Aided Manufacturing) tool — feed it a cabinet spec, get back everything a workshop needs to cut, band, and drill the panels.
