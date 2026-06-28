-- ══════════════════════════════════════════════════════════════════
-- KUCHNIE CATALOG — Migration Phase 1: Worktop Specifications
-- Version: 1.1.0
-- Date: 2026-06-27
-- Requires: 01-schema.sql
-- ══════════════════════════════════════════════════════════════════
--
-- Adds support for:
--   1. Worktop construction methods (postformed, ABS Square Edge, Slim Line, FitLine, BLACK WOOD)
--   2. Edge profiles (U, U-U, R3, SQUARE, NATURAL)
--   3. Worktop-specific specifications (max length, available widths, edge radius)
--   4. Sheet formats (lookup table — eliminates JSON in `format_mm`)
--   5. Subcollections (Slim Line "Global" vs "Plus")
--   6. Synchronized texture flag on structures (KronoSwiss ♻)
--   7. Bilingual decor names (PL + EN for KronoSwiss)
--   8. Decor metadata flags (one_global, new_2024, discontinued)
--
-- Design principles (same as 01):
--   - CREATE TABLE IF NOT EXISTS (idempotent)
--   - INSERT OR IGNORE for seed data (idempotent)
--   - CHECK constraints for domain validation
--   - FK enforced
--
-- ══════════════════════════════════════════════════════════════════


-- ──────────────────────────────────────────────────────────────────
-- 1. SHEET_FORMATS — lookup table for physical board dimensions
-- ──────────────────────────────────────────────────────────────────
--
-- Replaces ad-hoc JSON in materials.format_mm and variants.format_mm.
-- Examples from analyzed catalogs:
--   2800×2070 — standard chipboard (Kronospan Global, KronoSwiss)
--   2800×1300 — MDF Acrylic Gloss/Matt (Kronospan)
--   2800×2050 — MDF Mirror Gloss (Kronospan)
--   4100×600  — Worktop postformed U (Kronospan, KronoSwiss)
--   4100×900  — Worktop postformed/FitLine U-U (Kronospan, KronoSwiss)
--   4100×1200 — Worktop postformed U-U (Kronospan)
--   4100×635  — Worktop ABS Square Edge single edge (Kronospan)
--   4100×1315 — Worktop BLACK WOOD (KronoSwiss)
--   4100×650  — Slim Line Global (Kronospan)
--   4100×1300 — Slim Line Plus (Kronospan)
--   3050×1320 — HPL laminate roll-out (Kronospan Pustków)
--   4110×1330 — HPL laminate (KronoSwiss Mielec, Kronospan Mielec)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sheet_formats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,           -- '2800x2070', '4100x600', '4100x1315'
    length_mm       INTEGER NOT NULL,               -- larger dimension
    width_mm        INTEGER NOT NULL,               -- smaller dimension
    use_hint        TEXT,                           -- 'board', 'worktop', 'slim', 'acrylic', 'mirror', 'hdf', 'hpl_roll'
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (length_mm > 0 AND width_mm > 0),
    CHECK (length_mm >= width_mm)                   -- canonical orientation
);

CREATE INDEX IF NOT EXISTS idx_sheet_formats_use_hint ON sheet_formats(use_hint);


-- ──────────────────────────────────────────────────────────────────
-- 2. SUBCOLLECTIONS — second-level grouping within a Collection
-- ──────────────────────────────────────────────────────────────────
--
-- Currently used only by Kronospan Slim Line which splits into:
--   - Slim Line "Global Collection" (10 decors, str. 64-65)
--   - Slim Line "Plus" (6 decors, premium)
--
-- KronoSwiss collections (Sensesation, BE Velvet, BLACK WOOD) are flat
-- but the schema supports them — just leave subcollection_id NULL.
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS subcollections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id   INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    slug            TEXT NOT NULL,                  -- 'slim_global', 'slim_plus'
    name            TEXT NOT NULL,                  -- 'Global Collection', 'SlimLine Plus'
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(slug, collection_id)
);

CREATE INDEX IF NOT EXISTS idx_subcollections_collection ON subcollections(collection_id);


