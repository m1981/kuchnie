# kitchen-cam — Architecture

> **This is the authoritative architecture document.**
> Last updated: 2026-06-23
>
> For domain specifications, see:
>
> - [LEGRABOX Specification](specs/legrabox-spec.md)
> - [Poradnik Kompleksowy](archive/comprehensive-guide.md)
> - [Panel Configurator Analysis](archive/configurator-analysis.md)

---

## 1. Current Architecture (As-Is)

### 1.1 Component Overview

```mermaid
graph TB
    subgraph "Entry Points"
        EX[example_generate.py]
        LBP[legrabox_side_panel.py<br/>⚠️ disconnected]
    end

    subgraph "kitchen_cam (src/)"
        M[models.py<br/>Pydantic + Enums]
        PC[panel_calculator.py<br/>Pure functions]
        DE[machining.py<br/>Pure functions]
        CSV[csv_generator.py<br/>CSV output]
    end

    subgraph "Output"
        CSVF[ciecie.csv<br/>oklejanie.csv]
        DXFF[bok_szafki_*.dxf<br/>⚠️ separate logic]
    end

    EX --> M
    EX --> PC
    EX --> DE
    EX --> CSV

    LBP -.->|should use| M
    LBP -.->|should use| PC
    LBP -.->|should use| DE
    LBP --> DXFF

    PC --> M
    DE --> M
    CSV --> M

    CSV --> CSVF

    style LBP stroke:#f66,stroke-width:2px,stroke-dasharray: 5 5
    style DXFF stroke:#f66,stroke-width:2px,stroke-dasharray: 5 5
```

### 1.2 Data Flow (Current)

```mermaid
flowchart LR
    A[CorpusSpec<br/>definition] --> B[calculate_panels]
    B --> C[list Panel]
    C --> D[apply_all_drilling]
    D --> E[list Panel<br/>+ DrillPoints]
    E --> F[generate_cutting_csv]
    E --> G[generate_edging_csv]
    F --> H[ciecie.csv]
    G --> I[oklejanie.csv]

    style H fill:#4CAF50,color:#fff
    style I fill:#4CAF50,color:#fff
```

---

## 2. Target Architecture (To-Be)

### 2.1 Component Overview — Full System

```mermaid
graph TB
    subgraph "Entry Points"
        EX[example_generate.py]
        CLI[cli.py<br/>⚡ NEW: CLI interface]
        API[api.py<br/>⚡ NEW: REST API<br/>optional]
    end

    subgraph "Configuration Layer ⚡ NEW"
        PRESETS[presets.py<br/>Cabinet templates]
        RUNNERS[runners.py<br/>Runner/fitting specs]
        MATS[materials.py<br/>Material catalog]
    end

    subgraph "Domain Layer"
        M[models.py<br/>Pydantic + Enums]
        VAL[validator.py<br/>⚡ NEW: Geometry checks]
    end

    subgraph "Calculation Layer"
        PC[panel_calculator.py<br/>Pure functions]
        DE[machining.py<br/>Pure functions]
        PIPE[pipeline.py<br/>⚡ NEW: Orchestration]
    end

    subgraph "Output Layer"
        CSV[csv_generator.py<br/>CSV output]
        DXF[dxf_exporter.py<br/>⚡ NEW: DXF output]
        NCF[nc_exporter.py<br/>🔮 FUTURE: G-code]
    end

    subgraph "Output Files"
        CSVF[ciecie.csv<br/>oklejanie.csv]
        DXFF[*.dxf<br/>CNC-ready]
        NCF2[*.nc<br/>Machine code]
    end

    %% Entry points → Pipeline
    EX --> PIPE
    CLI --> PIPE
    API --> PIPE

    %% Configuration → Domain
    PRESETS --> M
    RUNNERS --> M
    MATS --> M

    %% Pipeline orchestration
    PIPE --> PC
    PIPE --> DE
    PIPE --> VAL

    %% Calculation → Domain
    PC --> M
    DE --> M
    VAL --> M

    %% Pipeline → Output
    PIPE --> CSV
    PIPE --> DXF

    %% Output → Files
    CSV --> CSVF
    DXF --> DXFF
    NCF --> NCF2

    style VAL stroke:#FF9800,stroke-width:2px
    style PIPE stroke:#2196F3,stroke-width:2px
    style DXF stroke:#FF9800,stroke-width:2px
    style PRESETS stroke:#FF9800,stroke-width:2px
    style RUNNERS stroke:#FF9800,stroke-width:2px
    style NCF stroke:#9E9E9E,stroke-width:1px,stroke-dasharray: 5 5
    style NCF2 stroke:#9E9E9E,stroke-width:1px,stroke-dasharray: 5 5
```

