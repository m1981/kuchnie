# CAD Principles — Rules & Conventions

This document combines project-specific CAD rules with general CAD software
development principles. Part 1 covers rules specific to this kitchen plugin.
Part 2 covers general CAD architecture and best practices.

---

# Part 1: Kitchen Plugin CAD Rules

## 1. Core Geometric Principles

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

---

# Part 2: General CAD Software Development Principles

1.  Core Architecture Principles

### Model-View-Controller (MVC) / Document-View

- Separate geometry/kernel from UI — the parametric model should exist independently of any rendering or interaction  
  layer
- Single source of truth — one canonical model representation; views are derived, never authoritative
- Undo/Redo as first-class citizen — command pattern with reversible operations; never bolt it on later

### Data-Driven, Not Hardcoded

- All dimensions, tolerances, materials, and standards should come from configurable data (databases, JSON/YAML), not
  magic numbers
- Support unit systems cleanly (SI, Imperial) with explicit conversion layers

────────────────────────────────────────────────────────────────────────────────

2.  Geometric Kernel Design

### Boundary Representation (B-Rep)

```
  Body → Shell → Face → Loop → Coedge → Edge → Vertex
```

- Use a half-edge or winged-edge data structure for topology
- Separate topology (connectivity) from geometry (math): a face references a surface, an edge references a curve
- Never store redundant geometric data — derive from parametric definitions

### Tolerance Management

- Never compare floats with == — use epsilon-based comparisons
- Maintain model tolerance (e.g., 1e-6) and display tolerance (pixel-level)
- Document tolerance assumptions everywhere — geometric booleans are notoriously sensitive

### Robustness Rules

- Degenerate cases first — always check for zero-length edges, coincident faces, self-intersections
- Make operations idempotent where possible
- Validate topology after every operation (Euler-Poincaré check: V - E + F = 2(S - H) + R)

────────────────────────────────────────────────────────────────────────────────

3.  Parametric & History-Based Modeling

### Dependency Graph

```
  Sketch → Extrude → Fillet → Shell → Pattern
           (depends on sketch, etc.)
```

- Build a DAG (Directed Acyclic Graph) of features
- Support partial recomputation — only recompute downstream features when a parent changes
- Detect circular dependencies early and reject them

### Constraint Solving

- Use a persistent solver (not re-solve from scratch each time)
- Prefer degrees-of-freedom analysis to guide the user
- Separate 2D sketch constraints (geometric + dimensional) from 3D operations
- Well-established solvers: Newton-Raphson, homotopy continuation, or graph-based decomposition

### Design Intent Preservation

- Features should capture intent, not just geometry
- Support references (e.g., "midpoint of edge X") that survive upstream changes
- When references break, flag them clearly — never silently produce garbage

────────────────────────────────────────────────────────────────────────────────

4.  Performance & Scalability

### Spatial Indexing

- BVH (Bounding Volume Hierarchy) for ray tracing and collision
- Octree / k-d tree for point clouds and proximity queries
- R-tree for spatial database queries

### Level of Detail (LOD)

- Full B-Rep for operations
- Tessellated mesh (triangulated) for rendering
- Bounding box for quick rejection
- Cache tessellations and invalidate only when geometry changes

### Memory & Compute

- Lazy evaluation — don't compute what you don't need
- Immutable geometry objects — share safely across threads
- Worker threads / thread pools for heavy ops (boolean, meshing, FEA)
- Pre-allocate buffers for tessellation; avoid GC pressure

────────────────────────────────────────────────────────────────────────────────

5.  Rendering & Graphics

### OpenGL / Vulkan / WebGPU Best Practices

- Batch draw calls — minimize state changes
- Instanced rendering for repeated components (bolts, patterns)
- Frustum culling + occlusion culling
- Separate shader programs for: solid, wireframe, X-ray, section views

### Selection & Picking

- Color-picking (FBO) for pixel-perfect entity selection
- Ray casting against tessellated geometry (not B-Rep directly)
- Support: vertex, edge, face, body, and feature-level selection

### Visual Feedback

- Snapping (grid, endpoint, midpoint, center, tangent) — must be fast (<1ms)
- Dynamic highlighting on hover
- Gizmos for transform operations (translate, rotate, scale)
- Real-time section/cut plane visualization

────────────────────────────────────────────────────────────────────────────────

6.  File Format & Interop

### Read-Write Discipline

┌────────────────────┬────────────────────────────────────────────────────┐  
 │ Format │ Purpose │  
 ├────────────────────┼────────────────────────────────────────────────────┤  
 │ STEP (AP214/AP242) │ Industry standard exchange — always support │  
 ├────────────────────┼────────────────────────────────────────────────────┤  
 │ IGES │ Legacy but still needed │  
 ├────────────────────┼────────────────────────────────────────────────────┤  
 │ STL / OBJ / 3MF │ Mesh/3D printing │  
 ├────────────────────┼────────────────────────────────────────────────────┤  
 │ JT │ Lightweight visualization │  
 ├────────────────────┼────────────────────────────────────────────────────┤  
 │ Native format │ Full fidelity, fast I/O, version-controlled schema │  
 └────────────────────┴────────────────────────────────────────────────────┘

### Rules

- Version your native format — schema migration is inevitable
- Validate on import — check topology, fix tolerances, report issues
- Never silently drop data — log warnings for unsupported entities
- Use streaming parsers for large files (STEP files can be 500MB+)

────────────────────────────────────────────────────────────────────────────────

7.  API & Extensibility

### Plugin Architecture

```
  Core Kernel (C++/Rust)
      ↓
  Scripting Layer (Python / C# / TypeScript)
      ↓
  User Macros / Plugins
```

