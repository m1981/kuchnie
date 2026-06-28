-- ══════════════════════════════════════════════════════════════════
-- KUCHNIE CATALOG — SQLite Schema
-- Version: 1.0.0 (design)
-- Date: 2026-06-27
-- ══════════════════════════════════════════════════════════════════
--
-- Design principles:
--   1. Normalized (3NF) — no data duplication
--   2. FK enforced — referential integrity at DB level
--   3. CHECK constraints — domain validation in DB
--   4. Soft deletes — nothing is ever truly deleted
--   5. Audit columns — created_at, updated_at on every table
--   6. ID conventions:
--        - Tables: snake_case plural (decors, variants)
--        - PKs: id (INTEGER AUTOINCREMENT)
--        - FKs: {referenced_table_singular}_id
--        - Business keys: TEXT UNIQUE (decor_id, variant_id)
--
-- ══════════════════════════════════════════════════════════════════


-- ──────────────────────────────────────────────────────────────────
-- LOOKUP TABLES (reference data, rarely changed)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE producers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,              -- 'kronospan', 'egger', 'swiss_krono'
    name            TEXT NOT NULL,                     -- 'Kronospan', 'Egger'
    country         TEXT,                              -- 'Polska', 'Austria'
    website         TEXT,                              -- 'kronosfera.pl'
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE material_types (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,              -- 'chipboard', 'mdf_acrylic', 'worktop_postformed'
    name            TEXT NOT NULL,                     -- 'Płyta wiórowa', 'Blat Post-formed'
    core            TEXT NOT NULL,                     -- 'chipboard', 'mdf', 'compact', 'hpl'
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE structures (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL,                     -- 'SM', 'PE', 'AG', 'RS', 'ST9'
    name            TEXT NOT NULL,                     -- 'Super Mat', 'Pearl Effect'
    type            TEXT,                              -- 'smooth', 'wood_grain', 'stone', 'metal'
    finish          TEXT,                              -- 'matt', 'silk_matt', 'gloss', 'structured'
    fingerprint_resistant BOOLEAN DEFAULT FALSE,
    description     TEXT,
    producer_id     INTEGER REFERENCES producers(id), -- NULL = shared across producers
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(code, producer_id)                         -- same code can exist per producer
);

CREATE TABLE color_families (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,              -- 'bialy', 'dab', 'szary'
    name            TEXT NOT NULL,                     -- 'Biały', 'Dąb', 'Szary'
    hex_approx      TEXT,                              -- '#FFFFFF' (for UI swatches)
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE edge_suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,              -- 'schilsner', 'rehau'
    name            TEXT NOT NULL,                     -- 'Schilsner', 'REHAU Interior Solutions'
    website         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);


-- ──────────────────────────────────────────────────────────────────
-- CORE TABLES (business entities)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE collections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,              -- 'global', 'acrylic_gloss', 'egger_standard'
    producer_id     INTEGER NOT NULL REFERENCES producers(id),
    name            TEXT NOT NULL,                     -- 'Global Collection 2026'
    source_pdf      TEXT,                              -- 'plyty-wiorowe-global-collection.pdf'
    has_edgebanding BOOLEAN DEFAULT TRUE,
    has_hdf         BOOLEAN DEFAULT FALSE,
    has_countertops BOOLEAN DEFAULT FALSE,
    has_express     BOOLEAN DEFAULT FALSE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(slug, producer_id)
);

CREATE TABLE materials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,              -- 'kronospan-chipboard-global'
    material_type_id INTEGER NOT NULL REFERENCES material_types(id),
    collection_id   INTEGER NOT NULL REFERENCES collections(id),
    name            TEXT NOT NULL,                     -- 'Global Collection — Płyta wiórowa'
    thicknesses_mm  TEXT,                              -- JSON: [12, 16, 18]
    format_mm       TEXT,                              -- JSON: [2800, 2070] or [4100, 600]
    sidedness       TEXT CHECK (sidedness IN (
                        'one_sided', 'two_sided_same', 'two_sided_different', 'varies'
                    )),
    has_edgebanding BOOLEAN DEFAULT TRUE,
    has_hdf         BOOLEAN DEFAULT FALSE,
    has_express     BOOLEAN DEFAULT FALSE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE decors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id     TEXT NOT NULL UNIQUE,              -- 'K8685', 'K091', '868S'
    producer_id     INTEGER NOT NULL REFERENCES producers(id),
    name            TEXT NOT NULL,                     -- 'Biel Alpejska'
    group_name      TEXT,                              -- 'WHITE FRONT', 'COLOR BASIC'
    color_family_id INTEGER REFERENCES color_families(id),
    ncs             TEXT,                              -- 'S 0500-N'
    ral             TEXT,                              -- '9016'
    pantone         TEXT,                              -- 'Cool Grey 10 C'
    img             TEXT,                              -- 'K8685.jpg'
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(business_id, producer_id)
);

