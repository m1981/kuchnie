> Type: A | Status: active | Role: CAM enrichment — machining ops, DXF for CNC | ADRs: 010, 012

# kitchen-cam — CAM Enrichment Layer

Downstream consumer of `kuchnie_core`. Takes panels produced by the
decomposition engine and adds machining operations for CNC manufacturing.

**One sentence:** `kuchnie_core` produces panels → `kitchen-cam` adds drilling →
DXF/CSV for CNC.

## Quick Start

```python
from kuchnie_core.model import CabinetInstance, HandleSpec
from kuchnie_core.blum_hinges import HingeGeometry
from kuchnie_core.decomposer import decompose
from kitchen_cam.machining import apply_all_drilling

cab = CabinetInstance(
    id="K01", type="dolna_drzwiowa", description="Szafka dolna 800",
    width_mm=800, height_mm=720, depth_mm=510,
    body_material="U119_VL", back_material="HDF_3mm", front_material="U119_EM",
    hinges=HingeGeometry(cup_diameter_mm=35, cup_drill_depth_mm=13),
    handles=HandleSpec(spacing_mm=256.0),
    shelves=[{"id": "P1", "pozycja_od_dolu": 352}],
    fronts=[{"id": "F1", "typ": "drzwiowy_lewy", "ilosc_zawiasow": 2}],
)

result = decompose(cab)
panels = apply_all_drilling(result.panels, cab)
# Each panel now has machining_ops with drill positions
```

## Architecture

```
kuchnie_core.CabinetInstance
    │
    ▼
kuchnie_core.decomposer.decompose()
    │  → DecompositionResult (panels + accessories)
    ▼
kitchen_cam.machining.apply_all_drilling()
    │  ┌── apply_system32()   — ∅5mm shelf-pin + System32 raster
    │  ├── apply_hinges()     — ∅35mm cup + ∅3mm screws (Blum CLIP top)
    │  └── apply_handles()    — ∅5mm handle holes on drawer fronts
    ▼
panels with machining_ops[]  →  DXF export (dxf/)
```

## Project Structure

```
kitchen-cam/
├── src/kitchen_cam/
│   ├── __init__.py
│   ├── machining.py              # System32, hinges, handles (imports kuchnie_core)
│   └── dxf/
│       └── legrabox_side_panel.py  # Blum LEGRABOX DXF side-panel generator
│
├── tests/                        # 45 tests
│   ├── test_drill_engine.py      # Machining ops: System32, hinges, handles
│   └── test_compare.py           # CSV/DXF comparison utilities
│
└── CHANGELOG.md
```

## Key Constraints

- `ezdxf` stays in `dxf/` only — keep it out of `machining.py`
- `kuchnie_core.model` is the canonical panel/cabinet model — kitchen-cam
  never defines its own (ADR-010)
- CNC company requires DXF format — don't add output formats without
  checking their requirements
- All coordinates in mm, relative to bottom-left of panel's inside face

## Technical Standards

- **System 32**: 32mm grid, 37mm offset, ∅5mm holes
- **Blum CLIP top**: ∅35mm cup, 45mm screw spacing
- **LEGRABOX**: Side heights N (66.5mm) / M (90.5mm) / K (128.5mm) / C (177mm)

## Tests

```bash
cd kitchen-cam && .venv/bin/python -m pytest tests -v
```
