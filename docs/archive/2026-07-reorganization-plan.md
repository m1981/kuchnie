# Documentation Reorganization Plan

Generated: 2026-07-01  
Based on: Evolution analysis + doc noise analysis

---

## Current Problems

1. **No layer separation** — vision, specs, and docs mixed in same directories
2. **Dead project docs not quarantined** — kitchen-app docs scattered
3. **Stale docs not marked** — post-cutoff docs look like current docs
4. **No clear entry points** — LLM can't tell what's trustworthy

## Target Structure

```
kuchnie/
├── docs/                              ← SHARED (cross-project)
│   ├── vision/                        ← Layer 1: strategy, mission
│   │   ├── 00-mission.md              ← Moved from docs/00-brief.md
│   │   ├── 01-user-journeys.md        ← NEW (extract from 00-brief2.md)
│   │   └── 02-pattern-mapping.md      ← Moved from docs/02_pattern_mapping.md
│   ├── adr/                           ← Immutable decisions (KEEP)
│   ├── glossary.md                    ← KEEP
│   ├── archive/                       ← Historical (merged archive + archive2)
│   └── README.md                      ← NEW: doc structure guide
│
├── catalog/                           ← ACTIVE PROJECT
│   ├── AGENTS.md                      ← KEEP
│   ├── CHANGELOG.md                   ← KEEP
│   ├── ROADMAP.md                     ← KEEP
│   └── docs/
│       ├── specs/                     ← Layer 2: contracts
│       │   ├── configurator-api.md    ← KEEP
│       │   ├── builder-gui.md         ← KEEP
│       │   └── scenarios-edge-cases.md ← KEEP
│       ├── adr/                       ← Project decisions (KEEP)
│       ├── architecture/              ← Layer 3: current state
│       │   ├── multi-producer-strategy.md ← KEEP
│       │   └── configurator-design.md ← Moved from 03-configurator-design.md
│       ├── materials/                 ← Reference data (KEEP)
│       ├── curated-kitchens.md        ← KEEP (reference data)
│       └── archive/                   ← Historical
│           └── STATE-SYNC-*.md        ← Point-in-time snapshots
│
├── kitchen-app/                       ← DEAD PROJECT
│   ├── AGENTS.md                      ← Mark as ARCHIVED
│   └── docs/
│       └── archive/                   ← ALL docs here
│           ├── README.md              ← "This project is archived"
│           ├── doc/                   ← Moved from doc/
│           └── archived/              ← Already archived docs
│
├── kitchen-cad/                       ← CUT PROJECT (Jun 28)
│   ├── AGENTS.md                      ← KEEP
│   ├── CHANGELOG.md                   ← KEEP
│   ├── ROADMAP.md                     ← KEEP
│   └── docs/
│       ├── specs/                     ← Layer 2
│       │   ├── legrabox-spec.md       ← Moved from LEGRABOX_SPEC.md
│       │   ├── cabinet-variants.md    ← Moved from CABINET-VARIANTS.md
│       │   └── 01-overview.md         ← KEEP
│       ├── adr/                       ← NEW: extract decisions
│       ├── architecture.md            ← KEEP
│       ├── design.md                  ← KEEP
│       └── archive/                   ← Stale docs
│           ├── PROJECT_LOG.md         ← Stale
│           ├── sessions/              ← Historical
│           └── test-plan.md           ← Stale
│
├── kitchen-plugin/                    ← CUT PROJECT (Jun 24)
│   ├── AGENTS.md                      ← KEEP
│   ├── CHANGELOG.md                   ← KEEP
│   ├── ROADMAP.md                     ← KEEP
│   └── docs/
│       ├── specs/                     ← Layer 2
│       │   ├── config-syntax.md       ← KEEP
│       │   └── wall-centric-model.md  ← KEEP
│       ├── adr/                       ← NEW: extract decisions
│       ├── architecture.md            ← KEEP
│       ├── archive/                   ← Historical
│       │   └── implementation-plan.md ← Already archived
│       └── reference/                 ← KEEP (external references)
│
└── krono-compositor-mvp/              ← PAUSED PROJECT (Jun 23)
    ├── AGENTS.md                      ← KEEP
    ├── CHANGELOG.md                   ← KEEP
    ├── ROADMAP.md                     ← Mark as ASPIRATIONAL
    └── docs/
        ├── specs/                     ← Layer 2
        │   ├── pipeline-rules.md      ← Moved from PIPELINE_RULES.md
        │   └── blender-scene-ref.md   ← Moved from blender-scene-reference.md
        ├── adr/                       ← NEW: extract decisions
        ├── architecture.md            ← Mark as "rewritten at cutoff"
        └── archive/                   ← Stale docs
            ├── conflicting-paradigms.md ← Stale
            ├── prompt_blender.md      ← Historical prompt
            ├── prompt_web.md          ← Historical prompt
            └── what_next.md           ← Aspirational
```

