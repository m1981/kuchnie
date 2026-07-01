# Test Plan — Konfigurator Formatek CNC

> Na podstawie: `analiza_konfiguratora_formatek.md`
> Cel: 100% pokrycie gałęzi decyzyjnych pipeline'a kitchen-cad

---

## Struktura testów

```
tests/
├── unit/                          # Testy jednostkowe (czyste funkcje)
│   ├── test_models.py             # Walidacja modeli
│   ├── test_panel_calculator.py   # Kalkulacja formatek
│   ├── test_drill_engine.py       # Obliczenia nawiertów
│   └── test_edge_banding.py       # Oklejanie krawędzi
│
├── integration/                   # Testy integracyjne (pipeline)
│   ├── test_pipeline.py           # Pełny pipeline
│   ├── test_runner_registry.py    # Rejestr prowadnic
│   └── test_presets.py            # Presety szafek
│
├── e2e/                           # Testy end-to-end (CSV/DXF output)
│   ├── test_csv_output.py         # Walidacja CSV
│   ├── test_dxf_output.py         # Walidacja DXF
│   └── test_full_kitchen.py       # Pełna kuchnia
│
└── conftest.py                    # Fixtures wspólne
```

---

## POZIOM 1: MATERIAŁ I PŁYTA

### TC-1.1: Typy płyt

| ID       | Test                            | Wejście                               | Oczekiwane                  | Priorytet |
| -------- | ------------------------------- | ------------------------------------- | --------------------------- | --------- |
| TC-1.1.1 | Płyta EGGER U702 PMST9 19mm     | `material="U702_PMST9", thickness=19` | Panel utworzony poprawnie   | HIGH      |
| TC-1.1.2 | Płyta Swiss Krono D3821 SW 18mm | `material="D3821_SW", thickness=18`   | Panel utworzony poprawnie   | HIGH      |
| TC-1.1.3 | Płyta MDF 22mm                  | `material="MDF_LAKIER", thickness=22` | Panel z grubością 22mm      | MEDIUM    |
| TC-1.1.4 | Płyta HDF 3mm (plecy)           | `material="HDF_3", thickness=3`       | Panel typu BACK z 3mm       | HIGH      |
| TC-1.1.5 | Nieznany materiał               | `material="XXX_999"`                  | ValidationError lub warning | LOW       |

### TC-1.2: Grubości płyt

| ID       | Test                 | Grubość | Oczekiwane                | Priorytet |
| -------- | -------------------- | ------- | ------------------------- | --------- |
| TC-1.2.1 | Standard 18mm        | 18.0    | `panel.thickness == 18.0` | HIGH      |
| TC-1.2.2 | Gruba 19mm (EGGER)   | 19.0    | `panel.thickness == 19.0` | HIGH      |
| TC-1.2.3 | Cienka 16mm          | 16.0    | `panel.thickness == 16.0` | MEDIUM    |
| TC-1.2.4 | Gruba frontowa 22mm  | 22.0    | `panel.thickness == 22.0` | MEDIUM    |
| TC-1.2.5 | HDF 3mm              | 3.0     | `panel.thickness == 3.0`  | HIGH      |
| TC-1.2.6 | HDF 5mm              | 5.0     | `panel.thickness == 5.0`  | MEDIUM    |
| TC-1.2.7 | Nieprawidłowa 0mm    | 0.0     | ValidationError           | HIGH      |
| TC-1.2.8 | Nieprawidłowa ujemna | -1.0    | ValidationError           | HIGH      |

### TC-1.3: Struktura powierzchni

| ID       | Test                 | Struktura      | Wpływ na obróbkę       | Priorytet |
| -------- | -------------------- | -------------- | ---------------------- | --------- |
| TC-1.3.1 | PM PerfectSense Matt | `surface="PM"` | Delikatniejsza obróbka | MEDIUM    |
| TC-1.3.2 | TM PerfectSense Matt | `surface="TM"` | Standardowa obróbka    | MEDIUM    |

---

## POZIOM 2: DEFINICJA FORMATKI

### TC-2.1: Wymiary formatki

| ID       | Test               | Szer × Wys | Oczekiwane           | Priorytet |
| -------- | ------------------ | ---------- | -------------------- | --------- |
| TC-2.1.1 | Front standardowy  | 596 × 713  | Panel OK             | HIGH      |
| TC-2.1.2 | Front szeroki      | 896 × 713  | Panel OK             | HIGH      |
| TC-2.1.3 | Front wąski        | 296 × 713  | Panel OK             | MEDIUM    |
| TC-2.1.4 | Półka              | 564 × 490  | Panel OK             | MEDIUM    |
| TC-2.1.5 | Bok szafki         | 510 × 720  | Panel OK             | HIGH      |
| TC-2.1.6 | Formatka minimalna | 50 × 50    | Panel OK lub warning | LOW       |
| TC-2.1.7 | Szerokość 0mm      | 0 × 713    | ValidationError      | HIGH      |
| TC-2.1.8 | Wysokość 0mm       | 596 × 0    | ValidationError      | HIGH      |
| TC-2.1.9 | Wymiary ujemne     | -100 × 713 | ValidationError      | HIGH      |

