# DRAFT upstream issue — `contradicts` edge → DISPUTED fold state

> Reader: Michał deciding whether to post this to the truth-ledger template
> repo | Enables: pasting the body below into `gh issue create` unchanged |
> Update-trigger: posted upstream (add the issue URL here), rejected, or
> superseded by a concept-doc revision

**Status: DRAFT — not posted. Posting is Michał's call.**
Target: `m1981/truth-ledger`.
Source: [two-ledger concept](../two-ledger-concept-2026-07-15.md) Part I
I.3 (b), §II.7 rule R5, §II.9 (wk-3894b44c).

---

## Proposed issue body

**Title:** contradicts edge: declared inconsistency folds both claims to DISPUTED

### Problem

29148's set-level *consistency* characteristic is unenforceable today:
near-dup intake catches restatement, but nothing catches contradiction —
two incompatible live claims coexist indefinitely, and every consumer
(specs, ready-gate premises, dashboards) happily leans on both. Observed
in the field: two back-panel formulas, two LEGRABOX width formulas — each
time the contradiction was discovered by a human diff, never by the
ledger.

### Proposal

A declared edge, mirroring how `premise` works (no NLP — the moment a
gate needs a model to fire, it is a review, not a refusal):

```
truth contradicts <tr-a> <tr-b> --basis "<why these cannot both hold>"
```

Fold change (small, still a pure function): while a `contradicts` edge
connects two claims whose statuses would otherwise be live, BOTH fold to
**DISPUTED**. DISPUTED behaves like `diverged` for every downstream gate:
ready-gate blocks premised work, spec-health fails specs citing either
side, both enter the review queue. The dispute resolves when one side is
retracted, superseded, or re-verified against corrected text — the edge
then points at a non-live record and stops firing.

Merge discipline: edges are append-only records like verdicts; union-merge
confluence holds because DISPUTED is derived from the edge set, not
stored.

### Non-goals

No automatic contradiction detection, no three-way disputes (chain edges
pairwise), no arbitration verb — humans resolve disputes by the existing
retract/supersede/verdict verbs.
