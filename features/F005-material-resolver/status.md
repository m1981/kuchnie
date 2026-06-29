# Status — F005

> **Machine-readable.** Agents can grep all `status.md` files to build a dashboard.

```yaml
feature_id: F005
title: "Material Resolver (decor_id → ResolvedMaterial)"
status: proposed                  # not started — Phase 5 begins after F004 closes
phase: 5
primary_context: core_plus_catalog  # split intentional — Protocol in Core, impl in Catalog
touched_contexts:
  - core      # Protocol, resolver, ResolvedMaterial, registered checks
  - catalog   # YAML reader implementation, curated decors/edges

started: null
completed: null
blocked_by:
  - F001                          # variant picked by ConstructionMethod.*_thickness_mm
  - F003                          # templates ship material_role_defaults that resolver consumes
  - F004                          # KIT-100 and CAM-100 codes reserved; register_check API
supersedes:
  - "kitchen-plugin wood_materials.py + finish_colors.py (legacy — left in plugin per Rule 4)"
  - "kitchen-plugin frameless/wood_materials.py (same; plugin-internal)"
superseded_by: null

spec_status: ready                # all 12 Open Questions in spec.md answered
adr_status: proposed              # accepted on first green integration test run
adr_needed: true

fulfills_reserved_codes:          # codes F004 reserved that F005 fills
  - KIT-100                       # SlotDeclarationCheck + DecorResolutionCheck
  - CAM-100                       # MaterialRoleResolutionCheck

glossary_terms_introduced:
  - MaterialResolver              # promote placeholder → concrete
  - MaterialRef                   # promote placeholder + refine (now dict[role, slot])
  - ResolvedMaterial              # promote placeholder → concrete
  - CatalogReader                 # new Protocol
  - DecorRecord                   # new
  - EdgeRecord                    # new
  - VariantRecord                 # new
  - GrainDirection                # new enum
  - MaterialResolverError         # new exception
  - MaterialSlot                  # new term: project-level slot name
  - SlotDeclarationCheck          # new check class
  - DecorResolutionCheck          # new check class
  - MaterialRoleResolutionCheck   # new check class

last_updated: 2026-06-28
last_updated_commit: "bootstrap"
```

---

## Current Activity

**Not started.** Blocked on F001 + F003 + F004 close (Phases 1, 3, 4 gates).

> **Note:** F005 does NOT depend on F002 directly. F002's output (panels with material_role strings) is consumed by F005's `CAM-100` check, but F005 can be planned and partially implemented independently. The full integration test depends on the whole pipeline.

When all three direct blockers close (Phase 4 gate passed), promote this feature's status to `in_progress` and write `tasks.md`. Spec and ADR are complete and reviewed.

---

## Blockers

- **F001 — Construction Method.** Resolver picks the variant matching `ConstructionMethod.front_thickness_mm` (or `side_thickness_mm`, etc.). The method must exist and be queryable.
- **F003 — Template Registry.** Templates ship `material_role_defaults: {body: project_body, ...}` that the resolver consumes. The role-to-slot mapping must be in place.
- **F004 — Validation Gates.** Reserved codes `KIT-100` and `CAM-100` must exist in the registry. The `register_check` API must work. F005 fills the codes via the API.

---

## Indirect dependencies (not blockers, but relevant)

- **F002 — Recipe Engine.** Recipes emit `Panel.material_role` strings. F005's `CAM-100` check walks the chain for each panel in a `DecompositionResult`. F005 unit tests can stub the result; integration test waits for F002.

---

## Decision Log (in-flight)

> Promote to ADR if any decision affects more than this feature.

- _(empty until work starts)_
