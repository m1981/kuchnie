# DRAFT upstream design RFC — the `nd-` record kind + `satisfies` edge

> Reader: Michał deciding whether to post this to the truth-ledger template
> repo | Enables: pasting the body below into `gh issue create` unchanged
> (label it RFC) | Update-trigger: posted upstream (add the issue URL
> here), rejected, or superseded by a concept-doc revision

**Status: DRAFT — not posted. Posting is Michał's call. This one is a
design RFC, not a feature request — it adds a record kind and is the
concept's Phase 3 (one ADR upstream).**
Target: `m1981/truth-ledger`.
Source: [two-ledger concept](../two-ledger-concept-2026-07-15.md)
§II.2–II.4, §II.6, §II.9, §II.11 (wk-3894b44c).

---

## Proposed issue body

**Title:** RFC: need records (nd-) + satisfies edge — derived, decaying satisfaction

### The one-paragraph idea

Add a second, parallel axis — the **intent ledger** — with the same DNA as
the truth ledger (append-only, fold-derived, gate-refused, id-cited), and
make every conformance statement a computed join between the two axes
rather than a stored status. Facts die when the *world* changes (a commit,
a TTL); needs die only when a *human decides* (supersede/withdraw).
Conflating those lifecycles is why commercial ALM tools rot — a
requirement marked "done" never notices the code regressing.

### The record kind

`nd-` records live in the same JSONL, same `(ts, id)` fold:

| Field | Gate at intake | Standard (29148) |
|---|---|---|
| `text` | non-empty, near-dup refused, quantifier gate reused verbatim | unambiguous |
| `altitude` | cloud/kite/sea; sea-level needs must cite a kite parent | traceable |
| `actor` | required | necessary |
| `accept_oracle` | a command or golden-diff ref | **verifiable** |
| `tier` | P0/P1/P2 — cost of NOT having it | prioritization |

Lifecycle, fold-derived: `proposed` (oracle optional — elicitation may be
vague) → `accepted` (the CLI **refuses** promotion without oracle +
altitude + actor — 12207's requirements analysis made syntax) → derived
states below → `superseded`/`withdrawn` (terminal, human-gated — the
tombstone gate reused verbatim).

### The keystone rule — satisfaction is derived and decays

One new edge kind: `satisfies` (claim → need), the mirror of `premise`
(work → claim). Then:

```
nd- is SATISFIED  iff  a live claim carries a `satisfies nd-…` edge
nd- is UNPROVEN   iff  that claim exists but is stale/diverged
nd- is OPEN       iff  no such claim exists
```

Because acceptance claims carry `evidence_paths` like any claim, a commit
that breaks a satisfied need automatically degrades it to UNPROVEN —
functional completeness becomes a live metric that can go **down**:
regression detection at the requirements level, riding entirely on the
existing staleness machinery. This is the sentence to defend hardest; the
rest is diligent standards engineering.

### What stays out (inherited refusals)

- No workflow states beyond the fold's minimum; trackers remain a
  read-only-joined view.
- No NL semantics in gates — consistency is declared edges, not NLP.
- No identity infrastructure — single-observer stays the disclosed limit.
- Elicitation stays human — the system proves a need-set is *internally*
  covered; it cannot know a need was never spoken.

### Migration evidence from the kuchnie pilot

Phase 1 (no core changes) is implemented downstream: a test-citation
gate (R4), an acceptance-completeness dashboard view (proto-R1/R7) whose
gauge is exactly the SATISFIED/accepted ratio computed lexically, and a
TRACED/MENTIONED/DARK backward-trace audit (R2-lite). The UC Acceptance
sections were written as pre-formed acceptance claims precisely so they
convert to nd- records nearly mechanically.
