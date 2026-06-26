# Kronospan Board Catalog — Data Schema

Normalized schema to represent all Kronospan 2026 collections.

---

## Entity Relationship (text)

```
Decor (master identity)
  ├── has many → Product (one per collection × structure × thickness × format)
  │     ├── has one → Collection (base physical properties)
  │     ├── has one → Structure (surface texture/finish)
  │     ├── has many → LaminationOption (which sides, codes)
  │     ├── has one → EdgeBanding (optional, per product)
  │     └── has many → ExpressAvailability (per thickness)
  │
  ├── has many → HdfLaminate (optional, fixed format)
  ├── has many → Countertop (optional, different code scheme)
  └── has many → CrossCollectionMatch (same decor in other collections)
```

---

## Tables

### `decor`

Master color/pattern identity. Shared across all product forms.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | text PK | yes | e.g. `"8685"`, `"AL01"` |
| `name_pl` | text | yes | `"Biel Alpejska"` |
| `group_code` | text | nullable | Roman numeral: `"XXI"`, `"XXIII"`, `"XXV"` |
| `group_name` | text | nullable | `"Color Basic"`, `"Aluminium"` |
| `ncs` | text | nullable | `"S 0500-N"` |
| `ral` | text | nullable | `"9016"` |
| `pantone` | text | nullable | `"Process Black C"` |
| `notes` | text | nullable | Free text |

**PK**: `id` (decor code — globally unique within Kronospan)

---

### `structure`

Surface texture/finish descriptor. Independent of collection.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `code` | text PK | yes | `"SM"`, `"PE"`, `"AG"`, `"SU"`, `"AL"` |
| `name` | text | yes | `"Super Mat"`, `"Pearl Effect"` |
| `fingerprint_resistant` | bool | no | default false |
| `antibacterial` | bool | no | default false |
| `texture_type` | text | no | `"smooth"`, `"brushed"`, `"wood_grain"`, `"stone"` |
| `finish` | text | no | `"gloss"`, `"matt"`, `"silk_matt"`, `"structured"` |
| `notes` | text | nullable | |

**Notes on ambiguity**: The same structure code can appear in multiple collections
with slightly different physical properties. If this matters, the `Product` row
captures the actual realized properties. `Structure` is the semantic label.

---

### `collection`

Product line / manufacturing family.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | text PK | yes | `"global"`, `"acrylic_gloss"`, `"mdf_lux"`, `"mdf_standard"` |
| `name` | text | yes | `"Global Collection 2026"`, `"Acrylic Gloss"` |
| `core_material` | enum | yes | `chipboard`, `mdf`, `hdf`, `compact` |
| `face_material` | text | yes | Free text describing face layers |
| `back_material` | text | yes | Free text describing back layers |
| `sidedness` | enum | yes | `one_sided`, `two_sided_same`, `two_sided_different` |
| `standard_thickness_mm` | float | yes | Primary thickness |
| `standard_width_mm` | int | yes | Sheet width |
| `standard_length_mm` | int | yes | Sheet length |
| `source_pdf` | text | no | PDF filename |
| `source_pages` | text | no | `"114–118"` |

**Collections identified**:

| id | core_material | standard_thickness | format (L×W) | sidedness |
|----|--------------|-------------------|--------------|-----------|
| `global` | chipboard | 12/16/18 | 2800×2070 | two_sided_same |
| `acrylic_gloss` | mdf | 18.3 | 2800×1300 | one_sided |
| `acrylic_matt` | mdf | 18.3 | 2800×1300 | one_sided |
| `mirror_gloss` | mdf | 18.0 | 2800×2050 | two_sided_same |
| `mirror_matt` | mdf | 18.0 | 2800×2050 | two_sided_same |
| `mdf_lux` | mdf | 18.0 | 2800×2070 | two_sided_same |
| `metal` | mdf | 18.7 | 2800×1300 | two_sided_different |
| `mdf_standard` | mdf | 38.0 | 2800×2070 | varies |
| `mdf_plus` | mdf | 16–28 | 2800×2070 / 2620×2070 | varies |
| `mdf_extra` | mdf | 18–19 | 2800×2070 / 2620×2070 | two_sided_same |

---

### `product`