- Expose stable, versioned APIs — internal refactoring must not break plugins
- Provide transactional API — begin edit → modify → commit/rollback
- Use interfaces/traits, not concrete classes, in the public API

### Macro / Automation

- Record user actions as scriptable commands
- Support parametric scripts (e.g., "create 10 holes at these positions")
- Provide a REPL / console for interactive scripting

────────────────────────────────────────────────────────────────────────────────

8.  UI/UX Conventions

### Interaction Model

- Command-first or object-first — support both paradigms
- Context-sensitive toolbar — show only relevant tools for current selection
- Multi-monitor friendly — detach panels, preserve layouts
- Keyboard shortcuts — customizable, discoverable (show in tooltips)

### Viewport Conventions

- Middle-mouse orbit, Shift+middle pan, Scroll zoom — industry standard
- View cube or orientation widget (always visible)
- Support: perspective, orthographic, 2D (for sketches)
- Section views and clipping planes as core features

### Feedback & Error Handling

- Preview before commit — show ghost/preview of operation result
- Graceful failure — if a boolean fails, show what went wrong, don't crash
- Progress indicators for long operations (boolean, import, mesh generation)

────────────────────────────────────────────────────────────────────────────────

9.  Testing Strategy

### Geometry Testing

- Regression tests with known geometry — store input models + expected results
- Boolean operation fuzzing — random CSG trees to find crashes
- Tolerance stress tests — near-degenerate, nearly-tangent, nearly-coincident
- Round-trip tests: export → import → compare

### Topology Validation

After every operation, verify:

- Every edge has exactly 2 half-edges
- Every face loop is closed
- No dangling vertices or edges
- Euler characteristic holds

### Performance Benchmarks

- Track: boolean time, tessellation time, file load time, viewport FPS
- Set performance budgets and regress them in CI

────────────────────────────────────────────────────────────────────────────────

10. Domain-Specific Rules

### Mechanical CAD

- GD&T awareness — datums, tolerances, feature control frames
- Assembly constraints (mates, aligns, tangent) with DOF solver
- Bill of Materials (BOM) — derive from assembly structure
- Sheet metal: bend tables, K-factor, flat pattern generation

### Architectural CAD / BIM

- IFC (Industry Foundation Classes) compliance
- Wall/door/window as intelligent objects, not just geometry
- Clash detection between disciplines

### CAM Integration

- Toolpath generation from geometry
- Feature recognition (pockets, holes, slots) for automatic machining strategy
- Stock simulation (material removal)

────────────────────────────────────────────────────────────────────────────────

11. Language & Tech Stack Considerations

┌───────────────────┬──────────────────────────────────┐  
 │ Layer │ Recommended │  
 ├───────────────────┼──────────────────────────────────┤  
 │ Geometric kernel │ C++, Rust (performance-critical) │  
 ├───────────────────┼──────────────────────────────────┤  
 │ Application layer │ C++, C#, or Rust │  
 ├───────────────────┼──────────────────────────────────┤  
 │ Scripting/plugin │ Python, TypeScript, C# │  
 ├───────────────────┼──────────────────────────────────┤  
 │ Web CAD │ Rust/WASM + WebGPU │  
 ├───────────────────┼──────────────────────────────────┤  
 │ Tessellation/mesh │ C++ or Rust with SIMD │  
 └───────────────────┴──────────────────────────────────┘

### Code Conventions

- Heavy use of value types for geometry (points, vectors, matrices) — avoid heap allocation for small math objects
- ECS (Entity Component System) is gaining traction for managing large assemblies
- Domain-specific naming: use geometric terminology precisely (face ≠ surface, edge ≠ curve, shell ≠ solid)

────────────────────────────────────────────────────────────────────────────────

12. Common Pitfalls to Avoid

┌───────────────────────────────┬───────────────────────────────────────────────┐  
 │ ❌ Anti-Pattern │ ✅ Better Approach │  
 ├───────────────────────────────┼───────────────────────────────────────────────┤  
 │ Comparing floats with == │ Use epsilon with context-aware tolerance │  
 ├───────────────────────────────┼───────────────────────────────────────────────┤  
 │ Storing geometry redundantly │ Single parametric source, derive tessellation │  
 ├───────────────────────────────┼───────────────────────────────────────────────┤  
 │ Blocking UI on boolean ops │ Background threads with progress + cancel │  
 ├───────────────────────────────┼───────────────────────────────────────────────┤  
 │ Silently fixing bad geometry │ Report issues, let user decide │  
 ├───────────────────────────────┼───────────────────────────────────────────────┤  
 │ Hardcoding units │ Explicit unit system with conversion │  
 ├───────────────────────────────┼───────────────────────────────────────────────┤  
 │ Monolithic feature tree │ DAG with partial recomputation │  
 ├───────────────────────────────┼───────────────────────────────────────────────┤  
 │ Rendering directly from B-Rep │ Tessellate once, cache, invalidate on change │  
 └───────────────────────────────┴───────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────────────────────

Key References

- "Solid Modeling" by Christoph Hoffmann — foundational B-Rep theory
- "Geometric and Solid Modeling" by Mantyla — CSG and Boolean operations
- OpenCASCADE (OCCT) — reference open-source B-Rep kernel
- CGAL — computational geometry algorithms library
- Parasolid / ACIS — commercial kernel references
- IFC / STEP standards — ISO 10303, ISO 16739

The single most important rule: geometry is hard, tolerances are everything, and robustness is the #1 quality metric.
A CAD system that crashes on edge cases is unusable, no matter how many features it has.
