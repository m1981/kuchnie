# Purchasing goldens — assumptions awaiting owner confirmation

> Reader: Michał confirming the business rules baked into board-order.csv,
> hardware-order.csv and edging-order.csv before the generator is built |
> Enables: turning these hand-drafted goldens into the acceptance baseline
> for wk-593a317b (board/hardware/edging order generation) | Update-trigger:
> any confirmed answer below — edit the golden AND this file together

Drafted 2026-08-01 from a System-32 trade-expert session (recall +
web-verified producer codes; sources in the session log). Every row marked
`DO-POTWIERDZENIA` in the CSVs traces to a numbered item here.

## The product-shaping verdict (expert, HIGH confidence)

For a one-person shop that subcontracts cutting, the PRIMARY purchasing
artifact is the **cutting-service order** (formatka list + per-edge banding,
priced per m² by the hurtownia) — NOT a full-sheet board order. On this
single D60 cabinet, whole-sheet ordering wastes 78–93% of every board
(utilization column in board-order.csv). Full sheets make sense only when
a whole kitchen is batched onto shared decors. The board-order golden
therefore records net m² + waste + the sheet count *as the batching
alternative*, with `Tryb_zamowienia = formatki` as the default.

## Owner confirmations (2026-08-01)

CONFIRMED by Michał: (1) formatki-first — cutting-service order is the
generator's primary output, full-sheet list is the batching view;
(4) K5307 band is 2×22 — reference bom.csv corrected; (5) screws/staples
are stock draws, never PO lines; (8) Blum components order as separate
lines (770…/750…/ZB7…). Still open: 2, 3, 6, 7 below.

## Assumptions to confirm

1. **Primary artifact**: cutting-service (formatki) order first, full-sheet
   only on explicit batching — is that how you actually buy?
   → CONFIRMED formatki-first.
2. **Waste factors**: 15% plain white, 20% directional decor (K5307 SN),
   10% HDF — confirm against your real scrap history.
3. **LEGRABOX colour**: assumed jedwabiście biały (silk white). The C-height
   white side-set code (770C5002S in white) needs dealer confirmation.
4. **K5307 band width**: 2×22 (Kronospan-partner standard) vs the 2×23 in
   the committed reference bom.csv — one of the two is wrong; resolving it
   also corrects bom.csv.
5. **Screws/staples as stock draws**: konfirmaty, euro screws, HDF staples
   are stock-checked, never per-job PO lines — matches your practice?
6. **Buffer rules**: exact qty on unique Blum SKUs; round-to-pack +1 on
   small fittings; none on bulk stock.
7. **Edging units**: standing 150 mb roll for white; cut-to-length mb for
   job-specific decors — do you already stock any decor rolls?
8. **Blum dealer bundling**: does your dealer's "komplet" SKU include
   runners + rear couplings, or are 770/750/ZB7 separate order lines?
   (Changes the generator's line-item model.)

## Component codes verified vs guessed

VERIFIED: 770M5002S (M NL500), 770C5002S (C NL500 — dealer-confirmed
2026-08-02), 750.5001S (runner), ZB7C000S, ZB7M000S (dealer-confirmed
2026-08-02 as BLUZB7M000S.ATM.R+L, wys. M = 90.5 mm), NM-BD-100-01 (GTV
leg), K5307 = Kronospan Dąb Artisan SN 2800×2070, HDF 3 mm 2800×2070,
150 mb roll standard.
LEARNED 2026-08-02 (dealer listings, owner-supplied): Blum base codes do
NOT encode colour — the base article is geometry only (770C5002S = boki
wys. C 177 mm, NL500) and the colour rides in a suffix. Decoded from the
owner's dealer: `JBM` = jedwabiście biały mat (770C5002S…JBM.R+L, biały),
`CS-M` = czarny carbon (770C5002S Z R+L V1 CS-M), `ATM` = antracyt mat
(ZB7M000S.ATM.R+L). Suffix spelling varies by dealer channel — the
generator therefore models (base_code, colour) as separate attributes
and keeps the dealer's full SKU string as a free column, never parsing
colour back out of it.
STILL OPEN: drawer-box COLOUR (golden assumed jedwabiście biały; the
dealer listings shown were czarny/antracyt — owner decision, see below);
plinth clip producer code; leg style confirmation.