### TC-2.2: Ilość sztuk

| ID       | Test         | Ilość       | Oczekiwane          | Priorytet |
| -------- | ------------ | ----------- | ------------------- | --------- |
| TC-2.2.1 | 1 sztuka     | quantity=1  | 1 panel w wyniku    | HIGH      |
| TC-2.2.2 | 2 sztuki     | quantity=2  | 2 identyczne panele | HIGH      |
| TC-2.2.3 | 10 sztuk     | quantity=10 | 10 paneli           | MEDIUM    |
| TC-2.2.4 | 0 sztuk      | quantity=0  | ValidationError     | HIGH      |
| TC-2.2.5 | Ilość ujemna | quantity=-1 | ValidationError     | HIGH      |

### TC-2.3: Nazwa formatki

| ID       | Test                     | Nazwa       | Oczekiwane                 | Priorytet |
| -------- | ------------------------ | ----------- | -------------------------- | --------- |
| TC-2.3.1 | Nazwa "front"            | "front"     | `panel.id == "front"`      | HIGH      |
| TC-2.3.2 | Nazwa z polskimi znakami | "bok_lewy"  | Panel OK                   | MEDIUM    |
| TC-2.3.3 | Nazwa pusta              | ""          | Warning lub auto-generacja | MEDIUM    |
| TC-2.3.4 | Nazwa z duplikatem       | "front" × 2 | Warning o duplikacie       | LOW       |

---

## POZIOM 3: OKLEJANIE KRAWĘDZI

### TC-3.1: Wybór krawędzi

| ID       | Test                        | Krawędzie         | Oczekiwane          | Priorytet |
| -------- | --------------------------- | ----------------- | ------------------- | --------- |
| TC-3.1.1 | Wszystkie krawędzie         | `edges=[1,2,3,4]` | 4 × EdgeBand        | HIGH      |
| TC-3.1.2 | Tylko front (krawędź 1)     | `edges=[1]`       | 1 × EdgeBand TOP    | HIGH      |
| TC-3.1.3 | Tylko prawo (krawędź 2)     | `edges=[2]`       | 1 × EdgeBand RIGHT  | HIGH      |
| TC-3.1.4 | Tylko dół (krawędź 3)       | `edges=[3]`       | 1 × EdgeBand BOTTOM | HIGH      |
| TC-3.1.5 | Tylko lewo (krawędź 4)      | `edges=[4]`       | 1 × EdgeBand LEFT   | HIGH      |
| TC-3.1.6 | Front + prawo               | `edges=[1,2]`     | 2 × EdgeBand        | MEDIUM    |
| TC-3.1.7 | Brak okleiny                | `edges=[]`        | 0 × EdgeBand        | HIGH      |
| TC-3.1.8 | Krawędzie niewidoczne (3,4) | `edges=[3,4]`     | Cieńsze obrzeże?    | MEDIUM    |

### TC-3.2: Grubość obrzeża

| ID       | Test                             | Grubość              | Oczekiwane  | Priorytet |
| -------- | -------------------------------- | -------------------- | ----------- | --------- |
| TC-3.2.1 | ABS 1.0mm (klejenie bezspoinowe) | `edge_thickness=1.0` | EdgeBand OK | HIGH      |
| TC-3.2.2 | ABS 1.0mm (standardowe)          | `edge_thickness=1.0` | EdgeBand OK | HIGH      |
| TC-3.2.3 | ABS 2.0mm (fronty)               | `edge_thickness=2.0` | EdgeBand OK | MEDIUM    |
| TC-3.2.4 | PCV 0.4mm (niewidoczne)          | `edge_thickness=0.4` | EdgeBand OK | MEDIUM    |
| TC-3.2.5 | Fornir 0.6mm                     | `edge_thickness=0.6` | EdgeBand OK | LOW       |

### TC-3.3: Kolor obrzeża

| ID       | Test                | Kolor               | Oczekiwane               | Priorytet |
| -------- | ------------------- | ------------------- | ------------------------ | --------- |
| TC-3.3.1 | Match do płyty U702 | `edge_color="U702"` | EdgeBand.color == "U702" | HIGH      |
| TC-3.3.2 | Inny kolor          | `edge_color="U164"` | EdgeBand.color == "U164" | MEDIUM    |
| TC-3.3.3 | Brak koloru         | `edge_color=""`     | Warning lub default      | LOW       |

### TC-3.4: Dostępność magazynowa

| ID       | Test              | Dostępność       | Oczekiwane            | Priorytet |
| -------- | ----------------- | ---------------- | --------------------- | --------- |
| TC-3.4.1 | Na magazynie      | `in_stock=True`  | Brak ostrzeżenia      | HIGH      |
| TC-3.4.2 | Brak na magazynie | `in_stock=False` | Warning o dostępności | MEDIUM    |

