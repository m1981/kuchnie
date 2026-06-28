-- ══════════════════════════════════════════════════════════════════
-- KUCHNIE CATALOG — Consolidated SQLite Schema
-- Version: 1.3.0
-- Tables ordered by FK dependency: no forward references.
-- ══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- ── 1. LOOKUP TABLES (no FK deps) ───────────────────────────────

CREATE TABLE IF NOT EXISTS producers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    country         TEXT,
    website         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS material_types (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    core            TEXT NOT NULL,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS color_families (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    hex_approx      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS edge_suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    website         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sheet_formats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    length_mm       INTEGER NOT NULL,
    width_mm        INTEGER NOT NULL,
    use_hint        TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (length_mm > 0 AND width_mm > 0),
    CHECK (length_mm >= width_mm)
);

CREATE TABLE IF NOT EXISTS worktop_constructions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    producer_hint   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS worktop_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    edge_radius_mm  REAL NOT NULL DEFAULT 0,
    profiled_sides  TEXT NOT NULL,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (edge_radius_mm >= 0),
    CHECK (profiled_sides IN ('front', 'front,back', 'none'))
);

CREATE TABLE IF NOT EXISTS tags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);


-- ── 2. TABLES DEPENDING ON producers ────────────────────────────

CREATE TABLE IF NOT EXISTS structures (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL,
    name            TEXT NOT NULL,
    type            TEXT,
    finish          TEXT,
    fingerprint_resistant BOOLEAN DEFAULT FALSE,
    synchronized_texture  BOOLEAN NOT NULL DEFAULT 0,
    description     TEXT,
    producer_id     INTEGER REFERENCES producers(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(code, producer_id)
);

CREATE TABLE IF NOT EXISTS collections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    producer_id     INTEGER NOT NULL REFERENCES producers(id),
    name            TEXT NOT NULL,
    source_pdf      TEXT,
    has_edgebanding BOOLEAN DEFAULT TRUE,
    has_hdf         BOOLEAN DEFAULT FALSE,
    has_countertops BOOLEAN DEFAULT FALSE,
    has_express     BOOLEAN DEFAULT FALSE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(slug, producer_id)
);

CREATE TABLE IF NOT EXISTS decors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id     TEXT NOT NULL,
    producer_id     INTEGER NOT NULL REFERENCES producers(id),
    name            TEXT NOT NULL,
    name_en         TEXT,
    group_name      TEXT,
    color_family_id INTEGER REFERENCES color_families(id),
    ncs             TEXT,
    ral             TEXT,
    pantone         TEXT,
    img             TEXT,
    one_global      BOOLEAN NOT NULL DEFAULT 0,
    new_2024        BOOLEAN NOT NULL DEFAULT 0,
    discontinued    BOOLEAN NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(business_id, producer_id)
);


-- ── 3. TABLES DEPENDING ON collections ──────────────────────────

CREATE TABLE IF NOT EXISTS subcollections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id   INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    slug            TEXT NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(slug, collection_id)
);

CREATE TABLE IF NOT EXISTS materials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    material_type_id INTEGER NOT NULL REFERENCES material_types(id),
    collection_id   INTEGER NOT NULL REFERENCES collections(id),
    subcollection_id INTEGER REFERENCES subcollections(id),
    name            TEXT NOT NULL,
    thicknesses_mm  TEXT,
    format_mm       TEXT,
    sidedness       TEXT CHECK (sidedness IN (
                        'one_sided', 'two_sided_same', 'two_sided_different', 'varies'
                    )),
    has_edgebanding BOOLEAN DEFAULT TRUE,
    has_hdf         BOOLEAN DEFAULT FALSE,
    has_express     BOOLEAN DEFAULT FALSE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);


-- ── 4. TABLES DEPENDING ON decors + materials ───────────────────

