# Kitchen Configurator — Data Model Design

> **Status**: Phase 1 MVP complete (2026-06-30). Phase 2 (curated content) pending.
> See `../specs/configurator-api.md` for the API spec; the completed phase log
> is archived at `../archive/ROADMAP.md`. New work is tracked in the truth ledger.

> **Goal**: Walk a customer through 6 steps to a complete material specification
> for their kitchen, with pre-filtered options at each step based on prior choices.

---

## Mental model: configurator = state machine

```
┌─────────┐  pick   ┌─────────┐  auto-  ┌─────────┐  pick   ┌─────────┐
│  START  │──front─►│ FRONT   │─suggest─►│ CARCASS │─worktop►│ WORKTOP │
└─────────┘         │ CHOSEN  │          │ CHOSEN  │         │ CHOSEN  │
                    └─────────┘          └─────────┘         └─────────┘
                                                                 │
                                                                 │ auto
                                                                 ▼
                                            ┌─────────┐  pick   ┌─────────┐
                                            │  DONE   │◄─plinth─│  EDGE   │
                                            │ (BOM)   │         │ CHOSEN  │
                                            └─────────┘         └─────────┘
```

Each state stores: `{front_variant_id, carcass_variant_id, worktop_variant_id, edge_id, side_panel_variant_id, plinth_variant_id}`.

Each transition: given current state, return list of valid next options + recommended default.

---

## New tables (additions to existing schema)

### Table 1: `configurator_sessions` — track in-progress configurations

```sql
CREATE TABLE configurator_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token   TEXT NOT NULL UNIQUE,        -- UUID for anonymous users
    user_id         INTEGER,                     -- nullable for guests
    kitchen_name    TEXT,                        -- "Mom's kitchen"
    current_step    TEXT NOT NULL DEFAULT 'front'
                    CHECK (current_step IN ('front','carcass','worktop','edge','side_panel','plinth','done')),
    front_variant_id        INTEGER REFERENCES variants(id),
    carcass_variant_id      INTEGER REFERENCES variants(id),
    worktop_variant_id      INTEGER REFERENCES variants(id),
    edge_id                 INTEGER REFERENCES edges(id),
    side_panel_variant_id   INTEGER REFERENCES variants(id),
    plinth_variant_id       INTEGER REFERENCES variants(id),
    style_tags      TEXT,                        -- JSON: ["modern", "scandinavian"]
    budget_tier     TEXT CHECK (budget_tier IN ('budget','standard','premium','luxury')),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Why**: Lets users come back, share configurations, get quotes. Without this, no persistence.

---

### Table 2: `style_tags` — semantic filtering

```sql
CREATE TABLE style_tags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name_pl         TEXT NOT NULL,
    name_en         TEXT,
    category        TEXT NOT NULL                -- 'aesthetic', 'era', 'material_feel'
                    CHECK (category IN ('aesthetic','era','material_feel','color_mood')),
    description     TEXT
);

-- Seed: modern, scandinavian, classic, industrial, rustic, minimalist,
--       art-deco, mid-century, country, mediterranean, japandi
--       warm, cool, neutral, bold, soft

CREATE TABLE decor_style_tags (
    decor_id        INTEGER NOT NULL REFERENCES decors(id) ON DELETE CASCADE,
    style_tag_id    INTEGER NOT NULL REFERENCES style_tags(id) ON DELETE CASCADE,
    relevance       INTEGER NOT NULL DEFAULT 1   -- 1=weak, 2=strong, 3=defining
                    CHECK (relevance BETWEEN 1 AND 3),
    PRIMARY KEY (decor_id, style_tag_id)
);
```

**Why**: Customers think in styles, not decor codes. "Show me Scandinavian fronts" must work.

---

### Table 3: `curated_kitchens` — pre-designed reference kitchens

```sql
CREATE TABLE curated_kitchens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,               -- "Skandynawski Dąb"
    description     TEXT,
    hero_image      TEXT,                        -- /kitchens/scandi_oak.jpg
    front_variant_id        INTEGER NOT NULL REFERENCES variants(id),
    carcass_variant_id      INTEGER NOT NULL REFERENCES variants(id),
    worktop_variant_id      INTEGER REFERENCES variants(id),
    edge_id                 INTEGER REFERENCES edges(id),
    side_panel_variant_id   INTEGER REFERENCES variants(id),
    plinth_variant_id       INTEGER REFERENCES variants(id),
    style_tag_slugs         TEXT,                -- JSON: ["scandinavian", "modern"]
    budget_tier             TEXT,
    featured                BOOLEAN DEFAULT FALSE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Why**: "Start from a template" is the #1 user request. Most users don't want to pick from 186 variants — they want 5–10 pre-designed kitchens to riff off.

