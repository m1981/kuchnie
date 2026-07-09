# Feature Spec Convention — ledger-wired specs

> Reader: any agent or human starting a new feature, or judging whether an old spec can still be trusted | Enables: writing a spec whose load-bearing facts cannot rot silently — and finding out mechanically when they do | Update-trigger: the section contract, the id-citing rule, or `scripts/spec-health.sh` semantics change

## Why specs rot, and the one rule that stops it

The freeze docs decayed at ~2 false rows per 2 weeks (see
`docs/truth-trial/TRIAL-LOG.md`, "Prior decay evidence"). They rotted because
they *restated* repository facts in prose, and prose has no tripwire. The fix
is one rule:

> **A fact appears in a spec only as a truth-ledger id, never as prose.**

Prose saying "58 of 148 decors have images" diverges silently. Prose saying
"see tr-e2bf767e" cannot — the ledger tracks that claim's status, and
`scripts/spec-health.sh` flags every spec standing on a dead fact. A one-line
hook of text next to the id is a courtesy for the reader; **the id is
authoritative, the hook is not.**

## What goes where

A feature spec carries four kinds of truth. Three already have homes; the
spec file holds only the fourth:

| Kind of truth | Example | Home |
|---|---|---|
| Decision (why we chose this) | "Material becomes a mirror, not an owner" | ADR (`docs/adr/`) — link it, never summarize it |
| Current-state fact (what is true now) | "Material is still an independent store" | `tr-` claim — cite the id |
| Intent (what should become true) | "route the CATALOG dict to the service" | `wk-` issue — cite the id |
| Narrative (scope, non-goals, data flow, UX) | everything the ledger can't hold | **the spec file** |

Do NOT put spec prose into the ledger (its auditability is a function of its
size — ADR-002 refusal list), and do NOT mint a bag of `UNVERIFIED` claims at
spec time. File claims when you verify something; file issues when you commit
to an intention; the spec cites what exists.

## Where a spec lives

`<component>/docs/specs/<kebab-case>.md` in the component that changes most
(the established location — `catalog/docs/specs/`,
`krono-compositor-mvp/docs/specs/`, ... already exist). If no single
component dominates, use root `docs/specs/` (create it if absent). Naming
per `docs/file-naming-convention.md`.

## Section contract

```markdown
# Spec: <title>

> Reader: ... | Enables: ... | Update-trigger: ...   ← new-doc gate, mandatory

## Intent
Prose. Why this exists, scope, explicit non-goals. Should stay stable.

## Decisions
Links to ADRs only. One line of hook text each.

## Ground truths
tr- ids this spec stands on, one line of hook text each.
This section is the spec's premise set — spec-health judges it by the
ADR-001 matrix (live passes; unverified warns; stale/diverged/retracted/
missing means STOP and renegotiate the spec before coding).

## Work
wk- ids implementing this spec (+ Beads twin ids while the A/B runs).

## Acceptance
The claim texts that will exist when this is done — written NOW, scoped to
what an evidence command can actually show. These become the
`truth done <wk-id> --claim ...` texts at completion (claim-at-death,
pre-written). Lesson from verification rounds 3 & 4: never a repo-wide
clause backed by a package-scoped grep.
```

## Health tripwire

```bash
bash scripts/spec-health.sh          # sweep every */docs/specs/*.md + docs/specs/*.md
```

Per spec it reports each cited id's status and fails (exit 1) if any spec
stands on a `stale`, `diverged`, `retracted`, `missing`, or `cancelled` id —
or on a `cannot_verify` P0 claim (`cannot_verify` on lower tiers warns), per
the ADR-001 matrix. It also warns when a ground truth is not carried as a
premise on any cited issue (then `truth ready` can't protect it — fix with
`truth premise <wk-id> <tr-id>`), and on `unverified` premises. Zero-id
specs get a WARN (unwired prose — the pre-convention legacy state, to be
wired opportunistically when next touched).

**Every id cited anywhere in a spec is tripwired** — non-goals and
"see also" included. If a boundary reference shouldn't fail the spec when
it dies, refer to it by title, not by id. For prose-vs-claim-text drift the
mechanical gate can't see, route spec reviews through the semantic gate
(`scripts/llm-doc-gate.sh`, manual for now).

Run it:

- **before starting work from a spec** — a dead ground truth means the plan
  predates reality; renegotiate the spec, don't code against it;
- **at session close** alongside the other quality gates;
- it also runs fast enough for hooks if it ever earns that.

## Lifecycle

Born when a feature is first seriously discussed (see `AGENTS.md` →
"Feature specs" for the fresh-session flow). Closed work turns Acceptance
into real `tr-` claims via `done --claim`; the spec then stops being a plan
and becomes documentation whose every load-bearing fact is still under live
decay-tracking. Specs are never deleted — a superseded spec gets a one-line
pointer to its successor at the top, like ADRs.

**Ordering note:** commit the work FIRST, then `done --claim`. A completion
claim filed before the shipping commit trips its own path tripwire the
moment that commit lands (observed live on tr-fd1bbb24) — not wrong, just
noise costing one re-verification.