---

## POZIOM 4: SZABLONY NAWIERTÓW (8 WARIANTÓW)

### TC-4.1: Szablon 1 — Formatka bez nawiertów

| ID       | Test                     | Szablon                            | Oczekiwane                 | Priorytet |
| -------- | ------------------------ | ---------------------------------- | -------------------------- | --------- |
| TC-4.1.1 | Brak nawiertów           | `template="none"`                  | `panel.drill_points == []` | HIGH      |
| TC-4.1.2 | Brak nawiertów + okleina | `template="none", edges=[1,2,3,4]` | 0 drill_points, 4 edges    | HIGH      |

### TC-4.2: Szablon 2 — Wręgowanie i nawierty ⭐

| ID       | Test                     | Parametry                            | Oczekiwane               | Priorytet |
| -------- | ------------------------ | ------------------------------------ | ------------------------ | --------- |
| TC-4.2.1 | Wręgowanie standardowe   | `groove_depth=9, groove_width=3.2`   | Rowek 3.2×9mm            | HIGH      |
| TC-4.2.2 | Wręgowanie HDF 3mm       | `groove_width=3.2, back_thickness=3` | Rowek dopasowany         | HIGH      |
| TC-4.2.3 | Wręgowanie przelotowe    | `groove_type="through"`              | Rowek przez całą długość | HIGH      |
| TC-4.2.4 | Wręgowanie nieprzelotowe | `groove_type="non_through"`          | Rowek z zatrzymaniem     | MEDIUM    |
| TC-4.2.5 | Wręgowanie + nawierty    | `template="groove_drill"`            | Rowek + otwory ∅5mm      | HIGH      |

### TC-4.3: Szablon 3 — Front lewy

| ID       | Test                   | Parametry                        | Oczekiwane        | Priorytet |
| -------- | ---------------------- | -------------------------------- | ----------------- | --------- |
| TC-4.3.1 | Front lewy 2 zawiasy   | `template="left", hinges=2`      | 2× ∅35mm + uchwyt | HIGH      |
| TC-4.3.2 | Front lewy 3 zawiasy   | `template="left", hinges=3`      | 3× ∅35mm + uchwyt | HIGH      |
| TC-4.3.3 | Front lewy bez uchwytu | `template="left", handle="none"` | Tylko zawiasy     | MEDIUM    |

### TC-4.4: Szablon 4 — Front prawy

| ID       | Test                        | Parametry                    | Oczekiwane              | Priorytet |
| -------- | --------------------------- | ---------------------------- | ----------------------- | --------- |
| TC-4.4.1 | Front prawy 2 zawiasy       | `template="right", hinges=2` | 2× ∅35mm (prawa strona) | HIGH      |
| TC-4.4.2 | Front prawy = mirror lewego | Porównanie z TC-4.3.1        | Lustrzane odbicie       | HIGH      |

### TC-4.5: Szablon 5 — Front uchylny (typ 1)

| ID       | Test         | Parametry                | Oczekiwane             | Priorytet |
| -------- | ------------ | ------------------------ | ---------------------- | --------- |
| TC-4.5.1 | Uchylny góra | `template="flip_top"`    | Zawiasy u góry korpusu | MEDIUM    |
| TC-4.5.2 | Uchylny dół  | `template="flip_bottom"` | Zawiasy u dołu korpusu | MEDIUM    |

### TC-4.6: Szablon 6 — Front uchylny (typ 2)

| ID       | Test              | Parametry            | Oczekiwane                  | Priorytet |
| -------- | ----------------- | -------------------- | --------------------------- | --------- |
| TC-4.6.1 | Wariant 2 uchylny | `template="flip_v2"` | Alternatywny układ zawiasów | LOW       |

### TC-4.7: Szablon 7 — Front szuflady

| ID       | Test               | Parametry                               | Oczekiwane            | Priorytet |
| -------- | ------------------ | --------------------------------------- | --------------------- | --------- |
| TC-4.7.1 | Szuflada LEGRABOX  | `template="drawer", runner="LEGRABOX"`  | Otwory pod prowadnice | HIGH      |
| TC-4.7.2 | Szuflada METABOX   | `template="drawer", runner="METABOX"`   | Inne pozycje otworów  | MEDIUM    |
| TC-4.7.3 | Szuflada TANDEMBOX | `template="drawer", runner="TANDEMBOX"` | Inne pozycje otworów  | MEDIUM    |

### TC-4.8: Szablon 8 — Frezowanie Aluprofil ⭐

| ID       | Test                 | Parametry              | Oczekiwane                 | Priorytet |
| -------- | -------------------- | ---------------------- | -------------------------- | --------- |
| TC-4.8.1 | Frezowanie pod wózki | `template="aluprofil"` | Frezowanie wg specyfikacji | LOW       |

---

## POZIOM 5: KONFIGURACJA ZAWIASÓW

### TC-5.1: Typ zawiasu

