# Kitchen CAD — Dziennik projektu

> **Cel:** Kompleksowy system do projektowania mebli kuchennych na wymiar, generowania szablonów DXF dla CNC i zarządzania produkcją.

---

## 📅 2026-06-17 — Start projektu

### Kontekst

Rozpoczęliśmy od serii pytań o wiedzę technologiczną w europejskim meblarstwie:

1. **System 32** — czym jest, jakie ma wymiary, dlaczego jest fundamentem europejskiego meblarstwa
2. **e-Rozkrój** — czym są systemy online do zamawiania cięcia płyt (eRozrys, FastCut, AGMAsoft)
3. **Formaty plików CNC** — DXF, DWG, CSV — co potrzebne do zlecenia nawierceń w centrum CNC
4. **Standardy nawiertów** — typy otworów, średnice, tolerancje, kompatybilność z okuciami (Blum, Hettich, Grass)
5. **Blum LEGRABOX + BLUMOTION** — specyfikacja techniczna prowadnic do szuflad

### Co zaplanowaliśmy

Stworzenie **kompleksowego dokumentu referencyjnego** (konspekt Markdown) opisującego:

- **Część I:** System 32 — wymiary bazowe, zasady
- **Część II:** Materiały — płyty, okleiny, obrzeża, producenci
- **Część III:** Wymiary standardowych korpusów (dolne, górne, słupki, AGD)
- **Część IV:** Nawiercanie — System 32, zawiasy, prowadnice, uchwyty, złącza
- **Część V:** Okleinowanie krawędzi
- **Część VI:** Przygotowanie plików do CNC (DXF/DWG — zasady, warstwy, tolerancje)
- **Część VII:** e-Rozkrój — systemy online, co można zamówić
- **Część VIII:** Jakość i tolerancje (normy PN-EN)
- **Część IX:** Workflow — od projektu po montaż
- **Część X:** Słownik terminów
- **Załączniki:** Wzory CSV, schematy nawiertów, przelicznik System 32

### Dlaczego?

Bo brakuje **jednego, kompleksowego źródła** które łączy:

- Wiedzę technologiczną (standardy, wymiary, tolerancje)
- Praktykę projektową (jak zaprojektować szafkę)
- Przygotowanie produkcji (jak zlecić CNC)
- Wiedzę o okuciach (Blum, Hettich — co pasuje do czego)

Taki dokument pozwala **sprawnie projektować i zlecać produkcję** bez szukania informacji w wielu źródłach.

---

### Co zostało zrobione

#### 1. Generator szablonów DXF (`generators/legrabox_side_panel.py`)

**Co robi:**
Generuje parametryzowane pliki DXF boku szafki dolnej z nawiertami pod szuflady Blum LEGRABOX + BLUMOTION.

**Dlaczego:**

- Bok szafki to **najczęściej powtarzalny element** w meblarstwie
- LEGRABOX to **najpopularniejszy system szuflad** w europejskich kuchniach
- Ręczne rysowanie DXF jest **czasochłonne i podatne na błędy**
- Parametryzacja pozwala **generować dowolne konfiguracje** jednym poleceniem

**Co zawiera plik DXF:**

- Kontur boku szafki (510×720mm standard)
- Otwory System 32 (∅5mm, 37mm od krawędzi, co 32mm) — 44 szt.
- Otwory pod prowadnice LEGRABOX (∅5mm, 9mm od dna, co 32mm) — 23 szt.
- Otwory pod kołki łączące (∅8mm, dno + góra) — 6 szt.
- Oznaczenia krawędzi do oklejenia (ABS)
- Notatki techniczne i wymiary kontrolne
- 7 warstw zgodnych ze standardami CNC

**Konfiguracje wygenerowane:**
| Plik | Szuflady | Wymiary | Zastosowanie |
|------|----------|---------|--------------|
| `N_M_K_510x720` | Normalna, Średnia, Wysoka | 510×720mm | Standardowa kuchnia |
| `M_M_K_510x720` | Średnia, Średnia, Wysoka | 510×720mm | Większe dolne szuflady |
| `N_K_C_560x720` | Normalna, Wysoka, Bardzo wysoka | 560×720mm | Szersza szafka (560mm) |
| `N_M_K_510x860` | Normalna, Średnia, Wysoka | 510×860mm | Podwyższona (860mm) |

#### 2. Dokumentacja techniczna LEGRABOX (`docs/LEGRABOX_SPEC.md`)

**Co zawiera:**

