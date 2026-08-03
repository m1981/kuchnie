# Agentic verification doctrine — what to adopt, what to refuse, how to test it (2026-08-03)

> Reader: whoever decides how much verification machinery this repo carries,
> or wonders why the truth ledger exists at all | Enables: adopting the
> historically-validated controls in order, refusing the ones already refuted,
> and testing that the machinery itself works | Update-trigger: a layer below
> is adopted (mark it), a refusal is overturned with evidence, or a new
> failure mode appears that the catalogue in §1 does not cover

**Why this exists.** The 2026-08-02 session shipped four repairs, then two
independent adversarial verifiers found four defects in that work — all mine,
all confirmed. The post-mortem produced a historical mapping and a
state-of-the-art survey that were about to be lost in a chat log. This
document preserves both, and turns them into a plan.

**One sentence of context.** The truth ledger was built to solve the problems
of agentic coding. The finding of this analysis is that it is a **correct and
unusually well-chosen design**, that its individual mechanisms were each
solved between 1976 and 2019 by people who are worth copying rather than
re-deriving, and that its single real risk is **maintenance cost**, which is
exactly what killed the closest historical precedent.

Everything below is written in English to match the docs corpus
(`docs/file-naming-convention.md` §3), though the conversation that produced
it was partly in Polish.

---

## 1. The failure catalogue and its history

Nine failure modes, observed live on 2026-08-02. Every one has a name and a
literature. The median discovery date is roughly 1980.

| # | What went wrong | Historical name | ~Date | Status |
|---|---|---|---|---|
| F1 | Accepting a proxy for the property | Goodhart's law; Campbell's law; Austin | 1975–96 | Named, not preventable |
| F2 | Evidence that cannot fail | **Mutation testing**; the oracle problem | **1978**, 1982 | **Solved, automatable** |
| F3 | Trusting a command's return message | **End-to-end argument** | 1984 | Solved |
| F4 | Gate with undeclared blind spots | **Soundiness manifesto**; Marick on coverage | 1997, 2015 | Solved as discipline |
| F5 | Closing work with acceptance criteria unmet | Fagan inspection; Definition of Done | 1976 | Solved |
| F6 | Author verifying their own work | **Fagan; IEEE 1012 IV&V; separation of duty** | 1976 | **Solved, best-validated** |
| F7 | Missing blast radius of a change | Change impact analysis; program slicing | 1978–96 | Solved, tooling exists |
| F8 | Shell foot-guns (unquoted glob, truncated output) | ShellCheck SC2086; poka-yoke | 1960s / 2012 | Solved, automated |
| F9 | The measuring instrument itself is wrong | Calibration; test-the-test | — | Partially solved |

### The three that matter most here

**F2 — evidence that cannot fail.** This is precisely mutation testing:
DeMillo, Lipton & Sayward, *"Hints on Test Data Selection"* (IEEE Computer,
1978); Hamlet arrived independently around 1977. Seed a fault; if the check
still passes, the check is not checking. Weyuker's *"On Testing Non-testable
Programs"* (1982) is the companion — the oracle problem, i.e. how you know an
output is *right* rather than merely *stable*.

An evidence command **is a test**, so it can be mutation-tested. Break the
mapping, re-run the recipe, confirm it fails. `tr-ce5c7845` would have died
instantly: it counted substrings in two files while its sentence was about a
mapping in a third. A 47-year-old technique applies unmodified.

The philosophical root is Popper's falsifiability (1934): a claim that cannot
fail tells you nothing. That is the sentence to apply to every recipe.

**F4 — undeclared blind spots.** Livshits et al., *"In Defense of Soundiness:
A Manifesto"* (CACM, 2015) is the precise match. Its thesis: real static
analyses are deliberately unsound in specific ways, and the profession's
failure is not the unsoundness but leaving it **undocumented**.
`64-reachability.sh` is a textbook soundy analysis whose unsoundness
(`__init__` re-export laundering) was undeclared — which is why a passing run
produced a false published conclusion about `recipe.py`.