| ID       | Test                      | Producent | Średnica | Oczekiwane        | Priorytet |
| -------- | ------------------------- | --------- | -------- | ----------------- | --------- |
| TC-5.1.1 | Blum puszka 35mm (wkręty) | Blum      | ∅35mm    | Otwory ∅35 + ∅3mm | HIGH      |
| TC-5.1.2 | Blum puszka 35mm (kołek)  | Blum      | ∅35mm    | Otwory ∅35 + ∅8mm | HIGH      |
| TC-5.1.3 | Hettich                   | Hettich   | ∅35mm    | Rozstaw 52mm      | MEDIUM    |
| TC-5.1.4 | Salice                    | Salice    | ∅35mm    | Inny rozstaw śrub | MEDIUM    |
| TC-5.1.5 | GTV                       | GTV       | ∅35mm    | Inny rozstaw śrub | LOW       |

### TC-5.2: Ilość zawiasów (zależność od wysokości)

| ID       | Test              | Wysokość frontu | Oczekiwana ilość | Priorytet |
| -------- | ----------------- | --------------- | ---------------- | --------- |
| TC-5.2.1 | ≤ 500mm           | 400mm           | 2 zawiasy        | HIGH      |
| TC-5.2.2 | 500mm (graniczna) | 500mm           | 2 zawiasy        | HIGH      |
| TC-5.2.3 | 501mm             | 501mm           | 3 zawiasy        | HIGH      |
| TC-5.2.4 | 900mm (graniczna) | 900mm           | 3 zawiasy        | HIGH      |
| TC-5.2.5 | 901mm             | 901mm           | 4 zawiasy        | HIGH      |
| TC-5.2.6 | Duży front        | 1500mm          | 4 zawiasy        | MEDIUM    |

### TC-5.3: Pozycja pierwszego zawiasu

| ID       | Test                 | Parametr             | Oczekiwane                    | Priorytet |
| -------- | -------------------- | -------------------- | ----------------------------- | --------- |
| TC-5.3.1 | Domyślna 100mm       | `first_position=100` | Pierwszy zawias 100mm od góry | HIGH      |
| TC-5.3.2 | Niestandardowa 80mm  | `first_position=80`  | Pierwszy zawias 80mm od góry  | MEDIUM    |
| TC-5.3.3 | Niestandardowa 120mm | `first_position=120` | Pierwszy zawias 120mm od góry | MEDIUM    |

### TC-5.4: Rozmieszczenie zawiasów

| ID       | Test              | Wysokość | Ilość | Oczekiwane rozmieszczenie   | Priorytet |
| -------- | ----------------- | -------- | ----- | --------------------------- | --------- |
| TC-5.4.1 | 713mm, 2 zawiasy  | 713      | 2     | 100mm, 613mm (symetrycznie) | HIGH      |
| TC-5.4.2 | 713mm, 3 zawiasy  | 713      | 3     | 100mm, 356.5mm, 613mm       | HIGH      |
| TC-5.4.3 | 1000mm, 3 zawiasy | 1000     | 3     | 100mm, 500mm, 900mm         | MEDIUM    |

---

## POZIOM 6: KONFIGURACJA UCHWYTU

### TC-6.1: Typ uchwytu

| ID       | Test                | Typ                      | Oczekiwane          | Priorytet |
| -------- | ------------------- | ------------------------ | ------------------- | --------- |
| TC-6.1.1 | Brak uchwytu        | `handle_type="none"`     | 0 otworów na uchwyt | HIGH      |
| TC-6.1.2 | Typowe (2 nawierty) | `handle_type="standard"` | 2× ∅5mm             | HIGH      |
| TC-6.1.3 | Gałka (1 nawiert)   | `handle_type="knob"`     | 1× ∅5mm             | HIGH      |

### TC-6.2: Pozycja uchwytu

| ID       | Test      | x_ref                    | y_ref | Oczekiwane                 | Priorytet |
| -------- | --------- | ------------------------ | ----- | -------------------------- | --------- |
| TC-6.2.1 | Od góry   | `y_from="top", y=100`    | —     | Otwór 100mm od góry        | HIGH      |
| TC-6.2.2 | Od dołu   | `y_from="bottom", y=100` | —     | Otwór 100mm od dołu        | HIGH      |
| TC-6.2.3 | Od prawej | `x_from="right", x=546`  | —     | Otwór 546mm od prawej      | HIGH      |
| TC-6.2.4 | Od lewej  | `x_from="left", x=50`    | —     | Otwór 50mm od lewej        | MEDIUM    |
| TC-6.2.5 | Środek X  | `x_from="center"`        | —     | Otwór na środku szerokości | MEDIUM    |
| TC-6.2.6 | Środek Y  | `y_from="center"`        | —     | Otwór na środku wysokości  | MEDIUM    |

### TC-6.3: Orientacja uchwytu

