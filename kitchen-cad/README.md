# kitchen-cad

Parametric furniture corpus → CSV (cutting list + edge banding) + DXF (drill positions).

Designed for Polish CNC centres outsourcing (e-rozkroj workflow).

## Quick start

```bash
cd kitchen-cad
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Architecture

```
CorpusSpec (YAML / Python)
       │
       ▼
┌──────────────────────┐
│  panel_calculator    │  → list[Panel]  (dimensions, edges)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  drill_engine        │  → list[Panel]  (+ drill points)
│   • System 32        │
│   • Blum hinges      │
│   • Handles          │
└──────────┬───────────┘
           │
      ┌────┴────┐
      ▼         ▼
  ciecie.csv  oklejanie.csv   (Phase 1 — done)
  *.dxf                        (Phase 2 — next)
```

## Models

| Model        | Purpose                                      |
| ------------ | -------------------------------------------- |
| `CorpusSpec` | Full cabinet spec (dims, material, hardware) |
| `Panel`      | Single cutting panel with edges + drills     |
| `DrillPoint` | Hole position, diameter, depth, face         |
| `HingeSpec`  | Blum/Hettich hinge parameters                |

## Phase 1 scope

- [x] Pydantic models with validation
- [x] Panel calculator (base, wall, drawer cabinets)
- [x] System 32 drill engine
- [x] Blum hinge drill engine
- [x] Handle drill engine
- [x] Cutting list CSV generator
- [x] Edge banding CSV generator
- [x] Full test suite (pytest)

## Phase 2 (planned)

- [ ] DXF generation (ezdxf) with named layers
- [ ] YAML loader for corpus definitions
- [ ] Hettich hinge support
- [ ] Drawer runner drill positions
- [ ] Minifix / cam-lock drill positions
- [ ] Streamlit visualiser