CREATE TABLE IF NOT EXISTS variants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id     TEXT NOT NULL UNIQUE,
    decor_id        INTEGER NOT NULL REFERENCES decors(id),
    material_id     INTEGER NOT NULL REFERENCES materials(id),
    structure_id    INTEGER REFERENCES structures(id),
    sheet_format_id INTEGER REFERENCES sheet_formats(id),
    roles           TEXT NOT NULL DEFAULT '["front"]',
    thickness_mm    REAL,
    width_mm        INTEGER,
    length_mm       INTEGER,
    format_mm       TEXT,
    sidedness       TEXT CHECK (sidedness IN (
                        'one_sided', 'two_sided_same', 'two_sided_different'
                    )),
    express         TEXT,
    konfekcja       BOOLEAN DEFAULT FALSE,
    splashback_available BOOLEAN DEFAULT FALSE,
    hpl_available   BOOLEAN DEFAULT FALSE,
    countertop      TEXT,
    multi_structures TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    supplier_id     INTEGER REFERENCES edge_suppliers(id),
    finish          TEXT,
    material        TEXT,
    thickness_mm    REAL,
    width_mm        REAL,
    radius_mm       REAL,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pairings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    front_decor_id      INTEGER NOT NULL REFERENCES decors(id),
    target_decor_id     INTEGER NOT NULL REFERENCES decors(id),
    pairing_type        TEXT NOT NULL CHECK (pairing_type IN (
                            'carcass', 'worktop', 'splashback', 'side_panel',
                            'plinth', 'hpl_laminate', 'acrylic', 'mirror',
                            'compact', 'kronoart', 'black_wood'
                        )),
    match_type          TEXT NOT NULL CHECK (match_type IN (
                            'exact', 'close', 'default'
                        )),
    priority            INTEGER NOT NULL DEFAULT 1,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(front_decor_id, target_decor_id, pairing_type)
);

CREATE TABLE IF NOT EXISTS decor_structures (
    decor_id        INTEGER NOT NULL REFERENCES decors(id) ON DELETE CASCADE,
    structure_id    INTEGER NOT NULL REFERENCES structures(id) ON DELETE CASCADE,
    is_primary      BOOLEAN NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (decor_id, structure_id)
);

CREATE TABLE IF NOT EXISTS decor_tags (
    decor_id        INTEGER NOT NULL REFERENCES decors(id) ON DELETE CASCADE,
    tag_id          INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (decor_id, tag_id)
);


-- ── 5. TABLES DEPENDING ON variants ─────────────────────────────

CREATE TABLE IF NOT EXISTS variant_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id      INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    edge_id         INTEGER NOT NULL REFERENCES edges(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(variant_id, edge_id)
);

CREATE TABLE IF NOT EXISTS worktop_specs (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id                  INTEGER NOT NULL UNIQUE REFERENCES variants(id) ON DELETE CASCADE,
    construction_id             INTEGER NOT NULL REFERENCES worktop_constructions(id),
    profile_id                  INTEGER NOT NULL REFERENCES worktop_profiles(id),
    max_length_mm               INTEGER NOT NULL DEFAULT 4100,
    available_widths_mm         TEXT NOT NULL,
    edge_material               TEXT,
    edge_material_thickness_mm  REAL,
    core_color                  TEXT,
    splashback_available        BOOLEAN NOT NULL DEFAULT FALSE,
    matching_board_available    BOOLEAN NOT NULL DEFAULT FALSE,
    pieces_per_pallet           INTEGER,
    pallet_weight_kg            REAL,
    pallets_per_truck           INTEGER,
    notes                       TEXT,
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (max_length_mm > 0)
);

CREATE TABLE IF NOT EXISTS variant_availability (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id      INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    channel         TEXT NOT NULL CHECK (channel IN (
                        'express_24h', 'konfekcja', 'standard', 'on_request'
                    )),
    available       BOOLEAN NOT NULL DEFAULT TRUE,
    min_order_qty   INTEGER NOT NULL DEFAULT 1,
    warehouse       TEXT,
    lead_time       TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(variant_id, channel)
);


-- ── 6. INDEXES ──────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_decors_producer ON decors(producer_id);
CREATE INDEX IF NOT EXISTS idx_decors_color_family ON decors(color_family_id);
CREATE INDEX IF NOT EXISTS idx_decors_name ON decors(name);
CREATE INDEX IF NOT EXISTS idx_variants_decor ON variants(decor_id);
CREATE INDEX IF NOT EXISTS idx_variants_material ON variants(material_id);
CREATE INDEX IF NOT EXISTS idx_variants_structure ON variants(structure_id);
CREATE INDEX IF NOT EXISTS idx_variants_thickness ON variants(thickness_mm);
CREATE INDEX IF NOT EXISTS idx_edges_supplier ON edges(supplier_id);
CREATE INDEX IF NOT EXISTS idx_pairings_front ON pairings(front_decor_id);
CREATE INDEX IF NOT EXISTS idx_pairings_target ON pairings(target_decor_id);
CREATE INDEX IF NOT EXISTS idx_pairings_type ON pairings(pairing_type);
CREATE INDEX IF NOT EXISTS idx_decor_structures_structure ON decor_structures(structure_id);
CREATE INDEX IF NOT EXISTS idx_sheet_formats_use_hint ON sheet_formats(use_hint);
CREATE INDEX IF NOT EXISTS idx_subcollections_collection ON subcollections(collection_id);
CREATE INDEX IF NOT EXISTS idx_worktop_specs_construction ON worktop_specs(construction_id);
CREATE INDEX IF NOT EXISTS idx_worktop_specs_profile ON worktop_specs(profile_id);
CREATE INDEX IF NOT EXISTS idx_variant_availability_variant ON variant_availability(variant_id);
CREATE INDEX IF NOT EXISTS idx_variant_availability_channel ON variant_availability(channel);
CREATE INDEX IF NOT EXISTS idx_decor_tags_decor ON decor_tags(decor_id);
CREATE INDEX IF NOT EXISTS idx_decor_tags_tag ON decor_tags(tag_id);


