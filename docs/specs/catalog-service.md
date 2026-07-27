# Spec: Catalog service — API surface and data pipeline

> Reader: anyone touching the decor catalog service or wondering whether a
> `catalog/` module is alive | Enables: knowing which modules serve which
> use case, and rebuilding `catalog.db` from committed data after loss |
> Update-trigger: a router/repo is added or removed, the rebuild sequence
> changes, or the UC-3 dressing decides the configurator's fate

Serves: UC-3 (first-visit decor session — browsing/pairing surface),
UC-9 (catalog maintenance), UC-8 (mirror refresh consumes `/admin/full`).
Born from the 2026-07-16 dark-triage: these modules were DARK not because
they are dead but because their consumption is transitive (FastAPI
`include_router` + app-level tests) — this spec is their upward trace.

## API surface (catalog/api + catalog/repositories)

| Router | Repository | Serves |
|---|---|---|
| `catalog/api/routers/decors.py` | `catalog/repositories/decor_repo.py` | UC-3 browsing, UC-9 |
| `catalog/api/routers/producers.py` | — | UC-3/UC-9 filters |
| `catalog/api/routers/worktops.py` | `catalog/repositories/worktop_repo.py` | UC-3 worktop pairing |
| `catalog/api/routers/availability.py` | `catalog/repositories/availability_repo.py` | UC-4 channel/lead-time lookup |
| `catalog/api/routers/configurator.py` | `catalog/repositories/configurator.py` | UC-3 **candidate** — see note |
| `catalog/api/routers/admin.py` | — (raw queries) | UC-8 mirror feed, stats |
| pairings (in decors router) | `catalog/repositories/pairing_repo.py` | UC-3 front↔carcass pairing |

All are wired in `catalog/api/main.py` and exercised through the app by
the catalog test suite. **Configurator note:** the session/step/template
flow (`configurator.py` router + repository) is an implementation
CANDIDATE for UC-3; adopting it here means *traced*, not *endorsed* —
keep-or-kill is decided when UC-3 gets dressed (`use-cases.md`
inventory note), and this spec's update-trigger fires then.

## Data pipeline — the verified rebuild path

`catalog/db/catalog.db` is fully rebuildable from committed sources.
Re-verified 2026-07-27 against a scratch database: the sequence below
reproduces production counts exactly (2 producers, 148 decors, 222
variants, 145 pairings, 123 variant-edge links, 87 edge rows) —
tr-44356ef4.

```bash
# 1. Core catalog from committed YAML (schema + import):
.venv/bin/python -m catalog.scripts.seed --db <target> \
    catalog/data/kronospan_full.yaml catalog/data/kronoswiss_full.yaml
# 2. Curated extras. ORDER MATTERS in one place: seed_curated_kitchens
#    creates the style_tags rows that seed_decor_style_tags links to, so
#    it must run first (falsified "in any order" 2026-07-27 — a wrong
#    order yields 0 style associations, silently):
#    seed_pairings_edges, seed_curated_kitchens, seed_decor_style_tags,
#    seed_worktop_compat, seed_worktop_uu
```

Living modules: `catalog/scripts/seed.py` (accepts `--db` since the
verification), `catalog/scripts/importer.py`, `catalog/scripts/seed_pairings_edges.py`,
`catalog/scripts/seed_decor_style_tags.py`, `catalog/scripts/seed_curated_kitchens.py`,
`catalog/scripts/seed_worktop_compat.py`, `catalog/scripts/seed_worktop_uu.py`
(U-U postformed worktops — see `catalog/docs/specs/worktop-uu-seeding.md`),
`catalog/db/engine.py` (schema + in-place migration). The one-shot YAML
generators and the 1.5.0 migration are atticized with tombstones
(`attic/catalog-*.py`) — their output is the committed data itself.

Known roughness, accepted for now: the five `seed_*` extras hardcode the
canonical DB path — and, sharper (2026-07-17 verifier observation): they
ACCEPT a `--db` argument and silently ignore it, so a naive
`--db scratch` run targets the canonical DB (idempotently). Rebuilding
to another target means patching `DB_PATH` in-process; a real shared
`--db` flag is filed only if a real rebuild ever needs it. Residual
found at the 2026-07-27 re-verification: production carries 6
`decor_style_tags` rows the tagger does not regenerate (decors
0514/0515 × modern/stone/matte) — hand-era tags outside the committed
rules; the pinned rebuild counts deliberately exclude that table.

## Ground truths

- tr-44356ef4 — the rebuild sequence reproduces production counts on a
  scratch database (verified 2026-07-16).

## Work

- wk-df912c3a (bd kuchnie-yki) — the 2026-07-16 dark-triage execution
  that created this spec.
