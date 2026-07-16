# Retro: first supervised multi-agent group (Group 1, 2026-07-15/16)

> Reader: Michał or a supervising agent planning the next agent group |
> Enables: choosing task shapes and supervision posture from measured
> experience instead of optimism | Update-trigger: a Group-2+ run confirms
> or refutes a doctrine candidate below (promote it to a convention or
> delete it)

Run reviewed: four Sonnet agents under one Fable supervisor — ERP spine
(wk-02a62298, worktree), extraction r2 (wk-81a47ab8, worktree), ledger
hygiene (wk-ea10d199, main tree), LEGRABOX audit (read-only) — plus one
dispatched verifier session. All landed; session-close green. Companion
evidence for the ledger paper lives in the meta-repo
(`PycharmProjects/truth-ledger/docs/field-notes-kuchnie-multiagent.md`).

## Findings

1. **Mechanical recovery beat memory every time it was tested.** The
   supervisor's context was wrong about the repo four times (rewind,
   compaction, a parallel session's correction, a stale worktree base);
   each time an artifact — `truth ready`, a gate, a diff — corrected it.
   The "chat is a scratchpad" principle is load-bearing, not decorative.
2. **Gates caught the supervisor more often than the agents.** This run:
   governance hook ×2 (dead component name; generated-doc rule),
   INV-M ×1 (untracked schema path), spec-health ×1 (a supersession
   footnote citing a dead id), freshness gate ×1 (corrupted STATUS
   header). The value is commit-time interception of a competent actor's
   small errors, in a domain where small errors are scrap.
3. **Task-shape economics.** Best value/risk: the read-only investigation
   (LEGRABOX audit — decision-grade output, zero merge surface). Good:
   the tightly-fenced main-tree process task. Expensive: implementation
   in worktrees (four infrastructure stalls, one stale base, the venv
   trap, merge-time ledger reconciliation). Parallelism bought ~30%
   wall-clock over careful serial, at real supervision cost.
4. **Half the supervision effort was ledger bookkeeping** (restales,
   successors, verdicts), not code review. Rule 8 (development-process §5)
   and source-only successor claims cut the noise mid-session; the
   residual churn is the regime's standing tax and should be stated
   plainly to anyone adopting it.
5. **The intent axis showed itself.** UC-2 step 2 flipping to supported
   required hand-editing two specs and rewiring citations — the manual
   choreography the two-ledger `nd-`/`satisfies` design would automate;
   and the R7 gauge demonstrated satisfaction that decays and recovers
   within one day of existing.
6. **The bottleneck moved to the owner.** With agent throughput solved,
   the growing queue is human-only decisions (retractions, triage verbs,
   UC dressing). Correct place for the limit; plan owner decision
   sessions as first-class work.

## Doctrine candidates — PROMOTED 2026-07-16

Group 2 (buildability orchestrator + purchasing variant model, two
worktree implementations run in parallel on disjoint components)
confirmed every candidate: both auto-created worktrees arrived 22
commits stale and the merge-base check stopped both agents before they
built on a pre-spine baseline; one agent stalled mid-run and resumed
losslessly from its milestone commit; merge-time invalidate-scans staled
12 claims that were re-judged on main; and the end-of-session verifier
independently re-ran every pinned test and caught the filer's own
miscounted verdict basis. One refinement earned by the run: parallel
implementations are safe when their components are disjoint — the
serial rule applies per component, not globally. The promoted doctrine
now lives in [development-process.md §2a](../development-process.md);
the list below stays as the original candidates for lineage.

- Fan out **investigations and small fenced tasks**; run **large
  implementations serially** with review.
- **Check a worktree's merge-base against main at spawn**; distrust any
  baseline statement from an agent whose base is stale.
- Instruct long-running agents to **commit after every milestone**
  (stall-resilience); a lost handoff message is recoverable from
  artifacts, lost uncommitted work is not.
- **End every multi-agent session with a verifier dispatch** — the
  filer≠verifier gate makes it structurally necessary, not optional
  (a claim filed and path-staled in the same session cannot be repaired
  by its own filer).
- Supervisor watches **proportion** (product vs process hours), because
  no gate does.

## Pointers

Shipped work and verdicts: see `git log --grep` for wk-02a62298,
wk-81a47ab8, wk-ea10d199; audit at
[legrabox-side-panel-audit-2026-07-15.md](legrabox-side-panel-audit-2026-07-15.md);
operational gotchas persisted via `bd memories worktree`.
