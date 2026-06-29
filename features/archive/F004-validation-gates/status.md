# Status — F004

> **Machine-readable.** Agents can grep all `status.md` files to build a dashboard.

```yaml
feature_id: F004
title: "Validation Gates (Four-Stage Quality Checks)"
status: proposed                  # not started — Phase 4 begins after F003 closes
phase: 4
primary_context: core             # single bounded context
touched_contexts:
  - core

started: null
completed: null
blocked_by:
  - F001                          # Gate 1 checks construction_method_id resolution
  - F002                          # Gate 1 checks recipe_id resolution; Gate 4 consumes engine output
  - F003                          # Gate 1 reads template constraints and sub-assembly defaults
supersedes:
  - "kitchen-plugin/src/config_parser.py validators (legacy — left in place inside plugin)"
  - "kitchen-plugin/src/manifest_validator.py (legacy — left in place inside plugin)"
superseded_by: null

spec_status: ready                # all 13 Open Questions in spec.md answered
adr_status: proposed              # accepted on first green full-pipeline integration test run
adr_needed: true

glossary_terms_introduced:
  - ValidationGate                # promote placeholder → concrete
  - ValidationResult              # promote placeholder → concrete
  - ValidationIssue               # new
  - ValidationContext             # new (per-gate variants)
  - Severity                      # new enum
  - IssueCode                     # new
  - Check                         # new protocol
  - CabinetValidationGate         # new
  - RowValidationGate             # new
  - KitchenValidationGate         # new
  - CAMReadinessGate              # new
  # "CAM Readiness" entry already exists from F001 glossary seed; refine to point to gate.

reserved_codes_for_downstream_features:
  KIT-100: F005    # decor resolution via catalog
  CAM-100: F005    # material role resolves to concrete decor

last_updated: 2026-06-28
last_updated_commit: "bootstrap"
```

---

## Current Activity

**Not started.** Blocked on F001 + F002 + F003 close (Phase 1, 2, 3 gates).

When all three blockers close (Phase 3 gate passed), promote this feature's status to `in_progress` and write `tasks.md`. Spec and ADR are complete and reviewed.

---

## Blockers

- **F001 — Construction Method.** Gate 1 (`CAB-010`) checks `construction_method_id` resolves in the registry. Gate 3 (`KIT-002`) checks project default.
- **F002 — Recipe Engine.** Gate 1 (`CAB-011`) checks `recipe_id` resolves. Gate 4 consumes `DecompositionResult` from the engine.
- **F003 — Template Registry.** Gate 1 reads template `dimension_constraints` (CAB-001/002/003) and `default_sub_assemblies` (CAB-020/021).

---

## Decision Log (in-flight)

> Promote to ADR if any decision affects more than this feature.

- _(empty until work starts)_