## Migration Steps

### Phase 1: Create new structure
```bash
mkdir -p docs/vision
mkdir -p docs/archive
mkdir -p catalog/docs/archive
mkdir -p kitchen-app/docs/archive/doc
mkdir -p kitchen-cad/docs/{specs,adr,archive}
mkdir -p kitchen-plugin/docs/{specs,adr}
mkdir -p krono-compositor-mvp/docs/{specs,adr,archive}
```

### Phase 2: Move vision docs
```bash
mv docs/00-brief.md docs/vision/00-mission.md
mv docs/00-brief2.md docs/vision/01-user-journeys.md
mv docs/02_pattern_mapping.md docs/vision/02-pattern-mapping.md
```

### Phase 3: Archive stale root docs
```bash
mv docs/COLD-REVIEW-*.md docs/archive/
mv docs/CATALOG_RELOCATION_PLAN.md docs/archive/
mv docs/DATA-FLOW-BLENDER.md docs/archive/
mv docs/ARCHITECTURE-kuchnie-core.md docs/archive/
mv docs/archive2/* docs/archive/
rmdir docs/archive2
```

### Phase 4: Quarantine kitchen-app
```bash
mv kitchen-app/doc/* kitchen-app/docs/archive/doc/
rmdir kitchen-app/doc
```

### Phase 5: Reorganize kitchen-cad
```bash
mv kitchen-cad/docs/LEGRABOX_SPEC.md kitchen-cad/docs/specs/legrabox-spec.md
mv kitchen-cad/docs/CABINET-VARIANTS.md kitchen-cad/docs/specs/cabinet-variants.md
mv kitchen-cad/docs/00-overview.md kitchen-cad/docs/specs/overview.md
mv kitchen-cad/docs/PROJECT_LOG.md kitchen-cad/docs/archive/
mv kitchen-cad/docs/sessions kitchen-cad/docs/archive/
mv kitchen-cad/docs/test-plan.md kitchen-cad/docs/archive/
mv kitchen-cad/docs/poradnik-kompleksowy.md kitchen-cad/docs/archive/
mv kitchen-cad/docs/analiza_konfiguratora_formatek.md kitchen-cad/docs/archive/
```

### Phase 6: Reorganize krono-compositor
```bash
mv krono-compositor-mvp/docs/PIPELINE_RULES.md krono-compositor-mvp/docs/specs/pipeline-rules.md
mv krono-compositor-mvp/docs/blender-scene-reference.md krono-compositor-mvp/docs/specs/blender-scene-ref.md
mv krono-compositor-mvp/docs/conflicting_paradigms.md krono-compositor-mvp/docs/archive/
mv krono-compositor-mvp/docs/prompt_blender.md krono-compositor-mvp/docs/archive/
mv krono-compositor-mvp/docs/prompt_web.md krono-compositor-mvp/docs/archive/
mv krono-compositor-mvp/docs/what_next.md krono-compositor-mvp/docs/archive/
mv krono-compositor-mvp/docs/rendering-improvements.md krono-compositor-mvp/docs/archive/
```

### Phase 7: Reorganize catalog
```bash
mv catalog/docs/03-configurator-design.md catalog/docs/architecture/configurator-design.md
mv catalog/docs/STATE-SYNC-*.md catalog/docs/archive/
```

### Phase 8: Add markers
Create README.md files in key directories explaining the structure.

## Execution

Run: `bash scripts/reorganize_docs.sh`
