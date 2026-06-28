-- ══════════════════════════════════════════════════════════════════
-- KUCHNIE CATALOG — Migration Phase 4a: Variant Availability
-- Version: 1.3.0
-- Date: 2026-06-27
-- Requires: 01-schema.sql, 02-phase1-worktop-specs.sql,
--           03-phase2-decor-structures-and-pairings.sql
-- ══════════════════════════════════════════════════════════════════
--
-- Tracks per-variant stock status and delivery information.
-- One variant can have multiple availability rows (e.g. Express 24h
-- AND standard 7-day delivery from different warehouses).
--
-- Source data:
--   Kronospan: EX flag on Global Collection, K (konfekcja), min.1 szt.
--   KronoSwiss: no explicit availability columns in catalog
--
-- ══════════════════════════════════════════════════════════════════


CREATE TABLE IF NOT EXISTS variant_availability (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id      INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    channel         TEXT NOT NULL CHECK (channel IN (
                        'express_24h',   -- available within 24h (EX flag)
                        'konfekcja',     -- cut-to-size / small quantities (K flag)
                        'standard',      -- regular lead time
                        'on_request'     -- special order only
                    )),
    available       BOOLEAN NOT NULL DEFAULT TRUE,
    min_order_qty   INTEGER NOT NULL DEFAULT 1,
    warehouse       TEXT,               -- 'Mielec', 'Pustków', 'Żary'
    lead_time       TEXT,               -- '24h', '7d', '14d', 'request'
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(variant_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_variant_availability_variant
    ON variant_availability(variant_id);
CREATE INDEX IF NOT EXISTS idx_variant_availability_channel
    ON variant_availability(channel);


-- View: all variants with their availability channels
DROP VIEW IF EXISTS v_variants_availability;

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


-- ══════════════════════════════════════════════════════════════════
-- END OF PHASE 4a MIGRATION
-- ══════════════════════════════════════════════════════════════════
