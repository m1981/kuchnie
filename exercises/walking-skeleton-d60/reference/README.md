# Reference: D60S3 — szafka dolna 600 z trzema szufladami LEGRABOX

> Reader: anyone diffing the pipeline output against ground truth | Enables:
> judging every pipeline line as correct/missing/wrong against a carpenter's
> hand computation | Update-trigger: the exercise's cabinet spec changes

Hand-computed BEFORE running any tool. Every number derived below.

## Cabinet contract

| Parameter | Value |
|---|---|
| Korpus (W×H×D) | 600 × 720 × 560 mm |
| Cokół | 100 mm (nóżki + listwa clip-on) → total 820 |
| Płyta korpus | biała 18 mm (W980-class), obrzeże ABS 0.8×22 biała |
| Płyta fronty | Kronospan **K5307** 18 mm, obrzeże ABS 2×23 K5307 |
| Plecy | HDF 3 mm biała, **wpust 4×8 mm, 10 mm od tylnej krawędzi** |
| Złącza | konfirmat 7×50 (bez kołków — decyzja ćwiczenia) |
| Szuflady | LEGRABOX pure, NL 500, 40 kg, stack **M + C + C** (góra→dół) |
| Fronty | szczelina 3 mm między frontami, 2 mm boczne odsłonięcie |
| Blat | brak (poza zakresem) |
| Uchwyty | brak w spec — luka wymagań, odnotowana w GAP-REPORT |

## Derivations

**Boki** 2× 720 × 560 × 18. Okleina: przednia krawędź.

**Dno** między bokami: 600 − 2×18 = **564** szer. × 560 gł. Okleina przód.

**Trawersy górne** (szafka szufladowa nie ma pełnego wieńca — bez trawersów
korpus się złoży równolegle): 2× 564 × 100 × 18, na płask, przedni licowany
z góry boków, tylny nad wpustem HDF.

**Plecy HDF**: KB 564 + 2×8 (wpust) − 2 (luz) = **578** szer.
Wysokość: 720 − 18 (dno) + 8 (wpust w dnie) − 18 (trawers tylny) + 8 − 2 =
**698**. → 578 × 698 × 3.

**Fronty** (600 − 2×2 = 596 szer.): stack od góry M/C/C →
**140 + 287 + 287** (+ 2×3 szczelin = 720 ✓).

**LEGRABOX** (ADR-006): KB = 564 → LW = 564 − 26 = **538**.
- tył szuflady: 538 − 38 = **500** szer.; wys. M = **63**, C = **148** (Blum)
- dno szuflady: 538 − 35 = **503** szer.; gł. NL − 10 = **490**
- części z płyty białej **16 mm** (standard Blum dla dna/tyłu)
- boki szuflad = metal (akcesorium, nie płyta)

**Cokół**: listwa 596 × 97 × 18 biała, klipsy.

**Nawierty prowadnic** (na 1 bok, lustrzane): wkręt euro → otwór Ø5 gł. 12
od wewnątrz. X od przedniej krawędzi (Blum, NL 500): **46, 78, 110, 398**.
Osie Y od dolnej krawędzi boku (oś prowadnicy ≈ 37 mm nad dnem otworu;
dno korpusu top = 18): S3 (C, dolna) **55** · S2 (C) **342** · S1 (M, górna)
**629**. Wysokości osi wymagają potwierdzenia w Blum planner — oznaczone
jako założenie w GAP-REPORT.

**Konfirmaty Ø7 przelot przez bok** (na 1 bok): do dna Y=9,
X = 50/280/510; do trawersów Y=711, X = 50 (przedni) i 510 (tylny).

## Sumy materiałowe (netto)

| Materiał | m² / mb |
|---|---|
| Płyta biała 18 (boki, dno, trawersy, cokół) | 1.293 m² |
| Płyta biała 16 (dna+tyły szuflad) | 0.919 m² |
| Płyta K5307 18 (fronty) | 0.426 m² |
| HDF 3 biała | 0.403 m² |
| ABS 0.8×22 biała | 2.57 mb |
| ABS 2×23 K5307 | 5.00 mb |