### 2.2 Data Flow — Full Pipeline

```mermaid
flowchart LR
    subgraph "Input"
        A[CorpusSpec]
        R[RunnerSpec]
        P[Preset]
    end

    subgraph "Pipeline"
        B[calculate_panels]
        C[apply_all_drilling]
        D[validate_panels]
    end

    subgraph "Output"
        E[generate_csv]
        F[export_dxf]
        G[export_nc<br/>future]
    end

    subgraph "Files"
        H[ciecie.csv]
        I[oklejanie.csv]
        J[panel.dxf]
        K[*.nc]
    end

    A --> B
    R --> C
    P --> A

    B -->|list Panel| C
    C -->|list Panel + DrillPoints| D
    D -->|validated Panels| E
    D -->|validated Panels| F
    D -->|validated Panels| G

    E --> H
    E --> I
    F --> J
    G --> K

    style D fill:#FF9800,color:#fff
    style F fill:#FF9800,color:#fff
    style G stroke:#9E9E9E,stroke-dasharray: 5 5
    style K stroke:#9E9E9E,stroke-dasharray: 5 5
```

---

## 3. Module Details

### 3.1 Domain Model — Class Diagram

```mermaid
classDiagram
    direction TB

    class CorpusType {
        <<enumeration>>
        BASE_DOOR
        BASE_DRAWER
        CORNER_BLIND
        CORNER_INTERNAL
        SINK
        CARGO
        OVEN
    }

    class CornerSide {
        <<enumeration>>
        LEFT
        RIGHT
    }

    class CarouselType {
        <<enumeration>>
        OPTIMA_800
        OPTIMA_900
    }

    class CargoType {
        <<enumeration>>
        MINI_40
    }

    class PanelRole {
        <<enumeration>>
        LEFT_SIDE
        RIGHT_SIDE
        BOTTOM
        TOP
        SHELF
        BACK
        FRONT_DOOR
        FRONT_DRAWER
    }

    class EdgeSide {
        <<enumeration>>
        TOP
        BOTTOM
        LEFT
        RIGHT
    }

    class DrillFace {
        <<enumeration>>
        INSIDE
        OUTSIDE
        FRONT
        BACK
    }

    class DrillType {
        <<enumeration>>
        SYSTEM_32
        HINGE_CUP
        HINGE_SCREW
        HINGE_DOWEL
        DOWEL_CONNECTOR
        MINIFIX
        HANDLE
        SHELF_PIN
    }

    class EdgeBand {
        <<value object>>
        +EdgeSide side
        +str material
    }

    class DrillPoint {
        <<value object>>
        +float x
        +float y
        +float diameter
        +float depth
        +DrillFace face
        +DrillType drill_type
        +str label
    }

    class Panel {
        <<entity>>
        +str id
        +PanelRole role
        +float width
        +float height
        +float thickness
        +str material
        +int quantity
        +list~EdgeBand~ edges
        +list~DrillPoint~ drill_points
    }

    class HingeSpec {
        <<specification>>
        +str type
        +float cup_diameter
        +float cup_depth
        +float screw_spacing
        +float screw_offset_x
        +float screw_diameter
        +float screw_depth
        +float edge_to_cup_centre
        +int count
        +float first_position
    }

    class DrawerSpec {
        <<specification>>
        +float internal_height
        +str runner_type
        +RunnerSpec runner  ⚡NEW
    }

    class HandleSpec {
        <<specification>>
        +str type
        +float spacing
        +str position
        +float hole_diameter
    }

    class CorpusSpec {
        <<aggregate root>>
        +str id
        +str name
        +float width
        +float height
        +float depth
        +float panel_thickness
        +float back_thickness
        +float back_groove_depth
        +str material_corpus
        +str material_back
        +str material_front
        +str edge_material
        +HingeSpec hinges
        +HandleSpec handles
        +float shelf_pin_diameter
        +float shelf_pin_depth
        +float shelf_pin_front_offset
        +float shelf_pin_back_offset
        +int shelf_pin_max_per_row
        +float front_gap
        +CabinetConfig config
    }

    class CabinetConfig {
        <<discriminated union>>
        BaseDoorConfig
        BaseDrawerConfig
        CornerBlindConfig
        CornerInternalConfig
        SinkConfig
        CargoConfig
        OvenConfig
    }

    class BaseDoorConfig {
        <<variant>>
        +list~float~ shelves
        +list~int~ doors
    }

    class BaseDrawerConfig {
        <<variant>>
        +list~DrawerSpec~ drawers
    }

    class CornerBlindConfig {
        <<variant>>
        +CornerSide corner_side
        +float second_width
        +list~float~ shelves
        +list~int~ doors
    }

    class CornerInternalConfig {
        <<variant>>
        +CarouselType carousel
        +list~float~ shelves
        +list~int~ doors
    }

    class SinkConfig {
        <<variant>>
        +bool has_sorting_drawer
        +DrawerSpec sorting_drawer
        +list~int~ doors
    }

    class CargoConfig {
        <<variant>>
        +CargoType cargo_type
        +str cargo_color
        +list~int~ doors
    }

    class OvenConfig {
        <<variant>>
        +float cavity_height
        +bool has_ventilation
        +bool reinforced_shelf
    }

    class RunnerSpec {
        <<specification ⚡NEW>>
        +str brand
        +str series
        +int nominal_length
        +int load_class
        +float side_height
        +bool blumotion
        +list~float~ profile_hole_offsets
        +float first_hole_from_bottom
        +float hole_spacing
    }

    class ValidationResult {
        <<value object ⚡NEW>>
        +bool is_valid
        +list~str~ errors
        +list~str~ warnings
    }

    Panel *-- PanelRole : role
    Panel *-- EdgeBand : edges
    Panel *-- DrillPoint : drill_points
    EdgeBand *-- EdgeSide : side
    DrillPoint *-- DrillFace : face
    DrillPoint *-- DrillType : drill_type
    CorpusSpec *-- CabinetConfig : config
    CabinetConfig *-- BaseDoorConfig
    CabinetConfig *-- BaseDrawerConfig
    CabinetConfig *-- CornerBlindConfig
    CabinetConfig *-- CornerInternalConfig
    CabinetConfig *-- SinkConfig
    CabinetConfig *-- CargoConfig
    CabinetConfig *-- OvenConfig
    BaseDrawerConfig *-- DrawerSpec : drawers
    CornerBlindConfig *-- CornerSide : corner_side
    CornerInternalConfig *-- CarouselType : carousel
    SinkConfig *-- DrawerSpec : sorting_drawer
    CargoConfig *-- CargoType : cargo_type
    CorpusSpec *-- HingeSpec : hinges
    CorpusSpec *-- HandleSpec : handles
    DrawerSpec --> RunnerSpec : runner ⚡NEW
```

