# ADR-004 — Producer generalization: remove producer-specific shapes before Egger onboarding

> Reader: anyone adding a third producer (Egger) or a new decor collection to the catalog.
> Enables: onboarding Egger (or any producer) via data inserts only — no schema rebuilds.
> Update-trigger: never edited; superseded by a new ADR if the variant grain changes.

Status: accepted 2026-07-04
Schema: 1.5.0 (`db/schema.sql`, incremental `docs/architecture/06-phase5-producer-generalization.sql`, runtime migration `scripts/migrate_1_5_0.py`)
Context doc: `docs/architecture/multi-producer-strategy.md`

## Context

The catalog holds Kronospan and Swiss Krono. Egger is next. Three schema
shapes were producer-specific and would have required a table rebuild per
new producer:

1. `pairings.pairing_type` was a CHECK enum containing marketing names
   (`kronoart`, `black_wood`). VERIFIED(grep schema.sql 1.4.0).
2. `decors.one_global` / `decors.new_2024` were columns encoding
   *collection membership* of two specific producers' 2024 collections —
   a concept that multiplies per producer and per collection year.
3. Variant identity relied solely on our synthetic `business_id`
   (`0190-CH-18-RS`); producers' own article numbers had no home, and
   Egger renumbers articles at collection changeovers.

## Decision

1. **`pairing_types` lookup table** (slug, name, producer_hint) replaces
   the CHECK. `pairings.pairing_type` is now an FK to it. Adding an
   Egger-branded pairing type is one INSERT.
2. **Collection flags become tags.** `one_global` → tag `one-global`,
   `new_2024` → tag `new-2024` in the existing `tags`/`decor_tags`
   tables. `v_decors_full` recomputes both as columns via EXISTS, so the
   API contract (`models/domain.py`) and repositories are unchanged.
   YAML import format is also unchanged — `scripts/importer.py` maps the
   YAML keys to tags. Future collections are new tag slugs.
3. **`variants.producer_sku`** (nullable, unique when present) stores the
   producer's own article number. Our `business_id` stays the primary
   business key so producer renumbering cannot break references.
4. **`variants.multi_structures` is DEPRECATED.** The orderable truth is
   per (decor, material, structure, thickness, format) — one variant row
   each. The 5 rows still using `multi_structures` remain valid until
   expanded; new imports must not write it.

## Egger variant business_id grammar

Same shape as Kronospan's: `{DECOR}-{MATERIAL}-{THICKNESS}[-{STRUCTURE}]`.

| Segment | Egger example | Notes |
|---|---|---|
| DECOR | `U702`, `H1180` | Egger decor code, `decors.business_id` |
| MATERIAL | `EU` Eurodekor MFC, `PM`/`PG` PerfectSense Matt/Gloss, `WT` worktop, `CP` compact, `HP` HPL | two-letter code |
| THICKNESS | `18`, `38` | mm |
| STRUCTURE | `ST9`, `ST37` | Egger ST code, omitted where the material implies it (PerfectSense) |

Example: `U702-EU-18-ST9`; its `producer_sku` holds Egger's article number.
Egger structures (`ST…`) enter `structures` scoped by `producer_id` —
no namespace collision with Kronospan codes (existing UNIQUE(code, producer_id)).

## Consequences

- Egger onboarding = `data/egger_full.yaml` + a `generate_egger_yaml.py`
  generator; no DDL.
- `init_schema()` auto-migrates pre-1.5.0 databases (detects the old
  `decors.one_global` column), preserving its idempotency contract.
- Two view-definition sources still exist (`db/schema.sql` vs
  `docs/architecture/*.sql` chain) and still diverge on
  `v_worktops_full`. Known debt, out of scope here.