The earlier statement is Brian Marick's *"How to Misuse Code Coverage"*
(late 1990s): coverage tells you what you did **not** test; it never tells you
that what you tested is correct. DO-178B/C institutionalised the same insight
by mandating MC/DC, precisely because statement and branch coverage have
known, named blind spots.

**F6 — independence.** The oldest and best-validated control in the whole
catalogue. Fagan (IBM, 1976) built author/inspector separation into the
method. IEEE 1012 formalises Independent Verification and Validation with
explicit technical, managerial and financial independence. Clark & Wilson
(1987) encode separation of duty as an integrity model. Auditing calls it
four-eyes.

**This is the control that worked on 2026-08-02**, and it worked for the
reason the literature predicts: independence, not diligence, catches
self-assessment error. Treat it as a standing cost, not a special measure.

---

## 2. State of the art — what exists, and what was abandoned

### 2.1 The truth ledger is a Truth Maintenance System

The `premise` → `HELD` → `--supersedes` mechanics are not new. They are a
**Truth Maintenance System**: Jon Doyle, MIT, *"A Truth Maintenance System"*
(Artificial Intelligence, 1979), extended as **ATMS** by Johan de Kleer
(1986). A TMS is, definitionally, a store of beliefs with recorded
justifications, in which retracting a premise automatically invalidates
everything resting on it.

That is exactly what happened when `tr-4476e4d8` died and `kuchnie-h45` needed
a redirected premise. The formal theory of *what else must go* when a belief
is withdrawn also exists — the **AGM postulates** (Alchourrón, Gärdenfors,
Makinson, 1985), belief revision.

**Assessment:** this repo independently reinvented a 1979 AI mechanism and
applied it to facts about a codebase. The reinvention is sound. The
application — TMS over code facts — is, as far as this analysis can tell,
genuinely unusual: TMS lived in expert systems, not software engineering.

### 2.2 Mainstream and solved — you are already aligned

- **Architectural fitness functions** — Ford, Parsons & Kua, *Building
  Evolutionary Architectures* (2017); **ArchUnit** (Java, ~2017),
  `dependency-cruiser`, NDepend. Your `60-arch-smells`, `64-reachability`,
  `spec-health`, `doc-health` are fitness functions. This is state of the art
  and needs no change.
- **Code as a queryable database** — **CodeQL** (Semmle; GitHub, 2019),
  **Glean** (Meta), **Kythe** (Google). A CodeQL query *is* a re-runnable,
  falsifiable claim about a codebase — a better substrate for evidence
  commands than `grep`.
- **Executable documentation, narrow form** — Rust doctests and Python
  `doctest` are the successful, surviving version: few, load-bearing,
  co-located with the thing they describe.

### 2.3 Tried and abandoned — the FIT warning

Ward Cunningham built **FIT** and then **FitNesse** in the early 2000s with an
aim identical to the truth ledger's: *documents that cannot lie*, because they
carry executable tables that fail when the system diverges.

**FIT did not die because the idea was wrong. It died from maintenance cost.**
Specifications went brittle on every code change; teams spent more effort
repairing executable documents than doing the work those documents described.

Measure this project against that curve honestly. On 2026-08-02, one merge
staled 35 claims, and ledger healing took longer than the code integration it
followed. **That is the same curve.** If this apparatus fails, it will fail
here — not on correctness.

### 2.4 The agentic frontier is empty

The dominant pattern in agentic coding tools is **"tests pass = done"**, which
is failure mode F1 with extra steps. Adjacent but not equivalent:

- **Process supervision** — Lightman et al., *"Let's Verify Step by Step"*
  (2023): reward each reasoning step rather than only the outcome. The truth
  ledger is process supervision applied to claims about code rather than to
  model reasoning.
- **in-toto** (2019), **SLSA** (2021) — provenance of build steps. They attest
  *who built what*, not *whether a statement about the code is still true*.
