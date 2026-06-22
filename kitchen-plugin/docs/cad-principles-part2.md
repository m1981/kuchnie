Best Principles, Rules & Conventions for CAD Software Development

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
