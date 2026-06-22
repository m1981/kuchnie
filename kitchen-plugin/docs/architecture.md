# Kitchen Plugin Architecture

## Overview

The kitchen plugin follows **SOLID principles** and **CAD best practices**
to generate 3D kitchen cabinet models from JSON configuration files.

---

## Layer Architecture

```mermaid
graph TB
    subgraph "Layer 1: Core (Pure Math)"
        G[geometry.py<br/>Vector2D, Vector3D<br/>BoundingBox, Transform2D]
        T[tolerances.py<br/>Named tolerances]
        TY[types.py<br/>Direction, CabinetType<br/>CabinetLevel, Dimensions]
    end

    subgraph "Layer 2: Kitchen (Domain Logic)"
        W[wall.py<br/>Wall, Room<br/>CornerReference]
        C[cabinet.py<br/>Cabinet, CabinetPlacement<br/>Countertop]
        L[layout.py<br/>Run, LayoutEngine]
        S[standards.py<br/>KitchenStandards<br/>EUROPEAN_STANDARDS]
    end

    subgraph "Layer 3: Builder (Config Parsing)"
        CP[config_parser.py<br/>JSON loading, validation]
        V[validators.py<br/>Semantic validation]
        WB[wall_builder.py<br/>Config → Wall conversion]
    end

    subgraph "Layer 4: Adapters (External)"
        GB[geometry_builder.py<br/>Blender mesh creation]
        EX[exporters.py<br/>OBJ, GLTF, .blend]
        MM[material_manager.py<br/>Cycles materials]
    end

    subgraph "Layer 5: Entry Points"
        M[main.py<br/>CLI entry point]
        T2[test files<br/>pytest]
    end

    G --> W
    G --> C
    T --> V
    TY --> C
    TY --> L
    W --> L
    C --> L
    S --> V
    CP --> V
    CP --> WB
    WB --> L
    L --> GB
    L --> EX
    M --> CP
    M --> GB
    M --> EX
```

---

## Dependency Rule

```mermaid
graph LR
    Core[core/] --> Kitchen[kitchen/]
    Kitchen --> Builder[builder/]
    Builder --> Adapters[adapters/]
    Adapters --> Main[main.py]

    style Core fill:#e1f5e1
    style Kitchen fill:#e1f5e1
    style Builder fill:#fff3e0
    style Adapters fill:#ffebee
    style Main fill:#e3f2fd
```

**Rule:** Dependencies point DOWN only. Never reverse.

| Layer | Dependencies | External |
|---|---|---|
| core/ | None | None |
| kitchen/ | core/ | None |
| builder/ | core/, kitchen/ | JSON |
| adapters/ | core/, kitchen/ | bpy |
| main.py | all | bpy, sys |

---

## Module Details

### Layer 1: Core (Pure Math)

```mermaid
classDiagram
    class Vector2D {
        +float x
        +float y
        +__add__(other) Vector2D
        +__sub__(other) Vector2D
        +__mul__(scalar) Vector2D
        +dot(other) float
        +length() float
        +normalized() Vector2D
        +perpendicular() Vector2D
    }

    class Vector3D {
        +float x
        +float y
        +float z
        +__add__(other) Vector3D
        +__sub__(other) Vector3D
        +__mul__(scalar) Vector3D
        +dot(other) float
        +cross(other) Vector3D
        +length() float
        +normalized() Vector3D
        +to_mm() Vector3D
        +to_m() Vector3D
    }

    class BoundingBox {
        +Vector3D min_point
        +Vector3D max_point
        +width() float
        +depth() float
        +height() float
        +center() Vector3D
        +contains_point(point) bool
        +intersects(other) bool
    }

    class Transform2D {
        +float cos
        +float sin
        +float tx
        +float ty
        +from_rotation(angle) Transform2D
        +from_translation(tx, ty) Transform2D
        +from_position_and_direction(x, y, dx, dy) Transform2D
        +apply_to_point(point) Vector2D
        +apply_to_vector(vec) Vector2D
    }

    Vector2D --> Transform2D : transformed by
    Vector3D --> BoundingBox : defines
```

**Files:**
- `src/core/geometry.py` — Vector2D, Vector3D, BoundingBox, Transform2D
- `src/core/tolerances.py` — Tolerances (position, dimension, gap, etc.)
- `src/core/types.py` — Direction, CabinetType, CabinetLevel, Dimensions