- **LLM-as-judge / self-critique** — self-assessment, which is precisely what
  failed four times on 2026-08-02. Not a foundation.

Instructive irony: **SWE-bench Verified** (2024) exists because the benchmark
used to evaluate coding agents itself contained claims that turned out to be
false, and humans had to re-verify them. Even the measuring instrument needed
an independent audit.

**Verdict:** no shipped product or open-source project known to this analysis
combines *facts as first-class objects + executable proofs + claim lifecycle +
invalidation propagating into work items*. The pieces were solved between 1979
and 2019; nobody assembled them, and certainly not for agents. Most teams meet
this problem and live with it: tests, code review, accepted drift.

---

## 3. Adoption plan, layer by layer

Ordered bottom-up. Each layer states what to adopt, the historical source, and
what it would have caught on 2026-08-02.

### L0 — Substrate: how a fact is expressed

**Adopt: AST- or query-based evidence instead of line-sensitive `grep`.**

Measured today: **25 of 175 claims (14%) with an evidence command use
`grep -n` or `grep -rn`.** Every one is a false-divergence generator — three
of them diverged on 2026-08-02 purely because an unrelated field shifted line
numbers, and one (`tr-ff8a5110`) could *never* verify because multi-file
`grep -c` emits nondeterministic ordering.

Cheapest viable step is not full CodeQL — it is a small Python helper that
answers structural questions over the AST (`does function F take parameter P`,
`does module M import N`, `how many call sites of C exist`). Grep stays fine
for genuinely textual facts.

*Would have caught:* `tr-ff8a5110`, `tr-0ba0f782`, `tr-89ff86d6`,
`tr-4674581b`.

### L1 — Evidence: can this claim fail?

**Adopt 1: refuse a recipe that does not read its own `evidence_paths`.**
Mechanical, a few lines, same shape as the existing ADR-007 quantifier gate.
Four defective claims found by audit share this single bug.

**Adopt 2: absence claims need a failable shape.** `tr-d9722e31` asserted a
regex was gone and silently omitted the check, because a `grep -c` returning 0
breaks an `&&` chain. Lint for absence-shaped claim text whose command uses
`&&` with a bare count.

**Adopt 3: mutation-test the evidence.** A `truth mutate <claim-id>` verb:
perturb a watched path, re-run the recipe, assert the output changes, restore.
A recipe that survives its own mutation is not evidence. This is the single
highest-value item in the document (DeMillo et al., 1978).

*Would have caught:* `tr-ce5c7845`, `tr-7f0c23cd`, `tr-d9722e31`,
`tr-5f88b6f8`.

### L2 — Gates: fitness functions with declared unsoundness

**Keep the gates as they are** — they are mainstream and correct.

**Adopt: a declared-unsoundness block in every gate, pinned by a test.** Each
gate states what it does *not* catch; a test constructs that case and asserts
the gate passes it. If someone later fixes the blind spot, the test fails and
forces the declaration to be updated. Self-maintaining (Livshits et al., 2015).

*Would have caught:* the false `recipe.py` conclusion.

### L3 — Belief lifecycle: the TMS you already have

**Keep.** The design is right and has a 1979 pedigree.

**Adopt: automatic `reaffirm` in a post-merge hook.** Today healing is a
manual step, which is the FIT death-curve. Auto-reaffirm the hash-matching
majority; surface only genuine divergences and manual-verification claims.

**Do not** extend toward full ATMS multi-context reasoning (§4.6).

### L4 — Process: independence and closure

**Adopt 1: `filer ≠ verifier` as a standing cost**, not an occasional
measure — the only control that caught anything on 2026-08-02.

**Adopt 2: acceptance criteria quoted line-by-line at close.** A close note
must address each AC line with a verdict. Two beads closed with unmet criteria
because the blocker was read and the acceptance text was not. A template can
prompt this; nothing can enforce it, because judging prose is a human act.