### 3.2 Pipeline — Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant Presets as presets.py
    participant Pipeline as pipeline.py
    participant Calc as panel_calculator.py
    participant Drill as machining.py
    participant Valid as validator.py
    participant CSV as csv_generator.py
    participant DXF as dxf_exporter.py

    User->>Presets: get_preset("legrabox_3x_NMK")
    Presets-->>User: CorpusSpec

    User->>Pipeline: CabinetPipeline(spec).run()
    activate Pipeline

    Pipeline->>Calc: calculate_panels(spec)
    Calc-->>Pipeline: list[Panel]

    Pipeline->>Drill: apply_all_drilling(panels, spec)
    Drill-->>Pipeline: list[Panel] + DrillPoints

    Pipeline->>Valid: validate_panels(panels)
    Valid-->>Pipeline: ValidationResult

    alt validation passed
        Pipeline-->>User: list[Panel] (validated)
    else validation failed
        Pipeline-->>User: raise ValidationError
    end
    deactivate Pipeline

    User->>CSV: generate_cutting_csv(panels, path)
    CSV-->>User: ciecie.csv

    User->>DXF: export_panels_dxf(panels, path)
    DXF-->>User: panel.dxf
```

### 3.3 Runner System — Class Diagram

```mermaid
classDiagram
    direction TB

    class RunnerSpec {
        <<specification>>
        +str brand
        +str series
        +int nominal_length
        +int load_class_kg
        +float side_height
        +bool integrated_blumotion
        +list~float~ profile_hole_offsets
        +float first_hole_from_bottom
        +float hole_spacing
        +float min_cabinet_depth
        +float back_fixing_offset
    }

    class RunnerRegistry {
        <<service>>
        +get(series: str, side_height: str) RunnerSpec
        +list_all() list~RunnerSpec~
        +register(spec: RunnerSpec) None
    }

    class LEGRABOX_N {
        <<preset>>
        brand = "Blum"
        series = "LEGRABOX"
        side_height = 66.5
        nominal_lengths = [270..600]
    }

    class LEGRABOX_M {
        <<preset>>
        brand = "Blum"
        series = "LEGRABOX"
        side_height = 90.5
        nominal_lengths = [270..600]
    }

    class LEGRABOX_K {
        <<preset>>
        brand = "Blum"
        series = "LEGRABOX"
        side_height = 128.5
        nominal_lengths = [270..600]
    }

    class LEGRABOX_C {
        <<preset>>
        brand = "Blum"
        series = "LEGRABOX"
        side_height = 177.0
        nominal_lengths = [270..600]
    }

    class METABOX {
        <<preset>>
        brand = "Blum"
        series = "METABOX"
        side_height = 54.0..86.0
    }

    class TANDEMBOX {
        <<preset>>
        brand = "Blum"
        series = "TANDEMBOX"
        side_height = 54.0..199.0
    }

    RunnerRegistry --> RunnerSpec : manages
    LEGRABOX_N --|> RunnerSpec
    LEGRABOX_M --|> RunnerSpec
    LEGRABOX_K --|> RunnerSpec
    LEGRABOX_C --|> RunnerSpec
    METABOX --|> RunnerSpec
    TANDEMBOX --|> RunnerSpec