| ID       | Test    | Orientacja                 | Oczekiwane     | Priorytet |
| -------- | ------- | -------------------------- | -------------- | --------- |
| TC-6.3.1 | Poziomy | `orientation="horizontal"` | Otwory w osi X | HIGH      |
| TC-6.3.2 | Pionowy | `orientation="vertical"`   | Otwory w osi Y | HIGH      |

### TC-6.4: Rozstaw nawiertów uchwytu

| ID       | Test              | Rozstaw       | Oczekiwane                | Priorytet |
| -------- | ----------------- | ------------- | ------------------------- | --------- |
| TC-6.4.1 | Rozstaw 128mm     | `spacing=128` | 2 otwory 128mm od siebie  | HIGH      |
| TC-6.4.2 | Rozstaw 160mm     | `spacing=160` | 2 otwory 160mm od siebie  | HIGH      |
| TC-6.4.3 | Rozstaw 256mm     | `spacing=256` | 2 otwory 256mm od siebie  | MEDIUM    |
| TC-6.4.4 | Rozstaw 320mm     | `spacing=320` | 2 otwory 320mm od siebie  | MEDIUM    |
| TC-6.4.5 | Rozstaw 0 (gałka) | `spacing=0`   | 1 otwór (ignoruj spacing) | HIGH      |

---

## POZIOM 7: WRĘGOWANIE (ROWKI)

### TC-7.1: Parametry wręgowania

| ID       | Test               | Głębokość | Szerokość | Oczekiwane     | Priorytet |
| -------- | ------------------ | --------- | --------- | -------------- | --------- |
| TC-7.1.1 | Standard 9mm/3.2mm | 9         | 3.2       | Rowek 3.2×9mm  | HIGH      |
| TC-7.1.2 | Płytki 6mm         | 6         | 3.2       | Rowek 3.2×6mm  | MEDIUM    |
| TC-7.1.3 | Głęboki 12mm       | 12        | 4.0       | Rowek 4.0×12mm | MEDIUM    |
| TC-7.1.4 | Wąski 2.8mm        | 9         | 2.8       | Rowek 2.8×9mm  | LOW       |
| TC-7.1.5 | Brak wręgowania    | —         | —         | Brak rowka     | HIGH      |

### TC-7.2: Typ wręgowania

| ID       | Test          | Typ                         | Oczekiwane              | Priorytet |
| -------- | ------------- | --------------------------- | ----------------------- | --------- |
| TC-7.2.1 | Przelotowe    | `groove_type="through"`     | Rowek na całą szerokość | HIGH      |
| TC-7.2.2 | Nieprzelotowe | `groove_type="non_through"` | Rowek z zatrzymaniem    | MEDIUM    |

### TC-7.3: Krawędź wręgowania

| ID       | Test                   | Krawędź         | Oczekiwane              | Priorytet |
| -------- | ---------------------- | --------------- | ----------------------- | --------- |
| TC-7.3.1 | Krawędź 3 (dół) — bok  | `groove_edge=3` | Rowek na dole boku      | HIGH      |
| TC-7.3.2 | Krawędź 1 (góra) — dno | `groove_edge=1` | Rowek na górze dna      | HIGH      |
| TC-7.3.3 | Krawędź 2 (prawo)      | `groove_edge=2` | Rowek na prawej stronie | MEDIUM    |
| TC-7.3.4 | Krawędź 4 (lewo)       | `groove_edge=4` | Rowek na lewej stronie  | MEDIUM    |

### TC-7.4: Odległość od krawędzi

| ID       | Test            | Odległość          | Oczekiwane             | Priorytet |
| -------- | --------------- | ------------------ | ---------------------- | --------- |
| TC-7.4.1 | Standardowa 8mm | `groove_offset=8`  | Rowek 8mm od krawędzi  | HIGH      |
| TC-7.4.2 | Głęboka 10mm    | `groove_offset=10` | Rowek 10mm od krawędzi | MEDIUM    |
| TC-7.4.3 | Płytki 5mm      | `groove_offset=5`  | Rowek 5mm od krawędzi  | MEDIUM    |

---

## POZIOM 8: WIERCENIE W PŁASZCZYŹNIE

### TC-8.1: Średnice nawiertów

| ID       | Test             | Średnica | Oczekiwane  | Priorytet |
| -------- | ---------------- | -------- | ----------- | --------- |
| TC-8.1.1 | ∅5mm (System 32) | 5.0      | Otwór ∅5mm  | HIGH      |
| TC-8.1.2 | ∅8mm (kołek)     | 8.0      | Otwór ∅8mm  | HIGH      |
| TC-8.1.3 | ∅10mm            | 10.0     | Otwór ∅10mm | MEDIUM    |
| TC-8.1.4 | ∅15mm (minifix)  | 15.0     | Otwór ∅15mm | HIGH      |
| TC-8.1.5 | ∅20mm            | 20.0     | Otwór ∅20mm | MEDIUM    |
| TC-8.1.6 | ∅25mm            | 25.0     | Otwór ∅25mm | LOW       |
| TC-8.1.7 | ∅35mm (zawias)   | 35.0     | Otwór ∅35mm | HIGH      |

