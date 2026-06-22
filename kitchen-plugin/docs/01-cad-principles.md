CAD Software Development: Principles, Rules & Conventions

1.  Core Geometric Principles

### Coordinate System Discipline

```
  Rule: ALWAYS define and document your coordinate system once.
  Convention: Stick to right-hand rule throughout.

    Z-up (architectural/BIM)     Y-up (game engines/some CAD)
    ┌───────┐                    ┌───────┐
    │  ↗ Z  │                    │  ↗ Y  │
    │ /     │                    │ /     │
    │/   → X│                    │/   → X│
    └───────┘                    └───────┘
         ↘ Y (into screen)           ↘ Z (into screen)

  Anti-pattern: Mixing conventions at boundaries (like your OBJ Y↔Z swap)
```

### Separation of Concerns: Model vs. View

```
  Model (pure math)        View (rendering/export)
  ─────────────────        ──────────────────────
  • Parametric data        • Mesh triangulation
  • Constraints            • Display lists
  • Topology               • Coordinate transforms
  • Units (always metric)  • File format specifics

  Rule: Model layer must be RENDERER-AGNOSTIC.
        Never put `bpy` calls in geometry math.
```

### Units & Precision

```
  Rule: Internal units = millimeters (mm) as integers or fixed-point.
        Export formats handle conversion.

  Why mm?  →  No floating-point errors for standard cabinet sizes
              300mm = 300, not 0.3000000000004

  Convention:
    • Internal:  mm (int32 or fixed-point)
    • Display:   mm with 1 decimal
    • Config:    mm (human-readable)
    • Export:    per format spec (OBJ=units, IFC=meters)
```

────────────────────────────────────────────────────────────────────────────────

2.  Parametric Design Principles

### Config-Driven Architecture (Your Current Pattern)

```python
  # GOOD: Config describes WHAT, code handles HOW
  {
    "cabinet": {
      "type": "base",
      "width": 600,      # WHAT size
      "position": [0, 0] # WHERE
    }
  }

  # BAD: Config embeds implementation details
  {
    "cabinet": {
      "mesh": "base_cabinet_600.obj",  # HOW to render
      "rotation_euler": [0, 0, 3.14]   # HOW to orient
    }
  }
```

### Parametric Hierarchy

```
  Project → Room → Run → Cabinet → Component (door, drawer, shelf)
      │         │        │           │
      └─ global └─ walls └─ local   └─ variants

  Rule: Parameters flow DOWN, constraints flow UP.
        A cabinet inherits room defaults unless overridden.
```

### Immutable Transform Pipeline

```
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │   Local     │ ──▶ │   World     │ ──▶ │   Export    │
  │  Space      │     │   Space     │     │   Space     │
  │             │     │             │     │             │
  │ Origin at   │     │ Placed per  │     │ Format-     │
  │ local (0,0) │     │ layout grid │     │ specific    │
  └─────────────┘     └─────────────┘     └─────────────┘
        ▲                   ▲                   ▲
        │                   │                   │
     geometry_builder   layout_engine      exporters
```

────────────────────────────────────────────────────────────────────────────────

3.  Topology & Mesh Rules

### Manifold Mesh Requirement

```
  Rule: Every exported mesh must be manifold (watertight).

  Why?  → CNC routers need closed volumes
         3D printers need printable meshes
         Boolean operations require clean topology

  Check: mesh.is_manifold in Blender Python
```

### Face Orientation (Normal Direction)

```
  Convention: Normals point OUTWARD from solid volume.

    ┌────────┐
    │        │
    │   →→→  │  ← Front face normal points into room (+Y)
    │        │
    └────────┘

  Rule: Never flip normals manually — fix the winding order.
        CCW winding = outward normal (right-hand rule).
```

### Vertex Order for CNC

```
  Rule: For CNC export, vertices must be ordered for tool path.

    Start →──→──→ End
        ↓           ↓
    Start ←──←──← End

  Convention: Outside-in cutting direction.
```

────────────────────────────────────────────────────────────────────────────────

4.  Constraint-Based Layout

### Constraint Types for Cabinetry

```python
  class ConstraintTypes:
      FIXED = "fixed"           # Absolute position: x=500
      RELATIVE = "relative"     # Offset: x=prev.x + prev.width + gap
      ALIGN = "align"           # Edge alignment: left, center, right
      SPAN = "span"             # Fill remaining: width=remaining
      ANCHOR = "anchor"         # Reference to wall/corner
```

### Solving Order

```
  Rule: Solve constraints in dependency order.

    1. Fixed positions first
    2. Relative offsets (depend on fixed)
    3. Spans (depend on relative)
    4. Alignment (depend on spans)

  Anti-pattern: Circular dependencies → infinite loop or wrong result
```