-- ──────────────────────────────────────────────────────────────────
-- 3. WORKTOP_CONSTRUCTIONS — manufacturing methods
-- ──────────────────────────────────────────────────────────────────
--
-- Classification of how a worktop is built (orthogonal to material_type):
--   - postformed         — HPL formed hot over R3-R3.3 edge (Kronospan, KronoSwiss)
--   - abs_square_edge    — Straight edge with 1.5mm ABS edge band (Kronospan)
--   - slim_line          — 12mm compact board, natural edge (Kronospan)
--   - fitline            — 18mm thin postformed (Kronospan, new collection)
--   - black_wood         — 12mm HPL on dark BLACK WOOD core (KronoSwiss)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worktop_constructions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,           -- 'postformed', 'abs_square_edge', 'slim_line', 'fitline', 'black_wood'
    name            TEXT NOT NULL,                  -- 'Post-formed', 'ABS Square Edge'
    description     TEXT,
    producer_hint   TEXT,                           -- 'kronospan', 'swiss_krono', NULL = any
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);


-- ──────────────────────────────────────────────────────────────────
-- 4. WORKTOP_PROFILES — edge shapes
-- ──────────────────────────────────────────────────────────────────
--
-- Geometry of the visible worktop edge:
--   U        — single edge rounded (front), R=3.3mm (Kronospan postformed 600mm)
--   U-U      — both edges rounded, R=3.3mm (Kronospan postformed 900/1200mm)
--   R3       — KronoSwiss postformed (R=3mm)
--   SQUARE   — straight ABS edge, R=1.5mm (Kronospan ABS Square Edge)
--   NATURAL  — raw compact board edge, no banding (Kronospan Slim Line, KronoSwiss BLACK WOOD)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worktop_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,           -- 'U', 'U-U', 'R3', 'SQUARE', 'NATURAL'
    name            TEXT NOT NULL,                  -- 'Profil U', 'Profil U-U', 'Square Edge'
    edge_radius_mm  REAL NOT NULL DEFAULT 0,        -- 3.3, 3.0, 1.5, 0
    profiled_sides  TEXT NOT NULL,                  -- 'front', 'front,back', 'none'
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (edge_radius_mm >= 0),
    CHECK (profiled_sides IN ('front', 'front,back', 'none'))
);


-- ──────────────────────────────────────────────────────────────────
-- 5. WORKTOP_SPECS — 1:0..1 with variants (only worktop-role variants)
-- ──────────────────────────────────────────────────────────────────
--
-- Each row corresponds to ONE variant whose roles include 'worktop'.
-- For non-worktop variants (fronts, carcass, splashback), no row here.
--
-- Why 1:0..1 (not extending variants):
--   - Prevents 6+ NULL columns on every non-worktop variant
--   - Worktop fields (profile, max_length, core_color) are domain-specific
--   - Clean separation respects ADR-002 (construction method ≠ instance)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worktop_specs (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id                  INTEGER NOT NULL UNIQUE REFERENCES variants(id) ON DELETE CASCADE,
    construction_id             INTEGER NOT NULL REFERENCES worktop_constructions(id),
    profile_id                  INTEGER NOT NULL REFERENCES worktop_profiles(id),

    -- Physical limits
    max_length_mm               INTEGER NOT NULL DEFAULT 4100,
    available_widths_mm         TEXT NOT NULL,            -- JSON: [600, 900, 1200]

    -- Materials at the edge (depends on construction)
    edge_material               TEXT,                     -- 'Unoflex', 'ABS 1.5mm', 'HPL', 'naturalna'
    edge_material_thickness_mm  REAL,                     -- 1.5 (ABS), 1.0 (Unoflex)

    -- Slim Line specific: visible core color
    -- ('Biały', 'Szary', 'Czarny', 'Beżowy'). NULL for non-slim worktops.
    core_color                  TEXT,

    -- Companion products availability
    splashback_available        BOOLEAN NOT NULL DEFAULT FALSE,
    matching_board_available    BOOLEAN NOT NULL DEFAULT FALSE,

    -- Pack/logistics
    pieces_per_pallet           INTEGER,
    pallet_weight_kg            REAL,
    pallets_per_truck           INTEGER,

    notes                       TEXT,
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now')),

    CHECK (max_length_mm > 0),
    CHECK (edge_material_thickness_mm IS NULL OR edge_material_thickness_mm >= 0),
    CHECK (pieces_per_pallet IS NULL OR pieces_per_pallet > 0)
);

CREATE INDEX IF NOT EXISTS idx_worktop_specs_construction ON worktop_specs(construction_id);
CREATE INDEX IF NOT EXISTS idx_worktop_specs_profile ON worktop_specs(profile_id);


-- ──────────────────────────────────────────────────────────────────
-- 6. ALTER EXISTING TABLES — incremental additions
-- ──────────────────────────────────────────────────────────────────
--
-- SQLite ALTER TABLE supports only ADD COLUMN — perfect for additive changes.
-- These are all nullable / defaulted, so existing rows from 01-schema.sql
-- remain valid without data migration.
-- ──────────────────────────────────────────────────────────────────

