# E2E D60 — golden design (wk-641a80a8)

> Reader: this file is the INDEPENDENT hand design, written BEFORE the hb5
> build and BEFORE any pipeline run | Enables: measuring the pipeline's
> distance from designer intent | Update-trigger: never — a golden is
> immutable for its run; a new run gets a new golden

Designed 2026-07-13 from first principles (Blum LEGRABOX katalog, shop
standards agreed in L1). Differences from round 1's carpenter reference are
deliberate and listed at the end.

## 1. The cabinet in one paragraph

Szafka dolna D60, trzy szuflady LEGRABOX (M na górze, 2×C niżej), bez blatu,
bez uchwytów (krawędziowy chwyt pod frontem M / TIP-ON decyzja odroczona —
nie wpływa na rozkrój). Korpus biała płyta 18 mm, fronty dekor **K5307**
(inny niż korpus — celowo, ćwiczenie dekorów), plecy HDF 3 mm **we wpustach**,
łączenie **konfirmaty 7×50**, prowadnice LEGRABOX NL500 40 kg. Cokół 100 mm
na nóżkach z klipsami.

## 2. Geometry

| Quantity | Value | Why |
|---|---|---|
| Total height | 820 | 720 carcass + 100 cokół |
| Carcass W×H×D | 600 × 720 × 560 | D60 standard, NL500 fits (interior clear ≥ 547) |
| Side height | 720 | sides run floor-of-carcass to top |
| Internal width (KB) | 564 | 600 − 2×18 |
| Front reveal | 2 mm/side, 3 mm between fronts | shop standard (G12) |
| Fronts (top→bottom) | M 140, C 287, C 287 | 140+287+287+2×3 = 720 exactly |
| HDF groove | 4 wide × 8 deep, near edge 10 mm from rear | in boki + dno + trawers tylny |
| Back panel | 578 × 698 | (600−36+16−2) × (720−36+16−2), luz 2 |

## 3. Part list (panels)

| Lp | Element | Dł×Szer×Gr | szt | Materiał | Usłojenie | Okleina | Uwagi |
|---|---|---|---|---|---|---|---|
| 1 | Bok lewy | 720×560×18 | 1 | PLYTA_BIALA_18 | brak | przód 0.8 | wpust HDF, nawierty |
| 2 | Bok prawy | 720×560×18 | 1 | PLYTA_BIALA_18 | brak | przód 0.8 | lustro lewego |
| 3 | Dno | 564×560×18 | 1 | PLYTA_BIALA_18 | brak | przód 0.8 | wpust HDF |
| 4 | Trawers przedni | 564×100×18 | 1 | PLYTA_BIALA_18 | brak | przód 0.8 | na płask, licowany z górą |
| 5 | Trawers tylny | 564×100×18 | 1 | PLYTA_BIALA_18 | brak | — | na płask, wpust HDF |
| 6 | Plecy | 698×578×3 | 1 | HDF_BIALA_3 | brak | — | w wpust, luz 2 |
| 7 | Front M | 140×596×18 | 1 | K5307_18 | pion | 4× ABS 2.0 K5307 | góra |
| 8 | Front C | 287×596×18 | 2 | K5307_18 | pion | 4× ABS 2.0 K5307 | środek + dół |
| 9 | Szuflada dno | 490×503×16 | 3 | PLYTA_BIALA_16 | brak | — | LEGRABOX NL500 |
| 10 | Szuflada tył M | 63×500×16 | 1 | PLYTA_BIALA_16 | brak | — | |
| 11 | Szuflada tył C | 148×500×16 | 2 | PLYTA_BIALA_16 | brak | — | |
| 12 | Cokół | 97×596×18 | 1 | PLYTA_BIALA_18 | brak | przód 0.8 | klipsy, luz 3 od podłogi |

Board areas (netto): PLYTA_BIALA_18 = 2×0.4032 + 0.3158 + 2×0.0564 +
0.0578 = **1.293 m²** · PLYTA_BIALA_16 = 3×0.2465 + 0.0315 + 2×0.0740 =
**0.919 m²** · K5307_18 = 0.0834 + 2×0.1710 = **0.425 m²** ·
HDF_BIALA_3 = **0.403 m²**.

## 4. Connections (joinery)

- **Konfirmat 7×50, 10 szt**: przez boki — 3/bok w dno (X = 50 / 280 / 510
  od przodu, oś w połowie grubości dna Y=9), 1/bok w każdy trawers
  (X = 50 przedni, X = 510 tylny, oś Y = 711 = 720 − 9).
- **Plecy HDF**: wsunięte we wpusty (boki + dno + trawers tylny), dobite
  zszywkami/wkrętami do trawersu tylnego — brak konfirmatów w plecach.
- **Cokół**: klipsy ×2 do nóżek przednich; nóżki 4× regulowane h=100.

## 5. Drillings (CNC, per bok — inside face; X od przodu, Y od dołu)

| Op | Ø×gł | Pozycje |
|---|---|---|
| Prowadnice LEGRABOX (euro 6.3×13) | 5×12 ślepy | X = 46 / 78 / 110 / 398; Y = 55, 342, 629 (12 otw./bok) |
| Konfirmat do dna | 7 przelot | (50, 9) (280, 9) (510, 9) |
| Konfirmat do trawersów | 7 przelot | (50, 711) (510, 711) |
| Wpust HDF | 4 szer × 8 gł | krawędź 10 od tyłu, pełna wysokość |

Runner rows (bottom-up): zone floors 18 / 305 / 592 → axis Y = floor + 37.
Drawer boxes stack **C dół, C środek, M góra** (fronty od góry: M, C, C).

## 6. Hardware BOM (poza płytą)

| Pozycja | Ilość |
|---|---|
| LEGRABOX kpl. C (boki + prowadnice NL500 40kg) | 2 |
| LEGRABOX kpl. M (boki + prowadnice NL500 40kg) | 1 |
| Konfirmat 7×50 | 10 |
| Nóżka regulowana 100 | 4 |
| Klips cokołowy | 2 |
| Zszywki/wkręty HDF do trawersu | 1 kpl |
| Obrzeże ABS 0.8 biała | 3.16 mb |
| Obrzeże ABS 2.0 K5307 | 5.02 mb |

Edge lm: białe = 720×2 + 564 + 564 + 596 = 3160 mm; K5307 = (596+140)×2 +
2×(596+287)×2 = 1472 + 3532 = 5004 ≈ 5.02 mb (with trim allowance quoted
as cut length — no waste factor in golden).

## 7. Deliberate differences vs round-1 reference & current pipeline

- Front widths **596** (2 mm reveal, shop standard) vs pipeline default 594
  (3 mm margins) — G12, still-open convention knob.
- Golden hardware includes konfirmaty/nóżki/klipsy/zszywki — pipeline BOM is
  known to underquote these (G13, report-only).
- Drawer-box material named **PLYTA_BIALA_16** vs pipeline literal
  `plyta_16mm` — G9, report-only.
- Edge banding identity: golden distinguishes ABS 0.8 white vs ABS 2.0 K5307
  — pipeline emits one derived `abs_<board>` name (G11).