-- ── 6b. PROPERTY FLAGS (EAV) ──────────────────────────────────

CREATE TABLE IF NOT EXISTS property_flags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id      INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    property        TEXT NOT NULL,
    value           BOOLEAN NOT NULL DEFAULT 1,
    source          TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(variant_id, property)
);

CREATE INDEX IF NOT EXISTS idx_property_flags_variant ON property_flags(variant_id);


-- ── 7. VIEWS ────────────────────────────────────────────────────

CREATE VIEW IF NOT EXISTS v_decors_full AS
SELECT
    d.id            AS decor_pk,
    d.business_id   AS decor_id,
    d.name          AS decor_name,
    d.name_en       AS decor_name_en,
    d.group_name,
    cf.slug         AS color_family,
    d.ncs, d.ral, d.pantone, d.img,
    d.one_global, d.new_2024, d.discontinued,
    p.slug          AS producer,
    v.id            AS variant_pk,
    v.business_id   AS variant_id,
    mt.slug         AS material_type,
    m.slug          AS material,
    s.code          AS structure,
    s.name          AS structure_name,
    s.type          AS structure_type,
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

CREATE VIEW IF NOT EXISTS v_pairings_full AS
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

CREATE VIEW IF NOT EXISTS v_worktops_full AS
SELECT
    v.id                            AS variant_pk,
    v.business_id                   AS variant_id,
    d.business_id                   AS decor_id,
    d.name                          AS decor_name_pl,
    d.name_en                       AS decor_name_en,
    p.slug                          AS producer,
    col.slug                        AS collection,
    mt.slug                         AS material_type,
    s.code                          AS structure_code,
    v.thickness_mm,
    wc.slug                         AS construction,
    wp.code                         AS profile_code,
    wp.edge_radius_mm,
    wp.profiled_sides,
    ws.max_length_mm,
    ws.available_widths_mm,
    ws.edge_material,
    ws.edge_material_thickness_mm,
    ws.core_color,
    ws.splashback_available,
    ws.matching_board_available
FROM worktop_specs ws
JOIN variants v          ON v.id = ws.variant_id
JOIN decors d            ON d.id = v.decor_id
JOIN producers p         ON p.id = d.producer_id
JOIN materials m         ON m.id = v.material_id
JOIN material_types mt   ON mt.id = m.material_type_id
JOIN collections col     ON col.id = m.collection_id
LEFT JOIN structures s   ON s.id = v.structure_id
JOIN worktop_constructions wc ON wc.id = ws.construction_id
JOIN worktop_profiles wp ON wp.id = ws.profile_id;

CREATE VIEW IF NOT EXISTS v_variants_availability AS
SELECT
    v.business_id   AS variant_id,
    d.business_id   AS decor_id,
    d.name          AS decor_name,
    p.slug          AS producer,
    mt.slug         AS material_type,
    s.code          AS structure,
    v.thickness_mm,
    va.channel,
    va.available,
    va.min_order_qty,
    va.warehouse,
    va.lead_time
FROM variant_availability va
JOIN variants v          ON v.id = va.variant_id
JOIN decors d            ON d.id = v.decor_id
JOIN producers p         ON p.id = d.producer_id
JOIN materials m         ON m.id = v.material_id
JOIN material_types mt   ON mt.id = m.material_type_id
LEFT JOIN structures s   ON s.id = v.structure_id;

