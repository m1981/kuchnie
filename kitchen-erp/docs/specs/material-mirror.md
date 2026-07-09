# Spec: Material mirror — kitchen-erp Material becomes a cache of catalog/

> Reader: whoever implements ADR-011 phase 3 (or audits it later) | Enables: starting the mirror work from verified reality instead of from memory of ADR-011 | Update-trigger: scope changes, an acceptance criterion is renegotiated, or spec-health flags a dead ground truth

## Intent

kitchen-erp's `Material` SQLModel table is today an independent, hand-seeded
material store. ADR-011 declares it must become a **local cache/mirror** of
the catalog service (ADR-008's canonical source): kitchen-erp reads material
identity, pricing inputs, and pairing data from catalog/, keeps a local copy
only for offline/latency reasons, and stops being a place where material
facts are *born*.

Scope: the read path — mirror population, refresh, and lookups the BOM/cost
flow needs. Non-goals: write-through editing of catalog data from the ERP
UI; decor miniature acquisition (wk-6716e9c8's territory); krono-compositor
routing (wk-03434168, deliberately dep-blocked behind this work).

## Decisions

- `docs/adr/011-*.md` (kitchen-erp naming/role) — names the component,
  declares Material-as-mirror as follow-up work.
- `docs/adr/008-*.md` — catalog service is the canonical material source;
  everything else consumes it.

## Ground truths

- `tr-e3c86dfd` — catalog schema is 1.5.0: pairing_types is a data lookup
  table, variants carry `producer_sku` (the shape the mirror consumes).
- `tr-b485d74c` — kitchen-erp already consumes `kuchnie_core` via
  `domain_adapter.py` (precedent for how kitchen-erp wraps an upstream
  contract behind an adapter seam).
- The pre-mirror claim "Material is still an independent store" (referred
  to by title, not id — it diverged the moment the work landed, exactly as
  this spec predicted, and was retired through the human queue; its
  successors are the Acceptance claims below).

## Work

- `wk-d5df7e30` (Beads twin: `kuchnie-8gc`) — this spec's implementation
  (**closed 2026-07-09** via claim-at-death).
- `wk-03434168` (Beads twin: `kuchnie-9vz`) — krono CATALOG dict routing;
  was dep-blocked behind `wk-d5df7e30`, unblocked by its closure.

## Acceptance (final — filed 2026-07-09)

- `tr-fff10d41` (claim-at-death of `wk-d5df7e30`) — board materials are
  born in the catalog service: `state.py` seeds via `catalog_client` +
  `refresh_material_mirror`; the only `Material()` constructions in
  production code are the mirror's own upsert, the admin form, and three
  named utility survivors (HDF back, two ABS edges) that catalog/ does
  not model. Evidence: construction-site grep over
  `kitchen-erp/kitchen_erp/`, verified by a fresh session.
- `tr-9f989a83` — mirror refresh is exercised by tests: faked catalog
  client; populate, price preservation, idempotency, local-row isolation,
  role/discontinued filtering, typed offline failure. Evidence: targeted
  pytest (6 passed), verified by a fresh session.

Design boundary the claims encode: **identity is catalog-owned, pricing is
ERP-owned** — the mirror never writes `price_per_unit` on existing rows;
new rows arrive at 0.0 and are priced in Admin (catalog's variant_prices
table is deferred).