**Adopt 3: verify by re-query, never by return message** (Saltzer et al.,
1984). Any state-changing command gets a follow-up query proving the new
state. The `bd close` that silently skipped `kuchnie-27b` was invisible
because stdout was read instead of the tracker being asked.

### L5 — Impact: blast radius before "done"

**Adopt: an explicit dependents check for schema and model changes.** The
`/admin` regression came from verifying a change and never enumerating what
else read `Material`. Bohner & Arnold (1996); Weiser's program slicing (1981).
For this repo the practical form is a checklist item, possibly assisted by
extending the reachability gate to assert that every route reaches the
migration step.

---

## 4. The refusal list — do NOT adopt these

As important as the adoption list. Each of these is either historically
refuted, or a cost model that does not transfer to a one-person shop.

**4.1 Literate programming at scale (Knuth, 1984).** Repeatedly attempted,
never survives maintenance. Do not try to make the whole documentation corpus
executable. Narrow doctests survive; comprehensive literate systems do not.

**4.2 Comprehensive FIT/FitNesse-style executable specification.** Refuted by
maintenance cost (§2.3). The lesson to carry: executable claims must be **few
and load-bearing**, never comprehensive. A ledger of 2,100 claims is already
near the edge; growth should be viewed as a cost, not an achievement.

**4.3 Coverage targets.** Marick. Coverage is a lower bound on what you failed
to test, never evidence of correctness. Do not set a coverage percentage goal;
`test-health` measuring citation validity is the better instrument you already
have.

**4.4 LLM-as-judge or self-critique as primary verification.** This is
self-assessment. It failed four times in one session, in the specific form of
confident summaries that omitted load-bearing qualifiers. Acceptable as a
first pass; never as the control.

**4.5 Chasing soundness in static analysis.** The Soundiness Manifesto's point
is that practical analyses are unsound and should say so. Do not attempt a
"complete" reachability or dependency analysis; declare the gaps instead.

**4.6 Full ATMS / multi-context belief reasoning (de Kleer, 1986).** The
justification-based TMS you have is the right size. Assumption-based
multi-context reasoning is a research-grade mechanism whose cost would land
squarely on the FIT curve. The `contradicts` verb already covers the one case
(two claims that cannot both hold) worth modelling.

