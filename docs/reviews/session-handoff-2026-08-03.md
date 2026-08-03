# Session handoff — kuchnie, 2026-08-03

> Reader: a fresh session picking this up, or Michał re-orienting | Enables:
> resuming without re-reading 700k tokens of transcript | Update-trigger: the
> owner answers a blocked question, `kuchnie-m0m` is measured, or wave 3 ships

**Paste-ready.** Self-contained; assumes only that you have the repo.
Start as always: `STATUS.md`, then `scripts/truth ready`.

---

## 1. Where the project is

**Owner decision 2026-08-02: fidelity first.** Deepen the domain before wiring
the app to it. The purchasing wiring (`kuchnie-ubc.1`) is deliberately parked;
the reachability gate stays high priority *because* it is parked — a deferred
decision must be a declared one.

**Shipped and verified** (waves 1–2): core import cycles broken
(`kuchnie-5un`), ERP DB path made absolute + migrations out of the Reflex state
class (`kuchnie-26s`), catalog schema-version handshake + one shared client
(`kuchnie-019`), reachability gate + `docs/not-yet-wired.txt` (`kuchnie-lh2`),
`DrawerBoxSpec` and one drawer-stacking loop (`kuchnie-27b`/`b30`),
`Material.structure` + `thickness_mm` (`kuchnie-h45` step 1), first tests for
`admin_state.py` (`kuchnie-33x`).

Suites: core 819, ERP 291, cam 57, catalog 267, scripts 32. `exercise-gate`
byte-identical. `spec-health`/`doc-health` 0 failures.

**Lead item: `kuchnie-lm8`** — decomposer routing + plinth bucket + drawer
vocabulary + NL rule, shipped as ONE change. It will force a deliberate golden
roll (the d60 flagship does cover a drawer base — confirmed).

**Blocked on the owner** (`docs/reviews/owner-todo-2026-08-02.md`): service and
hardware rates (Q2 — the only item silently affecting money today), the
depth→NL table beyond 560→NL 500, and two claimed work items
(`wk-593a317b`, `wk-59b943b1`) that keep `session-close.sh` from passing.

---

## 2. Operational lessons — these cost real time

1. **Verify by re-query, never by return message.** A batch `bd close` silently
   skipped one bead; `tail -1` hid it; the P1 lead item sat blocked by finished
   work. After any state change, ask the tool for the new state.
2. **Positive control on every grep.** An unquoted `--include=*.py` was eaten by
   zsh and returned a clean `0` that looked like a finding. Always run the
   pattern against a case you know matches.
3. **Never `git checkout <file>` to undo a scratch perturbation** — it reverted
   the fix I was testing. Use a copy.
4. **Venv map.** Repo-root `.venv` covers kuchnie-core, kitchen-cam, catalog and
   home-builder-adapter. `kitchen-erp` and `krono-compositor-mvp` have their
   own. **Worktrees have none** — run the main interpreter with `PYTHONPATH`
   and confirm `__file__` resolves *inside* the worktree before trusting green.
5. **Agent worktrees arrive stale.** Every agent in wave 1 did. Make step 0 a
   merge-base check.
6. **Agents must not commit `.truth/`.** The post-commit hook dirties it;
   healing is the coordinator's job. One agent committed the hook output and
   caused a merge conflict.
7. **`docs/code-inventory.json` regenerates with `--stdout`** — that is the
   form its freshness test compares against.
8. **`dashboard.py` writes `STATUS.md` itself.** Never redirect its stdout.
9. **Gates can sweep `.claude/worktrees/`.** `spec-health` did, reported 125
   failures where the truth was 25, and blocked its own fix through the
   pre-commit hook. Fixed; check the others if you add worktrees.
10. **Ledger healing dominates integration cost.** One merge staled 35 claims
    and healing outlasted the code integration. `scripts/truth reaffirm`
    hash-matches the majority; the rest need judgment.
11. **WebSearch budget is 200/session** and research agents exhaust it fast.

---

## 3. Verification lessons — the expensive ones

**Filer ≠ verifier is the only control that caught anything.** Two independent
adversarial verifiers found four defects in work I had integrated *and*
signed off. Every failure of mine had one shape: **I accepted a proxy for the
property** — a passing gate for "the property holds", a close message for
"closed", an agent summary for "the code does this".

