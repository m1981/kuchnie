# Features

> **Source of truth for what comes next:** [`../docs/03_ROADMAP.md`](../docs/03_ROADMAP.md).
> Per-feature folders here are created **only when a feature is actively being implemented** — not preemptively. Speculative specs cause drift.

---

## Status

**Current phase:** P0 — Walking Skeleton (see [`../docs/02_WALKING_SKELETON.md`](../docs/02_WALKING_SKELETON.md)).
No feature folder exists yet; the skeleton is its own work item.

---

## When To Create A Feature Folder

1. Skeleton (P0) is green.
2. You start work on the next phase item per `03_ROADMAP.md`.
3. Copy `TEMPLATE/` to `F00X-<slug>/` (e.g., `F001-construction-method/`).
4. Fill `spec.md` (one page max) with: goal, acceptance criteria, affected files, day estimate.
5. Skip `adr.md` unless a non-obvious architectural choice is being made that isn't already in `01_DECISIONS.md`.

---

## Archived Speculative Specs (2026-06-29)

The previous F001–F008 spec/ADR folders were written before the audit in `06_AUDIT_EVIDENCE.md` revealed six already-working prototypes. They described greenfield builds for things that mostly already exist. Archived under `archive/` for historical reference; **do not** treat them as the active plan. The active plan is `03_ROADMAP.md`.
