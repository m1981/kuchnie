# Spec: Builder GUI — Walking Skeleton

## Problem

The configurator API works (6 endpoints, 227 tests pass) but the frontend is
still a flat catalog grid. Users can't build a kitchen — they can only browse
decors. The mockup-builder.html shows the target UX: grid + sidebar assembly.

**Motivation (ground truth: ADR-005)**: templates make repeat work cheap.
The sidebar is free slot composition + saved templates, deliberately chosen
over the rigid wizard flow the backend implements — load a proven
combination, swap one slot, save as a new template. The wizard API stays the
validation/recommendation engine; it does not dictate the UI's step order.

## Walking Skeleton (thinnest end-to-end slice)

```
┌────────────────────────────┬──────────────────┐
│  Grid (Alpine.js)          │  Sidebar          │
│                            │                   │
│  Load /catalog/full        │  4 slots:         │
│  Show cards                │    base_front     │
│  Click card → assign       │    wall_front     │
│                            │    carcass        │
│                            │    worktop        │
│                            │                   │
│                            │  [Zapisz szablon] │
└────────────────────────────┴──────────────────┘
```

### What's IN scope (walking skeleton)

1. **Layout**: CSS grid with main area (60%) + sidebar (40%)
2. **Grid**: Load variants from `/catalog/full`, render cards with:
   - Color swatch (background color from hex_approx or placeholder)
   - Name + business_id
   - Role badges (front/blat/korpus)
   - Assigned badge when selected (DÓŁ/GÓRA/KORPUS/BLAT)
3. **Sidebar**: 4 slots as per mockup-builder.html
   - base_front (required)
   - wall_front (optional, collapsible)
   - carcass (required)
   - worktop (required)
4. **Click-to-assign**: Click card → fill active slot → advance to next empty
5. **Clear slot**: Click ✕ → empty slot, remove badge from card
6. **Save template**: Button calls API or saves to localStorage
7. **Session sync**: On load, check localStorage for existing session

### What's OUT of scope (later)

- Search input *(since shipped)*
- Filter dropdowns (producer, type, structure, color) *(since shipped)*
- Role tab filtering *(since shipped — slot focus auto-filters, advisory per ADR-005)*
- Edge auto-assignment
- Compatibility check *(partially shipped — pairing recommendations + role
  mismatch warnings + discontinued flags, all advisory)*
- Template list in sidebar *(since shipped)*
- Compare mode
- Two-tone toggle *(since shipped — wall_front advances after base_front
  with explicit "pomiń" skip; decision persisted)*
- Responsive/mobile
- Keyboard navigation

Backend sync (session replay on BOM export, shareable token) also shipped —
see CHANGELOG and ADR-005.

## Architecture

### Current state

- `public/index.html` — Alpine.js, loads `/catalog/full`, flat grid
- `api/routers/admin.py` — serves `/catalog/full` with all data
- `api/routers/configurator.py` — 6 endpoints (session, options, select, bom, templates, from_template)

### What changes

| File | Change |
|---|---|
| `public/index.html` | Replace flat grid with builder layout (grid + sidebar) |
| `public/index.html` | Add sidebar Alpine.js state (slots, assign, clear) |
| `public/index.html` | Add CSS for sidebar, slots, assigned badges |
| `api/routers/admin.py` | No change — `/catalog/full` already returns everything |
| `api/routers/configurator.py` | No change — endpoints already exist |

### Data flow

```
1. Page loads → GET /catalog/full → store in Alpine.allDecors
2. User clicks card → Alpine assigns to active slot
3. (Optional) POST /configurator/sessions → get token
4. (Optional) PATCH .../select → sync with backend
5. "Zapisz" → localStorage.save(template) or POST .../from_template
```

### Alpine.js state model

```javascript
{
  // Grid data
  allDecors: [],           // from /catalog/full
  
  // Sidebar slots
  slots: {
    base_front: null,      // { variant_id, name, code, color }
    wall_front: null,      // same or null
    carcass: null,
    worktop: null,
  },
  activeSlot: 'base_front',
  
  // Session (optional sync)
  sessionToken: null,
  
  // Methods
  assignCard(decor, variant) → fills activeSlot, advances
  clearSlot(slotName) → empties slot
  saveTemplate() → localStorage or API
  loadTemplate(data) → fills all slots
}
```

## Test Cases

These are browser-level tests (manual or Playwright later):

```
test_grid_loads_cards_from_api
test_click_card_assigns_to_active_slot
test_assigned_card_shows_badge
test_click_clear_empties_slot
test_clear_removes_badge_from_card
test_active_slot_advances_after_assign
test_wall_front_slot_is_optional
test_save_template_to_localstorage
test_load_restores_from_localstorage
```

## Success Criteria

- [ ] Grid shows all variants from /catalog/full
- [ ] Clicking a card fills the active sidebar slot
- [ ] Assigned cards show a badge (DÓŁ/GÓRA/KORPUS/BLAT)
- [ ] Clicking ✕ clears the slot and removes the badge
- [ ] Active slot advances to next empty after assign
- [ ] "Zapisz jako szablon" saves to localStorage
- [ ] Page reload restores from localStorage
- [ ] Existing API endpoints still work (227 tests pass)
- [ ] Layout matches mockup-builder.html structure

## File Inventory

| File | Action | Purpose |
|---|---|---|
| `public/index.html` | Rewrite | Builder layout (grid + sidebar) |
| `docs/specs/builder-gui.md` | Create | This spec |
| `tests/test_configurator.py` | Verify | Existing tests still pass |

## Status
- [x] Spec reviewed
- [ ] Implementation
- [ ] Verify
- [ ] Docs
- [ ] Changelog