But the literature qualifies this sharply (`docs/reviews/sources/`):

- Independence and effectiveness **trade off**. The low defect yield of code
  review is explained by *understanding*, not diligence, and independence is
  the deliberate removal of context. Fagan paid for it with an overview step, a
  reader step and error-type checklists. **Spend on briefing the verifier, not
  on more verifiers.**
- Two verifiers from the same model and prompt shape **violate Clark & Wilson's
  non-collusion assumption**. Diversify model, lens or seeded bias — not just
  scope.
- Our 4-of-4 is an **existence proof, not a rate**. Published rates are far
  lower (Bacchelli & Bird: defects were 14 % of 570 review comments).
- **Agent summaries hide load-bearing qualifiers.** "The defect is FIXED" meant
  LEGRABOX only; two of three drawer systems still emitted a scrap drilling
  pattern. Read the artifact, not the report.

---

## 4. Doctrine — what to build, what to refuse

Full text: `docs/reviews/agentic-verification-doctrine-2026-08-03.md` (with
corrections in §§3a–3c), `verification-system-scratch-design-2026-08-03.md`,
and ~6,000 lines of sourced research in `docs/reviews/sources/`.

**Three claims of mine that the research falsified — do not repeat them:**

1. **The truth ledger is NOT a TMS.** `truth premise` takes `<issue>
   <claim_id>`; the dependent is always a work item. All 42 premise records
   point at beads. The graph is bipartite, depth 1 — nothing to propagate.
   Belief death is 656 path-triggered invalidations vs 42 premise edges: that
   is `make`, not Doyle. **Drop the novelty claim** (reflexion models,
   iComment, traceability, Daikon).
2. **The FIT "died of maintenance cost" story is folklore.** Fit's own project
   coordinator puts the failed collaboration premise first; controlled
   experiments found Fit tables *helped* maintenance. What transfers is the
   tooling failure — executable specs refactoring cannot reach, i.e. our 25
   `grep -n` claims.
3. **Invariant-vs-testimony is half a rediscovery.** Testimony is Zave &
   Jackson's K; our invariants are *not* their S. The genuine advance is small
   and specific: **they never solved keeping K true; a TTL on testimony does.**

**Order of work, and the gate on all of it:**

- **`kuchnie-m0m` — MEASURED 2026-08-03, and it refuted the migration
  premise.** Of 75 retractions, 49 (65 %) record no cause at all. Of the 26
  that do: `wrong` 38 %, `moved` 26 %, `fixed` 23 %, `version` 11 %. **`fixed`
  is not dominant — `wrong` is**, so the ledger is catching bad claims rather
  than expiring repaired ones. Caveat: the 26 are self-selected toward
  interesting failures, so this weakens the migration argument rather than
  killing it. Consequences: **`kuchnie-glu` demoted**, **`kuchnie-amu`
  promoted** (it attacks the dominant readable failure), `kuchnie-bs2`
  supported.
  Forward half is **built upstream** as ADR-049 on branch `retraction-cause`
  in `gh:m1981/truth-ledger` — verified but **not merged, not released**, so
  kuchnie does not have it yet. Its taxonomy is `restated` / `expired` /
  `wrong`, three not four: `moved` was rejected because a still-true fact whose
  recipe moved is a *restatement*, not a tombstone. `restated` must name a
  validated `--successor`.
- `kuchnie-bs2` — content-hash verifying traces (Build Systems à la Carte).
  Kills false staleness at the root; largely subsumes auto-reaffirm.
- `kuchnie-oij` — stale baseline entries must FAIL (import-linter pattern), and
  entries must carry the **original standard + expiry**. Recording only the
  reason is Vaughan's normalisation step 4, not a guard against it.
- `kuchnie-z00` — every gate declares its unsoundness, pinned by a test that
  fails when the blind spot is closed.
- `kuchnie-y5c` — metamorphic relations (mirror a cabinet → drilling mirrors;
  double drawers → screws double). Survives golden rolls; would have caught the
  wave-2 defect goldens missed.
- `kuchnie-amu` — mutation testing, repriced **S → M/L**: 85 % of raw mutants
  are unproductive and a suppression list is mandatory from day one, or the
  gate gets switched off.

