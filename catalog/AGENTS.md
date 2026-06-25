# Agent Guide — catalog

Read this before making changes. It's short on purpose.

---

## Project at a glance

Material catalog browser for board manufacturers (Kronospan, Swiss Krono, Egger). Takes YAML source files, validates against reference data, generates JSON, serves via Vite with live reload.

**One sentence**: YAML → `build.js` (validate + generate) → `catalog.json` → Vite → browser

---

## Architecture (3 rules)

1. **YAML is the source of truth.** Never edit `catalog.json` directly. It's generated. Edit the YAML, run `make build`.

2. **One file per collection.** Each collection (e.g., Acrylic Gloss, Global Collection) gets its own YAML file. Collections are independent — adding one doesn't require editing another.

3. **Reference tests catch drift.** The MD files in `docs/materials-boards/` contain data extracted from PDFs. Test fixtures mirror that data. If YAML drifts from the reference, tests fail.

---

## File map

```
catalog/
├── package.json          Own deps (vite, js-yaml, zod). Independent from root.
├── Makefile              make dev / test / build / validate
├── dev.js                Watch YAML → rebuild → Vite HMR
├── index.html            Frontend (Alpine.js, fetches catalog.json)
├── vite.config.mjs       publicDir = public/
└── public/               Images + generated catalog.json
    ├── catalog.json      (generated, gitignored)
    ├── kronospan/img/
    ├── swiss-krono/img/
    └── egger/img/

data/materials/
├── shared/
│   ├── concepts.yaml     Tags, surface types, color families (cross-producer)
│   └── schema.js         Zod schemas for validation
├── kronospan/
│   ├── collections.yaml  Metadata + structures for all Kronospan collections
│   └── *.yaml            One file per collection (acrylic-gloss.yaml, etc.)
├── swiss-krono/          (same structure)
├── egger/                (same structure)
├── tests/
│   ├── validate.test.js  All automated checks
│   └── fixtures/         Reference data from MD files
└── build.js              YAML → JSON + validation
```

**Data flows**: `data/materials/**/*.yaml` → `build.js` → `data/dist/catalog.json` → copied to `catalog/public/catalog.json` → Vite serves it

---

## Adding a new producer

1. Create directory: `data/materials/{producer}/img/`
2. Create `data/materials/{producer}/collections.yaml` with structures, formats, metadata
3. Create collection YAML files (e.g., `standard.yaml`)
4. Add `{producer}` to `PRODUCERS` array in `build.js`
5. Create `.gitkeep` in `catalog/public/{producer}/img/`
6. Run `make validate` from `catalog/`
7. Create test fixtures from reference data (MD/PDF)

---

## Adding a new collection to existing producer

1. Create `data/materials/{producer}/{collection-name}.yaml`
2. Follow existing YAML structure (see `acrylic-gloss.yaml` as template)
3. Add collection metadata to `{producer}/collections.yaml`
4. Run `make validate`
5. Create reference fixture if data comes from a new PDF/MD source

---

## YAML format conventions

```yaml
# Collection file structure:
collection: collection_id     # matches key in collections.yaml

decors:
  - id: "8685"                # string, matches producer's code system
    name: "Biel Alpejska"     # Polish name from catalog
    group: "XXI Color Basic"  # producer's grouping
    structure: AG             # code from collections.yaml structures
    thickness_mm: 18.3
    format: [2800, 1300]      # [length, width] in mm
    sidedness: one_sided
    konfekcja: true           # piece-ordering available
    global_decor_id: K8685    # FK to global-collection (if applicable)
    edge:
      code: "K-8685-HG/AG"   # producer's edge code
      supplier: Schilsner
      finish: HG              # edge finish code
      material: ABS
    notes: "Optional notes"   # anything non-standard
```

**ID format**: matches the producer's catalog exactly. Kronospan uses `"8685"`, Swiss Krono uses `"D3025"`, Egger uses `"U112"`. Don't normalize.

**Structure codes**: defined in `collections.yaml` per producer. Same code can mean different things across producers (Kronospan `SM` ≠ Swiss Krono `SM`). Don't assume equivalence.

---

## Validation layers

| Layer | What it checks | When it runs |
|-------|---------------|-------------|
| Zod schema | Required fields, types, structure | `make build` |
| Cross-reference | Structures exist in collections.yaml | `make build` |
| Edge pattern | Edge codes match producer convention | `make build` |
| Uniqueness | No duplicate IDs or edge codes | `make build` |
| Reference comparison | YAML matches MD/PDF source data | `make test` |
| Image existence | Referenced img files exist | `make build` (warn) |

---

## Testing conventions

- **Reference fixtures in `tests/fixtures/`**: one per collection, named `{collection}-ref.js`
- **Fixtures are hand-copied from MD files**: the MD is the authority from the PDF
- **Tests compare YAML against fixtures**: if YAML drifts, test fails
- **Run `make test` before every commit**

---

## What NOT to do

- Don't edit `catalog.json` or `data/dist/*.json` directly — they're generated
- Don't put producer-specific data in `shared/concepts.yaml` — that's for cross-producer concepts only
- Don't assume structure codes are interchangeable across producers
- Don't hardcode structure metadata in the frontend — read it from catalog.json
- Don't add images to `data/materials/` — put them in `catalog/public/{producer}/img/`
- Don't commit `catalog/public/catalog.json` — it's generated and gitignored

---

## Commands

```bash
cd catalog

make dev         # Start dev server (watch + rebuild + HMR at localhost:5173)
make build       # YAML → catalog.json
make test        # Run 55 validation tests
make validate    # build + test
make prod        # Production bundle
make clean       # Remove generated files
```

Module resolution: `build.js` and tests live in `data/materials/` but run with `NODE_PATH=catalog/node_modules` (set by Makefile) to access `js-yaml` and `zod`.

---

## Current state

- 1 producer: Kronospan (partial)
- 1 collection: Acrylic Gloss (6 decors)
- 55 tests passing
- Global Collection (174 decors) exists as `global-collection-decory.yaml` in old format — needs migration to new YAML structure
- Swiss Krono data exists as inline JS in old `kolekcja.html` — needs migration
- Egger: empty, waiting for data
