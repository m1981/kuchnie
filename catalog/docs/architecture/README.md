# Architecture — Kuchnie Catalog

Version: 1.0.0 (design)
Date: 2026-06-27

## Files

| File | Description |
|------|-------------|
| `01-schema.sql` | SQLite schema — tables, indexes, views, seed data |
| `02-pydantic-models.py` | Pydantic v2 models — API schemas, validation, migration |
| `03-fastapi-design.py` | FastAPI API design — endpoints, queries, business logic |

## Stack

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Alpine.js + Vite)                                │
│  catalog/index.html                                         │
└─────────────────────────┬───────────────────────────────────┘
                          │ fetch('/api/...')
┌─────────────────────────▼───────────────────────────────────┐
│  FastAPI (Python 3.12+)                                     │
│  catalog/api/main.py                                        │
│  ├── /api/decors        ← CRUD + filters                    │
│  ├── /api/variants      ← CRUD + filters                    │
│  ├── /api/pairings      ← resolve + suggest                 │
│  ├── /api/materials     ← read-only                         │
│  ├── /api/search        ← full-text                         │
│  └── /api/admin         ← migrate, stats                    │
└─────────────────────────┬───────────────────────────────────┘
                          │ aiosqlite / SQLAlchemy
┌─────────────────────────▼───────────────────────────────────┐
│  SQLite                                                     │
│  catalog/db/catalog.db                                      │
│  ├── producers, collections, materials                      │
│  ├── decors, variants, edges                                │
│  ├── pairings                                               │
│  └── v_decors_full, v_pairings_full (views)                 │
└─────────────────────────▲───────────────────────────────────┘
                          │ migration
┌─────────────────────────┴───────────────────────────────────┐
│  YAML (source of truth)                                     │
│  data/materials/kronospan/decors.yaml                       │
│  data/materials/egger/decors.yaml (future)                  │
│  data/materials/swiss-krono/decors.yaml (future)            │
└─────────────────────────────────────────────────────────────┘
```

## Migration Plan

```
Phase 1 (NOW): Design — schema + models + API (this directory)
Phase 2: Add Egger PDF → validate schema with 2nd producer
Phase 3: Add Swiss-Krono PDF → validate schema with 3rd producer
Phase 4: Implement SQLite + FastAPI + migration script
Phase 5: Frontend → API (replace direct JSON fetch)
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite (not Postgres) | File-based, no server, sufficient for <100K rows |
| Pydantic v2 (not dataclasses) | FastAPI native, validation, JSON Schema generation |
| Business IDs as TEXT (not INT) | Human-readable, stable across migrations |
| Soft deletes | Audit trail, undo capability |
| Views for common queries | Performance, simplicity |
| Pairings at decor level (not variant) | Same pairing applies to all variants of a decor |
| Roles as JSON array in SQLite | Flexible, avoids junction table for 1:N |
| Edge as separate entity | Shared across variants, different suppliers |

## Data Scale (projected)

| Entity | Kronospan | Egger | Swiss-Krono | Total |
|--------|-----------|-------|-------------|-------|
| Decors | 177+70 (worktops) | ~200 | ~100 | ~550 |
| Variants | ~900 | ~400 | ~200 | ~1500 |
| Pairings | ~500 | ~200 | ~100 | ~800 |
| Edges | ~50 | ~30 | ~20 | ~100 |