**Refuse:** coverage targets; LLM-as-judge as the *control* (fine as a first
pass); comprehensive executable specs; metrics as targets; whole-codebase
formal methods; full ATMS; DO-178-scale traceability; **a gate that warns
forever**. **CodeQL is out** — licence forbids the engine on a private
commercial repo, and it does not finish at our scale. Use a local AST helper.

**Still unanswered:** the adequacy obligation `S, K ⊢ R` — nothing here answers
"why is this the right set of statements?" That is the F9 gap and no design in
the lineage closes it.

---

## 5. Retro — what the reading actually changed, and what it did not

Written after the source studies landed. Keep it: this is the part that
disappears first under compaction, and it is the part that would stop the next
session repeating the pattern.

### Sources that changed an engineering decision

Each of these altered a choice I had already made, rather than decorating it.

| Source | What it changed |
|---|---|
| Google mutation data — 85 % unproductive, six years of suppression | `kuchnie-amu` repriced S → M/L; suppression list mandatory from day one. Without it I would have shipped a noise generator |
| Schuler & Zeller — assertion-free suites still kill mutants | `mutation:` spec changed from "turns RED" to "turns RED **for the stated reason**" |
| Bacchelli & Bird + Sadowski — 14 % of comments, 2 of 44 | Reframed our 4-of-4 as an existence proof, not a rate; produced "brief the verifier, not more verifiers", which visibly changed later agent prompts |
| Vaughan — normalisation step 4 | Inverted refusal §4.11 by 180°: recording the reason is the normalising mechanism, not a guard against it |
| Build Systems à la Carte + Estler | Filed `kuchnie-bs2`; demoted `kuchnie-94t` from fix to stopgap |
| Chen et al. — metamorphic testing | Filed `kuchnie-y5c`; a capability I would not have proposed |
| Claessen & Hughes — three-way error split | Forced the `kuchnie-m0m` measurement, which then refuted my own mortality diagnosis |

### Cited constantly, implemented not at all

**Fagan is the embarrassment.** He is quoted in every document here, and
nothing of his method was adopted: no overview step, no reader/paraphrase
step, no error-type checklists, no bounded checking rate, no re-inspection
threshold. Only "author ≠ inspector", which we already had. The process
lineage said this explicitly as correction C3; the correction was *recorded*
and then not acted on — longer prompts were treated as equivalent to context
transfer, which is the thing Fagan's machinery exists to provide.

**Knight & Leveson**: noted that 217 claims are not 217 independent checks,
and that a claim and its evidence command usually share an author. Nothing
done.

**Clark & Wilson non-collusion**: I observed that two verifiers sharing a
model and prompt shape violate the assumption — and then dispatched the next
three agents from the same model anyway. It changed the documentation and not
the practice.

**Boehm** (no validation layer, only verification) was a *deliberate*
omission, recorded as such. That one is honest; the three above are not.

### The pattern, and it is uncomfortable

**Quantitative findings moved decisions. Conceptual frameworks moved prose.**
Everything that changed an implementation carried a number — 85 %, 14 %,
2-of-44, an order of magnitude, 26 of 75. Everything that produced only
documentation was a framework: Popper, Fagan's method, Goodhart, Knight &
Leveson. The source cited most reverently is the one implemented least.

**The refutation rate did not decline across three rounds.** Round one
undercut the verifier claim, round two repriced the top-ranked item, round
three falsified three headline claims at once. A converging process would show
fewer corrections per round. This one did not — which means confident
syntheses were being produced faster than they were validated. That is the
same failure this whole session set out to diagnose, one floor up.

**The best implementation result did not come from the reading.** ADR-049's
`restated / expired / wrong` taxonomy — sharper than my four, and it rejected
`moved` with an argument I accepted — came from an agent instructed to
challenge my design. Adversarial delegation outperformed the bibliography.

### What to do differently next time

1. **Prefer a measurement to a synthesis.** `kuchnie-m0m` cost one afternoon
   and overturned a conclusion three documents rested on.
2. **Diversify verifiers by model or lens, not only by scope** — the one
   concrete unimplemented control that is cheap and would have caught the
   non-collusion gap.
3. **Before writing doctrine, check the upstream.** Four consecutive backlog
   items turned out to exist already in `gh:m1981/truth-ledger` (ADR-037
   recipe lints, ADR-032 expiry, ADR-033 velocity, "Explicit non-goals").
   The doctrine surveyed the industry since 1970 and never surveyed this
   project since v0.9.14.