### TC-8.2: Głębokości nawiertów

| ID       | Test                 | Głębokość         | Oczekiwane           | Priorytet |
| -------- | -------------------- | ----------------- | -------------------- | --------- |
| TC-8.2.1 | 5mm                  | 5                 | Otwór głęboki 5mm    | MEDIUM    |
| TC-8.2.2 | 8mm                  | 8                 | Otwór głęboki 8mm    | MEDIUM    |
| TC-8.2.3 | 10mm                 | 10                | Otwór głęboki 10mm   | HIGH      |
| TC-8.2.4 | 12mm (minifix)       | 12                | Otwór głęboki 12mm   | HIGH      |
| TC-8.2.5 | 13.5mm (zawias Blum) | 13.5              | Otwór głęboki 13.5mm | HIGH      |
| TC-8.2.6 | 15mm                 | 15                | Otwór głęboki 15mm   | MEDIUM    |
| TC-8.2.7 | 20mm                 | 20                | Otwór głęboki 20mm   | MEDIUM    |
| TC-8.2.8 | Przelotowy           | `depth="through"` | Otwór na wylot       | HIGH      |

### TC-8.3: Typ nawiertu

| ID       | Test        | Typ                        | Oczekiwane          | Priorytet |
| -------- | ----------- | -------------------------- | ------------------- | --------- |
| TC-8.3.1 | Pojedynczy  | `drill_type="single"`      | 1 otwór             | HIGH      |
| TC-8.3.2 | Wielowiert  | `drill_type="multi_step"`  | Otwór + pogłębienie | HIGH      |
| TC-8.3.3 | Pogłębienie | `drill_type="counterbore"` | Tylko pogłębienie   | MEDIUM    |

### TC-8.4: Grupy nawiertów

| ID       | Test                | Ilość | Odległość | Kierunek | Oczekiwane      | Priorytet |
| -------- | ------------------- | ----- | --------- | -------- | --------------- | --------- |
| TC-8.4.1 | 1 otwór             | 1     | —         | —        | 1× ∅mm          | HIGH      |
| TC-8.4.2 | 2 otwory X          | 2     | 20mm      | X        | 2× ∅mm w osi X  | HIGH      |
| TC-8.4.3 | 3 otwory Y          | 3     | 32mm      | Y        | 3× ∅mm w osi Y  | MEDIUM    |
| TC-8.4.4 | 5 otworów System 32 | 5     | 32mm      | Y        | 5× ∅5mm co 32mm | HIGH      |

### TC-8.5: Współrzędne

| ID       | Test               | X   | Y   | Oczekiwane            | Priorytet |
| -------- | ------------------ | --- | --- | --------------------- | --------- |
| TC-8.5.1 | Lewy dolny róg     | 10  | 10  | Otwór na (10,10)      | HIGH      |
| TC-8.5.2 | Środek             | 298 | 356 | Otwór na środku       | MEDIUM    |
| TC-8.5.3 | Prawy górny róg    | 586 | 703 | Otwór blisko krawędzi | MEDIUM    |
| TC-8.5.4 | Poza formatką X    | 600 | 356 | ValidationError       | HIGH      |
| TC-8.5.5 | Poza formatką Y    | 298 | 750 | ValidationError       | HIGH      |
| TC-8.5.6 | Współrzędne ujemne | -10 | 356 | ValidationError       | HIGH      |

---

## POZIOM 9: WIERCENIE W CZOLE (BOKU)

### TC-9.1: Parametry nawiertu w boku

| ID       | Test              | Krawędź | Odległość | Średnica | Głębokość | Oczekiwane          | Priorytet |
| -------- | ----------------- | ------- | --------- | -------- | --------- | ------------------- | --------- |
| TC-9.1.1 | Krawędź 2 (prawo) | 2       | 50mm      | 8mm      | 20mm      | Otwór w prawym boku | HIGH      |
| TC-9.1.2 | Krawędź 4 (lewo)  | 4       | 50mm      | 8mm      | 20mm      | Otwór w lewym boku  | HIGH      |
| TC-9.1.3 | Krawędź 1 (góra)  | 1       | 100mm     | 5mm      | 15mm      | Otwór w górnym boku | MEDIUM    |
| TC-9.1.4 | Krawędź 3 (dół)   | 3       | 100mm     | 5mm      | 15mm      | Otwór w dolnym boku | MEDIUM    |

### TC-9.2: Pozycja w grubości płyty

| ID       | Test       | Grubość płyty | Oczekiwana pozycja      | Priorytet |
| -------- | ---------- | ------------- | ----------------------- | --------- |
| TC-9.2.1 | Płyta 18mm | 18            | Otwór na środku (9mm)   | HIGH      |
| TC-9.2.2 | Płyta 19mm | 19            | Otwór na środku (9.5mm) | HIGH      |
| TC-9.2.3 | Płyta 22mm | 22            | Otwór na środku (11mm)  | MEDIUM    |

