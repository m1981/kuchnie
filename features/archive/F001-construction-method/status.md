# Status — F001

> **Machine-readable.** Agents can grep all `status.md` files to build a dashboard.

```yaml
feature_id: F001
title: "Construction Method as first-class entity"
status: in_progress
phase: 1
primary_context: core
touched_contexts:
  - core
# CAD will become a consumer in Phase 2 (F002), not in F001.

started: 2026-06-28
completed: null
blocked_by: []
supersedes: []
superseded_by: null

spec_status: ready          # all Open Questions answered
adr_status: accepted        # accepted on first use
adr_needed: true

glossary_terms_introduced:
  - ConstructionMethod
  - JoineryType
  - BackType
  - ConstructionMethodRegistry

last_updated: 2026-06-28
last_updated_commit: "bootstrap"
```

---

## Current Activity

**Phase 1 — Domain Foundations.** This is the foundation feature. No prior features to depend on. Work proceeds in the order listed in `tasks.md`.

---

## Blockers

None.

---

## Decision Log (in-flight)

> Promote to ADR if any decision affects more than this feature.

- _(empty — fill while working)_