**4.7 DO-178-style comprehensive traceability matrices.** The technique is
sound; the cost model assumes an avionics budget and a certification
authority. Selective traceability (`wk-a1898db5`'s "claim per external
constant") is the right adaptation and is already filed.

**4.8 Metrics as targets (Goodhart, 1975).** Do not count verified claims,
do not target a claim count, do not reward ledger growth. The moment "number
of live claims" becomes a goal, it stops measuring anything.

**4.9 "Tests pass = done" as the agent oracle.** Refuted repeatedly on
2026-08-02: 819 core tests passed while `/admin` crashed on every legacy
database, and 290 ERP tests passed while two of three drawer systems emitted
a scrap drilling pattern.

**4.10 Formal methods over the whole codebase.** Reserve for kernels and
invariants if ever. The panel's anti-over-engineering duty applies.

**4.11 A gate that warns forever.** Not from the literature but earned here:
a permanently-NEW warning trains people to ignore the gate. Either accept the
finding into a baseline *with the reason recorded*, or fix it. This is the
normalisation-of-deviance mechanism (Vaughan, 1996) in miniature.

---

## 5. How to test the verification machinery itself

The machinery is code, and it is code whose failure is silent — a broken gate
reports success. So it needs the same treatment as any other silent-failure
system: **seed the fault, assert it is caught.**

### 5.1 The governing principle

For every mechanism, two test families:

- **Positive control** — a deliberately broken artifact the mechanism **must**
  reject. Without this, a mechanism that always passes looks healthy.
- **Declared blind spot** — a case the mechanism **must** pass despite being
  wrong, pinning the known unsoundness. When someone fixes it, this test fails
  and forces the declaration to be updated.

The second family is unusual and is the direct implementation of §3 L2.

### 5.2 Per-mechanism test design

**Evidence commands (L1).** A mutation harness. For claim *C* with watched
paths *P*: apply a perturbation to *P* (rename a symbol, delete a line, change
a mapping), re-run *C*'s recipe, assert the output hash changes, restore.
A claim whose recipe survives every perturbation is flagged. Run as a periodic
sweep, not on every commit — it is expensive and mutating.

*Success criterion:* every claim whose paths can be perturbed shows at least
one perturbation that changes its output.

**Gates (L2).** Each gate gets a fixture directory with: one case it must
FAIL, one case it must PASS, and one case that is its declared blind spot.
`64-reachability.sh` already has 15 self-tests, including a vendored-code
fixture asserting an exact swept count so a silently widened sweep fails —
that is the right pattern; generalise it. Its missing test is the blind spot
one: an `__init__`-re-exported orphan that the gate passes *by design*.

*Success criterion:* removing any single gate rule makes at least one test
fail.

**The TMS (L3).** Seed a retraction in a fixture ledger, assert dependents
derive HELD; seed a `--supersedes` redirect, assert they recover; seed two
`contradicts` claims, assert both go DISPUTED. Test the propagation, not the
storage.

*Success criterion:* a work item standing on a retracted premise never appears
in `truth ready`.

**Process controls (L4).** Independence cannot be unit-tested. The honest
instrument is a **retrospective**: for each audit, record how many findings
the verifier caught that the filer missed. On 2026-08-02 that number was 4 of
4 — total. If it ever trends toward zero, either the work got better or the
verifiers stopped being independent, and only reading the findings tells you
which. **Do not turn this into a target** (§4.8).

**Impact analysis (L5).** For each schema or model change, a test that
enumerates entry points and asserts each reaches the migration step. The
regression test added on 2026-08-02
(`test_app_module_runs_migrations_at_import_not_from_a_route`) is the first
instance and was itself validated by moving the call and watching it fail —
which is the mutation principle applied by hand.

### 5.3 The meta-test

One test above all: **the canary sweep.** A fixture repository containing one
seeded instance of each of the nine failure modes in §1, run against the whole
gate suite. If the suite goes green on the canary repo, the suite is broken.

This is the only test that checks the *system* of controls rather than each
control alone, and it is the direct answer to F9 ("the instrument is wrong").

---

## 6. Order of work

Ranked by (defects caught on 2026-08-02) ÷ (cost). Nothing here is urgent
relative to the fidelity backlog; this is infrastructure that pays off over
months.

| # | Item | Layer | Effort | Caught |
|---|---|---|---|---|
| 1 | `evidence_paths` ⊆ recipe check | L1 | S | 4 claims |
| 2 | Auto-`reaffirm` post-merge hook | L3 | S | the FIT cost curve |
| 3 | Declared blind spot + pinning test per gate | L2 | S | the `recipe.py` error |
| 4 | AST evidence helper; migrate the 25 `grep -n` claims | L0 | M | 4 divergences |
| 5 | `truth mutate` harness | L1 | M | the whole F2 class |
| 6 | Canary repo + meta-test | L5 | M | F9 |
| 7 | Close-note AC template | L4 | S | 2 beads |

Items 1–3 are small, independent, and need no owner input.

---

## 7. Open questions

- Is the ledger's growth rate sustainable? 2,100 records and one merge staling
  35 claims is the number to watch. If auto-reaffirm does not flatten it,
  the correct response is **fewer claims**, not more machinery (§4.2).
- Should evidence commands move to a real query engine (CodeQL/Glean) rather
  than a local AST helper? Bigger dependency, much stronger substrate.
  Not yet — revisit if the AST helper proves insufficient.
- Is there prior art for TMS-over-codebase-facts that this analysis missed?
  Worth a literature check before investing further; being wrong about
  novelty is cheap to discover and expensive to assume.