---

## POZIOM 10: ODBICIE LUSTROWE

### TC-10.1: Odbicie X (w pionie)

| ID        | Test               | Oryginał             | Odbicie         | Oczekiwane              | Priorytet |
| --------- | ------------------ | -------------------- | --------------- | ----------------------- | --------- |
| TC-10.1.1 | Front lewy → prawy | `left_front`         | `mirror_x=True` | Zawiasy po prawej       | HIGH      |
| TC-10.1.2 | Odbicie nawiertów  | DrillPoint(100, 356) | `mirror_x=True` | DrillPoint(496, 356)    | HIGH      |
| TC-10.1.3 | Odbicie obrzeży    | EdgeBand(TOP)        | `mirror_x=True` | EdgeBand(TOP) unchanged | MEDIUM    |

### TC-10.2: Odbicie Y (w poziomie)

| ID        | Test                    | Oryginał             | Odbicie         | Oczekiwane           | Priorytet |
| --------- | ----------------------- | -------------------- | --------------- | -------------------- | --------- |
| TC-10.2.1 | Front → front odwrócony | `front`              | `mirror_y=True` | Zawiasy na dole      | MEDIUM    |
| TC-10.2.2 | Odbicie nawiertów       | DrillPoint(298, 100) | `mirror_y=True` | DrillPoint(298, 613) | MEDIUM    |

---

## POZIOM 11: ZARZĄDZANIE FORMATKAMI

### TC-11.1: Kopiowanie

| ID        | Test                   | Akcja                    | Oczekiwane                              | Priorytet |
| --------- | ---------------------- | ------------------------ | --------------------------------------- | --------- |
| TC-11.1.1 | Kopiuj ostatnią        | `copy_last()`            | Nowa formatka z tymi samymi parametrami | HIGH      |
| TC-11.1.2 | Kopiuj + zmień wymiary | `copy_last(), width=400` | Nowa formatka 400mm                     | MEDIUM    |

### TC-11.2: Import CSV

| ID        | Test              | Akcja                             | Oczekiwane             | Priorytet |
| --------- | ----------------- | --------------------------------- | ---------------------- | --------- |
| TC-11.2.1 | Import z PRO100   | `import_csv("pro100.csv")`        | Formatki zaimportowane | HIGH      |
| TC-11.2.2 | Dodaj do listy    | `import_csv(..., mode="add")`     | Nowe + istniejące      | HIGH      |
| TC-11.2.3 | Zastąp listę      | `import_csv(..., mode="replace")` | Tylko nowe             | HIGH      |
| TC-11.2.4 | Pusty CSV         | `import_csv("empty.csv")`         | Warning                | MEDIUM    |
| TC-11.2.5 | Nieprawidłowy CSV | `import_csv("bad.csv")`           | ValidationError        | HIGH      |

---

## POZIOM 12: PIPELINE — PEŁNA ŚCIEŻKA

### TC-12.1: Szafka dolna z drzwiami

| ID        | Test            | Konfiguracja                             | Oczekiwane                         | Priorytet |
| --------- | --------------- | ---------------------------------------- | ---------------------------------- | --------- |
| TC-12.1.1 | D60 z drzwiami  | `base_door_600, 2 zawiasy, uchwyt`       | 6 formatek, CSV OK                 | HIGH      |
| TC-12.1.2 | D80 z drzwiami  | `base_door_800, 3 zawiasy, uchwyt`       | 6 formatek, CSV OK                 | HIGH      |
| TC-12.1.3 | D60 bez uchwytu | `base_door_600, 2 zawiasy, brak uchwytu` | 6 formatek, brak otworów na uchwyt | MEDIUM    |

### TC-12.2: Szafka dolna z szufladami

| ID        | Test           | Konfiguracja               | Oczekiwane                  | Priorytet |
| --------- | -------------- | -------------------------- | --------------------------- | --------- |
| TC-12.2.1 | D60 2 szuflady | `base_drawer_600, [N,M]`   | 8 formatek, CSV OK          | HIGH      |
| TC-12.2.2 | D60 3 szuflady | `base_drawer_600, [N,M,K]` | 10 formatek, CSV OK         | HIGH      |
| TC-12.2.3 | D60 LEGRABOX   | `runner="LEGRABOX"`        | Otwory wg specyfikacji Blum | HIGH      |

### TC-12.3: Szafka górna

| ID        | Test           | Konfiguracja               | Oczekiwane         | Priorytet |
| --------- | -------------- | -------------------------- | ------------------ | --------- |
| TC-12.3.1 | G60 z drzwiami | `wall_door_600, 2 zawiasy` | 6 formatek, CSV OK | HIGH      |
| TC-12.3.2 | G80 z drzwiami | `wall_door_800, 2 zawiasy` | 6 formatek, CSV OK | HIGH      |

### TC-12.4: Szafka narożna

