# Blaty FitLine — Specyfikacja techniczna

## Analiza kolekcji (strony 10-11 z katalogu, str. 49-50)

---

## 1. Definicja i zastosowanie

**Blaty FitLine** to nowa kolekcja blatów roboczych (NOWOŚĆ | NEW) o cieńszej konstrukcji niż blaty postformed. Charakteryzują się prostym profilem U z zaokrągleniem R=3.3mm.

### Zastosowanie:
- Blaty kuchenne
- Blaty stołowe
- Blaty biurek

---

## 2. Budowa przekroju (str. 49)

```
┌─────────────────────────────────────────────────────┐
│  Pasek HDF  │  HPL dekoracyjny  │  Pasek HDF       │  ← góra
├─────────────────────────────────────────────────────┤
│                   Płyta wiórowa                      │  ← rdzeń
├─────────────────────────────────────────────────────┤
│              Laminat CPL (Craft Paper)               │  ← spód
├─────────────────────────────────────────────────────┤
│         Pasek klejowy (Silicone strip)               │  ← klej
└─────────────────────────────────────────────────────┘
```

### Warstwy (od dołu do góry):

| Warstwa | Materiał | Funkcja |
|---------|----------|---------|
| **1. Klej** | Pasek klejowy (Silicone strip) | Mocowanie obrzeża |
| **2. Spód** | Laminat CPL (Craft Paper) | Ochrona spodu |
| **3. Rdzeń** | Płyta wiórowa | Główny materiał nośny |
| **4. Wzmocnienie** | Pasek HDF (lewy i prawy) | Wzmocnienie krawędzi |
| **5. Górna** | HPL dekoracyjny | Warstwa dekoracyjna i ochronna |

### Kluczowe cechy konstrukcji:

1. **Cieńsza konstrukcja** - 18 mm vs 38 mm w postformed
2. **Prosty profil U** - R = 3.3 mm, jedna krawędź wykończona
3. **Paski HDF** - wzmocnienie po obu stronach krawędzi
4. **Laminat CPL** - laminat papierowy na spodzie

---

## 3. Profile blatów (str. 49)

### Profile U (jedna krawędź wykończona)

```
     ←───────────── 900 mm ─────────────→
    ┌────────────────────────────────────┐
    │  ╭──────────────────────────────╮  │
    │  │                              │  │  R = 3.3 mm
    │  │        Płyta wiórowa         │  │
    │  │                              │  │
    │  ╰──────────────────────────────╯  │
    └────────────────────────────────────┘
              ↑ krawędź postformed
```

- **Szerokość**: 900 mm
- **Grubość**: 18 mm
- **Krawędź**: jedna strona wykończona (frontowa)
- **Zastosowanie**: blaty przy ścianie

---

## 4. Tabela pakowania (str. 49)

| Grubość (mm) | Długość (mm) | Szerokość (mm) | Profil | Sztuk w palecie |
|--------------|--------------|----------------|--------|-----------------|
| 18 | 4100 | 900 | U | 10 |

### Wymiary stałe:
- **Grubość**: 18 mm
- **Długość**: 4100 mm
- **Szerokość**: 900 mm

---

## 5. Tabela techniczna — FitLine (str. 49-50)

### Kolumny tabeli:

| # | Kolumna | Opis |
|---|---------|------|
| 1 | **Dekor** | Kod dekoru |
| 2 | **Str.** | Struktura powierzchni (skrót) |
| 3 | **Nazwa PL** | Nazwa polska |
| 4 | **Profil U (900mm)** | Dostępność: EX=Express 24h, K=konfekcja |
| 5 | **Splashback** | • = dostępny |
| 6 | **Obrzeże ABS** | Kod obrzeża ABS Schilsner |

### Dekory FitLine (5 szt.):

| Lp | Dekor | Str | Nazwa PL | Profil U 900mm | Splashback | Obrzeże ABS |
|----|-------|-----|----------|----------------|------------|-------------|
| 1 | 868S | RS | Biel Alpejska | EX, K | • | Spander |
| 2 | 2794 | BS | Marmur Calacatta | EX, K | • | Spander |
| 3 | 2738 | FP | Dąb Cremona Torro | EX, K | • | Spander |
| 4 | 5527 | FP | Dąb Kamienny | EX, K | • | Spander |
| 5 | 0190 | RS | Czarny | EX, K | • | Spander |

