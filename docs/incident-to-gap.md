# Incident-to-Gap Ritual

> Reader: any agent or human who just hit a bug, a surprise, or a falsified assumption | Enables: converting the surprise into a permanent guard (spec assertion, claim, issue, or recorded refusal) instead of a fixed-and-forgotten patch | Update-trigger: the five closing outcomes, the question-birth rule, or the bank's consultation points change

A lightweight practice, deliberately unmechanized (the mechanized design
lives in the truth-ledger growth-gate notes). Two contracts make it work:
the queue cannot be silently emptied, and the question bank only grows.

## When to run

On any surprise, immediately, before the fix is declared done:

- a bug, wherever caught;
- a falsified assumption — something written or believed turned out untrue;
- a verifier diverge that carries a lesson beyond the single claim;
- a red-team finding that survived triage.

## The classification question

Ask: **was the expectation ever written?** If yes — why didn't the written
form catch this (weak evidence, wrong scope, dead tripwire)? If no — a gap
exists, and it enters the queue below.

## The five closing outcomes

The queue cannot be silently emptied. An incident leaves it ONLY as:

1. **a new spec assertion** — an SC- marker in the owning spec plus the
   test that cites it (`docs/spec-convention.md` § Verification &
   Validation; the spec-coverage sentinels keep marker, manifest, and test
   citation in lockstep);
2. **a new ledger claim or sentinel** — filed per `.truth/README.md`
   (`scripts/truth claim ...`);
3. **a wk- issue** — when the closing move is work, not a fact
   (`scripts/truth issue ...`);
4. **a rejection-with-reason** — recorded INLINE in the question-bank
   entry, never merely spoken;
5. **an expiring deferral** — `deferred until YYYY-MM-DD by <owner>`,
   recorded inline in the bank entry. On expiry the incident re-enters
   the queue. (TTL'd ledger claims per `docs/adr/019-*.md` are the
   mechanized big brother; here a date in the bank plus the monthly audit
   sweep is enough.)

## The question-birth rule

Every incident ALSO births a question that joins
[docs/question-bank.md](question-bank.md) permanently. The bank grows
monotonically: a question may be retired by a written rejection note in
its entry, never deleted. The question generalizes the incident — it asks
about the *class* of gap, so the next spec, brief, or audit probes for it
before the next incident does.

## Worked example — QB-001

Incident (2026-07-27): `catalog-service.md` said seeding extras run "in
any order"; false — `seed_curated_kitchens` creates the style_tags that
`seed_decor_style_tags` links to, and the wrong order seeded 0
associations silently. Classification: the expectation (order
independence) WAS written, and was wrong. Closing outcome: doc correction
plus rebuild re-verification tr-0dda200b. Question born: QB-001 — for a
documented multi-step procedure, which step creates data a later step
consumes, and is the required order stated and tested?

## Where the bank is consulted

- **spec authoring** — walking a new spec out of the archetype blank, run
  the bank's questions against the feature;
- **red-team briefs** — the bank is the standing probe list;
- **the monthly audit** (the operator's routine, R11 in the truth-ledger
  roadmap) — which also sweeps expired deferrals back
  into the queue.
