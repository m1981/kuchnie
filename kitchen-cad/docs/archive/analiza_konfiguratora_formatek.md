# Analiza Rozgałęzień Decyzyjnych - Konfigurator Formatek CNC

Analiza programu do zamawiania elementów meblowych z obróbką CNC.

---

## POZIOM 1: WYBÓR PŁYTY I FORMATU

### 1.1. Wybór materiału płyty

- **Płyta głęboki mat EGGER U702 PMST9 (Perfectsense Matt/ST9) Kaszmir 19 mm**
    - Format płyty: **2070x2800 mm**
    - Grubość: **19,0 mm** (dropdown - możliwość innych grubości)
    - Wodoodporność: **Suchotrwała** (dropdown)

### 1.2. Wybór struktury powierzchni

- **PM PerfectSense Matt** (radio button - zaznaczony)
- **TM PerfectSense Matt** (radio button - alternatywa)

**Znaczenie techniczne**: Struktura wpływa na obróbkę (PM wymaga delikatniejszej obróbki, TM jest bardziej odporna na zarysowania).

---

## POZIOM 2: DEFINICJA FORMATKI

### 2.1. Rozmiar formatki

- **Szer [mm]**: 596
- **Wys [mm]**: 713
- **UWAGA**: "rozmiar podawaj w milimetrach (zamknij)" - system dodaje automatycznie grubość obrzeża

### 2.2. Ilość sztuk

- Licznik z przyciskami +/- (domyślnie: 1)

### 2.3. Nazwa formatki

- Pole tekstowe: np. "front" - ważne dla identyfikacji w produkcji

---

## POZIOM 3: OKLEJANIE KRAWĘDZI

### 3.1. Wybór krawędzi do oklejenia

Checkbox: **"oklej wszystkie krawędzie"** (szybki wybór)

**LUB**

Indywidualny wybór krawędzi (checkbox dla każdej):

- **Krawędź 1** (góra)
- **Krawędź 2** (prawo)
- **Krawędź 3** (dół)
- **Krawędź 4** (lewo)

**Wizualizacja**: Schemat formatki z numeracją krawędzi (1-4 zgodnie z ruchem wskazówek zegara od góry).

### 3.2. Rodzaj obrzeża

- **Kolor obrzeża**: U702, PMST9 (match do płyty)
- **Grubość obrzeża**:
    - **1,0 mm** (radio - klejenie bezspoinowe/szczególy) - zaznaczone
    - **1,0 mm** (radio - standardowe)

### 3.3. Dostępność magazynowa

- ✅ **"- na magazynie"** (zielony check) - obrzeże dostępne od ręki

**Przycisk**: **"ZMIEŃ"** - zmiana koloru/grubości obrzeża

---

## POZIOM 4: SZABLON NAWIERTÓW

### 4.1. Wybór szablonu nawiertów (8 opcji):

1. **Formatka bez nawiertów**
    - Czysty element, tylko cięcie + oklejanie

2. **Wręgowanie i nawierty** ⭐ NOWOŚĆ
    - Rowki pod plecy + otwory konstrukcyjne
    - Najbardziej złożony szablon

3. **Front lewy**
    - Nawierty pod zawiasy lewe + uchwyt

4. **Front prawy**
    - Nawierty pod zawiasy prawe + uchwyt

5. **Front uchylny**
    - Zawiasy uchylne (góra/dół korpusu)

6. **Front uchylny** (drugi typ)
    - Wariant zawiasów uchylnych

7. **Front szuflady**
    - Nawierty pod prowadnice szuflad

8. **Frezowanie pod wózki Aluprofil** ⭐ NOWOŚĆ
    - Specjalne frezowanie pod systemy jezdne

---

## POZIOM 5: KONFIGURACJA ZAWIASÓW (dla szablonu "Front lewy/prawy")

### 5.1. Typ zawiasu

Dropdown: **"BLUM puszka 35mm (wkręty)"**

- Inne opcje: Salice, Hettich, GTV (różni producenci)

**Parametry techniczne**:

