# kitchen-cam — dokumentacja projektowa

> **Wersja:** 2.0
> **Data:** 2026-06-23
> **Status:** Phase 1 + Phase 2 features completed

---

> **Note:** Run `make test` to verify all tests pass. Run `make coverage` for current coverage report.

---

## Spis treści

1. [Cel projektu](#1-cel-projektu)
2. [Architektura](#2-architektura)
3. [Standardy technologiczne](#3-standardy-technologiczne)
4. [Modele danych (Pydantic)](#4-modele-danych-pydantic)
5. [Kalkulator formatek](#5-kalkulator-formatek)
6. [Silnik nawiertów](#6-silnik-nawiertów)
7. [Generatory CSV](#7-generatory-csv)
8. [Narzędzia porównawcze](#8-narzędzia-porównawcze)
9. [Strategia testów](#9-strategia-testów)
10. [Roadmapa](#10-roadmapa)

---

## 1. Cel projektu

Parametryczny system do projektowania mebli skrzyniowych, który z definicji
korpusu (YAML/Python) generuje:

- **CSV cięcie** — lista formatek do centrum CNC
- **CSV oklejanie** — lista krawędzi do okleiniarki
- **DXF nawierty** — plik z pozycjami otworów (Faza 2)

### Użytkownik docelowy

Stolarz/projektant kuchni na wymiar, który:

- projektuje w programie CAD (Corpus, PRO100)
- zleca cięcie i nawiercanie do centrum CNC
- montuje meble u klienta

### Workflow

```
Pomiar pomieszczenia
       │
       ▼
Projekt w Corpus CAD
       │
       ▼
Definicja korpusu (YAML)  ──► kitchen-cad ──► CSV cięcie
       │                         │         ──► CSV oklejanie
       │                         │         ──► DXF nawierty (Faza 2)
       │                         │
       ▼                         ▼
Walidacja z reference files   Wysyłka do CNC
```

---

## 2. Architektura

> **For detailed architecture diagrams and component descriptions, see [architecture.md](architecture.md).**

### Quick Overview

```
kitchen-cad/
├── src/kitchen_cad/          # Core library
│   ├── models.py             # Pydantic models
│   ├── panel_calculator.py   # Panel dimensions
│   ├── drill_engine.py       # Drill positions
│   └── csv_generator.py      # CSV output
│
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
│
└── output/                   # Generated files
```

### Pipeline Overview

```python
spec = CorpusSpec(...)                      # 1. Define corpus
panels = calculate_panels(spec)             # 2. Calculate panels
panels = apply_all_drilling(panels, spec)   # 3. Add drill points
generate_cutting_csv(panels, path)          # 4. CSV cutting list
generate_edging_csv(panels, path)           # 5. CSV edge banding
```

> Run `make test` to verify all tests pass.

---

## 3. Standardy technologiczne

### 3.1 System 32

Europejski standard rozmieszczenia otworów w meblach skrzyniowych.

| Parametr                        | Wartość   | Opis                              |
| ------------------------------- | --------- | --------------------------------- |
| Rozstaw pionowy                 | **32 mm** | Otwory co 32mm (i wielokrotności) |
| Odległość od krawędzi przedniej | **37 mm** | Pierwszy rząd pionowy             |
| Odległość od krawędzi tylnej    | **37 mm** | Tylny rząd pionowy                |
| Średnica otworu                 | **∅5 mm** | Standardowy otwór montażowy       |
| Głębokość                       | **13 mm** | Typowo (nieprzelotowy)            |

#### Algorytm obliczania pozycji Y

```
Dla panelu o wysokości H:
  pierwszy_otwór = 37 mm od dołu
  ostatni_otwór  = H - 37 mm od dołu
  rozstaw        = 32 mm

  Pozycje: 37, 69, 101, 133, ..., (H - 37)
```

#### Przykłady

| Wysokość panelu | Ilość otworów | Pierwszy | Ostatni |
| --------------- | ------------- | -------- | ------- |
| 720 mm          | 21            | 37       | 677     |
| 560 mm          | 16            | 37       | 517     |
| 200 mm          | 5             | 37       | 165     |

### 3.2 Zawiasy puszkowe ∅35 mm

Standard europejski — kompatybilny z Blum, Hettich, Grass, Häfele.

| Parametr              | Blum CLIP top | Hettich Sensys |
| --------------------- | ------------- | -------------- |
| Średnica puszki       | **∅35 mm**    | **∅35 mm**     |
| Głębokość puszki      | **13 mm**     | **13 mm**      |
| Rozstaw śrub          | **45 mm**     | **52 mm**      |
| Odległość od krawędzi | **5 mm**      | **4 mm**       |
| Średnica śrub         | **∅3 mm**     | **∅3 mm**      |
| Głębokość śrub        | **2 mm**      | **2 mm**       |

#### Rozmieszczenie na froncie

```
Front panel (widok od strony wewnętrznej):

    ┌──────────────────────────────────────────────┐
    │                                              │
    │  ←5mm→                                      │
    │  ┌──┐                                        │
    │  │○ │ ← ∅35mm (puszka)     Y = 100mm od góry│
    │  │  │                                        │
    │  │● │ ← ∅3mm (śruba)       Y + 22.5mm       │
    │  │  │                                        │
    │  │● │ ← ∅3mm (śruba)       Y - 22.5mm       │
    │  └──┘                                        │
    │                                              │
    │         ...                                  │
    │                                              │
    │  ┌──┐                                        │
    │  │○ │ ← drugi zawias       Y = 100mm od dołu│
    │  └──┘                                        │
    │                                              │
    └──────────────────────────────────────────────┘
```

#### Rozmieszczenie zawiasów

| Ilość zawiasów | Pozycje (od dołu frontu)              |
| -------------- | ------------------------------------- |
| 1              | H/2 (środek)                          |
| 2              | 100mm, H - 100mm                      |
| 3              | 100mm, H/2, H - 100mm                 |
| N              | równomiernie między 100mm a H - 100mm |

### 3.3 Uchwyty relingowe

| Parametr        | Wartość                                                  |
| --------------- | -------------------------------------------------------- |
| Średnica otworu | **∅5 mm**                                                |
| Typ             | Przelotowy (depth = 0)                                   |
| Rozstaw         | 128, 160, 192, 224, 256, 320, 384, 416, 448, 480, 512 mm |
| Pozycja         | Środek frontu (X i Y)                                    |

### 3.4 Wymiary standardowych korpusów

#### Szafki dolne (stojące)

| Parametr          | Standard   | Zakres     |
| ----------------- | ---------- | ---------- |
| Wysokość korpusu  | **720 mm** | 700-780 mm |
| Głębokość korpusu | **510 mm** | 480-560 mm |
| Grubość płyty     | **18 mm**  | 16-18 mm   |
| Nóżki             | **100 mm** | 80-200 mm  |
| Blat              | **36 mm**  | 28-40 mm   |

**Wysokość całkowita:** nóżki + korpus + blat = 100 + 720 + 36 = **856 mm**

#### Szafki górne (wiszące)

| Parametr           | Standard   | Zakres      |
| ------------------ | ---------- | ----------- |
| Wysokość korpusu   | **720 mm** | 360-1080 mm |
| Głębokość korpusu  | **300 mm** | 280-350 mm  |
| Odległość od blatu | **600 mm** | 450-700 mm  |

#### Szerokości standardowe

```
300, 400, 500, 600, 800, 900, 1000 mm
```

### 3.5 Oklejanie krawędzi

| Element                 | Krawędzie oklejone | Uwagi            |
| ----------------------- | ------------------ | ---------------- |
| Boki (lewy/prawy)       | góra + przód       | 2 krawędzie      |
| Góra/dno                | przód              | 1 krawędź        |
| Półki                   | przód              | 1 krawędź        |
| Plecy                   | brak               | HDF, niewidoczne |
| Fronty (drzwi/szuflady) | wszystkie 4        | 4 krawędzie      |

#### Typy obrzeży

| Typ | Grubość    | Zastosowanie          |
| --- | ---------- | --------------------- |
| ABS | 0.4 mm     | Standardowe krawędzie |
| ABS | 0.8 mm     | Wzmocnione krawędzie  |
| ABS | 2.0 mm     | Fronty premium        |
| PCV | 0.5-2.0 mm | Tańsze alternatywy    |

### 3.6 Materiały (Swiss Krono — przykładowe kody)

| Element       | Kod struktury    | Przykład                 |
| ------------- | ---------------- | ------------------------ |
| Korpusy       | VL (Mat)         | D3821_SW (Dąb Sztokholm) |
| Fronty matowe | EM (BE.VELVET)   | U164_EM (Antracyt)       |
| Fronty drewno | CX (Sensesation) | D20270_CX (Eden)         |
| Plecy         | HDF 3mm          | HDF_3mm_bialy            |

---

## 4. Modele danych (Pydantic)

### 4.1 CorpusSpec — specyfikacja korpusu (z dyskryminowaną unią)

```python
class CorpusSpec(BaseModel):
    id: str                    # np. "K01"
    name: str                  # np. "Szafka dolna pod zlew 800"

    # Wymiary zewnętrzne
    width: float               # mm (szerokość)
    height: float              # mm (wysokość)
    depth: float               # mm (głębokość)

    # Konstrukcja
    panel_thickness: float = 18.0
    back_thickness: float = 3.0
    back_groove_depth: float = 8.0

    # Materiały
    material_corpus: str = "U119_VL"
    material_back: str = "HDF_3mm_bialy"
    material_front: str = "U119_EM"

    # Oklejanie
    edge_material: str = "ABS_0.8"

    # Okucia
    hinges: HingeSpec | None = None
    handles: HandleSpec | None = None

    # Luki frontów
    front_gap: float = 3.0     # mm luka z każdej strony

    # Konfiguracja specyficzna dla typu (dyskryminowana unia)
    config: CabinetConfig      # BaseDoorConfig | BaseDrawerConfig | ...
```

#### Warianty konfiguracji (CabinetConfig)

```python
# Szafka drzwiowa z półkami
class BaseDoorConfig(BaseModel):
    type: Literal["base_door"] = "base_door"
    shelves: list[float] = []      # pozycje półek od dna wewnątrz (mm)
    doors: list[int] = []          # ilość zawiasów na drzwi

# Szafka z szufladami
class BaseDrawerConfig(BaseModel):
    type: Literal["base_drawer"] = "base_drawer"
    drawers: list[DrawerSpec] = [] # specyfikacja szuflad (góra → dół)

# Szafka narożna ślepa (L-kształtna)
class CornerBlindConfig(BaseModel):
    type: Literal["corner_blind"] = "corner_blind"
    corner_side: CornerSide        # LEFT | RIGHT
    second_width: float            # mm — szerokość prostopadła
    shelves: list[float] = []
    doors: list[int] = []

# Szafka narożna wewnętrzna (z karuzelą)
class CornerInternalConfig(BaseModel):
    type: Literal["corner_internal"] = "corner_internal"
    carousel: CarouselType = "optima_800"  # OPTIMA_800 | OPTIMA_900
    shelves: list[float] = []
    doors: list[int] = []

# Szafka zlewowa
class SinkConfig(BaseModel):
    type: Literal["sink"] = "sink"
    has_sorting_drawer: bool = False
    sorting_drawer: DrawerSpec | None = None
    doors: list[int] = []

# Szafka z koszem cargo
class CargoConfig(BaseModel):
    type: Literal["cargo"] = "cargo"
    cargo_type: CargoType = "mini_40"
    cargo_color: str = "ocynk"
    doors: list[int] = []

# Szafka do zabudowy piekarnika
class OvenConfig(BaseModel):
    type: Literal["oven"] = "oven"
    cavity_height: float           # mm — wysokość komory piekarnika
    has_ventilation: bool = True
    reinforced_shelf: bool = True
```

### 4.2 Panel — pojedyncza formatka

```python
class Panel(BaseModel):
    id: str                    # np. "K01-BOK-L"
    role: PanelRole            # bok_lewy, bok_prawy, dno, gora, polka, plecy, front_drzwi, front_szuflada
    width: float               # mm (wymiar cięcia)
    height: float              # mm (wymiar cięcia)
    thickness: float           # mm
    material: str              # kod materiału
    quantity: int = 1
    edges: list[EdgeBand]      # krawędzie do oklejenia
    drill_points: list[DrillPoint]  # otwory
```

### 4.3 DrillPoint — pojedynczy otwór

```python
class DrillPoint(BaseModel):
    x: float                   # mm od lewej krawędzi
    y: float                   # mm od dolnej krawędzi
    diameter: float            # mm
    depth: float               # mm (0 = przelotowy)
    face: DrillFace            # inside | outside | front | back
    drill_type: DrillType      # system32 | puszka_zawiasu | znacznik_wkret | uchwyt | ...
    label: str = ""            # opis czytelny
```

### 4.4 HingeSpec — specyfikacja zawiasów

```python
class HingeSpec(BaseModel):
    type: str = "blum_clip_35"
    cup_diameter: float = 35.0
    cup_depth: float = 13.0
    screw_spacing: float = 45.0        # Blum=45, Hettich=52
    screw_offset_x: float = 9.5
    screw_diameter: float = 3.0
    screw_depth: float = 2.0
    edge_to_cup_centre: float = 5.0
    count: int = 2
    first_position: float = 100.0      # mm od góry frontu
```

### 4.5 Enumy

```python
CorpusType:  base_door | base_drawer | corner_blind | corner_internal | sink | cargo | oven
PanelRole:   bok_lewy | bok_prawy | dno | gora | polka | plecy | front_drzwi | front_szuflada
EdgeSide:    gora | dol | lewo | prawo
DrillFace:   inside | outside | front | back
DrillType:   system32 | puszka_zawiasu | znacznik_wkret | kolek_zawiasu |
             kolek_laczacy | minifix | uchwyt | podporka_polki
CornerSide:  left | right
CarouselType: optima_800 | optima_900
CargoType:   mini_40
```

### 4.6 Shared Constants

```python
SYSTEM32_OFFSET: float = 37.0   # mm from front/bottom edge
SYSTEM32_SPACING: float = 32.0  # mm between holes
```

These constants are defined in `models.py` and used by both `panel_calculator` and `drill_engine`.

---

## 5. Kalkulator formatek

### 5.1 Wzory obliczania wymiarów

Dla korpusu o wymiarach zewnętrznych W × H × D, grubości płyty T,
głębokości rowka G, grubości pleców BT:

| Panel           | Szerokość       | Wysokość                                | Grubość | Ilość |
| --------------- | --------------- | --------------------------------------- | ------- | ----- |
| Bok lewy        | D               | H                                       | T       | 1     |
| Bok prawy       | D               | H                                       | T       | 1     |
| Góra            | W - 2T          | D - G                                   | T       | 1     |
| Dno             | W - 2T          | D - G                                   | T       | 1     |
| Półka           | W - 2T          | D - G - SYSTEM32_OFFSET                 | T       | N     |
| Plecy           | W - 2T          | H                                       | BT      | 1     |
| Front (1 drzwi) | W - 2×gap       | H - 2×gap                               | T       | 1     |
| Front (2 drzwi) | (W - 3×gap) / 2 | H - 2×gap                               | T       | 2     |
| Front szuflady  | W - 2×gap       | (H - top_gap - bot_gap - (n-1)×gap) / n | T       | n     |

### 5.2 Przykład: K01 (800×720×510, T=18, G=8, BT=3)

```
Bok L/P:    510 × 720 × 18
Góra:       764 × 502 × 18    (800-36 × 510-8)
Dno:        764 × 502 × 18
Półka:      764 × 465 × 18    (502-37)
Plecy:      764 × 720 × 3
Front:      794 × 714 × 18    (800-6 × 720-6)
```

### 5.3 Zasady oklejania

Reguły domyślne (możliwość nadpisania):

```python
# Boki: góra + przód (lewa krawędź w orientacji formatki)
edges = [
    EdgeBand(side=EdgeSide.TOP, material="ABS_0.8"),
    EdgeBand(side=EdgeSide.LEFT, material="ABS_0.8"),  # "przód" korpusu
]

# Góra/dno: tylko przód
edges = [EdgeBand(side=EdgeSide.LEFT, material="ABS_0.8")]

# Półki: tylko przód
edges = [EdgeBand(side=EdgeSide.LEFT, material="ABS_0.8")]

# Plecy: brak
edges = []

# Fronty: wszystkie 4
edges = [EdgeBand(side=s) for s in EdgeSide]
```

---

## 6. Silnik nawiertów

### 6.1 System 32 — na bokach korpusu

```
Współrzędne na boku (widok od strony wewnętrznej):
  X = 37 mm od krawędzi przedniej
  Y = 37, 69, 101, ..., H-37

Parametry:
  ∅5 mm, głębokość 13 mm
  Twarz: INSIDE
```

### 6.2 Podpórki półek

```
Na boku, w miejscu półki:
  X = 37 mm (rząd przedni)
  X = D - 37 mm (rząd tylny)
  Y = T + pozycja_półki

Parametry:
  ∅5 mm, głębokość 12 mm
  Twarz: INSIDE
```

### 6.3 Zawiasy Blum CLIP top

```
Na froncie (widok od strony wewnętrznej):
  X = 5 mm od krawędzi
  Y = pozycja_zawiasu

Otwory na zawias:
  1× ∅35 mm, gł. 13 mm    (puszka)
  2× ∅3 mm, gł. 2 mm      (śruby, Y ± 22.5mm)
```

### 6.4 Uchwyty relingowe

```
Na froncie szuflady:
  X = (szer_frontu / 2) ± (rozstaw / 2)
  Y = wys_frontu / 2

Parametry:
  ∅5 mm, przelotowy
```

### 6.5 Kolejność aplikacji makr

```python
def apply_all_drilling(panels, spec):
    panels = apply_system32(panels, spec)   # 1. System 32 na bokach
    panels = apply_hinges(panels, spec)     # 2. Zawiasy na frontach
    panels = apply_handles(panels, spec)    # 3. Uchwyty na szufladach
    return panels
```

> **Note:** All `apply_*` functions are **pure** — they return a new list with
> copied panels. The original `panels` list is never modified.

---

## 7. Generatory CSV

### 7.1 CSV cięcie

```
Separator: ;
Kodowanie: UTF-8

Kolumny:
  id;role;width;height;thickness;material;quantity;edges

Przykład:
  K01-BOK-L;bok_lewy;510;720;18;D3821_SW;1;gora,lewo
  K01-F1;front_drzwi;794;714;18;U164_EM;1;gora,dol,lewo,prawo
```

### 7.2 CSV oklejanie

```
Separator: ;
Kodowanie: UTF-8

Kolumny:
  panel_id;edge;length_mm;material

Przykład:
  K01-BOK-L;gora;510;ABS_0.8
  K01-BOK-L;lewo;720;ABS_0.8
  K01-F1;gora;794;ABS_0.8
```

### 7.3 Zasady obliczania długości krawędzi

| Krawędź      | Długość      |
| ------------ | ------------ |
| gora / dol   | panel.width  |
| lewo / prawo | panel.height |

---

## 8. Narzędzia porównawcze

### 8.1 Porównanie CSV (`compare_csv`)

```python
from kitchen_cad.compare import compare_csv

diff = compare_csv(
    reference="output/reference/K01_ciecie.csv",
    generated="output/generated/K01_ciecie.csv",
    key_column="id",
    numeric_tol=0.001,  # 0.1% tolerancja na float
)
assert diff.ok, diff.report()
```

**Co porównuje:**

- Wiersze po kluczu `id` (missing / extra)
- Wartości numeryczne z tolerancją (np. 465.0 vs 465.001)
- Wartości tekstowe exact match

### 8.2 Porównanie DXF (`compare_dxf`)

```python
from kitchen_cad.compare import compare_dxf

diff = compare_dxf(
    reference="output/reference/K01_nawierty.dxf",
    generated="output/generated/K01_nawierty.dxf",
    pos_tol=0.2,    # ±0.2mm tolerancja pozycji
    diam_tol=0.1,   # ±0.1mm tolerancja średnicy
)
assert diff.ok, diff.report()
```

**Co porównuje:**

- Wyciąga CIRCLE entities z obu plików
- Dopasowuje okręgi po pozycji (X,Y) i średnicy
- Ignoruje kolejność, metadata, timestampy
- Raportuje: missing, extra, layer_mismatch

**Dlaczego nie byte-level diff:**

- DXF może mieć różną kolejność encji
- Float precision różni się między programami
- Metadata (timestampy, wersje) się różnią
- Ta sama geometria może być zapisana różnie

---

## 9. Strategia testów

### 9.1 TDD — Test-Driven Development

```
1. Napisz test (definiuje zachowanie)
2. Uruchom test (FAIL — czerwony)
3. Napisz implementację (minimalna)
4. Uruchom test (PASS — zielony)
5. Refaktoryzuj (utrzymaj zielone)
```

### 9.2 Struktura testów

```
tests/
├── conftest.py              # Fixtures: base_door_spec, base_drawer_spec, wall_door_spec
├── test_models.py           # 10 testów — walidacja Pydantic
├── test_panel_calculator.py # 22 testów — wymiary formatek
├── test_drill_engine.py     # 24 testów — pozycje otworów
├── test_csv_generator.py    # 14 testów — struktura CSV
└── test_compare.py          # 5 testów — narzędzia porównawcze
```

### 9.3 Co testujemy

| Moduł            | Co testujemy           | Przykłady                                         |
| ---------------- | ---------------------- | ------------------------------------------------- |
| models           | Walidacja pól          | zerowa szerokość → błąd, ujemne koordynaty → błąd |
| panel_calculator | Wymiary formatek       | bok = D×H,półka = (W-2T)×(D-G-37)                 |
| drill_engine     | Pozycje otworów        | System 32 X=37, Blum cup X=5, spacing 45mm        |
| csv_generator    | Struktura pliku        | separator `;`, kolumny, brak krawędzi na plecach  |
| compare          | Walidacja referencyjna | self-compare, missing rows, value mismatch        |

### 9.4 Fixtures (dane testowe)

```python
# base_door_spec: 800×720×510, 1 półka, 1 drzwi (2 zawiasy Blum)
# base_drawer_spec: 800×720×510, 2 szuflady (Metabox)
# wall_door_spec: 800×720×300, 1 półka, 1 drzwi (2 zawiasy Blum)
```

### 9.5 Coverage

```
Name                              Stmts  Miss  Cover
─────────────────────────────────────────────────────
src/kitchen_cad/models.py           91     0   100%
src/kitchen_cad/panel_calculator    58     0   100%
src/kitchen_cad/csv_generator       29     0   100%
src/kitchen_cad/drill_engine        72    11    85%
─────────────────────────────────────────────────────
TOTAL                              250    11    96%
```

---

## 10. Roadmapa

### Faza 1 ✅ (zakończona)

- [x] Modele Pydantic (CorpusSpec, Panel, DrillPoint, HingeSpec, HandleSpec)
- [x] Kalkulator formatek (base, drawer, wall, 2-door)
- [x] Silnik nawiertów System 32
- [x] Silnik nawiertów Blum CLIP 35mm
- [x] Silnik nawiertów uchwyty relingowe
- [x] Generator CSV cięcie
- [x] Generator CSV oklejanie
- [x] Narzędzia porównawcze (CSV + DXF)
- [x] Test suite (run `make test` for current count)

> **For current roadmap and planned features, see [ROADMAP.md](../ROADMAP.md).**

---

## Załącznik A: Słownik terminów

| Termin         | Definicja                                          |
| -------------- | -------------------------------------------------- |
| Formatka       | Gotowy element płyty przycięty na wymiar           |
| Korpus         | Konstrukcja szafki (boki, dno, góra, półka)        |
| Front          | Widoczna część drzwiczek/szuflady                  |
| System 32      | Europejski standard rozmieszczenia otworów (32mm)  |
| Puszka zawiasu | Część zawiasu wpuszczana w front (∅35mm)           |
| CLIP           | System montażu zawiasów bez narzędzi (Blum)        |
| ABS            | Tworzywo sztuczne na obrzeża                       |
| Rzaz           | Szczelina po pile (standard 3-4mm)                 |
| Formatyzacja   | Proces cięcia płyt na formatki                     |
| Nut            | Rowek w płycie na plecy (8mm głęboki, 3mm szeroki) |
| Okleiniarka    | Maszyna do nakładania obrzeży                      |
| PUR            | Klej poliuretanowy (wodoodporny)                   |
| CNC            | Computerized Numerical Control                     |
| DXF            | Drawing Exchange Format — format pliku CAD         |

---

## Załącznik B: Przykład użycia

```python
from kitchen_cad.models import CorpusSpec, BaseDoorConfig, HingeSpec, HandleSpec
from kitchen_cad.panel_calculator import calculate_panels
from kitchen_cad.drill_engine import apply_all_drilling
from kitchen_cad.csv_generator import generate_cutting_csv, generate_edging_csv

# 1. Zdefiniuj korpus
spec = CorpusSpec(
    id="K01",
    name="Szafka dolna pod zlew 800",
    width=800, height=720, depth=510,
    material_corpus="D3821_SW",
    material_front="U164_EM",
    hinges=HingeSpec(count=2),
    handles=HandleSpec(spacing=256),
    config=BaseDoorConfig(
        shelves=[352],
        doors=[2],
    ),
)

# 2. Oblicz formatki
panels = calculate_panels(spec)

# 3. Dodaj nawiercy
panels = apply_all_drilling(panels, spec)

# 4. Generuj CSV
generate_cutting_csv(panels, Path("output/ciecie.csv"))
generate_edging_csv(panels, Path("output/oklejanie.csv"))

# 5. Podsumowanie
for p in panels:
    print(f"{p.id:15s} {p.width:6.0f}×{p.height:6.0f}×{p.thickness:2.0f}  "
          f"{p.material:12s}  {len(p.drill_points):2d} otworów  "
          f"{len(p.edges)} krawędzi")
```

---

## Załącznik C: Wzorzec nazewnictwa

```
{id}-BOK-L     bok lewy
{id}-BOK-P     bok prawy
{id}-GORA      góra korpusu
{id}-DNO       dno korpusu
{id}-POL{n}    półka nr n
{id}-PLECY     plecy (HDF)
{id}-F{n}      front nr n (drzwi lub szuflada)
```

---

_Dokument wygenerowany automatycznie na podstawie kodu źródłowego._
_Ostatnia aktualizacja: 2026-06-23_
_Dla aktualnego roadmapy patrz [ROADMAP.md](../ROADMAP.md)_
