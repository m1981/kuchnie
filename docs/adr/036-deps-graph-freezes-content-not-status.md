# ADR-036: the deps graph freezes content, never ledger status

Status: Accepted (2026-08-13, operator) — prompted by hitting
`test_committed_graph_is_current` on three consecutive push attempts, the last
of which turned out to be caused by no code change at all. Implemented in
`scripts/deps-graph.py`; tests `test_committed_graph_holds_no_ephemeral_edges`
and `test_query_recomputes_the_ephemeral_edges_live`, both red-proven against
seeded regressions.
Date: 2026-08-13
Supersedes: — (narrows what `--build` writes; the extractor, the query surface
and the blocking test all stand)

## Context

`docs/deps-graph.jsonl` is a committed artifact, and
`test_committed_graph_is_current` blocks the push when it drifts. The
rationale is sound and stated in the test itself: *a stale graph is worse than
none — every query below it answers with yesterday's repo while looking
exactly as authoritative.*

That rationale is true of content and false of ledger status, and the artifact
did not distinguish them.

**What the third failed push looked like.** The committed graph and a fresh
build differed by exactly one line:

```
{"src": "tr-a71e0a32", "dst": "truthlib/*.py", "kind": "watches",
 "via": "unverified", ...}
```

No code had changed. The claim watched `truthlib/*.py`, a template bump
touched `cli.py`, the post-commit scan staled the claim, and `x_watches`
correctly stopped emitting the edge — it declares that a stale or retracted
claim contributes nothing, because *the graph shows live coupling, not
historical coupling*. The artifact went stale because a **status** moved.

**Measured over 36 days on this repo:**

| | |
|---|---|
| commits | 501 → 13.9 / day |
| status transitions of path-carrying claims | 1659 → **46.1 / day** |
| ratio | **3.3 : 1** |
| worst single days | 292, 256, 230 transitions |

**And the composition, which is the sharper number:**

| kind | edges | share |
|---|---|---|
| cites | 3801 | 66% |
| references | 1054 | 18% |
| reads | 339 | 6% |
| invokes | 163 | 3% |
| premise | 152 | 3% (ledger-derived, but append-only — stable) |
| imports | 95 | 2% |
| **watches** | **73** | **1.3% — keys on status, turns over with scans** |

One point three percent of the artifact caused most of its rebuilds. Freezing
two populations with different volatility in one file makes the whole file
inherit the churn of the faster one.

**The decisive finding.** Nothing queried those edges from the file. The
readers of `docs/deps-graph.jsonl` are the generator, the test that gates the
push, and a blind-spot probe. `truth impact` — the one verb that asks exactly
"what does a change to these paths endanger?" — does not read the graph at
all; it folds the ledger directly, in ~43 ms, comfortably under the FS-3 gate.

So the committed copy held data with no reader, lied about it for most of any
given day, and blocked pushes for the privilege. That is the shape ADR-046
evicts from a ledger record, appearing in an artifact instead.

## Decision

**`--build` writes content-derived edges only. Query recomputes the rest.**

1. **A declared ephemeral set.** `EPHEMERAL_EXTRACTORS` names the extractors
   whose edge set keys on ledger status rather than repository content.
   Currently `(x_watches,)`. `x_premise` is deliberately NOT in it: premise
   records are append-only, so those 152 edges move with commits, not scans.
2. **`build(root, skip_ephemeral=True)`** skips them; `--build` passes it.
3. **The query path recomputes them live** from the fold, on every invocation,
   before filtering and walking. `--no-live` answers from the artifact alone,
   for reproducing a query offline.
4. **Failure stays loud.** `x_watches` already raises when it examined
   nothing (the F1 rule). The query path catches that, says so on stderr, and
   answers from the file — rather than silently returning a graph missing an
   entire kind.

**The test keeps its teeth and gains a falsifier.** The strict byte comparison
now runs against `skip_ephemeral=True`, and a second arm asserts that no
ephemeral kind ever appears in the committed file. If a future extractor keys
on status and is written to the artifact, the push gate starts failing on
scans again — and that arm names which extractor did it.

## Consequences

Graph rebuilds fall from the scan rate to the commit rate. On the measured
window that is 46.1 forced rebuilds per day going to zero: no rebuild is now
caused by anything other than a change to the repository's content, which is
what the artifact was always supposed to freeze.

No information is lost. A reader asking for a `watches` edge gets it, computed
from the live fold, which is strictly fresher than the frozen copy ever was.
The file shrank by 73 lines and stopped making a claim it could not keep.

Cost: one fold per query invocation (~43 ms). The artifact is no longer a
complete answer offline unless `--no-live` is intended, which is stated in the
flag's help.

## Non-goals

Not removing the extractor, not weakening the blocking test, and not
auto-rebuilding in a hook — this repo's gates refuse and explain rather than
silently repairing, and that consistency is worth more than the saved command.

Not a general rule that ledger-derived data may never be frozen: `x_premise`
stays in the artifact precisely because append-only records do not turn over.
The test is volatility, not provenance.

**Falsifier:** a consumer that needs `watches` edges offline, without access
to the ledger. None exists today; `--no-live` would answer it wrongly and
should be the first thing examined if one appears.
