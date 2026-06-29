# ADR — F0XX — <Decision Title>

> **WHEN TO WRITE AN ADR**
>
> Write one if the decision is:
> - **Architectural** (touches structure, not just behavior)
> - **Cross-context** (affects more than one bounded context's contract)
> - **Irreversible** (cheap to do, expensive to undo)
> - **Rejects an obvious alternative** (future agents will ask "why not X?")
>
> Do NOT write one for:
> - Pure refactors with no API change
> - Local naming choices
> - Bug fixes
>
> One page max. If it's longer, you're explaining the implementation instead of the decision.

---

**Date:** YYYY-MM-DD
**Status:** `Proposed` | `Accepted` | `Superseded by F0YY` | `Rejected`
**Feature:** F0XX
**Author:** _developer name or "solo dev"_

---

## Context

> 2-4 sentences. Why is this decision needed **now**? What forces it?

_Describe the situation that requires a decision. Reference relevant prior decisions, constraints, or external factors._

---

## Decision

> Imperative voice. One paragraph. The thing we will do.

_State the decision clearly. Use "We will..." not "We might..."._

---

## Alternatives Considered

> List every realistic alternative an agent might suggest. Reject each with a one-line reason. This is the most important section for future LLM sessions.

| Option | Why rejected |
|---|---|
| **A.** _alternative name_ | _one-line reason — usually about a quality attribute_ |
| **B.** _alternative name_ | _one-line reason_ |
| **C.** _do nothing_ | _what would break if we don't decide_ |

---

## Consequences

### Positive
- _What gets better_
- _What becomes possible_

### Negative
- _What gets worse or harder_
- _What we now have to maintain_

### Neutral
- _Trade-offs that are neither win nor loss_

---

## Affected Files (canonical)

Files that exist or will exist because of this decision:

- `src/kuchnie_core/...`
- `features/F0XX/...`
- `docs/GLOSSARY.md` (new terms: [list])
- `docs/schemas/...` (if schema changed)

---

## LLM Hints

> Direct instructions for future LLM sessions encountering this decision area.

- When asked "_question pattern_" → answer based on this ADR.
- When asked "why don't we _alternative X_" → point to "Alternatives Considered" table above.
- **Do not propose:** _list of common helpful-but-wrong suggestions to head off._
- **Related ADRs:** F0XX (depends on this), F0XX (this depends on).

---

## Sign-off

- [ ] Glossary updated with new terms.
- [ ] Tests in place covering the decision's behavior.
- [ ] Status changed from `Proposed` to `Accepted` after first successful use.

> **Status transition rule:**
> - `Proposed` → can be changed or rejected without breaking anything
> - `Accepted` → in use; only `Superseded by F0YY` can replace it
> - `Superseded` → keep the file; do not delete history
