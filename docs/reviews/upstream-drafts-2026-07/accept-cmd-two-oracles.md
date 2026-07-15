# DRAFT upstream issue — accept-cmd: two-oracle shape + its own allowlist

> **POSTED 2026-07-16:** https://github.com/m1981/truth-ledger/issues/2

> Reader: Michał deciding whether to post this to the truth-ledger template
> repo (extends truth-ledger#1) | Enables: pasting the body below into
> `gh issue create` unchanged | Update-trigger: posted upstream (add the
> issue URL here), rejected, or superseded by a concept-doc revision

**Status: DRAFT — not posted. Posting is Michał's call.**
Target: `m1981/truth-ledger`, extends issue #1 (`--accept-cmd`).
Source: [two-ledger concept](../two-ledger-concept-2026-07-15.md) §II.5,
Part I I.4 (wk-3894b44c).

---

## Proposed issue body

**Title:** accept-cmd: distinguish verification from validation oracles, and give acceptance commands their own allowlist

### Problem

Issue #1 proposes `--accept-cmd`: `truth done` refuses until the declared
finish-line command passes. Two design gaps surface when the command is a
*real* acceptance oracle rather than a lint:

1. **12207 keeps two V's that the single flag conflates.** A suite/gate
   command checks "built right" (verification); a golden-diff command —
   e.g. an exercise runner in `--strict` mode whose golden encodes
   stakeholder intent — checks "built the right thing" (validation).
   If the mechanism cannot express which oracle a work item declares,
   every conformance mapping back to 12207/29148 has to guess, and
   `done` semantics ("demonstrated" vs "validated") stay ambiguous.

2. **Acceptance commands execute repository code by nature.** The ADR-009
   evidence screen exists precisely to keep re-executable commands
   read-only, and test runners are deliberately NOT allowlisted there.
   If `--accept-cmd` is screened by that same allowlist, every real
   oracle (pytest, an exercise runner) needs an unsafe override — the
   gate teaches its own bypass, the confused-deputy lesson the paper
   already recorded.

### Proposal

- `--accept-cmd <cmd>` plus `--accept-kind {verification,validation}`
  (default `verification`), stored on the issue record at birth.
- Acceptance commands are screened against a **separate committed
  allowlist** — `.truth/accept-allow` — with its own header warning:
  entries here execute repository code at `done` time inside the closing
  session; that is their purpose. The ADR-009 evidence allowlist stays
  read-only and untouched.
- `truth done` runs the command from the repo root; non-zero exit refuses
  the close (work stays claimed). The `done --claim` completion fact can
  record the acceptance exit status alongside the evidence hash.
- Fold impact: none — acceptance is a gate at close, not a stored status
  (derive-never-store is preserved).

### Non-goals

No NL semantics, no oracle discovery, no retry policy. A missing or
failing oracle refuses loudly; fixing it is work, not configuration.