CREATE TABLE variants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id     TEXT NOT NULL UNIQUE,              -- 'K8685-CH', '868S-PF-600'
    decor_id        INTEGER NOT NULL REFERENCES decors(id),
    material_id     INTEGER NOT NULL REFERENCES materials(id),
    structure_id    INTEGER REFERENCES structures(id),

    -- Role: what this variant can be used for
    -- Stored as JSON array: '["front"]', '["carcass"]', '["worktop"]'
    roles           TEXT NOT NULL DEFAULT '["front"]',

    -- Physical properties
    thickness_mm    REAL,
    width_mm        INTEGER,                           -- 600, 900, 1200 (worktops)
    length_mm       INTEGER,                           -- 4100 (worktops), 2800 (boards)
    format_mm       TEXT,                              -- JSON: [2800, 2070]
    sidedness       TEXT CHECK (sidedness IN (
                        'one_sided', 'two_sided_same', 'two_sided_different'
                    )),

    -- Availability
    express         TEXT,                              -- JSON: [12, 16, 18]
    konfekcja       BOOLEAN DEFAULT FALSE,
    splashback_available BOOLEAN DEFAULT FALSE,
    hpl_available   BOOLEAN DEFAULT FALSE,
    countertop      TEXT,                              -- '868S RS' (matched worktop code)

    -- Multi-structure (e.g. "BS, PD")
    multi_structures TEXT,

    -- Metadata
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,              -- 'K-8685-SM/BS/PD', 'WK-8685-RS'
    supplier_id     INTEGER REFERENCES edge_suppliers(id),
    finish          TEXT,                              -- 'HG', 'UM', 'SM', 'ABS'
    material        TEXT,                              -- 'ABS', 'Unoflex', 'HPL'
    thickness_mm    REAL,                              -- 1.2, 1.5
    width_mm        REAL,                              -- 23, 42, 43
    radius_mm       REAL,                              -- 3.3, 1.5
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE variant_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id      INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    edge_id         INTEGER NOT NULL REFERENCES edges(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(variant_id, edge_id)
);


-- ──────────────────────────────────────────────────────────────────
-- PAIRINGS (relationship between decors)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE pairings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    front_decor_id      INTEGER NOT NULL REFERENCES decors(id),
    target_decor_id     INTEGER NOT NULL REFERENCES decors(id),
    pairing_type        TEXT NOT NULL CHECK (pairing_type IN (
                            'carcass', 'worktop', 'splashback', 'side_panel', 'plinth'
                        )),
    match_type          TEXT NOT NULL CHECK (match_type IN (
                            'exact', 'close', 'default'
                        )),
    priority            INTEGER NOT NULL DEFAULT 1,   -- 1 = highest
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(front_decor_id, target_decor_id, pairing_type)
);

-- Wildcard pairings: front = '*' means "any decor"
-- Implemented via a special decor with business_id = '*'


-- ──────────────────────────────────────────────────────────────────
-- TAGS (flexible metadata)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE tags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,              -- 'frontowy', 'korpusowy', 'drewno'
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE decor_tags (
    decor_id        INTEGER NOT NULL REFERENCES decors(id) ON DELETE CASCADE,
    tag_id          INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (decor_id, tag_id)
);


-- ──────────────────────────────────────────────────────────────────
-- INDEXES (query optimization)
-- ──────────────────────────────────────────────────────────────────

-- Decors
CREATE INDEX idx_decors_producer ON decors(producer_id);
CREATE INDEX idx_decors_color_family ON decors(color_family_id);
CREATE INDEX idx_decors_name ON decors(name);

-- Variants
CREATE INDEX idx_variants_decor ON variants(decor_id);
CREATE INDEX idx_variants_material ON variants(material_id);
CREATE INDEX idx_variants_structure ON variants(structure_id);
CREATE INDEX idx_variants_thickness ON variants(thickness_mm);

-- Pairings
CREATE INDEX idx_pairings_front ON pairings(front_decor_id);
CREATE INDEX idx_pairings_target ON pairings(target_decor_id);
CREATE INDEX idx_pairings_type ON pairings(pairing_type);

-- Edges
CREATE INDEX idx_edges_supplier ON edges(supplier_id);

-- Tags
CREATE INDEX idx_decor_tags_decor ON decor_tags(decor_id);
CREATE INDEX idx_decor_tags_tag ON decor_tags(tag_id);


-- ──────────────────────────────────────────────────────────────────
-- VIEWS (convenience queries)
-- ──────────────────────────────────────────────────────────────────

