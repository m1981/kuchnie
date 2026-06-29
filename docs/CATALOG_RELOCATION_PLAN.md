# Catalog Relocation Plan

Generated: 2026-06-29

---

## Current State: Catalog Files Scattered Across 4 Locations

```
kuchnie/
├── catalog/                    ← 136 files (the "home")
│   ├── data/                   ← generated YAML (kronospan_full.yaml, kronoswiss_full.yaml)
│   ├── public/                 ← catalog.json, images, frontend
│   ├── scripts/                ← YAML generators, seed, importer
│   └── ...
│
├── data/materials/             ← SOURCE YAML + build pipeline (should be in catalog/)
│   ├── build.js                ← builds catalog.json → outputs to catalog/public/
│   ├── kronospan/
│   │   ├── collections.yaml
│   │   └── decors.yaml         ← 83KB, primary decor data
│   ├── shared/
│   │   ├── concepts.yaml
│   │   └── schema.js
│   ├── egger/                  ← empty (placeholder)
│   ├── swiss-krono/            ← empty (placeholder)
│   └── tests/
│       ├── validate.test.js
│       └── fixtures/
│
├── docs/materials-boards/      ← SOURCE DOCS (PDFs + markdown specs)
│   ├── Kronospan/
│   │   ├── *.md                ← 18 markdown spec files
│   │   ├── *.pdf               ← 3 source PDFs
│   │   ├── extracted/          ← 16 extracted PDF pages
│   │   └── *-images/           ← ~60 PNG images from PDFs
│   ├── KronoSwiss/
│   │   └── *.md                ← 3 spec files
│   ├── kronospan-schema.md
│   └── materialy.md
│
├── scripts/                    ← CONVERSION SCRIPTS
│   ├── convert-global-collection.js  ← reads docs/materials-boards/ → writes data/materials/
│   └── export_pdf_pages.py     ← generic PDF→PNG utility
│
└── (other projects referencing catalog data)
    ├── src/kuchnie_core/materials/   ← core engine's material bridge (reads catalog DB)
    ├── tests/test_materials_bridge.py
    └── features/archive/F005-material-resolver/ ← spec only
```

---

## Dependency Map: Who Reads What

### `data/materials/` (root)

| Consumer | File | Reference |
|----------|------|-----------|
| `catalog/package.json` | `build`, `test`, `validate` scripts | `cd .. && node data/materials/build.js` |
| `data/materials/build.js` itself | reads YAML from `data/materials/{producer}/` | writes to `catalog/public/catalog.json` |
| `catalog/AGENTS.md` | documentation | `data/materials/{producer}/decors.yaml` |
| `catalog/docs/architecture/README.md` | architecture diagram | references `data/materials/` |

**No other project reads `data/materials/` at runtime.** The `kitchen-plugin` and `krono-compositor` references to `data.materials` are **Blender API calls** (`bpy.data.materials`), not file paths.

### `docs/materials-boards/` (root)

| Consumer | File | Reference |
|----------|------|-----------|
| `catalog/scripts/generate_kronospan_yaml.py` | source data | `docs/materials-boards/Kronospan/global-collection.md` |
| `scripts/convert-global-collection.js` | source data | `docs/materials-boards/Kronospan/global-collection-decory.yaml` |
| `catalog/docs/architecture/04-er-diagram.md` | documentation | references spec files |

### `scripts/` (root)

| Consumer | File | Reference |
|----------|------|-----------|
| `scripts/convert-global-collection.js` | reads from | `docs/materials-boards/Kronospan/` |
| `scripts/convert-global-collection.js` | writes to | `data/materials/kronospan/` |
| `scripts/export_pdf_pages.py` | standalone | generic utility, no catalog refs |

---

## Relocation Proposal

### Move 1: `data/materials/` → `catalog/data/materials/`

**What**: The entire `data/materials/` directory  
**Where**: `catalog/data/materials/` (alongside existing `catalog/data/kronospan_full.yaml`)

```
catalog/data/
├── kronospan_full.yaml         ← already here (generated)
├── kronoswiss_full.yaml        ← already here (generated)
├── materials/                  ← NEW (moved from root)
│   ├── build.js
│   ├── kronospan/
│   │   ├── collections.yaml
│   │   └── decors.yaml
│   ├── shared/
│   │   ├── concepts.yaml
│   │   └── schema.js
│   ├── egger/
│   ├── swiss-krono/
│   └── tests/
```

**Files to update** (4 files):

