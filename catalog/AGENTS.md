## Co robiliśmy

Zbudowaliśmy system katalogu materiałów meblowych z YAML → JSON → Vite frontend.
Model: **Decor + Variant** — dekor (kolor/wzór) + warianty materiałowe (płyta, MDF, HPL...).

---

## Architektura danych (co gdzie mieszka)

```
data/materials/
├── shared/
│   ├── concepts.yaml       ← wspólne tagi, typy powierzchni, kolorystyka
│   └── schema.js           ← Zod walidacja (DecorSchema, VariantSchema, DecorsFileSchema)
├── kronospan/
│   ├── collections.yaml    ← metadane kolekcji + definicje 18 struktur (SM, PE, BS...)
│   ├── decors.yaml         ← 177 dekorów, 180 wariantów (JEDYNE źródło prawdy)
│   └── img/                ← (obrazy są w catalog/public/)
├── tests/
│   ├── validate.test.js    ← 75 testów
│   └── fixtures/
│       └── acrylic-gloss-ref.js ← dane referencyjne z PDF
└── build.js                ← YAML → catalog.json + walidacja

catalog/
├── public/
│   ├── catalog.json        ← generowany (gitignored)
│   └── kronospan/img/      ← zdjęcia dekorów (K8685.jpg, K0190.jpg...)
├── index.html              ← frontend Alpine.js (z filtrami: materiał, kolor, struktura)
├── vite.config.mjs
├── Makefile                ← make dev / test / build / validate
└── package.json
```

---

## Model danych: Decor + Variant

```yaml
# decors.yaml — JEDEN dekor = JEDNA tożsamość wizualna
- id: K8685
  name: Biel Alpejska
  color_family: bialy
  ncs: S 0500-N
  ral: '9016'

  variants:                    # ← warianty materiałowe
    - id: K8685-CH
      material: chipboard      # płyta wiórowa
      collection: global
      structure: SM
      roles: [front]
      edge: { code: K-8685-SM/BS/PD, supplier: Schilsner }

    - id: K8685-AG
      material: mdf_acrylic    # MDF akrylowy
      collection: acrylic_gloss
      structure: AG
      roles: [front]
      thickness_mm: 18.3
      format: [2800, 1300]
      sidedness: one_sided
      edge: { code: K-8685-HG/AG, supplier: Schilsner, finish: HG }
```

### Kluczowe zasady:
- **Decor** = tożsamość (kolor, wzór, NCS, RAL, color_family) — niepowtarzalny
- **Variant** = konkretny materiał + format — purchasable, ma `id`, `material`, `roles`
- **Variant ID** = `{decor_id}-{material_suffix}` (np. `K8685-CH`, `K8685-AG`)
- **Jeden plik `decors.yaml`** — jedyne źródło prawdy
- **Multi-variant** — K8685, K0514, K7045 mają po 2 warianty (chipboard + mdf_acrylic)

---

## Typy materiałów (MATERIAL_TYPES)

| Typ | Opis | Przykład |
|-----|------|---------|
| `chipboard` | płyta wiórowa laminowana | Global Collection |
| `mdf_acrylic` | MDF z powłoką akrylową | Acrylic Gloss |
| `mdf_lacquered` | MDF lakierowany | (przyszłość) |
| `mdf_foil` | MDF foliowany | (przyszłość) |
| `compact` | compact HPL | Compact Interior |
| `hpl` | HPL na chipboard | (przyszłość) |
| `worktop` | blat roboczy | (przyszłość) |
| `splashback` | panel ścienny | (przyszłość) |

---

## Role elementów (ROLES)

| Rola | Opis | Przykład |
|------|------|---------|
| `carcass` | korpus (boki, półki, dno) | biała płyta 18mm |
| `front` | front (drzwi, szufronty) | MDF akryl, lakierowany |
| `worktop` | blat roboczy | HPL 28mm, kamień |
| `splashback` | panel ścienny | HPL 6mm, szkło |
| `plinth` | cokół | płyta 10-16mm |
| `side_panel` | panel boczny zabudowy | płyta 18mm |
| `housing` | maskownica (lodówka, zmywarka) | front / płyta |

---

## Źródło prawdy

```
PDF katalogu producenta    ← ULTIMATE SOURCE
  │
  ▼  ręcznie / skrypt
YAML: decors.yaml          ← KANONICZNE ŹRÓDŁO DLA APLIKACJI
  │
  ▼  build.js
JSON: catalog.json          ← generowane, nigdy nie edytować
  │
  ▼  fetch()
Frontend: index.html        ← czyta JSON, wyświetla
```

---

## Walidacja (75 testów)

| Test suite | Co sprawdza |
|---|---|
| Schema Validation | DecorsFileSchema, material types, roles |
| Identity Model | K-prefix, variant ID pattern, uniqueness |
| Color Family | obecność, poprawne enumy, ≥15 rodzin |
| Multi-variant Decors | K8685/K0514/K7045 mają 2 warianty, łącznie 177/180 |
| Variant Completeness | edge na chipboard, thickness+format na mdf_acrylic |
| Reference Data | migracja acrylic-gloss zachowała dane |
| Cross-reference | struktury i kolekcje istnieją w collections.yaml |

---

## Frontend

- **Karty** = warianty (nie dekory) — każdy wariant osobna karta
- **Filtry**: producent, powierzchnia, struktura, tagi, **materiał**, **kolor (color_family)**, szukaj
- **Szczegóły**: dekor + wariant, NCS/RAL, obrzeże, struktura, zastosowanie (roles)

---

## Jak dodać nową kolekcję

1. Utwórz `data/materials/{producer}/decors.yaml` (lub dodaj warianty do istniejącego)
2. Dodaj metadane w `{producer}/collections.yaml` (struktury, formaty)
3. Uruchom `make build`
4. Dodaj obrazy dekorów do `catalog/public/{producer}/img/`
5. Uruchom `make test`

---

## Komendy

```bash
cd catalog
make dev         # dev server → http://localhost:5173
make build       # YAML → catalog.json
make test        # 75 testów
make validate    # build + test
```

---

## Historia modelu

Poprzedni model (do 2026-06-26): osobne pliki `global-collection.yaml` + `acrylic-gloss.yaml`, dekory jako płaskie obiekty.
Aktualny model: jeden `decors.yaml`, dekory z wariantami (Decor + Variant).

---

## Co NIE działa / brakuje

- [ ] Zdjęcia dekorów Global Collection (tylko 55 z 174 ma pliki img)
- [ ] Swiss Krono i Egger (puste, czekają na dane)
- [ ] Substitutions.yaml (zamienniki między producentami)
- [ ] Eksport do CSV / druk
- [ ] Blaty, splashback, compact (osobne kolekcje YAML)
- [ ] Ceny materiałów