```

### 3.4 Cabinet Presets — Class Diagram

```mermaid
classDiagram
    direction TB

    class PresetRegistry {
        <<service>>
        +get(name: str) CorpusSpec
        +list_all() list~str~
        +register(name: str, spec: CorpusSpec) None
    }

    class CorpusSpec {
        <<aggregate>>
    }

    class base_door_800 {
        <<preset>>
        config = BaseDoorConfig(shelves=[352], doors=[2])
        width = 800
        height = 720
        depth = 510
    }

    class base_drawer_600 {
        <<preset>>
        config = BaseDrawerConfig(drawers=[N, M, K])
        width = 600
        height = 720
        depth = 510
    }

    class wall_door_800 {
        <<preset>>
        config = BaseDoorConfig(shelves=[352], doors=[2])
        width = 800
        height = 720
        depth = 300
    }

    class corner_blind_900 {
        <<preset>>
        config = CornerBlindConfig(corner_side=LEFT, second_width=510)
        width = 900
        height = 720
        depth = 510
    }

    class oven_600 {
        <<preset>>
        config = OvenConfig(cavity_height=600)
        width = 600
        height = 2000
        depth = 560
    }

    PresetRegistry --> CorpusSpec : creates
    base_door_800 --|> CorpusSpec
    base_drawer_600 --|> CorpusSpec
    wall_door_800 --|> CorpusSpec
    corner_900 --|> CorpusSpec
    tall_cabinet_600 --|> CorpusSpec
