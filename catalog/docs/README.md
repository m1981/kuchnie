# Catalog Documentation

This directory documents the **why** behind the catalog. The **what** lives
in code:

- `db/schema.sql` — table definitions (single source of truth for shape)
- `api/routers/*.py` — endpoint contracts
- `tests/` — behavior verification

Docs here capture decisions, comparisons, and future plans — not field lists.

---

## Index

| Path | Purpose |
|---|---|
| `adr/001-pairings-as-decor-relations.md` | Why pairings are decor-level, not variant-level |
| `adr/002-configurator-session-fk-strategy.md` | Why sessions store business_id strings, not integer FKs |
| `architecture/01-schema.sql` … `05-…sql` | Historical migration log (the path we took) |
| `architecture/multi-producer-strategy.md` | Kronospan vs Egger vs Swiss Krono modeling |
| `specs/configurator-api.md` | Configurator API spec + test cases |
| `03-configurator-design.md` | 6-step wizard data model + API design |
| `curated-kitchens.md` | Reference kitchen templates for configurator |
| `materials/` | Source material spec scans + extracted decor lists |

---

## Scope — what this catalog is and is NOT

### IS

- A queryable inventory of **producers, decors, variants, structures, edges, pairings, worktop specs**.
- Producer-agnostic (Kronospan, Swiss Krono today; Egger planned).
- A *visual* catalog — names, codes, colors, images, compatibility rules.
- The data layer for a kitchen configurator UI.

### IS NOT

| Concept | Why excluded | Where it belongs |
|---|---|---|
| Pricing | Region/dealer-specific; changes weekly | Separate `variant_prices` table when needed |
| Inventory levels | Real-time; ERP system territory | External ERP integration |
| Bill of materials (BOM) | Cabinet-quantity dependent | `kuchnie-core` decomposer |
| Customers / orders | Out of scope for catalog layer | Future commerce module |
| 3D / CAD assets | Different storage requirements | CDN / file server |
| Algorithmic pairing rules | Premature — explicit rows work today | Maybe v3 |
| NCS color tables | NCS string on decor is sufficient | — |

This boundary is deliberate. The catalog is a **read-mostly reference** of
what exists. Anything that changes per-customer, per-order, or per-day lives
elsewhere.

---

## Documentation rules (per repo AGENTS.md)

1. **Code is the documentation.** If a fact lives in schema.sql or a test,
   don't restate it here.
2. **Decisions go in ADRs.** Immutable. New decision = new ADR, supersedes old.
3. **Comparisons and rationale go in `architecture/`.** Living docs.
4. **Field-by-field tables are forbidden.** They drift. Link to schema instead.
5. **Polish vs English**: User-facing strings in Polish; schema and code in
   English; docs in English (this language).