-- Full decor with all variants (main query for frontend)
CREATE VIEW v_decors_full AS
SELECT
    d.id            AS decor_pk,
    d.business_id   AS decor_id,
    d.name          AS decor_name,
    d.group_name,
    cf.slug         AS color_family,
    d.ncs, d.ral, d.pantone, d.img,
    p.slug          AS producer,
    v.id            AS variant_pk,
    v.business_id   AS variant_id,
    mt.slug         AS material_type,
    m.slug          AS material,
    s.code          AS structure,
    v.roles,
    v.thickness_mm,
    v.width_mm,
    v.length_mm,
    v.format_mm,
    v.sidedness,
    v.express,
    v.konfekcja,
    v.splashback_available,
    v.hpl_available,
    v.countertop,
    v.multi_structures
FROM decors d
JOIN producers p ON p.id = d.producer_id
LEFT JOIN color_families cf ON cf.id = d.color_family_id
JOIN variants v ON v.decor_id = d.id
JOIN materials m ON m.id = v.material_id
JOIN material_types mt ON mt.id = m.material_type_id
LEFT JOIN structures s ON s.id = v.structure_id;

-- Pairings with decor names (for pairing queries)
CREATE VIEW v_pairings_full AS
SELECT
    p.id            AS pairing_pk,
    fd.business_id  AS front_decor_id,
    fd.name         AS front_decor_name,
    td.business_id  AS target_decor_id,
    td.name         AS target_decor_name,
    p.pairing_type,
    p.match_type,
    p.priority,
    p.notes
FROM pairings p
JOIN decors fd ON fd.id = p.front_decor_id
JOIN decors td ON td.id = p.target_decor_id;


-- ──────────────────────────────────────────────────────────────────
-- SEED DATA (reference tables)
-- ──────────────────────────────────────────────────────────────────

INSERT INTO material_types (slug, name, core) VALUES
    ('chipboard',           'Płyta wiórowa laminowana',     'chipboard'),
    ('mdf_acrylic',         'MDF Akryl',                    'mdf'),
    ('mdf_lacquered',       'MDF Lakierowany',              'mdf'),
    ('mdf_foil',            'MDF Foliowany',                'mdf'),
    ('compact',             'Compact HPL',                  'compact'),
    ('hpl',                 'Laminat HPL',                  'hpl'),
    ('worktop_postformed',  'Blat Post-formed',             'chipboard'),
    ('worktop_fitline',     'Blat FitLine',                 'chipboard'),
    ('worktop_abs_edge',    'Blat ABS Square Edge',         'chipboard'),
    ('worktop_slim',        'Blat Slim Line',               'compact'),
    ('splashback',          'Panel ścienny (Splashback)',   'hpl');

INSERT INTO color_families (slug, name, hex_approx) VALUES
    ('bialy',       'Biały',        '#FFFFFF'),
    ('bezowy',      'Beżowy',       '#F5DEB3'),
    ('szary',       'Szary',        '#808080'),
    ('czarny',      'Czarny',       '#1A1A1A'),
    ('brazowy',     'Brązowy',      '#8B4513'),
    ('kremowy',     'Kremowy',      '#FFFDD0'),
    ('dab',         'Dąb',          '#C4A35A'),
    ('orzech',      'Orzech',       '#5C4033'),
    ('jesion',      'Jesion',       '#B8860B'),
    ('buk',         'Buk',          '#D2691E'),
    ('brzoza',      'Brzoza',       '#FAEBD7'),
    ('olcha',       'Olcha',        '#A0522D'),
    ('wisnia',      'Wiśnia',       '#8B0000'),
    ('klon',        'Klon',         '#DAA520'),
    ('wenge',       'Wenge',        '#3C2415'),
    ('wiaz',        'Wiąz',         '#8B7355'),
    ('marmur',      'Marmur',       '#E8E8E8'),
    ('beton',       'Beton',        '#A9A9A9'),
    ('lupek',       'Łupek',        '#708090'),
    ('niebieski',   'Niebieski',    '#4682B4'),
    ('zielony',     'Zielony',      '#228B22'),
    ('czerwony',    'Czerwony',     '#DC143C'),
    ('rozowy',      'Różowy',       '#FFB6C1'),
    ('zloty',       'Złoty',        '#FFD700'),
    ('srebrny',     'Srebrny',      '#C0C0C0'),
    ('metal',       'Metal',        '#A8A8A8'),
    ('unikolor',    'Unikolor',     '#CCCCCC');

INSERT INTO edge_suppliers (slug, name) VALUES
    ('schilsner',   'Schilsner'),
    ('rehau',       'REHAU Interior Solutions');
