# Drzewo wariantów szafek — Cabinent Variants

> Na podstawie analizy screenshotów z aplikacji konfiguracyjnej (cabinet-types/)
> Data: 2026-06-23

---

## 1. TYP KORPUSU

```
SZAFKA DOLNA (Base)
├── 1.1 Standardowa — drzwi + półki
│   ├── 1 front (lewy lub prawy)
│   └── 2 fronty (lewy + prawy)
│
├── 1.2 Z szufladami
│   ├── 1 szuflada (pod szufladą: otwarte lub front)
│   ├── 2 szuflady (równa podział)
│   ├── 3 szuflady (równa podział)
│   ├── 4 szuflady (podział 2-1-1-1: 2 górne małe + 1+1 większe)
│   └── N szuflad (konfigurowalne —patrz 1.3)
│
├── 1.3 Z konfigurowalnymi szufladami (Custom drawers)
│   └── Każda szuflada niezależna: wysokość + typ prowadnic
│
├── 1.4 Narożna ślepa (Corner blind)
│   ├── Lewy narożnik, front po prawej
│   └── Prawy narożnik, front po lewej
│
├── 1.5 Narożna wewnętrzna (Corner internal / Diagonal)
│   └── Karuzela: Corner Optima 2 półki (800×450 / 900×500)
│
├── 1.6 Zlewowa (Sink base)
│   └── Front szuflady na sortowanie
│
├── 1.7 Z koszem cargo (Pull-out larder)
│
└── 1.8 Do zabudowy piekarnika (Oven housing)
    └── Półka stała (nie regulowana)
```

### Minimalne wysokości korpusów:

| Typ szafki | Min wysokość | Max wysokość | Uwagi |
|------------|--------------|--------------|-------|
| Standardowa dolna | 250mm | 1000mm | Zależna od ilości szuflad i typu prowadnic |
| Z piekarnikiem | 600mm | 1000mm | Min 600mm dla standardowego piekarnika do zabudowy |
| Zlewowa | 400mm | 1000mm | Min 400mm dla komory zlewu |
| Cargo | 600mm | 1000mm | Zależna od kosza cargo |
| Narożna | 250mm | 1000mm | Jak standardowa |
| Ścienna (górna) | 300mm | 900mm | Zależna od wysokości montażu |

**Uwaga:** Wysokość 160mm jest niepraktyczna — minimalna nóżka to 80-100mm, a korpus musi zmieścić min. 1 szufladę lub półkę. Poprawiono minimum na 250mm.

---

## 2. WYMIARY

```
Szerokość (W):   200 — 1200 mm  (min 200mm dla 1-front, max 1200mm)
Wysokość (H):    250 — 1000 mm  (zależna od typu: base 250-1000, oven 600-1000)
Głębokość (D):   300 — 700 mm   (patrz: typy głębokości poniżej)
```

### Typy głębokości:

| Typ | Wartość | Uwagi |
|-----|---------|-------|
| **Głębokość korpusu (zewnętrzna)** | 560 mm | Standard dla szafek dolnych (bez frontu i bez pleców) |
| **Głębokość wewnętrzna** | ~520 mm | Po odjęciu pleców (5mm) i frontu (18mm) — wymagana dla prowadnic Blum |
| **Głębokość całkowita** | ~580 mm | Korpus + front (18mm) + plecy (5mm) |
| **Głębokość minimalna** | 300 mm | Dla szafek ściennych/płytkich |

**Uwaga:** Standard 560mm zapewnia kompatybilność z prowadnicami Blum Tandembox (wymagają min. 500mm wewnętrznej głębokości).

### Auto-obliczenia:

- **Wys. całkowita** = nóżki (10cm) + wysokość korpusu
- **Głęb. całkowita** = głębokość + front (~1.8cm)
- **Głęb. prostopadła szafek** (narożne) = osobny parametr

### Ostrzeżenia auto-korekty:

- Min szerokość dla bieżących ustawień (np. min 884mm, min 976mm)
- Auto-zmiana szerokości, głębokości przy konflikcie wymiarów
- Auto-zmiana nawierceń pod uchwyty (poziome niedostępne przy dużym uchwycie)

### Minimalne szerokości per typ:

| Typ szafki | Min szerokość | Uwagi |
|------------|---------------|-------|
| 1-front (drzwi) | 200mm | Miejsce na zawias + front |
| 2-fronty | 400mm | 2× drzwi min. 200mm |
| 1 szuflada | 250mm | Min. dla prowadnic Blum |
| Narożna ślepa | 800mm | 400mm widoczny front + 400mm ukryty |
| Narożna diagonalna | 900mm | Rogowa, min. dla mechanizmu |
| Zlewowa | 500mm | Miejsce na komorę zlewu |
| Cargo | 300mm | Min. dla kosza cargo |
| Piekarnik | 600mm | Standardowa szerokość piekarnika |

---

## 3. FRONTY (Doors / Drawer fronts)

### 3.1 Konfiguracja frontów dolnych

```
Bez frontów
├── 1 front — otwierany w lewo
├── 1 front — otwierany w prawo
├── 2 fronty — lewy i prawy
├── Bez frontów — nawierty pod prowadniki lewe
├── Bez frontów — nawierty pod prowadniki prawe
└── Bez frontów — nawierty pod prowadniki lewe i prawe
```

### 3.2 Front szuflady (drawer front)

```
Bez frontu szuflady  (szuflada wewnętrzna, niewidoczna)
1 front szuflady     (pełny front na szufladzie)
```

### 3.3 Wymiary frontów

- **Drzwi:** szerokość i wysokość z uwzględnieniem luzów (gap 3mm)
- **Szuflady:** wysokość zależna od liczby szuflad i typu prowadnicy

---

## 4. PÓŁKI (Shelves)

```
0 półek (bez)
1 półka
2 półki
3 półki
4 półki
5 półek
```

### Rozmieszczenie półek:

```
Rozmieszczenie półek (System 32)
├── Normalne — otwory co 32mm (pełna siatka System 32)
│   └── Każda półka wspierana na 2-4 kołkach (w zależności od szerokości)
│
└── Symetryczne — otwory co 64mm (co drugi otwór System 32)
    └── 3 otwory na stronę na półkę (6 total: 3 lewa + 3 prawa strona)
    └── Zastosowanie: lżejsze obciążenie, szybsze wiercenie
```

**Uwaga:** System 32 zawsze używa siatki 32mm. Opcja "symetryczne" oznacza użycie co drugiego otworu (64mm odstęp), co daje rozkład symetryczny wizualnie i wystarczający dla większości zastosowań.

### Szafki narożne — warianty półek:

```
Standardowe półki
Corner Optima 2 półki 800×450 wysuwane
Corner Optima 2 półki 900×500 wysuwane
```

---

## 5. SYSTEM PROWADNIC I SZUFLAD

### 5.1 Typ prowadnic (per szuflada)

```
Blum TANDEMBOX antaro
├── Wys N  (h=83mm)   — niska
├── Wys M  (h=116mm)  — średnia (klasyczny)
└── Wys D  (h=199mm)  — wysoka / z relingiem

Blum MERIVOBOX
├── Wys N  (h=65.5mm) — niska
├── Wys M  (h=90mm)   — średnia
└── Wys E  (h=184mm)  — wysoka / z relingiem

Blum LEGRABOX
├── Wys S  (h=77mm)   — niska
├── Wys M  (h=116mm)  — średnia
└── Wys C  (h=167mm)  — wysoka
```

### 5.2 Długość prowadnic

```
270 mm
300 mm
350 mm
400 mm
450 mm
500 mm   ← standard
550 mm
600 mm
650 mm
```

### 5.3 Kolory prowadnic

```
Blum Tandembox:     Szary / Biały
Blum Merivobox:     Antracyt / Szary Indium / Jedwabiście biały
Blum Legrabox:      Antracyt / Biały
```

### 5.4 System domyku

```
Otwieranie uchytem      (+Hamulec Blumotion)
Otwieranie naciskiem    (Tip-On + Hamulec)
Otwieranie elektryczne  (Servo-Drive)
```

### 5.5 Prowadnica z hamulcem

```
TANDEMBOX ANTARO 578 M  →  do TIP-ON BLUMOTION / 30kg / wysuw 100%
MERIVOBOX BLUMOTION 450 B  →  40kg / wysuw 100%
LEGRABOX BLUMOTION 750 S  →  40kg / wysuw 100% / do Tip-On
```

---

## 6. ZAWIASY (Hinges)