-- structures: synchronized texture flag (KronoSwiss SD/SW/CL/SE/OV ♻)
ALTER TABLE structures ADD COLUMN synchronized_texture BOOLEAN NOT NULL DEFAULT 0;

-- materials: nullable FK to subcollection (Slim Line Global vs Plus)
ALTER TABLE materials ADD COLUMN subcollection_id INTEGER REFERENCES subcollections(id);

-- variants: nullable FK to sheet_format (cleaner than JSON `format_mm`)
ALTER TABLE variants ADD COLUMN sheet_format_id INTEGER REFERENCES sheet_formats(id);

-- decors: bilingual name (KronoSwiss has PL + EN), one_global flag (🌐),
--         new_2024 (12 worktops marked NEW 2024), discontinued (do wyczerpania zapasów)
ALTER TABLE decors ADD COLUMN name_en TEXT;
ALTER TABLE decors ADD COLUMN one_global BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE decors ADD COLUMN new_2024 BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE decors ADD COLUMN discontinued BOOLEAN NOT NULL DEFAULT 0;


-- ──────────────────────────────────────────────────────────────────
-- 7. SEED DATA — worktop_constructions
-- ──────────────────────────────────────────────────────────────────

INSERT OR IGNORE INTO worktop_constructions (slug, name, description, producer_hint) VALUES
    ('postformed',
     'Post-formed',
     'Klasyczny blat z laminatem HPL formowanym na gorąco na zaokrąglonej krawędzi (R=3.3mm). Doklejka HDF 3mm wzmacnia krawędź.',
     NULL),
    ('abs_square_edge',
     'ABS Square Edge',
     'Nowoczesny blat z prostą krawędzią wykończoną obrzeżem ABS 1.5mm (R=1.5mm). Bez zaoblenia.',
     'kronospan'),
    ('slim_line',
     'Slim Line',
     'Cienki blat 12mm z płyty kompaktowej o monochromatycznym rdzeniu. Krawędź naturalna, bez obrzeża.',
     'kronospan'),
    ('fitline',
     'FitLine',
     'Cienki blat 18mm postformed (R=3.3mm) z paskami HDF wzmacniającymi krawędzie. Nowa kolekcja Kronospan.',
     'kronospan'),
    ('black_wood',
     'BLACK WOOD',
     'Ultracienki blat 12mm na bazie płyty BLACK WOOD (gęstość 900 kg/m³) z laminatem HPL jednostronnie. Trudnopalny D-s1,d0.',
     'swiss_krono');


-- ──────────────────────────────────────────────────────────────────
-- 8. SEED DATA — worktop_profiles
-- ──────────────────────────────────────────────────────────────────

INSERT OR IGNORE INTO worktop_profiles (code, name, edge_radius_mm, profiled_sides, description) VALUES
    ('U',
     'Profil U',
     3.3,
     'front',
     'Pojedyncza krawędź zaokrąglona postformed. Stosowane w blatach 600mm (Kronospan postformed).'),
    ('U-U',
     'Profil U-U',
     3.3,
     'front,back',
     'Obie krawędzie zaokrąglone postformed. Stosowane w blatach 900/1200mm (Kronospan postformed, FitLine).'),
    ('R3',
     'Profil R3 (KronoSwiss)',
     3.0,
     'front',
     'Pojedyncza krawędź R=3mm postformed. KronoSwiss postformed worktops.'),
    ('SQUARE',
     'Square Edge (ABS)',
     1.5,
     'front',
     'Prosta krawędź wykończona obrzeżem ABS 1.5mm. Kronospan ABS Square Edge.'),
    ('NATURAL',
     'Krawędź naturalna',
     0,
     'none',
     'Surowa krawędź płyty kompaktowej, bez wykończenia. Slim Line (12mm) i BLACK WOOD (12mm).');


-- ──────────────────────────────────────────────────────────────────
-- 9. SEED DATA — sheet_formats (most common from analyzed catalogs)
-- ──────────────────────────────────────────────────────────────────