- **Ilość nawiertów zależna od długości boku**: automatyczne wyliczenie
- **Średnica nawiertu**: 35mm (standard europejski)
- **Głębokość nawiertu**: 13,5mm (precyzja ±0.1mm)

---

## POZIOM 6: KONFIGURACJA UCHWYTU

### 6.1. Typ uchwytu

- **Brak** (radio)
- **Typowe (2 nawierty)** (radio)
- **Gałka (1 nawiert)** (radio - zaznaczone)

### 6.2. Tył frontu - pozycja uchwytu

Dropdown: **"od góry/dołu" + wartość liczbowa**

- **x1**: 100 mm (odległość od górnej krawędzi)
- **x2**: 100 mm (odległość od dolnej krawędzi - jeśli 2 nawierty)

**Orientacja**:

- **Poziomy** (radio)
- **Pionowy** (radio)

### 6.3. Współrzędne nawiertów (Ø5mm)

- **x: prawy** - 546 mm (dropdown: prawy/lewy/środek)
- **y: środek** - 356 mm (dropdown: środek/góra/dół)

**LUB** ręczne wartości liczbowe

### 6.4. Rozstaw nawiertów uchwytu (NIE długość uchwytu)

- **z**: dropdown (wartość w mm) - odległość między otworami dla uchwytu 2-punktowego
- **Uwaga**: To NIE jest długość samego uchwytu, tylko rozstaw centrów otworów!

---

## POZIOM 7: WRĘGOWANIE (ROWKI)

### 7.1. Checkbox: "Wręgowanie (nutowanie)"

Aktywuje funkcję frezowania rowków pod plecy HDF.

### 7.2. Parametry wręgowania

- **Powierzchnia**: Przód/Tył (dropdown)
- **Krawędź**: Krawędź 1/2/3/4 (dropdown - która krawędź ma rowek)
- **Głębokość**: 9 mm (dropdown: 6/8/9/10/12 mm)
- **Szerokość wręgu**: 3,2 mm (dropdown: 2.8/3.0/3.2/4.0 mm)
    - **Znaczenie**: dopasowanie do grubości pleców HDF (3mm plecy = 3.2mm rowek)
- **Odległość od krawędzi**: 44 mm (dropdown: typowo 5-10mm od krawędzi tylnej)

### 7.3. Rodzaj wręgowania

- **Przelotowe** (radio - zaznaczone) - rowek przez całą długość
- **Nieprzelotowe** (radio) - rowek z zatrzymaniem (np. pod szklane plecy)

**Przycisk**: **"+ dodaj wręg"** - możliwość wielu rowków na jednej formatce

---

## POZIOM 8: WIERCENIE W PŁASZCZYŹNIE

### 8.1. Checkbox: "Wiercenie w płaszczyźnie"

**Uwaga**: "Pozycja nawiertu jest liczona od środka nawiertu" (nie od krawędzi otworu!)

### 8.2. Parametry nawiertu

1. **Powierzchnia**: Przód/Tył (dropdown)
2. **Wsp X**: 200 mm (odległość od punktu 0 w osi X)
3. **Wsp Y**: 50 mm (odległość od punktu 0 w osi Y)
4. **Średnica nawiertu**: 15 mm (dropdown: 5/8/10/15/20/25/35 mm)
5. **Głębokość nawiertu**: 10 mm (dropdown: 5/8/10/12/15/20/przelot)
6. **Typ nawiertu**: wielowiert (dropdown: pojedynczy/wielowiert/pogłębienie)
    - **Wielowiert**: otwór z pogłębieniem pod łeb wkręta
7. **Ilość nawiertów**: 2 szt
8. **Odległość między nimi**: 20 mm
9. **Kierunek**: w osi X (dropdown: w osi X / w osi Y)

**Przycisk**: **"+ dodaj nawiert"** - możliwość wielu grup otworów

---

## POZIOM 9: WIERCENIE W CZOLE (BOKU)

### 9.1. Checkbox: "Wiercenie w czole (boku)"

**Uwaga**: "Nawiert jest robiony na środku grubości płyty. Odległość jest liczona do środka nawiertu."

### 9.2. Parametry nawiertu w boku

