# Spec: Route the compositor's material catalog to the catalog service

> Reader: the agent or human implementing wk-03434168, or judging later whether the compositor really left the hardcoded-dict era | Enables: replacing `presentation/catalog_db.py` with a catalog-service-backed source without breaking the render path or the sales frontend | Update-trigger: the `/api/v1/catalog` contract, the catalog service's decor-row shape, or the field-mapping decisions below change

## Intent

The compositor is the Stage-1 sales tool. Today it ships its own invented
material list; the material master lives in the catalog service. This work
routes the compositor's catalog endpoint to that service so the ids a client
picks at the first visit are real, purchasable decor codes that flow onward
to ERP quotes and CAM.

**Scope:** a read-only, stdlib-only catalog source inside
`krono-compositor-mvp` that fetches decor-variant rows from the catalog
service, maps them to the material shape the compositor already serves, and
caches them with a graceful offline fallback (sales visits happen away from
the office; a dead catalog service must degrade to the last snapshot with a
warning, never crash the app). `presentation/catalog_db.py` is deleted;
`GET /api/v1/catalog` keeps its response shape.

**Field mapping (the load-bearing decisions):**

| Compositor field | Source | Rule |
|---|---|---|
| `id` | decor/variant business id | texture files on disk are renamed to match decor codes |
| `name` | catalog decor name | as-is (already Polish) |
| `allowed_zone` | variant role | worktop → COUNTERTOP_ONLY; front → FRONT_ONLY; carcass/universal → ANY |
| `hex_color` | catalog color-family hex approximation, overridden by decor miniature when the frontend can show images | swatch fidelity improves as miniatures land (see the decor-miniature acquisition issue, tracked separately by title on purpose) |
| `texture_width_mm` | **local override table** in the compositor, keyed by decor id | the catalog does not model it yet; promoting it into the catalog is a follow-up decision, not part of this work |
| `price_group` | **local mapping** in the compositor | prices are ERP-owned; the sales-UI grouping stays a presentation concern until a real pricing decision is made |
| `scenes` | stays local | scenes are compositor render assets, not materials |

**Non-goals:**
- No texture acquisition: `/render` still requires a tileable JPG on disk
  per decor; decors without one are served in the catalog payload but the
  render endpoint keeps failing loudly for them (existing 500 behavior).
  Texture/miniature sourcing rides with the decor-miniature acquisition
  issue, referenced by title.
- No catalog schema changes (no `texture_width_mm` column upstream).
- No pricing logic.
- No import from `kitchen-erp` — the client pattern is copied, not shared;
  components only import `kuchnie_core`.

**Pattern to copy:** kitchen-erp's material mirror (ADR-011 phase 3): a
stdlib `urllib` client paging `GET /catalog/decors`, a typed
`CatalogUnavailable` failure, tests against a faked client, live smoke
against the real service.

## Decisions

- `docs/adr/008-material-master-catalog.md` — catalog/ is the single
  material master; components reference it by business id.
- `docs/adr/011-*-becomes-kitchen-erp.md` — the compositor is the
  Stage-1 sales tool; the mirror pattern (catalog owns identity, consumers
  own their local concerns) established in phase 3.

## Ground truths

- tr-88dc0d9a — the compositor still ships the hardcoded CATALOG dict
  (the fact this whole spec exists to kill).
- tr-80b8e06f — `/render` reads `texture_width_mm` + `allowed_zone` from
  CATALOG and loads textures from `assets/textures/<id>.jpg` on disk.
- tr-0ba0f782 — catalog decor-variant models expose `img_url` but no
  `texture_width_mm` or `hex_color`; hence the local-override decisions
  above.
- tr-ee966c4c — the frontend depends on the
  `price_groups`/`materials`/`scenes` payload shape and per-material color
  swatches.
- tr-7e7a33cd — the catalog SQLite database exists (gitignored artifact);
  needed for the live smoke.

## Work

- wk-03434168 — Route krono-compositor CATALOG dict to catalog service
  (ADR-008). Beads twin: kuchnie-9vz.

## Acceptance

Pre-written `done --claim` texts (file after the shipping commit lands,
per the ordering note in the convention):

1. "krono-compositor-mvp/src/compositor/presentation/ contains no
   module-level CATALOG dict; /api/v1/catalog is served from a
   catalog-service-backed source with an offline snapshot fallback"
   — evidence: `grep -rn "^CATALOG" krono-compositor-mvp/src/compositor/presentation/`
   (empty) plus a grep for the source module wiring in `api.py`.
2. "the compositor catalog source is tested against a faked catalog
   client: decor-row mapping, allowed-zone derivation, offline
   degradation to snapshot, and the /api/v1/catalog contract shape"
   — evidence: `grep -n "def test" krono-compositor-mvp/tests/test_catalog_source.py`.