A purchasable board. The core fact table.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | text PK | yes | Generated: `"{decor_id}:{collection_id}:{structure_code}"` |
| `decor_id` | FK → decor | yes | |
| `collection_id` | FK → collection | yes | |
| `structure_code` | FK → structure | yes | |
| `thickness_mm` | float | yes | Actual thickness (18.3, 18.7, 18.0, etc.) |
| `width_mm` | int | yes | Sheet width (1300, 2050, 2070) |
| `length_mm` | int | yes | Sheet length (2800) |
| `konfekcja` | bool | no | Piece-order available (K in catalog) |
| `notes` | text | nullable | |

**Example rows**:

| id | decor_id | collection_id | structure_code | thickness_mm | width_mm | length_mm |
|----|----------|--------------|----------------|-------------|----------|-----------|
| `8685:global:SM` | 8685 | global | SM | 18.0 | 2070 | 2800 |
| `8685:acrylic_gloss:AG` | 8685 | acrylic_gloss | AG | 18.3 | 1300 | 2800 |
| `8685:acrylic_matt:AM` | 8685 | acrylic_matt | AM | 18.3 | 1300 | 2800 |
| `8685:mirror_gloss:MG` | 8685 | mirror_gloss | MG | 18.0 | 2050 | 2800 |
| `8685:mirror_matt:MM` | 8685 | mirror_matt | MM | 18.0 | 2050 | 2800 |
| `8685:mdf_lux:SU` | 8685 | mdf_lux | SU | 18.0 | 2070 | 2800 |
| `AL01:metal:AL` | AL01 | metal | AL | 18.7 | 1300 | 2800 |

---

### `product_thickness_option`

Some products are available in multiple thicknesses (MDF Plus/Extra, Global Collection).

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `product_id` | FK → product | yes | |
| `thickness_mm` | float | yes | |
| `express_24h` | bool | no | EX in catalog |

**Composite PK**: `(product_id, thickness_mm)`

---

### `lamination_option`

Which sides are laminated and with what code. Critical for MDF Standard/Plus/Extra.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | serial PK | yes | |
| `product_id` | FK → product | yes | |
| `code` | text | yes | `"0110"`, `"0101"`, `"0004"` |
| `front` | text | yes | Description of front face |
| `back` | text | yes | Description of back face |
| `sides_laminated` | enum | yes | `one`, `two_same`, `two_different` |

**Codes**:
| code | meaning |
|------|---------|
| `0110` | Front: decor, Back: decor (or balancing) |
| `0101` | Front: decor, Back: white/balancing |
| `0004` | Front: decor, Back: raw/special |

---

### `back_decor`

For products with `two_sided_different` — specifies what's on the back.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `product_id` | FK → product PK | yes | |
| `back_decor_id` | FK → decor | yes | What decor is on back |
| `back_structure_code` | FK → structure | nullable | If different from front |

**Example**: Metal AL08 (Tytan) → back is AL06 (Brąz).

---

### `edge_banding`

Edge banding reference per product.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | serial PK | yes | |
| `product_id` | FK → product | yes | |
| `supplier` | text | yes | `"Schilsner"`, `"Spander"` |
| `catalog_code` | text | yes | `"K-8685-SM/BS/PD"`, `"K-8685-HG/AG"` |
| `edge_finish` | text | no | `"HG"` (high gloss), `"UM"` (ultra matt) |
| `edge_material` | text | no | `"ABS"`, `"PVC"` |
| `edge_width_mm` | int | no | 23mm for Metal |
| `edge_thickness_mm` | float | no | 1mm for Metal |
| `order_only` | bool | no | default false (Metal edge is order-only) |
| `roll_length_m` | int | nullable | 75m for Metal |

**Edge finish acronyms** (from catalog):
| acronym | meaning |
|---------|---------|
| HG | High Gloss |
| UM | Ultra Matt |
| AG | Acrylic Gloss (edge matches board) |
| AM | Acrylic Matt (edge matches board) |
| AL | Aluminium |

---

### `hdf_laminate`

HDF laminate available for Global Collection decors.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | serial PK | yes | |
| `decor_id` | FK → decor | yes | |
| `thickness_mm` | float | yes | Always 0.8 |
| `width_mm` | int | yes | 1320 |
| `length_mm` | int | yes | 3050 |
| `express_24h` | bool | no | Available in Pustkowie |
| `warehouse` | text | nullable | `"Kronospan HPL, Pustkowie"` |