---

### Table 4: `worktop_compatibility` — front ↔ worktop curated matches

```sql
CREATE TABLE worktop_compatibility (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    front_decor_id  INTEGER NOT NULL REFERENCES decors(id),
    worktop_decor_id INTEGER NOT NULL REFERENCES decors(id),
    match_quality   TEXT NOT NULL                -- 'designer_pick','safe','bold'
                    CHECK (match_quality IN ('designer_pick','safe','bold','clash')),
    style_note      TEXT,                        -- "Warm neutral combo"
    priority        INTEGER DEFAULT 1,
    UNIQUE(front_decor_id, worktop_decor_id)
);
```

**Why**: `pairings` table has `pairing_type='worktop'` but no quality dimension. A user wants to see *"designer's pick"* vs *"bold contrast"* vs *"safe default"*.

---

### Table 5: `configurator_steps_meta` — the canonical step definitions

```sql
CREATE TABLE configurator_steps (
    step_key        TEXT PRIMARY KEY,            -- 'front', 'carcass', etc.
    step_order      INTEGER NOT NULL,
    name_pl         TEXT NOT NULL,
    name_en         TEXT,
    description     TEXT,
    is_required     BOOLEAN DEFAULT TRUE,
    can_skip        BOOLEAN DEFAULT FALSE,
    fallback_logic  TEXT                         -- 'use_carcass', 'use_front', 'manual'
);

INSERT INTO configurator_steps VALUES
    ('front',       1, 'Front',          'Front',          'Wybierz wygląd kuchni', 1, 0, NULL),
    ('carcass',     2, 'Korpus',         'Carcass',        'Wnętrze szafek',        1, 0, 'use_front'),
    ('worktop',     3, 'Blat',           'Worktop',        'Powierzchnia robocza',  1, 0, NULL),
    ('edge',        4, 'Obrzeże',        'Edge',           'Krawędzie paneli',      0, 1, 'auto_match'),
    ('side_panel',  5, 'Bok szafki',     'Side panel',     'Widoczne boki szafek',  0, 1, 'use_carcass'),
    ('plinth',      6, 'Cokół',          'Plinth',         'Listwa dolna',          0, 1, 'use_carcass');
```

**Why**: Hardcoding step order in app code = brittle. Schema-driven = swap order, add steps without code change.

---

## API endpoints — the configurator flow

### `POST /configurator/sessions`
Start a new session. Returns `session_token`.

```json
{ "session_token": "abc-123", "current_step": "front" }
```

### `GET /configurator/sessions/{token}/options`
Return available choices for the current step, given prior selections.

```json
{
  "current_step": "carcass",
  "front_variant": { "id": "K101-CH-18-PE", "name": "Biały Frontowy" },
  "options": [
    {
      "variant_id": "K110-CH-18-SM",
      "name": "Biały Korpusowy",
      "img_url": "/producers/kronospan/decors/K0110.jpg",
      "recommendation": "designer_pick",
      "rationale": "Standardowy biały korpus, idealnie dopasowany",
      "price_delta": 0
    },
    {
      "variant_id": "K101-CH-18-PE",
      "name": "Biały Frontowy (matching)",
      "recommendation": "premium",
      "rationale": "Korpus z tego samego dekoru — bardziej spójny wygląd",
      "price_delta": 120
    }
  ],
  "default_choice": "K110-CH-18-SM"
}
```

### `PATCH /configurator/sessions/{token}/select`
Make a choice, advance to next step.

