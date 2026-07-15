# DRAFT upstream issue — `truth impact --inverse`: files no active claim watches

> **POSTED 2026-07-16:** https://github.com/m1981/truth-ledger/issues/5

> Reader: Michał deciding whether to post this to the truth-ledger template
> repo | Enables: pasting the body below into `gh issue create` unchanged |
> Update-trigger: posted upstream (add the issue URL here), rejected, or
> superseded by a concept-doc revision

**Status: DRAFT — not posted. Posting is Michał's call.**
Target: `m1981/truth-ledger`.
Source: [two-ledger concept](../two-ledger-concept-2026-07-15.md) Part I
I.2, §II.10 (24765 backward trace) (wk-3894b44c).

---

## Proposed issue body

**Title:** impact --inverse: list tracked files watched by no active claim

### Problem

`truth impact <paths>` answers the forward question — "what knowledge does
editing these paths endanger?". The backward question (ISO/IEC/IEEE 24765
bidirectional traceability) has no verb: "which tracked files does the
ledger know nothing about?". The ledger only knows what was filed —
curation, not enumeration — so dark regions are invisible by
construction; a field audit found 8 of 9 sampled modules untraced and the
ledger had no way to say so itself.

### Proposal

`truth impact --inverse [--under <dir>]`: join `git ls-files` (optionally
scoped) against the union of `evidence_paths` globs of active
(non-retracted) claims; print the tracked files matched by none.

- Read-only, no fold change, no new record kind — the cheapest backward
  slice, sibling of the existing `impact` prediction.
- Exit codes mirror `impact`: 0 silent when everything is watched, a
  distinct code when dark files exist, so satellites can gate on it.
- Expect noise on first run (assets, lockfiles): `--under` and a plain
  path-prefix exclude flag are enough; anything smarter (per-repo policy
  files, verdict classes) belongs in downstream satellites, not the core.

Downstream repos can then build their own R2-grade audits (inventory ⋈
claims ⋈ specs ⋈ tests) on top; this verb is the kernel's contribution.

### Non-goals

No module/AST awareness (that is repo-specific), no verdict taxonomy, no
auto-filing of claims for dark files.
