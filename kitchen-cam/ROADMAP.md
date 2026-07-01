# Kitchen CAD — Roadmap

> **Last updated:** 2026-06-23
> **Current status:** Phase 1 completed, Phase 2 in progress

---

## Phase 1 — Core Engine ✅ (Completed)

- [x] Pydantic models (CorpusSpec, Panel, DrillPoint, HingeSpec, HandleSpec)
- [x] Panel calculator (base, drawer, wall, 2-door)
- [x] System 32 drill engine
- [x] Blum CLIP 35mm drill engine
- [x] Handle drilling (relingowe)
- [x] CSV cutting list generator
- [x] CSV edge banding generator
- [x] Comparison tools (CSV + DXF)
- [x] Shelf pin drilling from Corpus .cmk reference
- [x] Comprehensive test suite

---

## Phase 2.5 — Discriminated Union Config ✅ (Completed 2026-06-24)

- [x] Discriminated union config pattern (BaseDoorConfig, BaseDrawerConfig, CornerBlindConfig)
- [x] CornerInternalConfig — diagonal back, carousel (Optima 800/900)
- [x] SinkConfig — optional sorting drawer
- [x] CargoConfig — cargo basket (MINI_40)
- [x] OvenConfig — reinforced shelf, ventilation
- [x] CarouselType, CargoType, CornerSide enums
- [x] Backward-compatible model_validator for legacy flat fields
- [x] Variant-specific panel calculators (7 types)
- [x] 292 tests passing

---

## Phase 2 — Extended Features 🔄 (In Progress)

- [x] Validator — geometry checks for drill points
- [x] Mirror — X/Y reflection for drill points and edges
- [x] Grooving — back panel groove calculation
- [x] Edge drilling — holes in panel edges
- [x] Flip-up fronts — AVENTOS-style hinges
- [x] Handle configuration — multiple handle types
- [x] Hinge configuration — multiple hinge specs
- [x] Materials catalog — material validation
- [ ] DXF generator with layers (ezdxf)
    - Layer `CUT` (red) — panel outlines
    - Layer `DRILL` (green) — holes as circles
    - Layer `NOTES` (gray) — dimensions, names
- [ ] YAML loader — corpus definitions in files
- [ ] Hettich Sensys support (screw_spacing=52mm)
- [ ] Minifix / cam-lock (∅15mm)
- [ ] Dowel connectors (∅8mm)
- [ ] Drawer runners (Blum METABOX, TANDEM, LEGRABOX)

---

## Phase 3 — User Interface (Planned)

- [ ] CLI interface (Typer/Click)
- [ ] Streamlit UI — corpus visualization in browser
- [ ] Import from Corpus LTR (CSV)
- [ ] Cut optimization (minimize waste)
- [ ] Barcode labels
- [ ] Integration with e-rozkroj (FastCut API)

---

## Phase 4 — Production Integration (Future)

- [ ] REST API for external tools
- [ ] G-code export (NC machine code)
- [ ] Multi-corpus kitchen generator
- [ ] Cost estimation (material + labor)
- [ ] PDF report generation

---

## Technical Debt

- [ ] Consolidate architecture documentation
- [ ] Add YAML schema validation
- [ ] Create CorpusSpec format documentation
- [ ] Add integration tests for full pipeline

---

## Completed Milestones

| Milestone        | Date       | Tests           | Coverage            |
| ---------------- | ---------- | --------------- | ------------------- |
| Phase 1 Core     | 2026-06-17 | Run `make test` | Run `make coverage` |
| Phase 2 Features | 2026-06-23 | Run `make test` | Run `make coverage` |

> **Note:** Run `make test` to verify all tests pass. Run `make coverage` for current coverage report.

---

_See [CHANGELOG.md](CHANGELOG.md) for detailed change history._
