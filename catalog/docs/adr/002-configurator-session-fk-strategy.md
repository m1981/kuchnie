# ADR-002: Configurator sessions store business_id strings, not integer FKs

**Status**: Accepted
**Date**: 2026-06-30

---

## Context

The `configurator_sessions` table needs to reference variants and edges chosen
by the user. The initial schema used `INTEGER REFERENCES variants(id)` and
`INTEGER REFERENCES edges(id)` — standard FK patterns.

However, the configurator API works with `business_id` strings (e.g.,
`K8685-CH-18-SM`), not integer PKs. Storing integer FKs would require a
lookup on every write and would add no referential integrity benefit over
application-level validation.

## Decision

Store `business_id` strings directly (TEXT columns, no FK constraint).
Validate existence at API level before writing.

```
front_variant_id  TEXT   -- 'K8685-CH-18-SM'
carcass_variant_id TEXT  -- 'K110-CH-18-SM'
edge_id           INTEGER -- edges.id (small table, integer PK is fine)
```

## Consequences

### Positive
- No extra JOIN to resolve integer PKs on every read/write.
- `business_id` is human-readable in the DB (easier to debug).
- API validation catches bad values with clear 400 errors.

### Negative
- No DB-level cascade if a variant is deleted. Acceptable: variants are
  never deleted in practice (they're catalog data).
- Need to keep `business_id` unique constraint on `variants` table (already
  exists).

## See also

- `db/schema.sql` — `configurator_sessions` table (lines ~310–325)
- `docs/specs/configurator-api.md` — spec