---

### `countertop`

Blaty robocze — matched countertops for selected decors.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | text PK | yes | `"868S"`, `"0190"`, `"K523"` |
| `matched_decor_id` | FK → decor | yes | Which decor this matches |
| `name` | text | nullable | |
| `structure_code` | text | nullable | `"RS"` (Robocze/Countertop) |
| `notes` | text | nullable | |

**Note**: Countertop codes differ from decor codes (`868S` vs `8685`).

---

### `cross_collection_match`

Which decors from Global Collection are available in which specialized collections.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `decor_id` | FK → decor | yes | |
| `collection_id` | FK → collection | yes | |
| `available` | bool | yes | |

**Composite PK**: `(decor_id, collection_id)`

This replaces the AG, AM, MG, CI, KA columns in the Global Collection table.

---

## Special Cases Handled

| Case | How |
|------|-----|
| Same decor code in multiple collections | Multiple `product` rows with same `decor_id` |
| Different surface structures for same decor | Multiple `product` rows with different `structure_code` |
| MDF Plus/Extra multi-thickness | `product_thickness_option` table |
| Metal AL08 asymmetric back | `back_decor` table |
| Edge banding finish ≠ board surface | Separate `edge_finish` field in `edge_banding` |
| MDF Standard as capability matrix | Separate collection, no decors in `product` (used as template) |
| Express 24h per thickness | `express_24h` flag on `product_thickness_option` or `hdf_laminate` |
| Countertop different code scheme | `countertop` table with `matched_decor_id` FK |
| HDF laminate for all Global decors | `hdf_laminate` table, one row per decor |
| Lamination codes (0110/0101/0004) | `lamination_option` table |
| Konfekcja (piece ordering) | `konfekcja` bool on `product` |
| Order-only edge banding | `order_only` bool on `edge_banding` |

---

## Example Query Patterns

### "What products can I buy in decor 8685 (Biel Alpejska)?"

```sql
SELECT p.id, c.name, s.name, p.thickness_mm, p.width_mm, p.length_mm
FROM product p
JOIN collection c ON c.id = p.collection_id
JOIN structure s ON s.code = p.structure_code
WHERE p.decor_id = '8685';
-- Returns: Global SM, Acrylic Gloss AG, Acrylic Matt AM,
--           Mirror Gloss MG, Mirror Matt MM, MDF LUX SU
```

### "What edge banding for Acrylic Gloss 8685?"

```sql
SELECT eb.catalog_code, eb.edge_finish, eb.edge_material
FROM edge_banding eb
JOIN product p ON p.id = eb.product_id
WHERE p.decor_id = '8685' AND p.collection_id = 'acrylic_gloss';
-- Returns: K-8685-HG/AG, ABS
```

### "Show all MDF Plus availability matrix"

```sql
SELECT p.decor_id, t.thickness_mm, t.express_24h, l.code AS lamination
FROM product p
JOIN product_thickness_option t ON t.product_id = p.id
JOIN lamination_option l ON l.product_id = p.id
WHERE p.collection_id = 'mdf_plus';
```

### "Which decors are available in both Global Collection AND Acrylic Gloss?"

```sql
SELECT d.id, d.name_pl
FROM decor d
WHERE EXISTS (SELECT 1 FROM product WHERE decor_id = d.id AND collection_id = 'global')
  AND EXISTS (SELECT 1 FROM product WHERE decor_id = d.id AND collection_id = 'acrylic_gloss');
```

---

## Data Loading Strategy

1. **Load `decor`** from Global Collection (174 rows) + Metal (6 rows)
2. **Load `structure`** from all collection docs (deduplicated)
3. **Load `collection`** — 10 rows (one per product line)
4. **Load `product`** — join decor × collection × structure from each collection's decor table
5. **Load `edge_banding`** from each collection's edge column
6. **Load `cross_collection_match`** from Global Collection's AG/AM/MG/CI/KA columns
7. **Load `hdf_laminate`** — one row per Global Collection decor
8. **Load `countertop`** from Global Collection's "Blaty robocze" column
9. **Load `back_decor`** for Metal AL08 special case

---

*Schema designed: 2026-06-26*
*Source: 8 extracted Kronospan 2026 catalog files*
