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

- `tr-d7dd1870` — Material is still an independent store, mirror not started
  (**the fact this spec exists to kill** — expect it to go stale/diverged
  the moment the work lands; that firing is correct behavior, and the
  completion claim below is its successor).
- `tr-e3c86dfd` — catalog schema is 1.5.0: pairing_types is a data lookup
  table, variants carry `producer_sku` (the shape the mirror consumes).
- `tr-b485d74c` — kitchen-erp already consumes `kuchnie_core` via
  `domain_adapter.py` (precedent for how kitchen-erp wraps an upstream
  contract behind an adapter seam).

## Work

- `wk-d5df7e30` (Beads twin: `kuchnie-8gc`) — this spec's implementation.
- `wk-03434168` (Beads twin: `kuchnie-9vz`) — krono CATALOG dict routing;
  dep-blocked behind `wk-d5df7e30` (absent from `ready` until the mirror
  closes).

## Acceptance

Draft `done --claim` texts — to be finalized (and possibly split) at
completion, each scoped to what its evidence command actually sweeps:

1. "kitchen-erp Material rows are populated from the catalog service, not
   hand-seeded: the seeding path imports the catalog client and no
   production module under kitchen_erp/ inserts Material rows from
   literals" — evidence: grep for the catalog client import plus absence
   of literal-insert patterns, both scoped to `kitchen-erp/kitchen_erp/`.
2. "Material mirror refresh is exercised by tests: a test fakes the catalog
   service and asserts the mirror converges" — evidence: targeted pytest
   run, scoped to the new test file.

When these are filed via `truth done wk-d5df7e30 --claim ...`, retire
`tr-d7dd1870` through the human queue (it will have diverged — that is the
lifecycle working, not an error).