```json
{ "step": "carcass", "variant_id": "K110-CH-18-SM" }
```

Response: next step's options.

### `GET /configurator/sessions/{token}/bom`
Get the full bill of materials for the current configuration.

```json
{
  "complete": true,
  "items": [
    { "role": "front",   "variant_id": "K101-CH-18-PE", "qty_m2": 12.5 },
    { "role": "carcass", "variant_id": "K110-CH-18-SM", "qty_m2": 28.0 },
    { "role": "worktop", "variant_id": "K093-WP-38-BS", "qty_lm": 4.2 },
    { "role": "edge",    "edge_id": "K-0101-PE",        "qty_lm": 45.0 }
  ],
  "estimated_price_pln": 8420
}
```

### `GET /configurator/templates`
Get curated starting points.

```json
[
  {
    "slug": "skandynawski-dab",
    "name": "Skandynawski Dąb",
    "hero_image": "/kitchens/scandi_oak.jpg",
    "style_tags": ["scandinavian", "warm"],
    "budget_tier": "standard",
    "preview": { "front": "K101", "worktop": "K093", "...": "..." }
  }
]
```

### `POST /configurator/sessions/{token}/from_template`
Initialize a session from a curated kitchen, user can then modify.

---

## Step-by-step logic (where the smarts live)

### Step 1: FRONT
- **Input**: optional style filter (`?style=scandinavian&color_family=dab`)
- **Source**: `variants` where `roles` contains `'front'`
- **Sort**: featured/popular first, then by color family
- **No prerequisites** — this is the entry point

### Step 2: CARCASS
- **Source**:
  1. `pairings` where `front_decor_id = chosen_front.decor_id AND pairing_type = 'carcass'`
  2. Sorted by `priority`, then `match_type` (exact → close → default)
- **Fallback** if no pairings: show all carcass-role variants from same producer
- **Recommended**: the `priority=1, match_type='default'` row (usually white K110)
- **Premium option**: variant with same `decor_id` as front (matching corpus)

### Step 3: WORKTOP
- **Source**:
  1. `worktop_compatibility` where `front_decor_id = chosen_front.decor_id`
  2. Group by `match_quality`: safe → designer_pick → bold
- **Sub-choices** (within picked worktop decor):
  - Construction (postformed / ABS / slim)
  - Profile (U / R3 / square)
  - Thickness (28 / 38 mm)
  - Width (600 / 900 / 1200 mm)

### Step 4: EDGE
- **Source**: `variant_edges` where `variant_id = chosen_front.variant_id`
- **Fallback**: lookup edges by matching decor code (e.g., K-0101-PE for K101)
- **Skippable**: defaults to auto-match
- **Premium option**: 2mm ABS (thicker, more impact-resistant)

### Step 5: SIDE PANEL
- **Default**: same as carcass (cheap)
- **Premium**: same as front (matching exposed sides)
- **Custom**: HPL laminate matching front decor (`pairing_type='hpl_laminate'`)
- **Skippable**: defaults to carcass

### Step 6: PLINTH
- **Default**: same as carcass
- **Options**: matching front, aluminum, stainless
- **Skippable**: defaults to carcass

---

## Critical data gaps to populate

Before this works end-to-end, we need to populate:

| Table | Current rows | Target | How |
|---|---|---|---|
| `pairings` (carcass) | ~5 | 108 (one per Kronospan decor) | For each front decor, set K110 as default carcass |
| `worktop_compatibility` | 0 | ~500 (5 worktops × 108 fronts) | Curated by designer or rule-based |
| `variant_edges` | sparse | 186 (one per variant) | Lookup by `obrzeze` field from `global-collection-decory.yaml` |
| `decor_style_tags` | 0 | ~400 (avg 3 tags × 148 decors) | Manual or LLM-classified |
| `curated_kitchens` | 0 | 8–12 | Designer-curated reference kitchens |