```

---

## 4. DXF Export Layer

### 4.1 DXF Exporter — Component Diagram

```mermaid
graph TB
    subgraph "Input"
        P[list Panel]
    end

    subgraph "dxf_exporter.py ⚡NEW"
        direction TB
        DOC[create_document<br/>R2000 format]
        LAYERS[create_layers<br/>CNC standard]
        DRAW[draw_panel<br/>outline + holes]
        ANNOTATE[add_annotations<br/>dimensions + notes]
    end

    subgraph "DXF Layers"
        L1[01_OUTLINE<br/>White]
        L2[02_SYSTEM32<br/>Green]
        L3[03_HINGE<br/>Red]
        L4[04_DOWEL<br/>Yellow]
        L5[05_EDGEBAND<br/>Magenta]
        L6[06_NOTES<br/>Gray]
    end

    subgraph "Output"
        F[*.dxf file]
    end

    P --> DOC
    DOC --> LAYERS
    LAYERS --> DRAW
    DRAW --> ANNOTATE

    LAYERS --> L1
    LAYERS --> L2
    LAYERS --> L3
    LAYERS --> L4
    LAYERS --> L5
    LAYERS --> L6

    ANNOTATE --> F

    style DOC fill:#FF9800,color:#fff
    style F fill:#4CAF50,color:#fff
```

### 4.2 DXF Export — Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant DXF as dxf_exporter.py
    participant Doc as ezdxf.Document
    participant Layers as DXF Layers

    User->>DXF: export_panels_dxf(panels, path)
    activate DXF

    DXF->>Doc: new("R2000")
    DXF->>Layers: create_cnc_layers(doc)

    loop for each Panel
        DXF->>DXF: draw_outline(panel)
        DXF->>DXF: draw_drill_holes(panel)
        DXF->>DXF: add_edgeband_marks(panel)
        DXF->>DXF: add_dimensions(panel)
    end

    DXF->>Doc: saveas(path)
    DXF-->>User: Path to .dxf
    deactivate DXF
```

---

## 5. Validator — Geometry Checks

### 5.1 Validation Flow

```mermaid
flowchart TD
    A[Panel with DrillPoints] --> B{Check bounds}
    B -->|x < 0 or x > width| C[ERROR: out of bounds X]
    B -->|y < 0 or y > height| D[ERROR: out of bounds Y]
    B -->|OK| E{Check overlaps}

    E -->|distance < min_gap| F[WARNING: holes too close]
    E -->|OK| G{Check edge clearance}

    G -->|hole near edge < min_clearance| H[WARNING: too close to edge]
    G -->|OK| I{Check depth}

    I -->|depth > panel_thickness| J[ERROR: hole too deep]
    I -->|OK| K[✅ VALID]

    C --> L[ValidationResult]
    D --> L
    F --> L
    H --> L
    J --> L
    K --> L

    style K fill:#4CAF50,color:#fff
    style C fill:#f44336,color:#fff
    style D fill:#f44336,color:#fff
    style J fill:#f44336,color:#fff
    style F fill:#FF9800,color:#fff
    style H fill:#FF9800,color:#fff
```

---

## 6. CLI Interface (Future)

### 6.1 CLI Commands

