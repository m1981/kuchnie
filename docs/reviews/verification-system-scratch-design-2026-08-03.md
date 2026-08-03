# SCRATCH — what a verification system would look like if built today (2026-08-03)

> Reader: Michał deciding whether to extend the truth ledger or replace it,
> and anyone tempted to add machinery to it | Enables: seeing the target
> design detached from the current implementation, and the cheap migration
> path to it | Update-trigger: the classification in §5 is executed, or the
> measurements in §1 are re-taken and contradict it
>
> **STATUS: SCRATCH. Nothing here is adopted.** This is a design exercise
> requested on 2026-08-03 to test whether the current system is worth
> building on. Its conclusion (§6) is *migrate, do not rewrite* — so this
> document exists to define the target, not to justify a rebuild.

Companion: `agentic-verification-doctrine-2026-08-03.md` holds the historical
analysis this design is derived from. It is not restated here.

---

## 1. The measurement that forced this document

Taken 2026-08-03 against `.truth/claims.jsonl`:

| Record kind | Count |
|---|---|
| `claim` | **217** |
| `verdict` | 990 |
| `invalidation` | 656 |
| `premise` | 42 |
| `issue` + `issue_event` | 228 |

**7.6 maintenance records per fact.** Bookkeeping is 76 % of the ledger's
volume.

Claim status distribution:

| Status | Count | Share |
|---|---|---|
| live | 131 | 60 % |
| **retracted** | **75** | **35 %** |
| stale / cannot_verify / unverified | 11 | 5 % |