1. **Krawędź**: Krawędź 1/2/3/4 (dropdown - który bok)
2. **Odległość od 0**: 50 mm (pozycja wzdłuż krawędzi)
3. **Średnica nawiertu**: 8 mm (dropdown)
4. **Głębokość nawiertu**: 20 mm (dropdown)
5. **Typ nawiertu**: pojedynczy (dropdown: pojedynczy/wielowiert)

**Uwaga techniczna**: Otwór w boku jest zawsze na środku grubości płyty (dla 19mm płyty = 9.5mm od powierzchni).

**Przycisk**: **"+ dodaj nawiert"**

---

## POZIOM 10: ODBICIE NAWIERTÓW I OBRZEŻY

### 10.1. Odbicie nawiertów i obrzeży w tej formatce

Funkcja mirror/odbicia lustrzanego:

- **Odbicie X (w pionie)**: checkbox + ikona z kropkami
- **Odbicie Y (w poziomie)**: checkbox + ikona z kropkami

**Znaczenie**:

- Szybkie utworzenie formatki prawej z lewej (lub odwrotnie)
- Obrzeża i nawiertu są automatycznie odbijane
- Oszczędność czasu konfiguracji dla elementów symetrycznych

---

## POZIOM 11: ZARZĄDZANIE FORMATKAMI

### 11.1. Akcje na formatce

- **"+ KOPIUJ OSTATNIĄ FORMATKĘ"** - duplikacja z możliwością edycji
- **"+ DODAJ KOLEJNĄ FORMATKĘ DO WYCIĘCIA"** - nowa pusta formatka

### 11.2. Import/Export

- **"Wczytaj listę formatek z CSV"**
    - Import z PRO100 (program projektowy)
    - Zwryfikuj dane po wczytaniu!
    - CSV obsługiwany przez system

**Opcje wczytania**:

- **Dodaj do bieżącej listy** (radio - zaznaczone)
- **Zastąp bieżącą listę** (radio)

**Przycisk**: **"WCZYTAJ PLIK"**

### 11.3. Zamówienie

**"ZAMÓW PRÓBKI I WZORNIKI"** - główny przycisk akcji (pomarańczowy)

---

## KLUCZOWE DECYZJE TECHNOLOGICZNE

### 1. Sekwencja obróbki na CNC:

```
1. Cięcie formatowe (pilarka)
2. Oklejanie krawędzi (oklejarka)
3. Nawiercanie płaskie (wiertarka CNC)
4. Wręgowanie (frezarka CNC)
5. Nawiercanie w czole (wiertarka pozioma CNC)
```

### 2. System współrzędnych:

- **Punkt 0,0**: dolny lewy róg formatki (narożnik 0)
- **Oś X**: pozioma (→ w prawo)
- **Oś Y**: pionowa (↑ w górę)
- **Numeracja krawędzi**: 1-góra, 2-prawo, 3-dół, 4-lewo (zgodnie z ruchem wskazówek zegara)

### 3. Tolerancje:

- Nawiercanie Ø35mm (zawiasy): ±0.1mm
- Wręgowanie: ±0.2mm
- Oklejanie: dokładność styku ±0.1mm

### 4. Zależności:

- **Długość boku → ilość zawiasów**:
    - do 500mm: 2 zawiasy
    - 500-900mm: 3 zawiasy
    - > 900mm: 4 zawiasy
- **Grubość pleców HDF → szerokość wręgu**:
    - 3mm HDF → 3.2mm rowek

---

## PROCES PRODUKCJI SZAFKI DOLNEJ Z DRZWIAMI

### 1. Projektowanie i przygotowanie

- Projekt w CAD (często Basis, Imos, Cabinet Vision)
- Wygenerowanie listy elementów z wymiarami netto
- Dodanie okleiny/obrzeża (zwykle 2mm ABS lub PCV) do wymiarów brutto
- Optymalizacja rozkroju na formatki (minimalizacja odpadu)

### 2. Cięcie formatowe na pilarce

Pierwsza operacja - cięcie płyt wiórowych/MDF na elementy:

