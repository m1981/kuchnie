# Spec: Kitchen Configurator API (Phase 1 — MVP)

## Problem

Users browsing the catalog see 186 flat cards with no guidance on what goes
together. There is no way to say "I want an oak kitchen" and be walked through
matching carcass, worktop, edge, and plinth. The `pairings` table exists but
isn't exposed through any user-facing flow.

## Proposed Solution

A REST API that models a 6-step configurator as a state machine. One session
token tracks the user's choices. Each endpoint returns filtered, pre-ranked
options for the current step.

```
POST /configurator/sessions                → create session
GET  /configurator/sessions/{t}/options    → options for current step
PATCH /configurator/sessions/{t}/select    → make choice, advance step
GET  /configurator/sessions/{t}/bom        → summary of all choices
GET  /configurator/templates               → curated starting points
POST /configurator/sessions/{t}/from_template → init from template
```

### Step logic

| Step | Source | Filter | Default |
|------|--------|--------|---------|
| front | `variants` WHERE roles LIKE '%front%' | None | Popular first |
| carcass | `pairings` WHERE pairing_type='carcass' | By chosen front decor | priority=1 |
| worktop | `variants` WHERE roles LIKE '%worktop%' | By color_family of front | Popular first |
| edge | `variant_edges` + `edges` | By chosen front variant | Auto-match |
| side_panel | `variants` WHERE roles LIKE '%side_panel%' | Same decor or carcass decor | Carcass match |
| plinth | `variants` WHERE roles LIKE '%plinth%' | Same decor or carcass decor | Carcass match |

### Step transitions

```
front → carcass → worktop → edge → side_panel → plinth → done
```

Steps 4–6 are skippable (mark as skipped, advance to next).

## Schema Changes

- Format: API (new endpoints)
- Schema: new table `configurator_sessions`
- Migration: additive (IF NOT EXISTS)
- Version bump: minor (1.3 → 1.4)

## Test Cases

```
test_create_session_returns_token_and_step_front
test_create_session_returns_session_with_current_step_front
test_options_front_returns_variants_with_front_role
test_options_front_filters_by_producer_when_specified
test_options_front_filters_by_color_family_when_specified
test_select_front_advances_to_carcass_step
test_select_front_without_session_returns_404
test_options_carcass_returns_pairings_for_chosen_front
test_options_carcass_returns_default_when_no_pairings_exist
test_select_carcass_advances_to_worktop_step
test_options_worktop_returns_worktop_variants
test_select_worktop_advances_to_edge_step
test_options_edge_returns_edges_for_chosen_front_variant
test_select_edge_advances_to_side_panel_step
test_options_side_panel_returns_side_panel_variants
test_select_side_panel_advances_to_plinth_step
test_options_plinth_returns_plinth_variants
test_select_plinth_advances_to_done_step
test_bom_returns_all_selections
test_bom_incomplete_session_returns_partial
test_templates_returns_list_of_curated_kitchens
test_from_template_initializes_session_with_all_choices
test_select_returns_400_for_invalid_step_transition
test_select_returns_400_for_nonexistent_variant
```

## Success Criteria

- [ ] All 23 tests pass
- [ ] Existing 30 tests still pass (no regressions)
- [ ] [SC-cfgapi-001] POST /configurator/sessions returns 201 with a session token and current_step=front
- [ ] [SC-cfgapi-002] Session persisted in SQLite (survives restart)
- [ ] Front step returns ≥10 variants for Kronospan
- [ ] [SC-cfgapi-003] Selecting a nonexistent variant returns 400
- [ ] [SC-cfgapi-004] Selecting for a step other than the current step returns 400
- [ ] [SC-cfgapi-005] Carcass step returns pairing results (or fallback)
- [ ] [SC-cfgapi-006] BOM endpoint returns all made selections
- [ ] Endpoint response time < 100ms (single session, local SQLite)

## File Inventory

| File | Action | Purpose |
|------|--------|---------|
| `db/schema.sql` | Modify | Add `configurator_sessions` table |
| `models/domain.py` | Modify | Add `ConfiguratorSession`, `ConfiguratorOption`, `ConfiguratorBOM` models |
| `repositories/configurator.py` | Create | Session CRUD + step logic |
| `api/routers/configurator.py` | Create | 6 endpoints |
| `api/main.py` | Modify | Include configurator router |
| `tests/test_configurator.py` | Create | 23 test cases |
| `data/kronospan_pairings.yaml` | Modify | Ensure pairings data exists for tests |

## Status
- [x] Spec reviewed
- [x] Tests written (20 cases)
- [x] Implementation complete
- [x] Docs updated (ADR-002, CHANGELOG, ROADMAP)
- [x] Marked ✅ in ROADMAP.md

## Verification & Validation

Verification: endpoint contract tests — the catalog configurator pytest
suite is the acceptance oracle, carried by `wk-e7a2992d` (ADR-014
`--accept-cmd`, kind verification; ran green at that item's close).

Validation: operator walkthrough of the BOM endpoint output against a
real production sheet — attestation pending; when the operator files it
(UNVERIFIED, `--ttl-days 90`), edit this line to cite the id. Until
then this spec is verified at the endpoint-contract level, not yet
validated.

Residual (accepted, not closable): "the pairings data drifting from the
showroom's actual pairing advice under a passing suite"
