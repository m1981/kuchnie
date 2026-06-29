# Status — F002

> **Machine-readable.** Agents can grep all `status.md` files to build a dashboard.

```yaml
feature_id: F002
title: "Recipe Engine (YAML-driven panel decomposition)"
status: proposed                # not started — Phase 2 begins after F001 closes
phase: 2
primary_context: core_plus_cad  # split intentional per 03_implementation_placement.md § Pattern 2
touched_contexts:
  - core   # owns Recipe data model + YAML files
  - cad    # owns RecipeEngine + asteval evaluator

started: null
completed: null
blocked_by:
  - F001   # ConstructionMethod must exist; recipes read construction.* fields
supersedes:
  - "kitchen-app/kitchen_erp/recipe_loader.py (legacy)"
superseded_by: null

spec_status: ready              # all Open Questions in spec.md answered
adr_status: proposed            # accepted on first green test run
adr_needed: true

glossary_terms_introduced:
  - Recipe                       # promote placeholder → concrete
  - RecipeEngine                 # promote placeholder → concrete
  - PanelRecipe
  - FormulaSpec
  - FormulaContext
  - RecipeRegistry
  - EdgeAssignment
  - DrillPatternRef

last_updated: 2026-06-28
last_updated_commit: "bootstrap"
```

---

## Current Activity

**Not started.** Blocked on F001 close.

When F001 closes (Phase 1 gate passed), promote this feature's status to `in_progress` and start `tasks.md` (to be written before work begins — but the spec and ADR are already complete and ready for review).

---

## Blockers

- **F001 — Construction Method.** F002's `FormulaContext` exposes `construction.*` fields; these only exist once F001 lands.

---

## Decision Log (in-flight)

> Promote to ADR if any decision affects more than this feature.

- _(empty until work starts)_