| ID        | Test        | Konfiguracja            | Oczekiwane                 | Priorytet |
| --------- | ----------- | ----------------------- | -------------------------- | --------- |
| TC-12.4.1 | Narożna 900 | `corner_900, 3 zawiasy` | Specjalne formatki, CSV OK | MEDIUM    |

### TC-12.5: Słupek

| ID        | Test            | Konfiguracja          | Oczekiwane               | Priorytet |
| --------- | --------------- | --------------------- | ------------------------ | --------- |
| TC-12.5.1 | Słupek 600×2000 | `tall_600, 4 zawiasy` | Wysokie formatki, CSV OK | MEDIUM    |

---

## POZIOM 13: WALIDACJA GEOMETRYCZNA

### TC-13.1: Sprawdzenia

| ID        | Test                     | Warunek                                | Oczekiwane | Priorytet |
| --------- | ------------------------ | -------------------------------------- | ---------- | --------- |
| TC-13.1.1 | Otwór poza X             | `drill.x > panel.width`                | ERROR      | HIGH      |
| TC-13.1.2 | Otwór poza Y             | `drill.y > panel.height`               | ERROR      | HIGH      |
| TC-13.1.3 | Otwór ujemny X           | `drill.x < 0`                          | ERROR      | HIGH      |
| TC-13.1.4 | Otwór ujemny Y           | `drill.y < 0`                          | ERROR      | HIGH      |
| TC-13.1.5 | Otwory za blisko         | `distance < 5mm`                       | WARNING    | MEDIUM    |
| TC-13.1.6 | Otwór za blisko krawędzi | `edge_distance < 3mm`                  | WARNING    | MEDIUM    |
| TC-13.1.7 | Głębokość > grubość      | `depth > thickness`                    | ERROR      | HIGH      |
| TC-13.1.8 | Wręg poza formatką       | `groove_offset + groove_depth > width` | ERROR      | HIGH      |

---

## POZIOM 14: TOLERANCJE

### TC-14.1: Tolerancje CNC

| ID        | Test              | Operacja | Tolerancja               | Priorytet |
| --------- | ----------------- | -------- | ------------------------ | --------- |
| TC-14.1.1 | Nawiercanie ∅35mm | ±0.1mm   | Sprawdź precyzję pozycji | HIGH      |
| TC-14.1.2 | Wręgowanie        | ±0.2mm   | Sprawdź precyzję rowka   | HIGH      |
| TC-14.1.3 | Oklejanie         | ±0.1mm   | Sprawdź dokładność styku | MEDIUM    |
| TC-14.1.4 | Cięcie formatki   | ±0.5mm   | Sprawdź wymiary          | HIGH      |

---

## Macierz pokrycia testów

```
Poziom 1 (Materiał)       ████████████ 13 testów
Poziom 2 (Formatka)       ██████████████ 14 testów
Poziom 3 (Oklejanie)      ██████████████ 14 testów
Poziom 4 (Szablony)       ████████████████████████ 24 testów
Poziom 5 (Zawiasy)        ████████████████ 16 testów
Poziom 6 (Uchwyt)         ██████████████████ 18 testów
Poziom 7 (Wręgowanie)     ██████████████ 14 testów
Poziom 8 (Wiercenie pł.)  ████████████████████ 20 testów
Poziom 9 (Wiercenie bok)  ████████ 8 testów
Poziom 10 (Odbicie)       ██████ 6 testów
Poziom 11 (Zarządzanie)   ████████ 8 testów
Poziom 12 (Pipeline)      ██████████████ 14 testów
Poziom 13 (Walidacja)     ████████ 8 testów
Poziom 14 (Tolerancje)    ████ 4 testów
─────────────────────────────────────────
RAZEM:                     ~181 testów
```

---

## Priorytety implementacji

### Faza 1 — KRYTYCZNE (HIGH)

- TC-1.1, TC-1.2: Materiały i grubości
- TC-2.1, TC-2.2: Wymiary i ilości
- TC-3.1: Oklejanie krawędzi
- TC-4.1, TC-4.3, TC-4.4, TC-4.7: Szablony nawiertów
- TC-5.1, TC-5.2: Zawiasy
- TC-6.1, TC-6.2: Uchwyty
- TC-8.1, TC-8.2: Nawiercanie płaskie
- TC-12.1, TC-12.2: Pipeline szafek

### Faza 2 — WAŻNE (MEDIUM)

- TC-4.2, TC-4.5: Wręgowanie i fronty uchylne
- TC-5.3, TC-5.4: Pozycje zawiasów
- TC-7.x: Wręgowanie pełne
- TC-9.x: Wiercenie w boku
- TC-10.x: Odbicie lustrzane
- TC-13.x: Walidacja

### Faza 3 — OPCJONALNE (LOW)

- TC-4.8: Frezowanie Aluprofil
- TC-5.1.4, TC-5.1.5: Salice, GTV
- TC-14.x: Tolerancje

---

_Ostatnia aktualizacja: 2026-06-17_
_Wersja: 1.0_
