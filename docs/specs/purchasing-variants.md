# Spec: Purchasing — variants, offers, prices (the UC-4 machine)

> Reader: anyone implementing wk-593a317b / wk-39ed9155 / wk-4c37f4ee, or
> recalling WHY purchasing works this way | Enables: building the variant
> comparison board, the offer/ACCEPT loop and price ingestion without
> re-deriving the owner's 2026-07-16 intent | Update-trigger: an increment
> ships (Acceptance line becomes a claim), a dealer/service contract
> changes, or UC-4's dress changes

Serves: UC-4 (primary), UC-1 (the comparison board is also the quoting
surface), UC-7 (price import). Design conversation: 2026-07-16 with the
owner; the dressed flow lives in [use-cases.md](use-cases.md) § UC-4 —
this spec holds the mechanisms and the reasoning ("intentions and killer
features") behind them.

## Intent — the three killer features, in the owner's scenario

The client accepts at the comparison board, not from a PDF three days
later. The physics: every cutting-service round-trip costs 1–3 days, so
the system's job is **iterate variants locally in minutes, send only the
finalist for a binding offer**. Three features carry that:

1. **Variants are parameters, not copies.** A Variant = the baseline
   design + overrides (front decor, drawer-system tier, corner mechanism,
   hinge class, worktop). Because decor and hardware are parameters of
   `decompose()`, a variant re-prices AND re-drills in seconds — nothing
   can drift from geometry.
2. **The cascade rule: a substitution is geometry, not a price line.**
   LEGRABOX→Tandembox moves runner pilots and drawer-box parts; a decor
   swap changes edging lines and may fail thickness/edge-band existence
   (checked against the catalog: variants, pairings, edges tables —
   tr-0dda200b's rebuilt-verified dataset). Every substitution re-derives
   the artifact set; no artifact is ever hand-patched to match a swap.
3. **The calibration loop.** Every received offer is stored against the
   estimate it answers. Bare total → the estimator learns total-per-job
   economics; itemized → per-category. After a handful of jobs the
   estimates converge on the service's real pricing (their waste
   included) with nobody maintaining a price file for the service.

## Non-goals

No nesting/optimization (the service's job); no accounting/invoicing; no
speculative scrapers (an adapter is built when a shop becomes real); no
warehouse system (min-stock top-up only); estimates never impersonate
offers (display rule, permanent).

## The variant lifecycle (state machine on the Project spine)

Draft → Frozen (artifacts derived from ONE decomposition) → Sent
(rozrys+DXF as ArtifactRefs, tr-e51ef4fd) → Offer-received (verbatim
archive + recorded amount) → **ACCEPTED** (lock; later edits are explicit
change-orders with visible redo cost) → Ordered (hardware CSVs out) →
stage 5→6 transition. Rejected offers loop back to Draft of a sibling
variant, never mutate a Sent one.

## Offer recording — no-granularity-lock-in (owner: "don't know yet")

```
Offer { variant_id, supplier, received_at, currency, total_net,
        source_ref (verbatim file archived), lines?: [
          { kind: board|cut|edge|drill|other, description, qty?, unit?,
            amount } ] }
```

`lines` is OPTIONAL. A bare total is a complete, valid offer; itemization
enriches calibration but is never required — so no service's paperwork
style can block the flow. Comparison and calibration read whatever
granularity exists and say which they used.

## Price ingestion (wk-39ed9155) — one doorway, many sources

Two-phase, provenance-first (the evidence discipline applied to money):

1. **Capture**: raw source archived verbatim (CSV/PDF/screenshot/page).
2. **Normalize** to the one canonical landing schema:

```
supplier;item_code;description;unit;price_net;currency;valid_from;source_ref
```

3. **Validate before import**: schema-complete, unit sane, price within
   ±tolerance of last known (jump → human eyeballs), rows failing are
   refused, never coerced.

Adapters per source, dumbest wins: CSV → column-map config; PDF/messy →
a fixed LLM extraction prompt whose output must validate against the
landing schema (spot-check gate before import); scraper → only when that
shop is real. **Prices decay**: every row carries `valid_from` +
implicit TTL; quotes standing on stale prices render estimate-grade with
age visible. Estimate ≠ offer, everywhere, forever.

## Hardware order CSV — the owner's format (composed 2026-07-16)

Semicolon-separated, Polish headers, one file per dealer per order;
producer code is the join key (every dealer understands Blum codes),
dealer code optional until a dealer is chosen:

```
# Zamowienie: <project>/<variant>; Odbiorca: <dealer>; Data: RRRR-MM-DD
Lp;Kod_producenta;Producent;Nazwa;Ilosc;Jm;Kod_dealera;Uwagi
1;750.5501B;Blum;LEGRABOX bok M 500mm;6;szt;;S1-S3 x2 (D60)
2;ZML.1100;Blum;Konfirmat 7x50;120;szt;;wg CNC listy
```

Quantities are NET TOP-UP: `required(variant accessories) − on_hand +
buffer`; the G13 families (konfirmaty, nóżki, klipsy, zszywki) must be
present, not runners alone. Stock is a small on-hand table, not a WMS.

## Substitution registry (seed set, owner-named)

| Axis | Alternatives | Cascade consequence |
|---|---|---|
| Drawer system | LEGRABOX ⇄ Tandembox ⇄ Merivobox (DrawerSystem ABC exists) | drilling + box parts change → re-decompose |
| Corner mechanism | Magic-Corner-class ⇄ half-carousel ⇄ plain shelves | price ± carcass changes |
| Hinge class | standard ⇄ soft-close | price only |
| Front decor | catalog pairings within family | edging lines, thickness/edge existence check |
| Worktop | per-lm alternatives (wk-4c37f4ee) | price + stage-9 artifacts |

## Ground truths

- tr-0dda200b — catalog data (decors, variants, pairings, edges) is
  complete and rebuildable; the substitution/validation checks stand on it.
- tr-e51ef4fd — Project spine with stage transitions and ArtifactRef
  exists; the variant lifecycle attaches to it.

## Work

- wk-593a317b (bd kuchnie-58o twin family) — the purchasing epic this
  spec designs: variant model, comparison board, offer recording,
  ACCEPT lock, hardware CSV emission, G11 edging-by-thickness, G13
  hardware completeness.
- wk-39ed9155 — price ingestion (landing schema + first adapters).
- wk-4c37f4ee — worktop per-lm (a comparison-board line).

## Acceptance

Pre-written `done --claim` texts:

- (variant model) SHIPPED 2026-07-16 as tr-6692cbe7: "kitchen-erp
  Variants hold parameter overrides on a project and re-derive rozrys,
  CNC and BOM from one decomposition per variant; a drawer-system
  substitution changes the emitted drilling ops, pinned by test"
  (`kitchen_erp/core/models.py` Variant + `variant_derivation.py`;
  corner-mechanism/hinge/worktop axes resolve into VariantParameters
  provenance, their cascades land with the later increments)
- (offer loop) SHIPPED 2026-07-17 as tr-c87a68f9: "Offers record
  against variants with optional line itemization, archive the source
  verbatim as an ArtifactRef, and an ACCEPT locks the variant so later
  edits require an explicit change-order; pinned by test"
  (`kitchen_erp/core/offers.py` — record_offer reuses the price-import
  capture idiom; accept_variant refuses without a recorded offer;
  rejection stays a no-op by design: loop back to a sibling draft)
- (hardware CSV) "Per-dealer hardware order CSVs emit net top-up
  quantities (required minus on-hand plus buffer) keyed by producer
  codes and include the G13 accessory families; pinned by test against a
  hand-computed golden order"
- (price ingestion) SHIPPED 2026-07-17 as tr-4afef6fb (third filing;
  the diverge lineage lives in the successor claims' texts): "Supplier
  price rows enter through the landing schema with verbatim source
  archived and validation refusing schema-incomplete or out-of-tolerance
  rows; assess_quote_freshness grades estimate-grade with age visible;
  pinned by test" (`kitchen_erp/core/price_import.py` — capture →
  normalize → validate → land; canonical + column-map CSV adapters;
  XLS/PDF adapters are follow-ups, re-save XLS as CSV meanwhile; the UI
  wiring landed 2026-07-17 as tr-4afef6fb — the quote header's
  estimate-grade badge with per-line price ages, wk-68b32f3b)
