# Kitchen CAD - Generator szablonów DXF dla mebli kuchennych

## Opis

Generator parametryzowanych plików DXF dla produkcji mebli kuchennych z CNC.
Zgodny z europejskimi standardami: System 32, Blum LEGRABOX, BLUMOTION.

## Dokumentacja

| Dokument                                                     | Opis                           |
| ------------------------------------------------------------ | ------------------------------ |
| [ROADMAP.md](ROADMAP.md)                                     | Plan rozwoju projektu          |
| [CHANGELOG.md](CHANGELOG.md)                                 | Historia zmian                 |
| [docs/architecture.md](docs/architecture.md)                 | Architektura systemu           |
| [docs/DESIGN.md](docs/DESIGN.md)                             | Dokumentacja projektowa        |
| [docs/LEGRABOX_SPEC.md](docs/LEGRABOX_SPEC.md)               | Specyfikacja LEGRABOX          |
| [docs/poradnik-kompleksowy.md](docs/poradnik-kompleksowy.md) | Kompleksowy poradnik meblarski |

## Struktura

```
kitchen-cad/
├── generators/          # Skrypty Python generujące DXF
│   └── legrabox_side_panel.py   # Bok szafki z nawiertami LEGRABOX
├── templates/           # Szablony DXF (gotowe wzorce)
├── output/              # Wygenerowane pliki DXF
└── docs/                # Dokumentacja standardów
```

## Wymagania

```bash
python3.11 -m pip install ezdxf
```

## Użycie

### Bok szafki dolnej - 3 szuflady LEGRABOX + BLUMOTION

```bash
# Domyślna konfiguracja: szafka 510x720mm, szuflady N/M/K
python3.11 generators/legrabox_side_panel.py

# Własne wymiary
python3.11 generators/legrabox_side_panel.py --depth 510 --height 720 --drawers N M K

# Szafka z szerszymi szufladami
python3.11 generators/legrabox_side_panel.py --depth 560 --height 720 --drawers M M K

# Wysoka szafka (słupek)
python3.11 generators/legrabox_side_panel.py --depth 560 --height 2000 --drawers N K C
```

### Typy szuflad LEGRABOX

| Typ   | Wysokość boku | Zastosowanie           |
| ----- | ------------- | ---------------------- |
| **N** | 66.5 mm       | Sztućce, drobiazgi     |
| **M** | 90.5 mm       | Garnki, przyprawy      |
| **K** | 128.5 mm      | Garnki, patelnie       |
| **C** | 177.0 mm      | Duże garnki, produkty  |
| **F** | 241.0 mm      | Specjalne zastosowania |

## Standardy techniczne

### System 32

- Rozstaw otworów: 32 mm
- Odległość od krawędzi przedniej: 37 mm
- Odległość od krawędzi tylnej: 37 mm
- Średnica otworu: ∅5 mm

### LEGRABOX

- Profil kab. mocowany na ∅5mm
- Pierwszy otwór: 9mm od dna otworu szuflady
- Rozstaw: 32mm (System 32)
- BLUMOTION: zintegrowany w prowadnicy

### Warstwy DXF (dla CNC)

| Warstwa               | Kolor    | Zawartość               |
| --------------------- | -------- | ----------------------- |
| `01_OUTLINE`          | Biały    | Kontur zewnętrzny       |
| `02_SYSTEM32`         | Zielony  | Otwory System 32 (∅5mm) |
| `03_LEGRABOX_PROFILE` | Czerwony | Otwory prowadnic        |
| `04_DOWELS`           | Żółty    | Otwory pod kołki (∅8mm) |
| `05_DIMENSIONS`       | Cyan     | Wymiary kontrolne       |
| `06_NOTES`            | Szary    | Opisy i notatki         |
| `07_EDGEBANDING`      | Magenta  | Krawędzie do oklejenia  |

## Format pliku

- Format: DXF R2000 (kompatybilny z AutoCAD, LibreCAD, QCAD)
- Skala: 1:1
- Jednostki: milimetry (mm)
- Płaszczyzna: XY (Z=0)

## Zlecenie CNC

1. Wygeneruj plik DXF
2. Otwórz w przeglądarce DXF (LibreCAD, AutoCAD) i zweryfikuj
3. Wyślij do centrum CNC z informacją o:
    - Materiale (płyta wiórowa laminowana, grubość 18mm)
    - Okleinowaniu (krawędź przednia i górna - ABS)
    - Typie okleinarki (jaka grubość obrzeża)

## Autor

Generator stworzony dla projektu kuchnie - meblarstwo europejskie