```
Premium:   Blum ClipTop 110 cichy domyk (standard)
Basic:     Brak (opcja "bez zawiasów")
```

---

## 7. UCHWYTY (Handles)

### 7.1 Typ uchwytu

```
Uchwyty (226 modeli)
├── Relingowe (proste)
│   ├── Rozstaw: 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 384,
│   │            416, 480, 492, 608, 640 mm
│   └── Przykład: Uchwyt 2576 czarny mat / rozstaw 192mm
│
Gałki (114 modeli)
├── Gałka GRAP 0109/17
│   ├── Czarny mat
│   ├── Miedź ciemna szczotkowana
│   ├── Mat anodowany
│   └── Efekt stali nierdzewnej
│
Bez uchwytów (11 opcji)
└── Brak nawierceń pod uchwyt
```

### 7.2 Pozycja nawierceń pod uchwyt

```
Centralnie na froncie, poziomo           ← standard
Środek frontu, po bokach (164mm), poziomo
Góra frontu (50mm), na środku, poziomo
Pionowo (zmiana orientacji)
Bez nawierceń pod uchwyt
```

### 7.3 Lokalizacja nawierceń

```
Dla drzwi:        Górę frontu (50mm), na środku, po boku, poziomo
Dla szuflad:      Centralnie na froncie, poziomo
                  Górę frontu (50mm), na środku, po boku, pionowo
                  Górę frontu (50mm), po boku (50mm), pionowo
```

---

## 8. NOŻKI (Legs)

```
Nóżka 10 cm z regulacją         ← standard
Nóżka Axilo 10 cm   250kg       (+17 zł)
Nóżka Axilo 12,5 cm 250kg       (+17 zł)
Nóżka Axilo 15 cm   250kg       (+18 zł)
```

---

## 9. KOSZE CARGO (Pull-out baskets)

```
Brak
Cargo Mini Dolne VARIANT MULTI 40 cm
├── Ocynk / miękki domyk
├── Biały / miękki domyk         (+11 zł)
└── Grafit / miękki domyk        (+11 zł)
```

---

## 10. KOLORY I MATERIAŁY

### 10.1 Front

```
Dąb Bardolino naturalny (H1145, ST10)  ← przykład
Kierunek usłojenia: pionowo / poziomo
```

### 10.2 Korpus

```
Biały klasyczny (W960, SM)  ← przykład
```

### 10.3 Krawędzie przednie

```
W kolorze frontu (H1145, ST10)   ← standard
W kolorze korpusu (W960, SM)
```

### 10.4 Boki szafki

```
Lewy: Domyślny (w kolorze korpusu) / w kolorze frontu
Prawy: Domyślny (w kolorze korpusu) / w kolorze frontu
```

---

## 11. BLENDA KORPUSU (Plinth fascia)

```
Dodatkowe 102mm (od korpusu) zajmuje prostopadła blenda
```

---

## 12. PODPÓRKI PÓŁEK (Shelf supports)

```
Podpórki Kuadro z zabezpieczeniem (typ 2)
```

---

## MACIERZ WARIANTÓW (Szybki przegląd)

| Typ szafki           | Front | Półki  | Szuflady     | Narożna | Specjalne     |
| -------------------- | ----- | ------ | ------------ | ------- | ------------- |
| Base 1-door          | 1     | 0-5    | —            | —       | —             |
| Base 2-door          | 2     | 0-5    | —            | —       | —             |
| Base 1-drawer        | 1     | —      | 1            | —       | front opcja   |
| Base 2-drawer        | —     | —      | 2 równe      | —       | —             |
| Base 3-drawer        | —     | —      | 3 równe      | —       | —             |
| Base 4-drawer        | —     | —      | 4 (2-1-1-1)  | —       | —             |
| Base N-drawer        | —     | —      | N custom     | —       | mix typów     |
| Base blind corner    | 1     | 0-2    | —            | L/R     | blendy        |
| Base internal corner | 1     | Optima | —            | —       | karuzela      |
| Base sink+drawer     | 1     | —      | 1 sortowanie | —       | min za szufl. |
| Base cargo           | 1     | —      | —            | —       | kosz mini     |
| Base oven            | —     | stała  | —            | —       | высота 60-100 |

---

_Dokument wygenerowany na podstawie analizy screenshotów z aplikacji konfiguracyjnej._
_Ostatnia aktualizacja: 2026-06-23_
