# Multi-Producer Strategy

> How the catalog handles multiple board producers (Kronospan, Swiss Krono,
> Egger, …) without forcing them into one shape.

---

## The producer asymmetry problem

Different board producers encode "same decor, different material" differently.
This affects how pairings, variants, and cross-references are modeled.

### Kronospan

- Decor codes differ between front and corpus variants of the "same" visual:
  - `K101` = Biały Frontowy (front-grade, PE structure)
  - `K110` = Biały Korpusowy (carcass-grade, SM structure)
  - These are **separate decors** despite both being "white".
- Structure code (`SM`, `PE`, `BS`) is a separate dimension from decor.
- Cross-material pairing requires **explicit `pairings` rows**.

### Egger (planned)

- Decor code is stable across materials:
  - `H3303 ST10` = Light Oak chipboard
  - `H3303 ST10` = Light Oak MDF
  - `H3303 ST10` = Light Oak HPL
- The structure code (`ST9`, `ST10`) is a *physical surface texture* baked
  into the decor name. It IS the structure.
- Cross-material pairing is **implicit by code identity** — no pairings
  table row needed.

### Swiss Krono (current)

- Similar to Kronospan: numeric decor codes, separate front/corpus naming.
- Structures (BS, FH, OW, …) overlap with Kronospan's by name only —
  the physical textures differ. We scope structures per-producer via
  `structures.producer_id`.

---

## Side-by-side comparison

| Aspect | Kronospan | Egger | Swiss Krono |
|---|---|---|---|
| Decor code | `K8685`, `K110` | `H3303` | `D198`, `BS`-suffixed |
| Structure code | `SM`, `PE`, `BS` | `ST9`, `ST10` | `BS`, `FH`, `OW` |
| Structure = physical texture? | partial (some are finishes) | yes (always) | yes |
| Front ↔ carcass relation | separate decors | same decor, different material | separate decors |
| Cross-collection pairing | explicit `pairings` rows | implicit (code match) | explicit `pairings` rows |
| HPL availability | `hpl_available` flag on variant | same code, different `material_type` | TBD |

---

## How the schema accommodates both

### 1. `structures` table is producer-scoped

```sql
CREATE TABLE structures (
    code TEXT NOT NULL,
    producer_id INTEGER REFERENCES producers(id),
    UNIQUE(code, producer_id)
);
```

`SM` from Kronospan and `SM` from Egger (if it existed) are different rows.
No accidental cross-producer collisions.

### 2. `pairings` is decor-level, not variant-level

See [ADR-001](./adr/001-pairings-as-decor-relations.md). This makes
Kronospan's explicit pairings cheap to maintain, and Egger's implicit
pairings simply means the rows reduce to identity (`front_decor_id =
target_decor_id`).

### 3. `material_types` is a shared vocabulary

```sql
material_types: chipboard, mdf_acrylic, mdf_lacquered, compact, hpl, ...
```

Both producers map their products into the same 11 types. Search by
"all chipboard fronts" works across producers.

### 4. `multi_structures` on variant for Kronospan's "available in multiple structures"

```sql
variants.multi_structures TEXT  -- "BS, PD, PW"
```

Kronospan's K8685 is available in SM (primary) + BS, PD, PW (alternates).
The primary structure is the `structure_id` FK; alternates are a CSV
string. Egger doesn't need this — each `H3303 ST9` and `H3303 ST10` is
its own variant row.

---

## Adding a new producer — checklist

1. Add row to `producers` (slug, name, country, website).
2. Add structures: each producer-specific code gets a row with
   `producer_id` set.
3. Add collections under the producer.
4. Add materials, decors, variants per existing patterns.
5. **For Kronospan-style producers**: populate `pairings` table with
   carcass/worktop/splashback relations.
6. **For Egger-style producers**: skip step 5 — pairings are identity.
   Configurator logic must fall back to "same decor in target role"
   when no explicit pairing exists.
7. Add edge bandings to `edges` + `variant_edges`.
8. Add a YAML fixture under `data/{producer_slug}_full.yaml`.

---

## Open questions

### Q1: Should we unify Egger and Kronospan decor codes?

No. Decor codes are producer-IP. `K8685` and `H3303` may *look* similar
but are different products with different physical properties (NCS color
varies slightly, even if marketed as "the same white"). The catalog
preserves producer identity.

### Q2: What if a customer wants to mix producers in one kitchen?

Allowed. The configurator's `pairings` query is producer-agnostic at
the join level: a Kronospan front can pair with a Swiss Krono worktop
if a `pairings` row says so. We currently seed only intra-producer
pairings; cross-producer pairings are a future curation effort.

### Q3: How do we handle decor renaming?

Producers occasionally rename or renumber decors. We keep `business_id`
as the producer's current code; historical codes go in `notes` or a
future `decor_aliases` table.

---

## See also

- `db/schema.sql` — current schema (v1.3.0)
- `docs/adr/001-pairings-as-decor-relations.md` — pairing design
- `data/kronospan_full.yaml`, `data/kronoswiss_full.yaml` — producer YAMLs
