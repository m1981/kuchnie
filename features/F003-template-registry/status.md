# Status — F003

> **Machine-readable.** Agents can grep all `status.md` files to build a dashboard.

```yaml
feature_id: F003
title: "Template Registry (Cabinet Macros)"
status: proposed                  # not started — Phase 3 begins after F002 closes
phase: 3
primary_context: core             # single bounded context — see spec Change Locality Test
touched_contexts:
  - core

started: null
completed: null
blocked_by:
  - F001                          # templates carry / inherit construction_method_id
  - F002                          # every template references an existing recipe_id; integration test depends on engine
supersedes: []
superseded_by: null

spec_status: ready                # all 10 Open Questions in spec.md answered
adr_status: proposed              # accepted on first green integration test run
adr_needed: true

glossary_terms_introduced:
  - CabinetTemplate               # promote placeholder → concrete
  - TemplateRegistry              # new
  - CabinetCategory               # new enum
  - DimensionConstraints          # new
  - DefaultSubAssembly            # new
  - MaterialRoleDefaults          # new
  - TemplateInstantiationError    # new exception

last_updated: 2026-06-28
last_updated_commit: "bootstrap"
```

---

## Current Activity

**Not started.** Blocked on F001 + F002 close (Phase 1 and Phase 2 gates).

When both blockers close (Phase 2 gate passed), promote this feature's status to `in_progress` and write `tasks.md` (spec and ADR already complete and reviewed).

---

## Blockers

- **F001 — Construction Method.** Templates resolve `construction_method_id` via override → project-default chain. The chain only exists once F001 lands.
- **F002 — Recipe Engine.** Every template's `recipe_id` must point to an existing recipe. The cross-feature integration test (`tests/integration/test_template_to_panels.py`) cannot pass without F002.

---

## Decision Log (in-flight)

> Promote to ADR if any decision affects more than this feature.

- _(empty until work starts)_
