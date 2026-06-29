# Status — F0XX

> **Machine-readable.** Agents can grep all `status.md` files to build a dashboard.
> **Keep it accurate.** Updating this is part of every commit that touches the feature.

```yaml
feature_id: F0XX
title: "<Feature Title>"
status: proposed       # proposed | in_progress | done | blocked | superseded | cancelled
phase: <N>             # which phase (from docs/PHASES.md)
primary_context: <catalog|core|cad|web|render>
touched_contexts: []   # list, must justify each in spec.md

started: null          # YYYY-MM-DD when status moved to in_progress
completed: null        # YYYY-MM-DD when status moved to done
blocked_by: []         # list of feature IDs blocking this one
supersedes: []         # feature IDs this replaces
superseded_by: null    # feature ID that replaces this

spec_status: draft     # draft | ready (Open Questions all answered)
adr_status: none       # none | proposed | accepted | superseded
adr_needed: true       # true | false (false ⇒ document why in tasks.md)

glossary_terms_introduced: []   # list of new GLOSSARY.md entries

# Last status change — keep updated on each commit
last_updated: YYYY-MM-DD
last_updated_commit: "<short hash>"
```

---

## Status Transitions

```
                 (spec written)
proposed ─────────────────────────────► in_progress
   │                                         │
   │ (cancelled before start)                │ (all tasks done, gate criteria met)
   ▼                                         ▼
cancelled                                  done
                                             │
                                             │ (replaced by a new feature)
                                             ▼
                                          superseded
```

**Blocked** is orthogonal — set it when blocked, clear it when unblocked. Document the blocker.

---

## Allowed Status Values — Quick Reference

| Status | When | Who can change it |
|---|---|---|
| `proposed` | Spec drafted, no code yet | Developer or first LLM session |
| `in_progress` | Code has started | Anyone with first commit |
| `blocked` | Cannot proceed; see `blocked_by` | Anyone hitting a block |
| `done` | All Acceptance Criteria from `spec.md` met | Only after `tasks.md` Close-out complete |
| `superseded` | Replaced by a newer feature | When `superseded_by` is set |
| `cancelled` | Will not be done; explain in Notes | Developer only |

---

## Anti-Patterns to Avoid

- ❌ Setting `done` before `tasks.md` Close-out is complete.
- ❌ Leaving `last_updated` stale (any commit touching the feature folder should update it).
- ❌ Skipping `blocked_by` when blocked — agents will try to proceed.
- ❌ Status `in_progress` with `started: null` — auto-fix on next commit.