INSERT OR IGNORE INTO sheet_formats (slug, length_mm, width_mm, use_hint, notes) VALUES
    -- Boards (chipboard, MDF)
    ('2800x2070', 2800, 2070, 'board',    'Standard chipboard/MDF (Kronospan Global, KronoSwiss)'),
    ('2800x1300', 2800, 1300, 'acrylic',  'MDF Acrylic Gloss/Matt (Kronospan)'),
    ('2800x2050', 2800, 2050, 'mirror',   'MDF Mirror Gloss (Kronospan)'),
    ('2620x2070', 2620, 2070, 'board',    'MX format (Kronospan MDF Plus)'),

    -- Worktops
    ('4100x600',  4100, 600,  'worktop',  'Postformed U (Kronospan, KronoSwiss)'),
    ('4100x900',  4100, 900,  'worktop',  'Postformed U-U, FitLine'),
    ('4100x1200', 4100, 1200, 'worktop',  'Postformed U-U (Kronospan)'),
    ('4100x635',  4100, 635,  'worktop',  'ABS Square Edge single (Kronospan)'),
    ('4100x1315', 4100, 1315, 'worktop',  'BLACK WOOD (KronoSwiss)'),
    ('4100x650',  4100, 650,  'slim',     'Slim Line Global (Kronospan)'),
    ('4100x1300', 4100, 1300, 'slim',     'Slim Line Plus (Kronospan)'),

    -- HPL rolls (laminate for self-application)
    ('3050x1320', 3050, 1320, 'hpl_roll', 'HPL laminate Kronospan Pustków'),
    ('4110x1330', 4110, 1330, 'hpl_roll', 'HPL laminate Mielec (Kronospan + KronoSwiss)'),

    -- HDF (backs/drawer bottoms)
    ('2800x2070_hdf', 2800, 2070, 'hdf',  'HDF 2.5/3.0mm (Kronospan)'),
    ('2050x1830',     2050, 1830, 'hdf',  'HDF door format');


-- ──────────────────────────────────────────────────────────────────
-- 10. VIEWS — convenience queries for worktop discovery
-- ──────────────────────────────────────────────────────────────────

-- Drop if exists (idempotency for development iterations)
DROP VIEW IF EXISTS v_worktops_full;

CREATE VIEW v_worktops_full AS
SELECT
    v.id                            AS variant_pk,
    v.business_id                   AS variant_id,
    d.business_id                   AS decor_id,
    d.name                          AS decor_name_pl,
    d.name_en                       AS decor_name_en,
    p.slug                          AS producer,
    col.slug                        AS collection,
    sc.slug                         AS subcollection,
    mt.slug                         AS material_type,
    s.code                          AS structure_code,
    s.synchronized_texture,
    v.thickness_mm,
    wc.slug                         AS construction,
    wp.code                         AS profile_code,
    wp.edge_radius_mm,
    wp.profiled_sides,
    ws.max_length_mm,
    ws.available_widths_mm,
    ws.edge_material,
    ws.core_color,
    ws.splashback_available,
    ws.matching_board_available,
    sf.slug                         AS sheet_format,
    sf.length_mm                    AS sheet_length_mm,
    sf.width_mm                     AS sheet_width_mm
FROM worktop_specs ws
JOIN variants v          ON v.id = ws.variant_id
JOIN decors d            ON d.id = v.decor_id
JOIN producers p         ON p.id = d.producer_id
JOIN materials m         ON m.id = v.material_id
JOIN material_types mt   ON mt.id = m.material_type_id
JOIN collections col     ON col.id = m.collection_id
LEFT JOIN subcollections sc ON sc.id = m.subcollection_id
LEFT JOIN structures s   ON s.id = v.structure_id
LEFT JOIN sheet_formats sf ON sf.id = v.sheet_format_id
JOIN worktop_constructions wc ON wc.id = ws.construction_id
JOIN worktop_profiles wp ON wp.id = ws.profile_id;


-- View: synchronized-texture decors (KronoSwiss SE/SD/SW/CL/OV ♻)
DROP VIEW IF EXISTS v_synchro_variants;

CREATE VIEW v_synchro_variants AS
SELECT
    d.business_id   AS decor_id,
    d.name          AS decor_name,
    p.slug          AS producer,
    s.code          AS structure_code,
    s.name          AS structure_name,
    v.business_id   AS variant_id,
    v.thickness_mm
FROM variants v
JOIN structures s ON s.id = v.structure_id
JOIN decors d ON d.id = v.decor_id
JOIN producers p ON p.id = d.producer_id
WHERE s.synchronized_texture = 1;


-- ══════════════════════════════════════════════════════════════════
-- END OF PHASE 1 MIGRATION
-- ══════════════════════════════════════════════════════════════════