**Rule-based seeding for `pairings`** (quick win):
```python
# For every Kronospan decor, add a default carcass pairing
for decor in decors_kronospan:
    add_pairing(front=decor, target='K110', type='carcass', match='default', priority=1)
    # If matching corpus variant exists, add as premium option
    if decor.has_corpus_variant:
        add_pairing(front=decor, target=decor, type='carcass', match='exact', priority=2)
```

**Rule-based seeding for `worktop_compatibility`**:
```python
# All worktops are "safe" with their own decor
# Worktops in same color_family are "designer_pick"
# Worktops in contrasting families are "bold"
for front in fronts:
    for worktop_decor in worktops:
        if front.decor_id == worktop_decor.decor_id:
            quality = 'designer_pick'
        elif front.color_family == worktop_decor.color_family:
            quality = 'safe'
        else:
            quality = 'bold'
        add_compat(front, worktop_decor, quality)
```

---

## What the frontend looks like

```
┌────────────────────────────────────────────────────────┐
│ KROK 2/6: Wybierz korpus                               │
├────────────────────────────────────────────────────────┤
│ Wybrany front: 🟫 Biały Frontowy (K101)                │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ⭐ POLECANE                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ [img]    │  │ [img]    │  │ [img]    │              │
│  │ K110     │  │ K0110-SM │  │ K8685    │              │
│  │ Biały    │  │ Biały    │  │ Biel     │              │
│  │ Korpusowy│  │ Korpusowy│  │ Alpejska │              │
│  │ +0 zł    │  │ +0 zł    │  │ +35 zł/m²│              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                        │
│  💎 PREMIUM (matching front)                           │
│  ┌──────────┐                                          │
│  │ [img]    │                                          │
│  │ K101     │                                          │
│  │ Biały    │                                          │
│  │ Frontowy │                                          │
│  │ +120 zł/m²│                                         │
│  └──────────┘                                          │
│                                                        │
│  [WSTECZ]                              [DALEJ →]       │
└────────────────────────────────────────────────────────┘
```

---

## Implementation phases

### Phase 1 (MVP, 1 day): Static configurator
- Add `configurator_sessions` table
- Endpoint: `GET /configurator/options?step=X&front=Y`
- Use existing `pairings` table, no curated logic yet
- Frontend: linear stepper with current data

### Phase 2 (2–3 days): Curated content
- Populate `pairings` for all decors (rule-based)
- Add `worktop_compatibility` table + seed it rule-based
- Add `curated_kitchens` table + seed 5–8 reference kitchens
- Frontend: "Start from template" entry point

### Phase 3 (1 week): Smart UX
- Add `style_tags` + `decor_style_tags`
- Add "compare 3 options side-by-side" view
- Add "shareable link" for sessions
- Add price calculation (needs price table — out of scope here)

### Phase 4 (future): AI assist
- "Upload a Pinterest photo, get matched decors"
- "Describe your style in words" → tag-based search
- 3D preview of selected combination

---

## Open questions / decisions needed

1. **Anonymous or required login?** — Recommend anonymous with `session_token` cookie, optional login to save.
2. **Pricing?** — Schema doesn't have prices. Need a separate `variant_prices` table with region/dealer dimensions.
3. **Quantity?** — Configurator picks materials. Cabinet count → square meters comes from `kuchnie-core` decomposer. Integration point.
4. **Multi-kitchen?** — One user, many saved kitchens. Easy via `configurator_sessions.user_id`.
5. **"Custom" option?** — Allow customer to specify a decor not in catalog? (e.g., supplier sample.) Recommend: no in MVP, add as `notes` field.
6. **Worktop subtype picker** — Worktop selection has nested choices (decor → construction → profile → thickness → width). Treat as one step with sub-wizard or split into multiple steps?

---

## Summary: what to build

**Schema**: 5 new tables (`configurator_sessions`, `style_tags`, `decor_style_tags`, `curated_kitchens`, `worktop_compatibility`, `configurator_steps`)

**API**: 5 endpoints (sessions CRUD + options + bom + templates)

**Data**: populate `pairings`, `worktop_compatibility`, `variant_edges`, `curated_kitchens`

**Frontend**: 6-step wizard + template gallery + summary/BOM view

**Estimate**: 1 day MVP, 2 weeks for polished v1.
