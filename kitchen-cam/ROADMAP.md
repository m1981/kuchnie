> Reader: kitchen-cam contributors | Enables: prioritising next CAM work |
> Update-trigger: after each milestone ships or scope changes

# Kitchen CAM — Roadmap

> **Last updated:** 2026-07-03
> **Status:** ADR-010 migration complete. kitchen-cam is now a pure downstream
> consumer of `kuchnie_core`.

---

## Done

- [x] **ADR-010 rename** — old name replaced with `kitchen-cam/`
- [x] **ADR-012 model extensions** — `PanelRole`, `MachiningOp.face/drill_type`,
      `HingeGeometry`, `HandleSpec`, `ShelfPinSpec`, `CabinetConfig` union
- [x] **Deletion queue** — removed `models.py`, `panel_calculator.py`,
      `csv_generator.py` and all deprecated test files
- [x] **machining.py** — rewired to import from `kuchnie_core.model`
- [x] **System 32** drilling (raster + shelf pins)
- [x] **Blum CLIP top** hinge cup + screw drilling
- [x] **Handle** drilling on drawer fronts
- [x] **CSV/DXF comparison** utilities

---

## Next

### DXF export

- [ ] DXF drilling file generator (panel → DXF with layers: CUT, DRILL, NOTES)
- [ ] LEGRABOX side-panel DXF with drilling patterns for CNC
- [ ] CLI: `kitchen-cam drill kitchen.json --out drilling/`

### Machining extensions

- [ ] Hettich Sensys support (screw_spacing=52mm)
- [ ] Minifix / cam-lock (∅15mm) edge drilling
- [ ] Dowel connectors (∅8mm)
- [ ] AVENTOS flip-up front mounting plates
- [ ] Groove (back-panel rabbet) as MachiningOp

### Integration

- [ ] Wire kitchen-cam into kitchen-erp pipeline (BOM → CAM enrichment → DXF)
- [ ] Read `kuchnie_core.Kitchen` from JSON intermediate format

---

## Not planned

- Panel decomposition — owned by `kuchnie_core.catalog`
- CSV cut lists — owned by `kuchnie_core.export`
- Material catalog — owned by `catalog/`

---

_See [CHANGELOG.md](CHANGELOG.md) for detailed change history._