- **Korpus**: bok lewy, bok prawy, dno, góra, tył (płyta HDF 3mm lub wiórowa 18mm)
- **Drzwi**: płyta frontowa (często płyta lakierowana lub fornirowana)
- Tolerancja: ±0.5mm, ale dobra pilarka osiąga ±0.2mm

### 3. Oklejanie krawędzi

Na oklejarce krawędziowej:

- Naniesienie kleju hotmelt
- Docisk okleiny (ABS, PCV, fornir)
- Frezowanie góra/dół (obcięcie nadmiaru)
- Frezowanie kopytko (zaokrąglenie krawędzi)
- Cyklinowanie (wygładzenie)
- **Krawędzie widoczne**: 2mm ABS
- **Krawędzie niewidoczne**: 0.4-1mm PCV lub bez okleiny

### 4. Obróbka CNC

#### A. Nawiercanie (drilling)

- **Otwory konstrukcyjne Ø5mm** - na minifix/excentryki (montaż korpusu)
    - Głębokość: 12-13mm dla gniazda minifix
    - Rozstaw: według systemu 32mm
- **Otwory pod półkodrzymacze** - Ø5mm, głębokość 10-12mm
- **Otwory pod zawiasy** - Ø35mm (standard europejski), głębokość 11.5-13mm
- **Nawierty pod wkręty** - Ø2.5-3mm dla wkrętów 4x30mm

#### B. Frezowanie (routing)

- **Rowki pod tył** - frez Ø6-8mm, głębokość 10mm, odległość od krawędzi 5-8mm
- **Wycięcia pod zawiasy** - jeśli drzwi wpuszczane
- **Uchwyty frezowane** - profile w drzwiach lub frontach
- **Fazowanie** - delikatne sfazowanie ostrych krawędzi (45° 0.5-1mm)

#### C. Wręgowanie (grooving)

- **Rowek pod plecy HDF** - szerokość 3-4mm, głębokość 8-10mm
- Położenie: 5-10mm od tylnej krawędzi boków i dna/góry

### 5. Montaż okuć

Na podłodze montażowej:

- **Minifix** - wkręcenie śrub minifix w front boków, włożenie excentryków w dno/górę
- **Zawiasy** - montaż misek zawiasowych w drzwiach (na otwory Ø35mm)
- **Prowadnice szuflad** - jeśli szafka z szufladami
- **Stopki regulowane** - wkręcenie w dno korpusu

### 6. Składanie korpusu

- Połączenie boków z dnem i górą (minifix/confirmat)
- Wbicie pleców HDF w rowki
- Sprawdzenie kątów (90°) i przekątnych
- Zabezpieczenie kątownikami/metalownikami jeśli potrzeba

### 7. Montaż drzwi

- Przykręcenie ramion zawiasów do boków korpusu
- Regulacja drzwi (3 płaszczyzny):
    - **Głębokość** - wkręt z tyłu zawiasu
    - **Luz boczny** - przesuw ramienia zawiasu
    - **Wysokość** - otwory montażowe zawiasu

### 8. Kontrola jakości

- Sprawdzenie wymiarów
- Jakość okleiny (brak odprysków, równomierne klejenie)
- Dokładność nawiercania
- Działanie zawiasów
- Szczeliny między drzwiami (równomierne 2-3mm)

### 9. Pakowanie

- Ochrona narożników (styropian/karton)
- Folia stretch lub karton
- Etykieta z oznaczeniem klienta i pozycji

---

## TYPOWE WYMIARY SZAFKI DOLNEJ D60

- Wysokość: 720mm (korpus) + stopki 100mm = 820mm z blatem
- Głębokość: 560mm (korpus), 600mm z drzwiami
- Szerokość: 600mm (zewnętrzna)
- Grubość płyty: 18mm (korpus), 18-19mm (drzwi)

## KLUCZOWE PARAMETRY CNC

- **Prędkość wrzeciona**: 12,000-18,000 RPM
- **Posuw roboczy**: 3-8 m/min (wiercenie), 4-12 m/min (frezowanie)
- **Tolerancja**: ±0.1mm dla nawiercania pod minifix
