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
| `renderable` *(additive)* | server-side check for `assets/textures/<id>.jpg` | lets the frontend grey out decors whose tileable texture is not yet acquired instead of 500-ing on render |

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

- tr-89ff86d6 — presentation/ has no module-level CATALOG dict;
  `/api/v1/catalog` is served by `CatalogSource` with an offline
  snapshot fallback (completion claim of this spec's work).
- tr-5fba4784 — the catalog source is tested against a faked catalog
  client: mapping, zone derivation, discontinued filtering, renderable
  flag, offline degradation, contract shape.
- tr-2007bfcc — the frontend consumes the payload null-safely and greys
  out non-renderable decors before they reach `/render`.
- tr-0ba0f782 — catalog decor-variant models expose `img_url` but no
  `texture_width_mm` or `hex_color`; hence the local-override decisions
  above.
- tr-f96d9afa — the catalog SQLite database exists (gitignored artifact);
  needed for the live smoke.

The original premise set — "the hardcoded CATALOG dict still ships",
"/render reads tiling width and zone from that dict", "the frontend
depends on the dict's payload shape" — was killed by this work shipping
(commit 870157e) and diverged by design; those pre-state facts are
referred to here by title only so their deaths don't fail this spec.

## Work

- wk-03434168 — Route krono-compositor CATALOG dict to catalog service
  (ADR-008). Beads twin: kuchnie-9vz. **Closed 2026-07-12** (870157e).

## Acceptance

Filed at close per the convention's ordering note (commit first, then
`done --claim`):

1. tr-89ff86d6 — no module-level CATALOG dict in presentation/;
   `/api/v1/catalog` served from the catalog-service-backed source with
   offline snapshot fallback.
2. tr-5fba4784 — catalog source tested against a faked catalog client
   across mapping, zone derivation, offline degradation, and contract
   shape.