────────────────────────────────────────────────────────────────────────────────

5.  Validation Pipeline

### Three-Level Validation

```
  Level 1: SYNTAX (JSON schema)
    → "Is this valid JSON with required fields?"
    → Before any geometry calculation

  Level 2: SEMANTIC (domain rules)
    → "Does width match standard sizes?"
    → "Do cabinets overlap?"
    → "Is clearance ≥ 900mm for walkways?"
    → During layout solving

  Level 3: GEOMETRIC (mesh checks)
    → "Is mesh manifold?"
    → "Are dimensions within tolerance?"
    → After export
```

### Standard Tolerances

```python
  TOLERANCES = {
      "position": 0.1,      # mm — placement accuracy
      "dimension": 0.5,     # mm — size accuracy
      "angle": 0.01,        # radians — rotation
      "gap": 2.0,           # mm — cabinet gap standard
  }
```

────────────────────────────────────────────────────────────────────────────────

6.  Export & Interoperability

### Format Layer Pattern

```python
  class Exporter(ABC):
      @abstractmethod
      def export(self, scene: Scene, path: Path) -> None:
          """Transform scene graph to format-specific output."""

      def _apply_axis_swap(self, vertices):
          """Handle format-specific coordinate conventions."""
          # OBJ: Y↔Z swap
          # glTF: Y-up to Z-up
          # STEP: Right-hand to left-hand

  Rule: Each exporter owns its axis conventions.
        Core geometry NEVER swaps axes.
```

### Lossless Round-Trip Test

```
  Rule: Config → Generate → Export → Import → Compare → Config

    original.json ──▶ model.obj ──▶ reimport.obj ──▶ diff(original)
         │                                                    │
         └─────────────── dimensions match? ──────────────────┘
```

────────────────────────────────────────────────────────────────────────────────

7.  Code Architecture Conventions

### File Organization

```
  src/
  ├── core/                  # Pure math, no Blender dependency
  │   ├── geometry.py       # Vector, Matrix, Transform
  │   ├── constraints.py    # Constraint solver
  │   └── types.py          # Dataclasses, enums
  │
  ├── kitchen/               # Domain logic
  │   ├── cabinet.py        # Cabinet parametric model
  │   ├── layout.py         # Run/corner placement
  │   └── standards.py      # European norms (32mm system)
  │
  ├── adapters/              # External integrations
  │   ├── blender_mesh.py   # bpy mesh creation
  │   ├── obj_exporter.py   # OBJ format
  │   └── json_config.py    # Config parsing
  │
  └── validation/            # Testing & checks
      ├── geometric.py      # Mesh validation
      └── semantic.py       # Domain rules
```

### Dependency Rule

```
  core/ ← kitchen/ ← adapters/ ← scripts/
    │         │            │
    └─────────┴────────────┘
        Never reverse arrows

  Rule: Adapters depend on core, not vice versa.
        Kitchen logic never imports bpy.
```

────────────────────────────────────────────────────────────────────────────────

8.  Testing Conventions

### Test Pyramid for CAD

```
          ╱╲
         ╱  ╲         Visual regression (few)
        ╱────╲
       ╱      ╲       Integration: Config → Mesh → Validate (some)
      ╱────────╲
     ╱          ╲     Unit: Pure geometry math (many)
    ╱────────────╲
```

### Snapshot Testing for Meshes

```python
  def test_cabinet_mesh_dimensions():
      cabinet = Cabinet(width=600, depth=560, height=720)
      mesh = build_mesh(cabinet)

      # Snapshot: expected bounding box
      assert mesh.bounding_box == BoundingBox(
          min=Vector(0, 0, 0),
          max=Vector(600, 560, 720)
      )

      # Snapshot: vertex count (catches regression)
      assert len(mesh.vertices) == 8
      assert len(mesh.faces) == 6
```

────────────────────────────────────────────────────────────────────────────────

9.  European Kitchen Standards (Quick Reference)

```
  Standard           │ Base Cabinet │ Wall Cabinet │ Tall Cabinet
  ───────────────────┼──────────────┼──────────────┼─────────────
  Height (body)      │ 720mm        │ 600mm        │ 2100-2400mm
  Plinth height      │ 120mm        │ —            │ 120mm
  Total height       │ 840mm        │ —            │ 2220-2520mm
  Depth              │ 560mm        │ 300-350mm    │ 560-600mm
  Mount height       │ —            │ 1400mm AFF   │ —
  ───────────────────┴──────────────┴──────────────┴─────────────

  Standard widths: 300, 400, 450, 500, 600, 800, 900, 1000, 1200mm
  Gap between doors: 2mm
  Countertop overhang: 20mm front, 30mm ends
```