```mermaid
graph LR
    subgraph "kitchen-cam CLI"
        CMD1[kitchen-cam generate<br/>Generate cabinet panels]
        CMD2[kitchen-cam export<br/>Export to DXF/CSV]
        CMD3[kitchen-cam validate<br/>Validate spec]
        CMD4[kitchen-cam presets<br/>List presets]
    end

    subgraph "Flags"
        F1[--preset base_drawer_600]
        F2[--width 600 --height 720]
        F3[--drawers N M K]
        F4[--output output/]
        F5[--format dxf csv]
    end

    CMD1 --> F1
    CMD1 --> F2
    CMD1 --> F3
    CMD1 --> F4
    CMD2 --> F5
```

---

## 7. File Structure — Target

```
kitchen-cam/
├── src/kitchen_cam/
│   ├── __init__.py
│   ├── models.py              # Domain models (existing)
│   ├── panel_calculator.py    # Geometry calculations (existing)
│   ├── machining.py           # Machining operations (existing)
│   ├── csv_generator.py       # CSV output (existing)
│   │
│   ├── runners.py             # ⚡ Runner specifications (LEGRABOX, METABOX...)
│   ├── materials.py           # ⚡ Material catalog (EGGER, Kronospan...)
│   ├── presets.py             # ⚡ Cabinet preset library
│   ├── validator.py           # ⚡ Geometry validation
│   ├── pipeline.py            # ⚡ Pipeline orchestration
│   ├── dxf_exporter.py        # ⚡ DXF output
│   │
│   ├── cli.py                 # 🔮 CLI interface (future)
│   └── nc_exporter.py         # 🔮 G-code output (future)
│
├── generators/                # Standalone generators (refactored)
│   └── legrabox_side_panel.py # Should use pipeline.py
│
├── tests/
│   ├── test_models.py
│   ├── test_panel_calculator.py
│   ├── test_machining.py
│   ├── test_csv_generator.py
│   ├── test_runner_registry.py    # ⚡ NEW
│   ├── test_presets.py            # ⚡ NEW
│   ├── test_validator.py          # ⚡ NEW
│   └── test_dxf_exporter.py       # ⚡ NEW
│
├── output/
│   ├── *.dxf                  # Generated DXF files
│   └── *.csv                  # Generated CSV files
│
├── docs/
│   ├── architecture-diagrams.md   # This file
│   ├── LEGRABOX_SPEC.md
│   └── poradnik-kompleksowy.md
│
└── example_generate.py
```

---

## 8. Technology Decisions

| Component          | Choice         | Rationale                                           |
| ------------------ | -------------- | --------------------------------------------------- |
| **Domain models**  | Pydantic v2    | Validation, serialization, IDE support              |
| **DXF generation** | ezdxf          | Pure Python, R2000 support, no AutoCAD needed       |
| **CLI**            | Typer / Click  | Type-safe, auto-generated help                      |
| **Testing**        | pytest         | Already in project                                  |
| **Future NC**      | G-code strings | Simple text format, machine-specific postprocessors |

---

## 9. Migration Path

```mermaid
gantt
    title Kitchen-CAD Development Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1 - Core
    Runner Registry (runners.py)        :a1, 2026-06-17, 2d
    Validator (validator.py)            :a2, after a1, 2d
    Pipeline (pipeline.py)              :a3, after a2, 1d
    section Phase 2 - Output
    DXF Exporter (dxf_exporter.py)      :b1, after a3, 3d
    Refactor legrabox_side_panel.py     :b2, after b1, 2d
    section Phase 3 - Configuration
    Presets (presets.py)                :c1, after b2, 2d
    Materials (materials.py)            :c2, after c1, 1d
    section Phase 4 - Interface
    CLI (cli.py)                        :d1, after c2, 2d
    section Future
    NC Exporter                         :e1, after d1, 5d
```

---

_Generated: 2026-06-17_
_Version: 1.0_
