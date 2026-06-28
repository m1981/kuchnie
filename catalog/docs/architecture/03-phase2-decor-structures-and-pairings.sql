-- ══════════════════════════════════════════════════════════════════
-- KUCHNIE CATALOG — Migration Phase 2: Decor-Structure Junction + Pairing Types
-- Version: 1.2.0
-- Date: 2026-06-27
-- Requires: 01-schema.sql, 02-phase1-worktop-specs.sql
-- ══════════════════════════════════════════════════════════════════
--
-- 2a. `decor_structures` — replaces multi_structures CSV on variants
--     "K8685 is available in SM, BS, PD, PW" becomes 4 proper rows.
--
-- 2b. `pairings` CHECK — adds missing pairing_type values:
--     'acrylic', 'mirror', 'compact', 'hpl_laminate', 'kronoart', 'black_wood'
--
-- ══════════════════════════════════════════════════════════════════


-- ──────────────────────────────────────────────────────────────────
-- 2a. DECOR_STRUCTURES — junction table (decor ↔ structure M2M)
-- ──────────────────────────────────────────────────────────────────
--
-- Replaces the CSV column `variants.multi_structures` ("BS, PD, PW").
-- One row per (decor, structure) pair.
--
-- is_primary = 1 marks the "main" structure from the catalog's "Str." column.
-- All others (is_primary = 0) come from the "multi_structures" column.
--
-- Example — Kronospan Global K8685 Biel Alpejska:
--   K8685 × SM  (is_primary=1)  — main structure ("Str." column)
--   K8685 × BS  (is_primary=0)  — from "multi_structures"
--   K8685 × PD  (is_primary=0)  — from "multi_structures"
--   K8685 × PW  (is_primary=0)  — from "multi_structures"
--
-- Each (decor, structure) pair should have at least one corresponding
-- Variant row, but that is enforced at application level (not FK —
-- because variant thickness/format can vary for same decor+structure).
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS decor_structures (
    decor_id        INTEGER NOT NULL REFERENCES decors(id) ON DELETE CASCADE,
    structure_id    INTEGER NOT NULL REFERENCES structures(id) ON DELETE CASCADE,
    is_primary      BOOLEAN NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (decor_id, structure_id)
);

-- Query patterns:
--   "What structures does K8685 come in?" → WHERE ds.decor_id = <K8685>
--   "Which decors have structure PD?"     → JOIN on structure_id
--   "What's the main structure for K8685?" → WHERE is_primary = 1

CREATE INDEX IF NOT EXISTS idx_decor_structures_structure
    ON decor_structures(structure_id);

CREATE INDEX IF NOT EXISTS idx_decor_structures_primary
    ON decor_structures(decor_id, is_primary);


-- ──────────────────────────────────────────────────────────────────
-- 2b. PAIRINGS — expand CHECK constraint
-- ──────────────────────────────────────────────────────────────────
--
-- Original CHECK allowed: 'carcass', 'worktop', 'splashback',
--                           'side_panel', 'plinth'
--
-- Missing from analyzed catalogs:
--   Kronospan: 'acrylic' (AG), 'mirror' (MG), 'compact' (CI),
--              'kronoart' (KA), 'hpl_laminate' (HPL)
--   KronoSwiss: 'black_wood' (BLACK WOOD ●)
--
-- SQLite does not support ALTER TABLE … ADD CONSTRAINT.
-- We must: create new table → copy data → drop old → rename.
-- ──────────────────────────────────────────────────────────────────

-- Step 1: Create new table with expanded CHECK
CREATE TABLE IF NOT EXISTS pairings_new (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    front_decor_id      INTEGER NOT NULL REFERENCES decors(id),
    target_decor_id     INTEGER NOT NULL REFERENCES decors(id),
    pairing_type        TEXT NOT NULL CHECK (pairing_type IN (
                            'carcass',
                            'worktop',
                            'splashback',
                            'side_panel',
                            'plinth',
                            'hpl_laminate',
                            'acrylic',
                            'mirror',
                            'compact',
                            'kronoart',
                            'black_wood'
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

-- Step 2: Drop views that reference the old pairings table
--         (they will be re-created in step 5)
DROP VIEW IF EXISTS v_pairings_full;

-- Step 3: Copy existing data (if any from 01-schema.sql)
INSERT OR IGNORE INTO pairings_new
    SELECT * FROM pairings;

-- Step 4: Swap tables
DROP TABLE IF EXISTS pairings;
ALTER TABLE pairings_new RENAME TO pairings;

-- Step 4: Re-create indexes (were on old table, now gone)
CREATE INDEX IF NOT EXISTS idx_pairings_front ON pairings(front_decor_id);
CREATE INDEX IF NOT EXISTS idx_pairings_target ON pairings(target_decor_id);
CREATE INDEX IF NOT EXISTS idx_pairings_type ON pairings(pairing_type);


-- ──────────────────────────────────────────────────────────────────
-- 2c. VIEWS — convenience queries
-- ──────────────────────────────────────────────────────────────────

-- All structures available for each decor (with structure details)
DROP VIEW IF EXISTS v_decor_structures_full;

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


-- Pairings with full decor details (expanded for new types)
DROP VIEW IF EXISTS v_pairings_full;

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


-- ══════════════════════════════════════════════════════════════════
-- END OF PHASE 2 MIGRATION
-- ══════════════════════════════════════════════════════════════════
