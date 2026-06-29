# F00X — <slug>

> One-page spec. If it doesn't fit on one page, the feature is too big.

**Phase:** (P1/P2/P3/P4 from `docs/03_ROADMAP.md`)
**Estimate:** N days of focused work
**Status:** proposed | in-progress | done | blocked
**Started:** YYYY-MM-DD
**Completed:** YYYY-MM-DD

---

## Goal

One sentence, outcome-focused.

## Why now

What it unblocks; why it can't wait or be deferred.

## Done when

Concrete acceptance criteria as a checklist. **No "TBD" allowed before status = in-progress.**

- [ ] …
- [ ] …
- [ ] All affected subsystems' existing tests still pass (no regressions).
- [ ] `scripts/check_imports.py` passes.
- [ ] New tests in `tests/test_<slug>.py` cover the happy path and at least one failure mode.

## Affected files (concrete)

| Path | Change |
|---|---|
| `src/kuchnie_core/…` | … |
| `kitchen-cad/…` | … |

## Out of scope

What an LLM might helpfully add but shouldn't. Each line is a `❌`.

## Open questions

- [ ] …  (must be answered before status moves to in-progress)

## References

- Roadmap entry: `docs/03_ROADMAP.md#…`
- Pattern: `docs/05_PATTERN_GOLD.md#…` (if applicable)
- Decision: `docs/01_DECISIONS.md#…`