- Wymiary boków szuflad (N/M/K/C/F)
- Nominalne długości prowadnic (270-650mm)
- Wymiary cięcia dna i tyłu szuflady
- Pozycje mocowania profilu kab. (System 32)
- Specyfikacja BLUMOTION
- Regulacja 3D frontu
- Typowe konfiguracje kuchenne
- Tolerancje i dopuszczalne odchyłki

**Dlaczego:**
Oficjalna dokumentacja Blum jest rozproszona po katalogach PDF. To jest **kompilacja najważniejszych danych** w jednym miejscu, w formacie Markdown.

#### 3. README projektu (`README.md`)

**Co zawiera:**

- Struktura projektu
- Wymagania (Python 3.11 + ezdxf)
- Przykłady użycia generatora
- Tabela warstw DXF
- Instrukcja zlecenia CNC

---

## 🎯 Następne kroki (do zrobienia)

### Priorytet 1 — Rozszerzenie generatora

- [ ] **Front kuchenny z nawiertami pod zawiasy Blum CLIP top** (∅35mm, rozstaw 45mm)
- [ ] **Generator CSV listy formatek** (do importu w e-rozkroju)
- [ ] **Wizualizacja matplotlib** (podgląd DXF bez zewnętrznych programów)

### Priorytet 2 — Pełna szafka

- [ ] **Generator kompletnej szafki** (wszystkie formatki naraz: boki, dno, góra, półki, fronty, plecy)
- [ ] **Eksport do ZIP** (paczka plików DXF + CSV gotowa do wysłania do CNC)

### Priorytet 3 — Kuchnia

- [ ] **Generator kuchni** (z listy szafek → komplet plików DXF)
- [ ] **Optymalizacja rozkroju** (minimalizacja odpadów z płyty)
- [ ] **Wycena materiału** (ile płyt potrzeba, jaki koszt)

### Priorytet 4 — Dokumentacja

- [ ] **Uzupełnienie konspektu** (Części I-X z planu)
- [ ] **Schematy w formacie ASCII** (wymiary, nawiercanie)
- [ ] **Słownik terminów meblarskich** (PL/EN/DE)

---

## 🔧 Decyzje techniczne

### Dlaczego Python + ezdxf?

- **ezdxf** to najpopularniejsza biblioteka Python do generowania DXF
- Python jest łatwy do parametryzacji (zmienne, funkcje, pętle)
- Można zintegrować z innymi narzędziami (CSV, matplotlib, GUI)
- Działa na macOS, Linux, Windows

### Dlaczego DXF R2000?

- **Najszersza kompatybilność** z programami CAD/CAM
- Obsługiwany przez: AutoCAD, LibreCAD, QCAD, Fusion 360, ezdxf
- CNC centra akceptują R2000 bez problemów

### Dlaczego 7 warstw?

- Rozdzielenie operacji CNC (cięcie, wiercenie, frezowanie)
- Operator CNC może włączać/wyłączać warstwy
- Zgodne ze standardami branżowymi
- Kolory warstw odpowiadają konwencjom AutoCAD

### Dlaczego LEGRABOX jako pierwszy?

- **Najpopularniejszy system szuflad** w Europie
- **BLUMOTION** jest zintegrowany (nie wymaga dodatkowych nawierceń)
- **Kompatybilny** z innymi okuciami Blum (CLIP top, AVENTOS)
- **Dokumentacja** jest dostępna i szczegółowa

---

## 📚 Źródła wiedzy

### Oficjalne dokumenty

- Blum Katalog 2022/2023 — pełna specyfikacja LEGRABOX
- Blum EASY ASSEMBLY App — instrukcje montażu
- Blum Product Configurator — dobór okuć online

### Standardy

- System 32 — międzynarodowy standard meblarski (nieznormalizowany formalnie)
- PN-EN 14749 — Meble domowe i kuchenne — Wymagania bezpieczeństwa
- ISO 2768 — Tolerancje ogólne obróbki

### Programy i narzędzia

- ezdxf 1.4.4 — biblioteka Python do generowania DXF
- LibreCAD — darmowy CAD do weryfikacji plików DXF
- eRozrys / FastCut (AGMAsoft) — systemy e-rozkroju online

---

## 📊 Metryki projektu

| Wartość                         | Liczba        |
| ------------------------------- | ------------- |
| Pliki DXF wygenerowane          | 4             |
| Otwory System 32 w jednym pliku | 44            |
| Otwory LEGRABOX w jednym pliku  | 23            |
| Otwory pod kołki                | 6             |
| Warstwy DXF                     | 7             |
| Typy szuflad LEGRABOX           | 5 (N/M/K/C/F) |
| Linie kodu generatora           | ~350          |

---

**Ostatnia aktualizacja:** 2026-06-17
**Autor:** Kitchen CAD Project
**Status:** W trakcie rozwoju
