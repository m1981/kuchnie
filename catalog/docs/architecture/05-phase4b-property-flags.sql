-- ══════════════════════════════════════════════════════════════════
-- KUCHNIE CATALOG — Migration Phase 4b: Property Flags
-- Version: 1.4.0
-- Date: 2026-06-27
-- Requires: 01–04
-- ══════════════════════════════════════════════════════════════════
--
-- EAV-style table for variant material properties.
-- Properties are NOT columns on `variants` — they vary per product
-- and catalog. EAV prevents schema bloat and allows future extension.
--
-- Known properties (from analyzed catalogs):
--   antibacterial      — KronoSwiss (all products), Kronospan (select)
--   waterproof          — Kronospan Slim Line, KronoSwiss BLACK WOOD
--   anti_fingerprint    — Kronospan SU structure, KronoSwiss BE Velvet
--   uv_stable           — Kronospan (select)
--   scratch_resistant   — Kronospan (select)
--   fire_resistant      — KronoSwiss BLACK WOOD (D-s1,d0)
--
-- ══════════════════════════════════════════════════════════════════


CREATE TABLE IF NOT EXISTS property_flags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id      INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    property        TEXT NOT NULL,
    value           BOOLEAN NOT NULL DEFAULT 1,
    source          TEXT,           -- 'datasheet', 'catalog_page', 'import'
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(variant_id, property)
);

CREATE INDEX IF NOT EXISTS idx_property_flags_variant
    ON property_flags(variant_id);


-- View: property flags with variant context
DROP VIEW IF EXISTS v_property_flags;

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


-- ══════════════════════════════════════════════════════════════════
-- END OF PHASE 4b MIGRATION
-- ══════════════════════════════════════════════════════════════════