| File | Change |
|------|--------|
| `catalog/package.json` | `"build": "node data/materials/build.js"` (remove `cd ..`) |
| `data/materials/build.js` | `CATALOG_PUBLIC` path: `../../public` → `../public` |
| `catalog/AGENTS.md` | Update path references |
| `catalog/docs/architecture/README.md` | Update diagram |

**Safety**: 🟢 **SAFE** — No external consumers. All references are within catalog/.

### Move 2: `docs/materials-boards/` → `catalog/docs/materials/`

**What**: The entire `docs/materials-boards/` directory  
**Where**: `catalog/docs/materials/`

```
catalog/docs/
├── architecture/               ← already here
├── materials/                  ← NEW (moved from root)
│   ├── Kronospan/
│   │   ├── *.md
│   │   ├── *.pdf
│   │   ├── extracted/
│   │   └── *-images/
│   ├── KronoSwiss/
│   ├── kronospan-schema.md
│   └── materialy.md
```

**Files to update** (3 files):

| File | Change |
|------|--------|
| `catalog/scripts/generate_kronospan_yaml.py` | Update source path comment (cosmetic) |
| `scripts/convert-global-collection.js` | `INPUT` path: `docs/materials-boards/...` → `catalog/docs/materials/...` |
| `catalog/docs/architecture/04-er-diagram.md` | Update path references |

**Safety**: 🟢 **SAFE** — Only catalog scripts reference these docs.

### Move 3: `scripts/convert-global-collection.js` → `catalog/scripts/`

**What**: The conversion script  
**Where**: `catalog/scripts/convert-global-collection.js`

**Files to update** (1 file):

| File | Change |
|------|--------|
| `catalog/scripts/convert-global-collection.js` | Update all relative paths (was `../docs/...` → now `../docs/...` or `../data/materials/...`) |

**Safety**: 🟢 **SAFE** — Standalone script, no external consumers.

### Keep in Place: `scripts/export_pdf_pages.py`

**Why**: Generic utility, not catalog-specific. Used for any PDF→PNG conversion.

### Keep in Place: `src/kuchnie_core/materials/`

**Why**: This is the **core engine's** material bridge, not the catalog. It reads from the catalog's SQLite DB at runtime. Different concern.

### Keep in Place: `features/archive/F005-material-resolver/`

**Why**: Archived spec, already in archive directory.

---

## Risk Assessment

| Move | Risk | Reason |
|------|------|--------|
| `data/materials/` → `catalog/` | 🟢 LOW | Only catalog references it. 4 files to update. |
| `docs/materials-boards/` → `catalog/` | 🟢 LOW | Only catalog scripts reference it. 3 files to update. |
| `scripts/convert-*` → `catalog/` | 🟢 LOW | Standalone script. 1 file to update. |
| `scripts/export_pdf_pages.py` | ⚪ NONE | Keep in place. |

**Total files to update**: 8 files  
**External consumers affected**: 0  
**Risk of breaking other projects**: None

---

## Execution Plan

```bash
# Step 1: Move data/materials/ → catalog/data/materials/
git mv data/materials catalog/data/materials

# Step 2: Move docs/materials-boards/ → catalog/docs/materials/
git mv docs/materials-boards catalog/docs/materials

# Step 3: Move conversion script
git mv scripts/convert-global-collection.js catalog/scripts/

# Step 4: Update references (8 files)
# - catalog/package.json
# - catalog/data/materials/build.js
# - catalog/AGENTS.md
# - catalog/docs/architecture/README.md
# - catalog/scripts/generate_kronospan_yaml.py
# - catalog/scripts/convert-global-collection.js
# - catalog/docs/architecture/04-er-diagram.md
# - CHANGELOG.md (root)

# Step 5: Verify
cd catalog && make build && make test
```

---

## Post-Move Structure

```
catalog/                          ← self-contained
├── AGENTS.md
├── Makefile
├── data/
│   ├── kronospan_full.yaml       ← generated
│   ├── kronoswiss_full.yaml      ← generated
│   └── materials/                ← MOVED from root data/materials/
│       ├── build.js
│       ├── kronospan/
│       ├── shared/
│       ├── egger/
│       ├── swiss-krono/
│       └── tests/
├── docs/
│   ├── architecture/
│   └── materials/                ← MOVED from root docs/materials-boards/
│       ├── Kronospan/
│       ├── KronoSwiss/
│       └── ...
├── public/
│   ├── catalog.json              ← generated by build.js
│   └── kronospan/
├── scripts/
│   ├── generate_kronospan_yaml.py
│   ├── generate_kronoswiss_yaml.py
│   ├── convert-global-collection.js  ← MOVED from root scripts/
│   ├── importer.py
│   └── seed.py
└── ...
```
