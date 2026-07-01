# Kitchen CAD — Parametric Cabinet Generator

> Parametryczny system do projektowania mebli kuchennych.
> Z definicji korpusu generuje listy cięcia (CSV) i planowane DXF.

## Quick Start

```python
from kitchen_cad.models import CorpusSpec, BaseDoorConfig, HingeSpec
from kitchen_cad.panel_calculator import calculate_panels
from kitchen_cad.drill_engine import apply_all_drilling
from kitchen_cad.csv_generator import generate_cutting_csv, generate_edging_csv

spec = CorpusSpec(
    id="K01",
    name="Szafka dolna 800",
    width=800, height=720, depth=510,
    hinges=HingeSpec(count=2),
    config=BaseDoorConfig(shelves=[352], doors=[2]),
)

panels = calculate_panels(spec)
panels = apply_all_drilling(panels, spec)
generate_cutting_csv(panels, "output/ciecie.csv")
generate_edging_csv(panels, "output/oklejanie.csv")
```

## Architecture

```
CorpusSpec (config: CabinetConfig)
    │
    ▼
panel_calculator.calculate_panels()
    │  ┌── _calculate_base_door()
    │  ├── _calculate_base_drawer()
    │  ├── _calculate_corner_blind()
    │  ├── _calculate_corner_internal()
    │  ├── _calculate_sink()
    │  ├── _calculate_cargo()
    │  └── _calculate_oven()
    ▼
drill_engine.apply_all_drilling()
    │  ┌── apply_system32()
    │  ├── apply_hinges()
    │  └── apply_handles()
    ▼
csv_generator.generate_*_csv()
```

## Cabinet Types (8 variants)

| Config Type            | Description           | Key Fields                          |
| ---------------------- | --------------------- | ----------------------------------- |
| `BaseDoorConfig`       | Standard door cabinet | `shelves[]`, `doors[]`              |
| `BaseDrawerConfig`     | Drawer cabinet        | `drawers[]`                         |
| `CornerBlindConfig`    | L-shaped corner blind | `corner_side`, `second_width`       |
| `CornerInternalConfig` | Corner with carousel  | `carousel` (Optima 800/900)         |
| `SinkConfig`           | Sink cabinet          | `has_sorting_drawer`                |
| `CargoConfig`          | Cargo basket          | `cargo_type`, `cargo_color`         |
| `OvenConfig`           | Oven housing          | `cavity_height`, `reinforced_shelf` |

## Documentation

| Document                                             | Description                            |
| ---------------------------------------------------- | -------------------------------------- |
| [ROADMAP.md](ROADMAP.md)                             | Development roadmap                    |
| [CHANGELOG.md](CHANGELOG.md)                         | Version history                        |
| [docs/architecture.md](docs/architecture.md)         | System architecture (Mermaid diagrams) |
| [docs/design.md](docs/design.md)                     | Design documentation (Polish)          |
| [docs/specs/cabinet-variants.md](docs/specs/cabinet-variants.md) | 12 cabinet type specification          |
| [docs/specs/legrabox-spec.md](docs/specs/legrabox-spec.md)       | LEGRABOX hardware specification        |

## Project Structure

```
kitchen-cad/
├── src/kitchen_cad/
│   ├── models.py              # Domain models (Pydantic)
│   ├── panel_calculator.py    # Panel geometry (7 variant calculators)
│   ├── drill_engine.py        # Drill point calculations
│   └── csv_generator.py       # CSV output
│
├── tests/                     # 292 tests
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # End-to-end tests
│
├── generators/                # Standalone DXF generators
│   └── legrabox_side_panel.py
│
└── docs/                      # Documentation
```

## Requirements

```bash
pip install pydantic>=2.0
```

## Tests

```bash
python -m pytest tests/ -v
```

## Technical Standards

- **System 32**: 32mm grid, 37mm offset, ∅5mm holes
- **Blum CLIP top**: ∅35mm cup, 45mm screw spacing
- **LEGRABOX**: Side heights N (66.5mm) / M (90.5mm) / K (128.5mm) / C (177mm)
