-- ══════════════════════════════════════════════════════════════════
-- PHASE 5 — PRODUCER GENERALIZATION (schema 1.5.0, ADR-004)
-- Prepares the schema for a third producer (Egger) without
-- producer-specific enums or columns:
--   1. pairing_types lookup table; pairings.pairing_type CHECK → FK
--   2. decors.one_global / new_2024 columns → decor_tags rows
--      (v_decors_full recomputes both — API shape unchanged)
--   3. variants.producer_sku + partial unique index
-- Runtime equivalent for data-bearing DBs: scripts/migrate_1_5_0.py
-- ══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = OFF;

-- Views must be dropped before table renames: ALTER TABLE RENAME
-- (SQLite ≥ 3.25) re-validates every view in the schema.
DROP VIEW IF EXISTS v_decors_full;
DROP VIEW IF EXISTS v_pairings_full;
DROP VIEW IF EXISTS v_worktops_full;
DROP VIEW IF EXISTS v_synchro_variants;
DROP VIEW IF EXISTS v_decor_structures_full;
DROP VIEW IF EXISTS v_variants_availability;
DROP VIEW IF EXISTS v_property_flags;


-- ── 1. pairing_types lookup + pairings rebuild ──────────────────

CREATE TABLE IF NOT EXISTS pairing_types (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    producer_hint   TEXT,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO pairing_types (slug, name, producer_hint) VALUES
    ('carcass','Korpus',NULL),
    ('worktop','Blat',NULL),
    ('splashback','Panel ścienny',NULL),
    ('side_panel','Bok widoczny',NULL),
    ('plinth','Cokół',NULL),
    ('hpl_laminate','Laminat HPL',NULL),
    ('acrylic','Akryl',NULL),
    ('mirror','Lustro',NULL),
    ('compact','Compact',NULL),
    ('kronoart','KronoArt','kronospan'),
    ('black_wood','BLACK WOOD','swiss_krono');

CREATE TABLE pairings_new (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    front_decor_id      INTEGER NOT NULL REFERENCES decors(id),
    target_decor_id     INTEGER NOT NULL REFERENCES decors(id),
    pairing_type        TEXT NOT NULL REFERENCES pairing_types(slug),
    match_type          TEXT NOT NULL CHECK (match_type IN (
                            'exact', 'close', 'default'
                        )),
    priority            INTEGER NOT NULL DEFAULT 1,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(front_decor_id, target_decor_id, pairing_type)
);

INSERT INTO pairings_new (id, front_decor_id, target_decor_id, pairing_type,
    match_type, priority, notes, created_at, updated_at)
SELECT id, front_decor_id, target_decor_id, pairing_type,
    match_type, priority, notes, created_at, updated_at
FROM pairings;

DROP TABLE pairings;
ALTER TABLE pairings_new RENAME TO pairings;

CREATE INDEX IF NOT EXISTS idx_pairings_front ON pairings(front_decor_id);
CREATE INDEX IF NOT EXISTS idx_pairings_target ON pairings(target_decor_id);
CREATE INDEX IF NOT EXISTS idx_pairings_type ON pairings(pairing_type);


-- ── 2. collection-membership flags → decor_tags ─────────────────

INSERT OR IGNORE INTO tags (slug) VALUES ('one-global'), ('new-2024');

INSERT OR IGNORE INTO decor_tags (decor_id, tag_id)
SELECT d.id, t.id FROM decors d JOIN tags t ON t.slug = 'one-global'
WHERE d.one_global = 1;

INSERT OR IGNORE INTO decor_tags (decor_id, tag_id)
SELECT d.id, t.id FROM decors d JOIN tags t ON t.slug = 'new-2024'
WHERE d.new_2024 = 1;

CREATE TABLE decors_new (
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
    discontinued    BOOLEAN NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(business_id, producer_id)
);

INSERT INTO decors_new (id, business_id, producer_id, name, name_en,
    group_name, color_family_id, ncs, ral, pantone, img,
    discontinued, notes, created_at, updated_at)
SELECT id, business_id, producer_id, name, name_en,
    group_name, color_family_id, ncs, ral, pantone, img,
    discontinued, notes, created_at, updated_at
FROM decors;

DROP TABLE decors;
ALTER TABLE decors_new RENAME TO decors;

CREATE INDEX IF NOT EXISTS idx_decors_producer ON decors(producer_id);
CREATE INDEX IF NOT EXISTS idx_decors_color_family ON decors(color_family_id);
CREATE INDEX IF NOT EXISTS idx_decors_name ON decors(name);


-- ── 3. producer's own article number on variants ────────────────

ALTER TABLE variants ADD COLUMN producer_sku TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_variants_producer_sku
    ON variants(producer_sku) WHERE producer_sku IS NOT NULL;


-- ── 4. RECREATE VIEWS (definitions match db/schema.sql 1.5.0) ───

CREATE VIEW v_decors_full AS
SELECT
    d.id            AS decor_pk,
    d.business_id   AS decor_id,
    d.name          AS decor_name,
    d.name_en       AS decor_name_en,
    d.group_name,
    cf.slug         AS color_family,
    d.ncs, d.ral, d.pantone, d.img,
    EXISTS(SELECT 1 FROM decor_tags dt JOIN tags t ON t.id = dt.tag_id
           WHERE dt.decor_id = d.id AND t.slug = 'one-global') AS one_global,
    EXISTS(SELECT 1 FROM decor_tags dt JOIN tags t ON t.id = dt.tag_id
           WHERE dt.decor_id = d.id AND t.slug = 'new-2024') AS new_2024,
    d.discontinued,
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

-- v_worktops_full keeps the phase-1 (02-…) definition, which is richer
-- than db/schema.sql's (subcollection, synchronized_texture, sheet format).
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

CREATE VIEW v_decor_structures_full AS
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

CREATE VIEW v_variants_availability AS
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

CREATE VIEW v_property_flags AS
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

PRAGMA foreign_keys = ON;

-- ══════════════════════════════════════════════════════════════════
-- END OF PHASE 5 MIGRATION
-- ══════════════════════════════════════════════════════════════════