---

### Layer 2: Kitchen (Domain Logic)

```mermaid
classDiagram
    class Wall {
        +str id
        +Vector2D start
        +Vector2D end
        +direction() Vector2D
        +normal() Vector2D
        +length() float
        +angle_rad() float
        +transform() Transform2D
        +point_at_offset(offset) Vector2D
        +point_at_depth(offset, depth) Vector2D
    }

    class Room {
        +List~Wall~ walls
        +get_wall(wall_id) Wall
        +corners() List
    }

    class Cabinet {
        +str id
        +CabinetType cabinet_type
        +str wall_id
        +float offset
        +Dimensions dimensions
        +level() CabinetLevel
        +width() float
        +depth() float
        +height() float
        +is_corner() bool
        +bounding_box_local() BoundingBox
    }

    class LayoutEngine {
        +float cabinet_gap
        +float front_gap
        +calculate_layout(runs) Layout
    }

    class Layout {
        +Room room
        +List~Run~ runs
        +List~CornerReference~ corners
        +List~CabinetPlacement~ placed_cabinets
    }

    Wall --> Room : contained in
    Cabinet --> Wall : references
    LayoutEngine --> Layout : creates
    Layout --> Room : contains
    Layout --> Cabinet : places
```

**Files:**
- `src/kitchen/wall.py` — Wall, Room, CornerReference
- `src/kitchen/cabinet.py` — Cabinet, CabinetPlacement, Countertop
- `src/kitchen/layout.py` — Run, LayoutEngine, Layout
- `src/kitchen/standards.py` — KitchenStandards, EUROPEAN_STANDARDS

---

### Layer 3: Builder (Config Parsing)

```mermaid
flowchart LR
    JSON[JSON Config] --> CP[config_parser.py]
    CP --> V[validators.py]
    CP --> WB[wall_builder.py]
    WB --> W[Wall objects]
    WB --> C[Cabinet objects]
```

**Files:**
- `src/config_parser.py` — JSON loading, defaults, validation
- `src/validators.py` — Semantic validation (dimensions, gaps, room fit)
- `src/wall_builder.py` — Config → Wall/Cabinet conversion

---

### Layer 4: Adapters (External)

```mermaid
flowchart LR
    L[Layout] --> GB[geometry_builder.py]
    GB --> BM[Blender Meshes]
    L --> EX[exporters.py]
    EX --> OBJ[.obj file]
    EX --> GLTF[.gltf file]
    EX --> BLEND[.blend file]
```

**Files:**
- `src/geometry_builder.py` — bpy mesh creation
- `src/material_manager.py` — Cycles materials
- `src/exporters.py` — OBJ, GLTF, .blend export

---

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Main as main.py
    participant Parser as config_parser
    participant Builder as wall_builder
    participant Engine as LayoutEngine
    participant Geo as geometry_builder
    participant Blender as Blender Scene

    User->>Main: Run with config file
    Main->>Parser: Load JSON
    Parser->>Parser: Apply defaults
    Parser->>Parser: Validate structure
    Parser-->>Main: Config dict

    Main->>Builder: Convert to walls
    Builder->>Builder: config_to_walls()
    Builder->>Builder: config_to_cabinets()
    Builder-->>Engine: Walls + Cabinets

    Engine->>Engine: Calculate positions
    Engine->>Engine: Detect corners
    Engine-->>Main: Layout

    Main->>Geo: Build meshes
    Geo->>Blender: Create objects
    Main->>Blender: Export
```

---

## Coordinate System

```mermaid
graph TB
    subgraph "Wall-Local Coordinates"
        direction[Direction: along wall]
        normal[Normal: into room]
        origin[Origin: wall start]
    end

    subgraph "Cabinet-Local Coordinates"
        width[Width: along wall +X]
        depth[Depth: into room +Y]
        height[Height: up +Z]
        origin2[Origin: back-left-bottom<br/>at wall face]
    end

    subgraph "World Coordinates"
        X[X: east +X]
        Y[Y: north +Y]
        Z[Z: up +Z]
    end

    origin --> |Transform2D| X
    origin2 --> |Wall.transform| origin