**A 35 % mortality rate is the finding.** These facts did not die from being
wrong. They died from being *fixed*. `tr-4476e4d8` ("Material has no thickness
field") was true when filed, true when verified, and false the moment
`kuchnie-h45` shipped — by design.

That is not an engineering defect. It is a **taxonomy defect**: a statement
describing a defect was stored as a *fact*, and facts describing defects are
built to expire. The FIT death-curve in the doctrine document is this ratio.

---

## 2. First principles — what are we actually trying to do?

*Let an agent or a human act on statements about a codebase without those
statements silently becoming lies.*

Three kinds of statement get mixed together today, and they have completely
different physics.

### A. Computable properties of the code

> "No first-party module is unreachable without a declaration."
> "Board identity carries thickness."
> "The BOM quantity fold is single-source."

**Decidable by running something.** Therefore they should never be *stored*.
Storing a computable property creates a cache, and every one of the 656
invalidation records is that cache going stale.

Correct form: an **invariant** with a derived RED/GREEN status. Not a claim.
No lifecycle, no verdict, no retraction — it just flips.

**Roughly 80 % of current claims are this kind, and they generate ~100 % of
the churn.**

### B. External testimony

> "Owner confirmed cutting rate 18 PLN/m² on 2026-08-03, supplier Drewpol."
> "Blum catalogue: NL 500 → runner screws at 46 / 78 / 110 / 398."
> "EN 1116 coordination dimensions."

**Not computable.** No amount of code reading establishes them. They need a
source, a date and an actor, and they are **immutable** — testimony given on a
date stays given. It is superseded by newer testimony, never retracted, and
never re-verified because there is nothing to re-run.

**Zero churn by construction.** This project needs maybe 20–40 of these
records in total.

### C. Events

> "Shipped X at commit Y."

That is git. Do not duplicate it in a ledger.

**The current system applies category-A machinery (evidence commands,
re-verification, invalidation, verdicts) to all three.**

---

## 3. The design

### 3.1 Layer 1 — Invariants

An invariant is a named, executable predicate with declared limits:

```
id:            board-identity-carries-thickness
statement:     Every board a purchasing document can order carries
               producer, decor, structure and thickness.
predicate:     <executable — exit 0 = GREEN>
blind_spots:   - does not check edge banding, only board
               - trusts the catalog mirror; does not re-query the service
mutation:      <perturbation that MUST turn it RED>
owner_bead:    kuchnie-h45          # required while RED, forbidden while GREEN
```

Properties that fall out of this shape:

- **Status is derived, never stored.** Nothing to invalidate, nothing to
  reaffirm, no staleness. The 656 invalidation records stop existing.
- **`blind_spots` is a required field.** Directly implements the soundiness
  lesson. An invariant with no declared limits is refused at authoring time —
  because every real analysis has some.
- **`mutation` is a required field.** This is the 1978 lesson made structural:
  you cannot register an invariant without supplying a perturbation that
  proves it can fail. No more evidence that cannot fail.
- **`owner_bead` while RED.** A known-violated invariant must name who is
  fixing it. This is the "no gate that warns forever" rule, enforced rather
  than remembered.

The existing gates (`60-arch-smells`, `64-reachability`, `spec-health`,
`doc-health`, `exercise-gate`) are already invariants in everything but name.
This layer largely exists.

### 3.2 Layer 2 — Testimony

```
id:         t-2026-08-03-cutting-rate
statement:  Cutting and nesting is 18 PLN/m2.
source:     owner, verbally, quoting Drewpol invoice of 2026-06
date:       2026-08-03
confidence: confirmed | assumption | hearsay
supersedes: t-2026-05-11-cutting-rate
```

No predicate. No re-verification. Append-only. `confidence: assumption` is
first-class, because "we guessed and said so" is a legitimate and *useful*
state — it is what forces a quote to estimate-grade.

### 3.3 Layer 3 — Links

Two link types, and only two:

- `bead --stands-on--> testimony` — the TMS edge, kept. If testimony is
  superseded, dependent work HOLDs. This is where Doyle's 1979 mechanism
  genuinely belongs, and at 20–40 testimony records it costs nothing.
- `bead --turns-green--> invariant` — **the acceptance criterion, made
  executable.**

That second link is the most valuable idea in this design. Today a bead's
acceptance criteria are prose, which is why two beads closed with criteria
unmet on 2026-08-02. If closing a bead requires its named invariant to be
GREEN, the machine enforces what a close note only promises.

### 3.4 What disappears

Verdicts. Invalidation records. Staleness. `reaffirm`. Human-gated retraction
for computable facts. Evidence-path watching. The whole 7.6-records-per-fact
overhead, for category A.

What survives: the TMS edges (tiny), testimony (tiny), and the gates
(already there and already cheap).

---

## 4. Checking the design against the historical lessons

| Lesson | Source | How this design answers it |
|---|---|---|
| Maintenance cost kills executable docs | FIT/FitNesse, ~2002 | Invariants do not churn; testimony does not change. Category-A cost → ~0 |
| Evidence that cannot fail | Mutation testing, 1978 | `mutation:` is a **required field**; unfailable invariants cannot be registered |
| Undeclared blind spots | Soundiness, 2015 | `blind_spots:` is a **required field** |
| Belief revision | TMS 1979 / AGM 1985 | Kept, scoped to testimony where it is cheap and correct |
| Metrics as targets | Goodhart, 1975 | Nothing countable is a score. RED count is a work queue, not a KPI |
| Author verifies own work | Fagan, 1976 | Orthogonal — stays a **process** control, cannot be designed away |
| Trusting a return message | End-to-end, 1984 | Status is always computed on read, never reported by a writer |
| Closing with criteria unmet | Fagan / DoD, 1976 | `turns-green` link makes the criterion machine-checkable |
| The instrument is wrong | — | Canary corpus (doctrine §5.3) still required; this design does not solve it |

The last row is honest: **no design solves F9.** A wrong invariant reports
GREEN exactly as confidently as a right one. Only the canary corpus and
independent verification address that, and both are process, not architecture.

---

## 5. Migration — classification, not rewrite

For each of the 131 live claims, one question: **can a machine decide this?**

- **Yes** → it is an invariant. Register it with `blind_spots` and `mutation`;
  delete the claim. Most will collapse into existing gates rather than
  becoming new ones — several current claims are really assertions that a gate
  already makes.
- **No, it is external testimony** → move to layer 2 with source and date.
  Expect very few: owner rates, manufacturer geometry, standards.
- **No, it is an event** → delete. Git already has it.

The 75 retracted claims are archived history and stay as they are — they are
the audit trail of what this project once believed, and that has value even
though it has no future.

**Estimated shape after migration:** ~15–25 invariants (most already exist as
gates), ~20–40 testimony records, ~40 premise links. Down from 2,133 records.

---

## 6. Verdict — extend, do not rewrite

Three reasons, in order of weight.

**1. The machinery is not the problem; the taxonomy is.** The TMS core is
correct and has a 1979 pedigree. The gates are mainstream fitness functions.
Path-based invalidation over-approximates, but it is only a *trigger* — the
real check is the recheck, which already auto-agrees the majority. Nothing in
the engine needs replacing. What needs replacing is *what we put in it*.

**2. The ADRs encode incidents a rewrite would re-learn.** ADR-007 (quantifier
scope), ADR-009 (evidence screening), ADR-012 (mechanical divergence),
ADR-018 (text similarity), ADR-030 (reaffirm), ADR-032 (override decay),
ADR-035/036/037. Each exists because something went wrong once. A fresh system
starts with none of them and re-earns them the same way. This is the classic
argument against rewriting working systems, and here it is unusually concrete
— three of those ADRs fired *correctly* on 2026-08-02 and stopped me filing
bad claims.

**3. The target design is reachable by subtraction.** §5 is a classification
pass, not an implementation. Most invariants already exist as gates. That is a
far cheaper path than a parallel system plus a cutover.

### What this changes about the three queued beads

The doctrine's first three items were about to be built on the wrong
assumption. Re-scoped:

| Bead | Was | Should become |
|---|---|---|
| `kuchnie-3xh` | recipe must read its `evidence_paths` | **`mutation:` required** — the stronger form; path-reading is a weak proxy for it |
| `kuchnie-94t` | auto-`reaffirm` post-merge | **short-term only.** Legitimate during migration; obsolete once category-A facts are invariants, since there is nothing to reaffirm. Do not build elaborate tooling here |
| `kuchnie-z00` | declared blind spots per gate | **unchanged and confirmed** — becomes a required *field*, not an add-on |

`kuchnie-94t` is the one worth pausing on: it is a cost-reduction for a
mechanism this design deletes. Build the cheap version or skip it.

---

## 7. What I am least sure about

- **Are 20–40 testimony records really enough?** If the true number is 200,
  the churn argument weakens and layer 2 needs more thought.
- **Expensive invariants.** Some properties cost minutes to evaluate. A
  fast/slow split is obvious but unspecified here.
- **Point-in-time facts that are neither computable nor testimony.** "The
  golden was regenerated at commit X, deliberately." That is an event with a
  justification. Git plus a commit message probably suffices, but I have not
  tested that claim against real cases.
- **Whether this is novel.** The doctrine already flags that TMS-over-code
  may have prior art. The invariant/testimony split resembles the distinction
  between *specification* and *domain assumption* in Michael Jackson's problem
  frames, and between requirements and domain properties in the
  Zave–Jackson framework (~1997). Worth reading before building anything.