CREATE VIEW IF NOT EXISTS v_decor_structures_full AS
SELECT
    d.business_id   AS decor_id,
    d.name          AS decor_name,
    p.slug          AS producer,
    s.code          AS structure_code,
    s.name          AS structure_name,
    s.synchronized_texture,
    ds.is_primary
FROM decor_structures ds
JOIN decors d    ON d.id = ds.decor_id
JOIN structures s ON s.id = ds.structure_id
JOIN producers p  ON p.id = d.producer_id;


CREATE VIEW IF NOT EXISTS v_property_flags AS
SELECT
    v.business_id   AS variant_id,
    d.business_id   AS decor_id,
    d.name          AS decor_name,
    p.slug          AS producer,
    mt.slug         AS material_type,
    s.code          AS structure,
    v.thickness_mm,
    pf.property,
    pf.value,
    pf.source
FROM property_flags pf
JOIN variants v          ON v.id = pf.variant_id
JOIN decors d            ON d.id = v.decor_id
JOIN producers p         ON p.id = d.producer_id
JOIN materials m         ON m.id = v.material_id
JOIN material_types mt   ON mt.id = m.material_type_id
LEFT JOIN structures s   ON s.id = v.structure_id;


-- ── 8. SEED DATA ────────────────────────────────────────────────

INSERT OR IGNORE INTO material_types (slug, name, core) VALUES
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

INSERT OR IGNORE INTO color_families (slug, name, hex_approx) VALUES
    ('bialy','Biały','#FFFFFF'),('bezowy','Beżowy','#F5DEB3'),
    ('szary','Szary','#808080'),('czarny','Czarny','#1A1A1A'),
    ('brazowy','Brązowy','#8B4513'),('kremowy','Kremowy','#FFFDD0'),
    ('dab','Dąb','#C4A35A'),('orzech','Orzech','#5C4033'),
    ('jesion','Jesion','#B8860B'),('buk','Buk','#D2691E'),
    ('brzoza','Brzoza','#FAEBD7'),('olcha','Olcha','#A0522D'),
    ('wisnia','Wiśnia','#8B0000'),('klon','Klon','#DAA520'),
    ('wenge','Wenge','#3C2415'),('wiaz','Wiąz','#8B7355'),
    ('marmur','Marmur','#E8E8E8'),('beton','Beton','#A9A9A9'),
    ('lupek','Łupek','#708090'),('niebieski','Niebieski','#4682B4'),
    ('zielony','Zielony','#228B22'),('czerwony','Czerwony','#DC143C'),
    ('rozowy','Różowy','#FFB6C1'),('zloty','Złoty','#FFD700'),
    ('srebrny','Srebrny','#C0C0C0'),('metal','Metal','#A8A8A8'),
    ('unikolor','Unikolor','#CCCCCC');

INSERT OR IGNORE INTO edge_suppliers (slug, name) VALUES
    ('schilsner','Schilsner'),('rehau','REHAU Interior Solutions');

INSERT OR IGNORE INTO worktop_constructions (slug, name, description, producer_hint) VALUES
    ('postformed','Post-formed','HPL formed hot over R3 edge',NULL),
    ('abs_square_edge','ABS Square Edge','Straight edge with 1.5mm ABS','kronospan'),
    ('slim_line','Slim Line','12mm compact board','kronospan'),
    ('fitline','FitLine','18mm thin postformed','kronospan'),
    ('black_wood','BLACK WOOD','12mm HPL on dark core','swiss_krono');

INSERT OR IGNORE INTO worktop_profiles (code, name, edge_radius_mm, profiled_sides) VALUES
    ('U','Profil U',3.3,'front'),('U-U','Profil U-U',3.3,'front,back'),
    ('R3','Profil R3',3.0,'front'),('SQUARE','Square Edge',1.5,'front'),
    ('NATURAL','Krawędź naturalna',0,'none');

INSERT OR IGNORE INTO sheet_formats (slug, length_mm, width_mm, use_hint) VALUES
    ('2800x2070',2800,2070,'board'),('2800x1300',2800,1300,'acrylic'),
    ('2800x2050',2800,2050,'mirror'),('4100x600',4100,600,'worktop'),
    ('4100x900',4100,900,'worktop'),('4100x1200',4100,1200,'worktop'),
    ('4100x635',4100,635,'worktop'),('4100x1315',4100,1315,'worktop'),
    ('4100x650',4100,650,'slim'),('4100x1300',4100,1300,'slim'),
    ('3050x1320',3050,1320,'hpl_roll'),('4110x1330',4110,1330,'hpl_roll');
