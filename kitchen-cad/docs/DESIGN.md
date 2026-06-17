# kitchen-cad — dokumentacja projektowa

> **Wersja:** 1.0 (Faza 1 — completed)
> **Data:** 2026-06-17
> **Status:** 75 testów, 96% coverage, CSV generowanie działa

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

```
kitchen-cad/
├── pyproject.toml
├── example_generate.py               # przykład użycia end-to-end
│
├── src/kitchen_cad/
│   ├── models.py                     # modele Pydantic (91 linii)
│   ├── panel_calculator.py           # wymiary formatek (58 linii)
│   ├── drill_engine.py               # pozycje otworów (72 linii)
│   └── csv_generator.py              # CSV output (29 linii)
│
├── tests/                            # 75 testów, 96% coverage
│   ├── conftest.py                   # fixtures (base_door, base_drawer, wall)
│   ├── test_models.py                # walidacja Pydantic
│   ├── test_panel_calculator.py      # wymiary formatek
│   ├── test_drill_engine.py          # System 32, Blum, uchwyty
│   ├── test_csv_generator.py         # struktura CSV
│   └── test_compare.py              # narzędzia porównawcze
│
└── output/
    ├── demo_kitchen/                 # przykładowe wygenerowane pliki
    │   ├── ciecie.csv
    │   └── oklejanie.csv
    └── reference/                    # pliki referencyjne z Corpus (TBD)
```

### Pipeline przetwarzania

```python
spec = CorpusSpec(...)                 # 1. Definicja korpusu
panels = calculate_panels(spec)        # 2. Oblicz formatki
panels = apply_all_drilling(panels, spec)  # 3. Dodaj nawiercy
generate_cutting_csv(panels, path)     # 4. CSV cięcie
generate_edging_csv(panels, path)      # 5. CSV oklejanie
# generate_dxf(panels, path)           # 6. DXF (Faza 2)
```

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

### 4.1 CorpusSpec — pełna specyfikacja korpusu

```python
class CorpusSpec(BaseModel):
    id: str                    # np. "K01"
    name: str                  # np. "Szafka dolna pod zlew 800"
    corpus_type: str           # base_door | base_drawer | wall_door | tall

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

    # Struktura wewnętrzna
    shelves: list[float] = []          # pozycje półek od dna wewnątrz (mm)
    drawers: list[DrawerSpec] = []     # specyfikacja szuflad
    doors: list[int] = []              # ilość zawiasów na drzwi

    # Okucia
    hinges: HingeSpec | None = None
    handles: HandleSpec | None = None

    # Luki frontów
    front_gap: float = 3.0             # mm luka z każdej strony
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
PanelRole:   bok_lewy | bok_prawy | dno | gora | polka | plecy | front_drzwi | front_szuflada
EdgeSide:    gora | dol | lewo | prawo
DrillFace:   inside | outside | front | back
DrillType:   system32 | puszka_zawiasu | znacznik_wkret | kolek_zawiasu |
             kolek_laczacy | minifix | uchwyt | podporka_polki
```

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
| Półka           | W - 2T          | D - G - 37                              | T       | N     |
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
- [x] 75 testów, 96% coverage

### Faza 2 (planowana)

- [ ] Generator DXF z warstwami (ezdxf)
    - Warstwa `CIECIE` (czerwona) — kontury formatek
    - Warstwa `WIERCENIE` (zielona) — otwory jako okręgi
    - Warstwa `OPIS` (szara) — wymiary, nazwy
- [ ] YAML loader (definicje korpusów w plikach)
- [ ] Hettich Sensys (screw_spacing=52mm)
- [ ] Minifix / cam-lock (∅15mm)
- [ ] Kołki łączące (∅8mm)
- [ ] Prowadnice szufladowe (Blum METABOX, TANDEM, LEGRABOX)

### Faza 3 (przyszłość)

- [ ] Streamlit UI (wizualizacja korpusu w przeglądarce)
- [ ] Import z Corpus LTR (CSV)
- [ ] Optymalizacja rozkroju (minimalizacja odpadów)
- [ ] Etykiety z kodami kreskowymi
- [ ] Integracja z e-rozkroj (FastCut API)

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
from kitchen_cad.models import CorpusSpec, HingeSpec, HandleSpec
from kitchen_cad.panel_calculator import calculate_panels
from kitchen_cad.drill_engine import apply_all_drilling
from kitchen_cad.csv_generator import generate_cutting_csv, generate_edging_csv

# 1. Zdefiniuj korpus
spec = CorpusSpec(
    id="K01",
    name="Szafka dolna pod zlew 800",
    corpus_type="base_door",
    width=800, height=720, depth=510,
    material_corpus="D3821_SW",
    material_front="U164_EM",
    shelves=[352],
    doors=[2],
    hinges=HingeSpec(count=2),
    handles=HandleSpec(spacing=256),
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
_Ostatnia aktualizacja: 2026-06-17_