```

**Convention:**
- Z-up (architectural/BIM standard)
- Right-hand rule
- Wall normal points into room
- Cabinet origin at back face (wall face)

---

## Test Architecture

```mermaid
graph TB
    subgraph "Unit Tests (Pure Python)"
        T1[test_core_geometry.py<br/>36 tests]
        T2[test_kitchen.py<br/>22 tests]
        T3[test_wall_centric_model.py<br/>21 tests]
        T4[test_wall_builder.py<br/>15 tests]
    end

    subgraph "Integration Tests"
        T5[test_config_parser.py<br/>11 tests]
        T6[test_positions.py<br/>6 tests]
        T7[test_l_shape.py<br/>11 tests]
        T8[test_u_shape.py<br/>11 tests]
    end

    subgraph "Contract Tests"
        T9[test_p0_gap_semantics.py<br/>18 tests]
        T10[test_p0_coordinate_system.py<br/>19 tests]
        T11[test_p1_*.py<br/>26 tests]
        T12[test_p2_*.py<br/>39 tests]
    end

    T1 --> T5
    T2 --> T5
    T3 --> T7
    T4 --> T7
```

**Total: 218 passing, 17 skipped (bpy required)**

---

## File Structure

```
kitchen-plugin/
├── src/
│   ├── core/                    # Layer 1: Pure math
│   │   ├── __init__.py
│   │   ├── geometry.py         # Vector2D, Vector3D, BoundingBox, Transform2D
│   │   ├── tolerances.py       # Named tolerances
│   │   └── types.py            # Direction, CabinetType, CabinetLevel
│   │
│   ├── kitchen/                 # Layer 2: Domain logic
│   │   ├── __init__.py
│   │   ├── wall.py             # Wall, Room, CornerReference
│   │   ├── cabinet.py          # Cabinet, CabinetPlacement, Countertop
│   │   ├── layout.py           # Run, LayoutEngine, Layout
│   │   └── standards.py        # KitchenStandards, EUROPEAN_STANDARDS
│   │
│   ├── config_parser.py         # Layer 3: Config parsing
│   ├── validators.py            # Layer 3: Validation
│   ├── wall_builder.py          # Layer 3: Config → Wall conversion
│   │
│   ├── geometry_builder.py      # Layer 4: Blender mesh creation
│   ├── material_manager.py      # Layer 4: Cycles materials
│   ├── exporters.py             # Layer 4: OBJ, GLTF, .blend
│   │
│   └── main.py                  # Layer 5: CLI entry point
│
├── tests/
│   ├── test_core_geometry.py    # 36 tests
│   ├── test_kitchen.py          # 22 tests
│   ├── test_wall_centric_model.py # 21 tests
│   ├── test_wall_builder.py     # 15 tests
│   ├── test_config_parser.py    # 11 tests
│   ├── test_positions.py        # 6 tests
│   ├── test_l_shape.py          # 11 tests
│   ├── test_u_shape.py          # 11 tests
│   ├── test_p0_*.py             # 37 tests
│   ├── test_p1_*.py             # 26 tests
│   └── test_p2_*.py             # 39 tests
│
├── configs/
│   ├── ref_i_shape.json
│   ├── ref_l_shape.json
│   └── ref_u_shape.json
│
├── output/
│   ├── meshes/
│   └── renders/
│
└── docs/
    ├── architecture.md          # This file
    ├── f02-kitchen-config-syntax.md
    ├── handoff-prompt.md
    └── wall-centric-model.md
```

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **Frozen dataclasses** | Immutable = thread-safe, no accidental mutation |
| **Z-up coordinates** | Industry standard for architecture/BIM |
| **Wall-centric positioning** | Same as IKEA, professional CAD software |
| **Back-face origin** | Natural for wall attachment |
| **Separate core/ layer** | No bpy dependency = testable without Blender |
| **Named tolerances** | Self-documenting, configurable |

---

## Future Work

| Priority | Task | Effort |
|---|---|---|
| High | Integrate kitchen/ with geometry_builder | Medium |
| High | Switch to back-face origin in mesh creation | Medium |
| Medium | Add countertop generation to LayoutEngine | Small |
| Medium | Add wall gap validation | Small |
| Low | Add 3D preview without Blender | Large |
| Low | Add interactive GUI | Very Large |
