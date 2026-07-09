# File Naming Convention

## Rules

### 1. Use kebab-case everywhere
```
✅ configurator-api.md
✅ wall-centric-model.md
✅ legrabox-spec.md
❌ DOC_ROUTING.md
❌ DESIGN.md
❌ blaty_abs_square_edge_spec.md
```

### 2. No number prefixes (except ADRs and vision)
```
✅ adr/001-panel-is-atomic-unit.md    ← ADRs are numbered (immutable)
✅ vision/00-mission.md               ← Vision is ordered (priority)
❌ specs/01-overview.md                ← Don't number specs
❌ specs/02-data-model.md              ← Order changes, names shouldn't
```

### 3. Use English for file names
```
✅ cabinet-variants.md
✅ european-kitchen-standards.md
❌ poradnik-kompleksowy.md
❌ materialy.md
❌ lazienkowe-drukowane.md
```
Content can be Polish. File names must be English (for tooling, URLs, LLM parsing).

### 4. Be descriptive, not generic
```
✅ configurator-api.md
✅ legrabox-spec.md
✅ blender-scene-reference.md
❌ overview.md                         ← Overview of what?
❌ design.md                           ← Design of what?
❌ spec.md                             ← Spec of what?
```

### 5. Suffixes indicate doc type (optional)
```
<name>.md              ← Default (architecture, how-to, reference)
<name>-spec.md         ← Specification/contract
<name>-guide.md        ← How-to/tutorial
<name>-reference.md    ← Reference data
```

### 6. Special files are SCREAMING_SNAKE
```
✅ README.md
✅ CHANGELOG.md
✅ LICENSE.md
✅ AGENTS.md
✅ ROADMAP.md
```
These are convention across the industry. Keep them.

## Current Violations

| Current | Should Be | Project |
|---------|-----------|---------|
| `DESIGN.md` | `design.md` | kitchen-cam |
| `GLOSSARY.md` | `GLOSSARY.md` | root (keep, it's special) |
| `DOC_ROUTING.md` | `doc-routing.md` | root |
| `REORGANIZATION_PLAN.md` | `reorganization-plan.md` | root |
| `blaty_abs_square_edge_spec.md` | `blaty-abs-square-edge-spec.md` | catalog/materials |
| `blaty_fitline_spec.md` | `blaty-fitline-spec.md` | catalog/materials |
| `blaty_kolekcje_porownanie.md` | `blaty-kolekcje-porownanie.md` | catalog/materials |
| `global-collection-decory.yaml` | `global-collection-decory.yaml` | catalog/materials (OK) |
| `materialy.md` | `materials-overview.md` | catalog/materials |
| `poradnik-kompleksowy.md` | `comprehensive-guide.md` | kitchen-cam |
| `analiza_konfiguratora_formatek.md` | `configurator-analysis.md` | kitchen-cam |
| `01-overview.md` | `user-context.md` | kitchen-cam (not an overview) |
| `overview.md` | `overview.md` | kitchen-cam (keep, it's the real overview) |

## Directory Structure

```
docs/
├── README.md              ← Special file
├── CHANGELOG.md           ← Special file
├── doc-routing.md         ← kebab-case
├── glossary.md            ← kebab-case
├── adr/                   ← Numbered ADRs
│   ├── 001-panel-is-atomic-unit.md
│   └── ...
├── vision/                ← Numbered vision docs
│   ├── 00-mission.md
│   └── 01-user-journeys.md
├── specs/                 ← kebab-case, no numbers
│   ├── configurator-api.md
│   └── builder-gui.md
├── architecture/          ← kebab-case
│   └── configurator-design.md
└── materials/             ← kebab-case, English names
    ├── kronospan/
    │   ├── acrylic-gloss.md
    │   └── blaty-abs-square-edge-spec.md
    └── kronoswiss/
        └── sensesation-spec.md
```
