# ADR-008: Material Master Catalog

## Status

**Accepted** — 2026-06-27

## Context

The kuchnie-core engine (`src/kuchnie_core/`) decomposes kitchen cabinets into physical panels. Each panel has a `material: str` field referencing an external material code (e.g. `"swiss_krono.U119_VL"`). The engine never knew WHAT that material was — only its string code.

With the import of Kronospan (~570+ SKU) and Swiss Krono (~300+ SKU) catalogs, we needed a structured way to store material metadata: thicknesses, surface structures, availability, worktop specifications, edge banding, and matching products.

The question was: should material data live inside `kuchnie_core` or in a separate catalog module?

## Decision

### 1. Catalog is a separate bounded context

Material Master lives in `catalog/` (SQLite + Python importer), NOT in `src/kuchnie_core/`. The project domain references catalog data via string codes (`business_id`), not integer FKs.

**Rationale:**
- **Stability**: JSON/YAML project files use human-readable codes, not opaque IDs
- **Portability**: a project designed on one catalog version can be loaded on another
- **Independence**: catalog schema can evolve without touching project domain code
- **Multiple catalogs**: Kronospan and Swiss Krono coexist without conflict

### 2. Variant = Decor × Material × Structure × Thickness

A single color (Decor, e.g. K8685 "Biel Alpejska") can be produced as:
- Chipboard 18mm, structure SM (fronts)
- Chipboard 16mm, structure SM (carcass)
- MDF Acrylic 18.3mm, structure AG (high-gloss front)
- Postformed worktop 38mm, structure RS (kitchen counter)
- HPL laminate 0.8mm (self-application)

Each combination is a separate **Variant**. The Decor is the shared identity; the Variant is the purchasable SKU.

### 3. Decor-Structure junction table (not CSV)

Kronospan Global Collection lists "multi_structures" for each decor (e.g. K8685 is available in SM, BS, PD, PW). Initially stored as CSV in `variants.multi_structures`. Replaced with a proper junction table `decor_structures(decor_id, structure_id, is_primary)`.

**Why:** CSV cannot be JOINed, filtered, or aggregated. The junction table enables:
- "What structures does K8685 come in?" → simple JOIN
- "Which decors have structure PD?" → reverse query
- Proper normalization (3NF)

### 4. EAV for property flags (not columns on Variant)

Material properties (antibacterial, waterproof, anti_fingerprint, etc.) vary per product and catalog. Storing them as columns on `variants` would require 10+ nullable boolean columns, most NULL for any given variant.

Instead, `property_flags(variant_id, property, value)` uses the Entity-Attribute-Value pattern.

**Why:** Each catalog describes different properties. KronoSwiss emphasizes antibacterial + fire resistance. Kronospan emphasizes anti_fingerprint + UV stability. EAV allows extension without schema migration.

### 5. Worktop specs as 1:0..1 extension (not columns on Variant)

Worktop-specific fields (profile, max_length, edge_material, core_color) only apply to variants with role "worktop". Storing them on `variants` would create 6+ NULL columns for every non-worktop variant.

`worktop_specs` is a 1:0..1 table linked to `variants` via UNIQUE(variant_id).

### 6. Pairings for matching products (expanded types)

Kronospan Global Collection has a "Dopasowanie 1:1" section showing which products match each decor (Acrylic Gloss, Mirror Gloss, Compact Interior, HPL laminate, worktop). Stored in `pairings(front_decor_id, target_decor_id, pairing_type)`.

Pairing types: `carcass`, `worktop`, `splashback`, `side_panel`, `plinth`, `hpl_laminate`, `acrylic`, `mirror`, `compact`, `kronoart`, `black_wood`.

### 7. Structures scoped by producer (not global)

Kronospan SM = "Super Mat" (smooth, matt). Swiss Krono SM = "Gładka" (smooth, matt). Same code, different producers, potentially different physical properties.

`structures` has `producer_id` FK (nullable — NULL = shared). `UNIQUE(code, producer_id)` allows the same code per producer.

## Consequences

### Positive
- Catalog schema is independent of project domain — can evolve separately
- YAML data files are self-contained and version-controlled
- Importer is idempotent (INSERT OR IGNORE) — safe to re-run
- 177 tests verify the full pipeline (schema → import → queries)
- Two producers coexist without code collision

### Negative
- String-based references (business_id) require resolution at query time
- No referential integrity between Catalog and Project at DB level (enforced in application)
- EAV queries require pivoting for UI display

### Neutral
- SQLite chosen for catalog (portable, file-based, good enough for ~1000 SKU)
- YAML as intermediate format (human-readable, git-friendly)

## References

- ER diagram: `catalog/docs/architecture/configurator-design.md`
- Schema: `catalog/docs/architecture/01-schema.sql` through `05-*.sql`
- Importer: `catalog/scripts/importer.py`
- Tests: `catalog/tests/test_*.py` (177 tests)
- CHANGELOG: `CHANGELOG.md` (2026-06-27 entry)