---

## 6. Dopasowanie produktów

| Produkt | Format | Grubość | Uwagi |
|---------|--------|---------|-------|
| **Blat FitLine** | 4100 x 900 mm | 18 mm | Profil U |
| **Splashback** | — | — | • = dostępny |
| **Obrzeże ABS Spander** | — | — | Do każdego blatu |

---

## 7. Uwagi techniczne

### Obrzeże Spander (Schilsner):
> Do każdego blatu FitLine dostępne obrzeże ABS Spander od Schilsner.
> Profesjonalne rozwiązanie do wykańczania krawędzi blatów kuchennych i roboczych.

### Różnice vs Postformed:
| Cecha | FitLine | Postformed |
|-------|---------|------------|
| Grubość | **18 mm** | 38 mm |
| Profil | U (900 mm) | U (600 mm), U-U (900, 1200 mm) |
| Konstrukcja | Cieńsza, lżejsza | Grubsza, cięższa |
| Zastosowanie | Blaty, stoły | Blaty kuchenne |

---

## 8. Encja techniczna (JSON)

```json
{
  "product": "Blaty robocze FitLine",
  "manufacturer": "Kronospan",
  "catalog": "Global Collection 2026",
  "new_collection": true,
  "construction": {
    "layers": [
      {"position": "bottom", "material": "Pasek klejowy (Silicone strip)", "function": "Mocowanie obrzeża"},
      {"position": "bottom_laminate", "material": "Laminat CPL (Craft Paper)", "function": "Ochrona spodu"},
      {"position": "core", "material": "Płyta wiórowa", "function": "Materiał nośny"},
      {"position": "reinforcement", "material": "Pasek HDF (lewy i prawy)", "function": "Wzmocnienie krawędzi"},
      {"position": "top", "material": "HPL dekoracyjny", "function": "Warstwa dekoracyjna i ochronna"}
    ],
    "total_thickness_mm": 18,
    "edge_radius_mm": 3.3
  },
  "profiles": [
    {
      "type": "U",
      "description": "Jedna krawędź wykończona (postformed)",
      "widths_mm": [900],
      "edge_finish": "single"
    }
  ],
  "dimensions": {
    "thickness_mm": 18,
    "length_mm": 4100,
    "widths_mm": [900]
  },
  "packaging": [
    {"width_mm": 900, "profile": "U", "pieces_per_pallet": 10}
  ],
  "decors": [
    {"lp": 1, "code": "868S", "structure": "RS", "name": "Biel Alpejska", "profile_u_900": "EX, K", "splashback": true, "abs_edge": "Spander"},
    {"lp": 2, "code": "2794", "structure": "BS", "name": "Marmur Calacatta", "profile_u_900": "EX, K", "splashback": true, "abs_edge": "Spander"},
    {"lp": 3, "code": "2738", "structure": "FP", "name": "Dąb Cremona Torro", "profile_u_900": "EX, K", "splashback": true, "abs_edge": "Spander"},
    {"lp": 4, "code": "5527", "structure": "FP", "name": "Dąb Kamienny", "profile_u_900": "EX, K", "splashback": true, "abs_edge": "Spander"},
    {"lp": 5, "code": "0190", "structure": "RS", "name": "Czarny", "profile_u_900": "EX, K", "splashback": true, "abs_edge": "Spander"}
  ],
  "total_decors": 5,
  "edge_bandings": {
    "abs_spander": "Spander by Schilsner - do każdego blatu"
  },
  "notes": [
    "Nowa kolekcja (NOWOŚĆ | NEW)",
    "Cieńsza konstrukcja (18 mm) niż blaty postformed (38 mm)",
    "Do każdego blatu dostępne obrzeże ABS Spander od Schilsner"
  ]
}
```

---

*Analiza wykonana: 2026-06-27*
*Źródła: blaty.pdf str. 10-11 (FitLine)*