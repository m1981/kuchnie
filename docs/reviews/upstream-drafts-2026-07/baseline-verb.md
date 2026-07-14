# DRAFT upstream issue — `truth baseline <ref>`: set-level status accounting

> Reader: Michał deciding whether to post this to the truth-ledger template
> repo | Enables: pasting the body below into `gh issue create` unchanged |
> Update-trigger: posted upstream (add the issue URL here), rejected, or
> superseded by a concept-doc revision

**Status: DRAFT — not posted. Posting is Michał's call.**
Target: `m1981/truth-ledger`.
Source: [two-ledger concept](../two-ledger-concept-2026-07-15.md) §II.8,
Part I I.1 (wk-3894b44c).

---

## Proposed issue body

**Title:** baseline verb: fold the ledger at a git ref and diff two folds

### Problem

The ledger is strong configuration status accounting (ISO 10007) at the
level of *individual* records, but has no set-level verb: there is no way
to say "this is the frozen status account at v1.0" or to answer the
auditor's question "what changed between v1.0 and v1.1?" other than by
reading the raw append log. 10007's point is that omission is caught by
comparing against a baseline — and the failure mode the loophole map
already names for this ledger is "omission, never corruption".

### Proposal

`truth baseline <git-ref>`: check out (or `git show`) `.truth/claims.jsonl`
at `<ref>`, run the existing fold over it, and emit the frozen set —
claims by status/tier, issues by state — as deterministic JSON (sorted, no
timestamps beyond the ref's own).

`truth baseline <ref-a> --diff <ref-b>`: fold both, print the delta —
claims born/died/degraded, issues opened/closed — the release-notes shape:
"between v1.0 and v1.1: +3 facts live, 1 regressed to stale, 2 retracted."

Near-free by construction: the append-only file already holds every
historical fold; no new record kind, no fold change, read-only both modes.

### Non-goals

No tags/release management, no persistence of baseline artifacts by the
CLI (caller redirects to a file and commits if desired), no cross-repo
baselines.
