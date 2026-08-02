# Consolidated architecture review — the verdict (2026-08-02)

> Reader: Michał deciding what to fund and in what order, or an agent about
> to start any repair | Enables: one scorecard over the whole system, the
> ranked backlog, the leave-it-alone list, and the decision about which
> tracking layer each piece of this review belongs in | Update-trigger: a
> backlog item ships, the one open owner question is answered, or a
> dimension's score changes

**This is the A.3/A.4 consolidated review** that closes the four-round
architecture pass. Rounds 0–1 (`architecture-refactor-plan-2026-08-02.md`),
round 2 (`architecture-review-round-2-2026-08-02.md`) and round 3
(`architecture-review-round-3-2026-08-02.md`) own the evidence; this document
does not restate it, it **judges** it.

Findings referenced by id: `P0-1…P1-2` (rounds 0–1), `N1…N11` (round 2),
`N12…N15` (round 3). Beads filed this session: `kuchnie-h45`, `kuchnie-5q3`,
`kuchnie-lm8`, `kuchnie-27b`, `kuchnie-4q8`, `kuchnie-5un`, `kuchnie-26s`,
`kuchnie-019`, `kuchnie-zae`, `kuchnie-ubc.1`, `kuchnie-lh2`, `kuchnie-33x`,
`kuchnie-05p`, `kuchnie-8ky`.

---

## TL;DR

This repo has a domain core most small-shop software never achieves — an
enforced dependency rule, a single geometry→quantity fold, golden-first
tests, and a working truth ledger — wrapped in an application that cannot
reach half of what that core provides.

The defect is not quality; it is **connection**. Every serious finding is a
seam: material identity flattened crossing into the domain, accessories
discarded crossing back out, and two whole process stages (purchasing, CAM)
built and tested but wired to nothing.

One 122-line file, `kitchen-erp/kitchen_erp/core/domain_adapter.py`, carries
six of the fourteen findings. It is the cheapest file in the repo to fix and
the most expensive to leave.

---

## The P0 findings

**P0-A · An entire subsystem is unreachable from the application** (N12,
round 3, `CONFIRMED`). `variant_derivation.py`, `offers.py`, `heights.py`,
`kitchen_cam/machining.py` and `kitchen_cam/dxf/panel_dxf.py` have **zero
importers** in any non-test source, counting `__init__` re-exports. The UI
contains no reference to `Variant`, `derive_variant`, `record_offer` or
`ArtifactRef`. Process stages 5 (purchasing) and 7 (CAM/drilling) — the two
that produce the formatki order and the drilling file, the documents the
business actually runs on — cannot be executed from the software. This is not
dead code; it is deliberately ahead of the UI. The defect is that **no gate
measures reachability**, so the gap is invisible: `coverage-audit.py` reports
`DARK=0` because tests and specs name these modules. → `kuchnie-lh2`

**P0-B · Material identity is destroyed at the seam, then guessed back**
(P0-1 + N11, `CONFIRMED`). `domain_adapter.py:62-64` passes only
`Material.name` into the domain; `Material` has no thickness field at all.
`purchasing.BOARD_DECOR_CATALOG` (4 entries) and `EDGE_IDENTITY_CATALOG` (2
entries) then reconstruct producer/decor/structure/width from hardcoded
dicts keyed on strings. The production join is string equality between an
admin-editable DB column and a literal — and it is exercised by no test.
*Expert 1:* a board you can order needs decor + structure + thickness +
format; three of four are re-derived, one does not exist. → `kuchnie-h45`

**P0-C · Hardware is computed from geometry, then thrown away and retyped**
(N1, `CONFIRMED`). `quantities_from_decomposition` reads only `panel` and
`edge_band` categories — the string `accessor` appears nowhere in
`domain_adapter.py`. Confirmats counted from actual drill ops, euro screws at
4 × runner profiles, LEGRABOX runner codes, plinth legs and clips: all
discarded, then re-added from a flat tag table that prices "Drawer System
(Blum/Hettich)" at 150 PLN. → `kuchnie-b2u` (updated with direction)

**P0-D · Prices without provenance bypass the freshness gate** (P0-3, widened
in round 2, `OBSERVED`). Four PLN literals in `bom_generator.py` (cutting
15.00/m², edgebanding 4.50/lm, plinth 25.00/lm, seal 3.50/lm) plus every
`rules_engine` hardware price (cargo 600.00, drawer system 150.00, hinges
15.00). None carry a supplier or `valid_from`; none are visible to
`assess_quote_freshness`. A quote can be graded offer-grade while these carry
it. In a subcontracting shop the cutting rate per m² is *the* primary
purchasing number. → `kuchnie-5q3`

---

## Scoring matrix — the eight dimensions

| # | Dimension | Score | Verdict, with the trade-off named |
|---|---|---|---|
| 1 | **Layering & dependency rule** | ✅ sound | Enforced and *stated in code* (`kitchen.py:96-98`); core imports no framework, no ORM, no `bpy` — one `sqlite3` behind a Protocol. **Trade-off:** enforced only at component granularity. Inside `kuchnie_core` the layering is not acyclic — nine function-local imports break real cycles (P1-2), and the repo's own gate independently agrees. |
| 2 | **Domain alignment** | ◐ strained | Ubiquitous language is genuinely well done: Polish at the boundary, English in code, `loader.py` as the translator; `formatka`, `obrzeże`, `widełka`, `rozrys`, `cokół` all present; units in names throughout (`width_mm`). **But** primitive obsession at the identities that matter — board and edge as strings (P0-B), drawers as raw dicts instead of the existing `DrawerSlot`, and `typ` carrying two vocabularies at once (N9). |
| 3 | **Pipeline integrity** | ✗ broken | `calculate_bom` is a real single fold and `decompose` a real single dispatch — the ADR-015 discipline holds where it was written. **But** the pipeline breaks at every crossing: accessories dropped (N1), the drawer stacking loop implemented twice (N8), identity re-derived from hardcoded tables (P0-B, N11), and the documents unreachable (P0-A). Expert 2's cardinal sin appears five times. |
| 4 | **Collaboration health** | ◐ strained | Core modules are cohesive and small; `decomposer.py` is 19 lines. **But** `domain_adapter.py` is a 122-line chokepoint carrying six findings, and the ERP UI holds two god-classes (`AdminState` 36 methods, `KitchenState` 34 and drifting). |
| 5 | **SOLID at signature level** | ◐ strained | Registries and dispatch used properly everywhere a type-switch would have grown: `TYPE_REGISTRY`, `ConstructionMethodRegistry`, `DrawerSystemFactory`, `HingeFactory`, `PurchasingStrategy`. **But** five param-bloat sites (10/11/8/9/12 args), and one ISP failure with real consequences — the `DrawerSystem` ABC lacks `runner_y_mm`, which is *why* the stacking loop got duplicated (N8). |
| 6 | **Anti-pattern sweep** | ◐ strained | No god object in the domain core; no big-ball-of-mud arrows; `catalog.py`'s 1021 lines are five honest per-type functions. **But** two hardcoded lookup tables re-deriving identity, one write with no reader (N9), one complete ports-and-adapters subsystem with no consumer (N14), and an orphaned subsystem (P0-A). |
| 7 | **Testability & test alignment** | ◐ strained | The process discipline here is better than most commercial shops: golden-first e2e, assertions that show the formula (`assert back.width_mm == 700  # LW−38`), byte-stable baselines, `DARK=0` on the coverage audit. **But** the tests pin code that cannot run (P0-A) — green on unreachable modules is the most expensive kind — the purchasing production join is exercised by nothing (P0-B), and `admin_state.py`, the largest class in the repo, is named by no test while being the landing site for two P0 repairs. |
| 8 | **Domain red flags** | ✗ broken | Units are in names, buffers are kept out of construction math (`WASTE_BY_CLASS` is separate and owner-confirmed), and the buildability gate refusing to emit a cutlist for an unbuildable kitchen is commercially the best idiom in the repo. **But** three trade-level breaks: prices with no provenance or date (P0-D), an identity too weak to order against (P0-B), and NL fixed at 500 regardless of carcass depth while the gate that would catch it (M3) only runs for a cabinet type the ERP cannot reach (N10). |

**Aggregate: 1 sound, 5 strained, 2 broken.** The shape is consistent — the
core scores well, every seam scores badly. That is a far better position than
the inverse, because seams are cheaper to repair than foundations.

---

## Unknowns still open (`NEEDS-BODY`)

- Is `kuchnie_core/recipe.py` orphaned like `materials`? `tr-fc74bc2e` says
  unwired; round 2 recommended deleting rather than wiring. Not re-checked.
- Does the d60 walking-skeleton exercise cover a drawer base? Determines
  whether `kuchnie-lm8` forces a golden roll.
- Have the `catalog/repositories/*` modules, tested only indirectly through
  API tests, ever masked a repository-level bug? Unmeasured.

---

## The one question for the owner — ANSWERED 2026-08-02: fidelity first

> **Is the near-term goal to get one real kitchen end-to-end through the
> software — survey to formatki order to drilling file — or to keep deepening
> domain fidelity (LEGRABOX carcasses, corner cabinets, material identity)
> before wiring anything up?**

**Owner decision (2026-08-02): fidelity first.** Deepen the domain before
wiring the application to it.

**What this changes:**

- **P0-A (`kuchnie-lh2`) splits.** The *reachability gate* still lands early
  and stays high priority; the *wiring epic* (`kuchnie-ubc.1`) is
  deliberately parked. This is the important consequence: choosing not to
  wire makes "built but unreachable" a **standing state**, so it must be a
  *declared* one. The gate plus its `not-yet-wired` allowlist is what keeps a
  deferred decision from decaying into a forgotten one — and it is the reason
  the gate does *not* drop in priority alongside the wiring it guards.
- **`kuchnie-lm8` leads the fidelity spine**, preceded by `kuchnie-27b` (the
  `DrawerSystem` ABC fix), which it depends on.
- **Q5 loses most of its force.** It asked whether to model LEGRABOX or
  TANDEMBOX. Under fidelity-first the answer is *route both correctly*; Q5 now
  only picks the **default** for a new drawer base, which is a one-line
  decision rather than a scope question.
- **Q1 is moot** for now — it asked whether the purchasing docs are intended
  as real output. That question re-opens when the wiring is unparked.
- **Q2 and Q3 still stand** and still gate their single items.

*Panel note, Expert 1 dissenting in part:* fidelity-first is defensible, but
the shop cannot produce a formatki order from this software until the wiring
lands, so every quote in the interim is still carried by the four
unprovenanced literals. That makes **Q2 the most valuable question to answer
now** — it is small, unblocks `kuchnie-5q3`, and improves every quote made
during the fidelity work.

---

## Prioritised action backlog — fidelity-first ordering

Reordered per the owner decision above. **Phase 1** is small, independent
work needing no owner input; **phase 2** is the fidelity spine; **phase 3** is
explicitly parked.

### Phase 1 — clear the ground (all S, no owner input except Q2)

| # | Item | Bead | Risk | Blast radius | First concrete step |
|---|---|---|---|---|---|
| 1 | Reachability gate + `not-yet-wired` allowlist | `kuchnie-lh2` | low | gate suite | Add the gate; allowlist today's orphans with bead ids. **Priority survives the fidelity-first decision** — parking the wiring is exactly what makes the declared state necessary. |
| 2 | Extract `Finding`/`GateStatus` to a leaf module | `kuchnie-5un` | low | imports only | Create `kuchnie_core/findings.py`; no behaviour change. Clears the core cycles before the fidelity work touches those modules. |
| 3 | Fix CWD-relative DB path; delete 0-byte decoys | `kuchnie-26s` | low | local envs | Resolve from package root or `KITCHEN_ERP_DB`. |
| 4 | `Material.thickness_mm` + `structure` + mirror | `kuchnie-h45` (step 1) | low | ERP schema | Migration + mirror population. Q4 already answered. Land `kuchnie-33x` tests with it. |
| 5 | **Q2** → prices into `SupplierPrice` | `kuchnie-5q3` | low | quote figures move | **Ask Q2 now** — highest-value question under fidelity-first, since interim quotes still ride on the literals. |
| 6 | Catalog schema-version handshake | `kuchnie-019` | low | 3 startups | Expose version in `/admin/stats`; assert at startup. |

### Phase 2 — the fidelity spine (the point of this plan)

| # | Item | Bead | Effort | Risk | Blast radius | First concrete step |
|---|---|---|---|---|---|---|
| 7 | `runner_y_mm` + `side_thickness` into the `DrawerSystem` ABC | `kuchnie-27b` | M | low | drawer geometry | Bundle with `kuchnie-b30` (same parameter list — two golden rolls otherwise). **Must precede 8.** |
| 8 | Decomposer routing + plinth bucket + vocabulary + NL rule | `kuchnie-lm8` | M | med | drawer-base quotes, goldens | **The lead fidelity item.** Ship as ONE change — the plinth double-count arms the moment routing lands. Q5 now only picks the default. |
| 9 | `BoardSpec`/`EdgeSpec` in full | `kuchnie-h45` | L | med | wide; golden roll | The expensive one, and the core of "fidelity". Identity shape already owner-confirmed. |
| 10 | Accessories across the seam, then consumed; `HardwareRule` → price-only | `kuchnie-b2u` | M | med | quote totals | Step 1 (carry, no consumer) is S and can land in phase 1; consumption must follow item 8. |
| 11 | **Q3** → construction math out of the adapter | `kuchnie-4q8` | M | low | drawer fronts | Confirm the reveal convention first so move and correction stay separable. |
| 12 | Triage `materials`; regenerate smells baseline | `kuchnie-05p`, `kuchnie-8ky` | S | low | — | Housekeeping after items 1 and 2. |

### Phase 3 — parked by the fidelity-first decision

| # | Item | Bead | Why parked |
|---|---|---|---|
| 13 | Wire the purchasing chain (UI → variant → docs) | `kuchnie-ubc.1` | Deferred by the owner decision. Must appear in item 1's `not-yet-wired` allowlist so the deferral is visible, not forgotten. Re-opens Q1 when unparked. |

**Three constraints that break things if ignored** — the first two encoded as
bead dependencies, the third as bead text:

1. Item 7 must precede item 8 (otherwise the routing fix leaves two live
   drawer paths instead of deleting one).
2. Item 9 must precede item 13 (wiring before identity travels cements the
   string join).
3. Accessories must not start flowing before the plinth bucket exists, or
   every base cabinet is charged legs twice.

---

## Leave it alone

Things that look refactorable and are not, each with why refactoring buys
nothing:

- **`kuchnie_core/catalog.py`, 1021 lines.** Five per-type decomposition
  functions behind a flat dispatch table. It grows linearly and honestly;
  splitting it adds import ceremony without reducing any unit of reasoning.
  This is how Polyboard-class systems organise construction methods.
- **`ui/state.py` and `admin_ui.py` as Reflex code.** Framework-shaped by
  necessity. The *narrow* exception stands: extract the row-layout maths and
  the runtime `ALTER TABLE` migrations (tracked separately), not the
  `rx.State` plumbing.
- **`validate_manifest` / `geometry_manifest`.** Round 2 proved it is a
  projection of the typed model, not a second geometry model. Do not "unify"
  them. (Its permanently-skipped gate is a separate, real item:
  `kuchnie-zae`.)
- **`BOARD_DECOR_CATALOG` raising `KeyError` on an unmapped material.** The
  loud failure is correct and must survive item 12. Only the *table* goes
  away; the refusal to emit a silently-wrong purchasing document stays.
- **The recipe-formula fallback in `BOMGenerator`.** Round 2 initially read it
  as a rival engine and was wrong: it fires only when the hub has no
  construction method. It is the correct PRO100 lesson — sales-time modelling
  stays fast and forgiving for what the precise path cannot yet build. Label
  estimate-grade lines in the cost trace instead.
- **`kuchnie_core.materials` as *code*.** Clean, Protocol-first, costs nothing
  sitting there. It needs to be *named* as not-yet-wired, not rewritten.

---

## What form the plan should take

**Short answer: neither a markdown plan nor beads alone — this repo already
specifies the answer, and the layer we are missing is the truth ledger.**

`docs/spec-convention.md` states the contract explicitly:

| Kind of truth | Example from this review | Home |
|---|---|---|
| Decision (why we chose this) | "board identity becomes a value object" | **ADR** (`docs/adr/`) |
| Current-state fact (what is true now) | "`board_order_rows` has no production caller" | **`tr-` claim** |
| Intent (what should become true) | "wire the purchasing chain" | **`wk-` issue / bead** |
| Narrative (scope, data flow, reasoning) | the six diagrams, the evidence chains | **the review documents** |

This review produced all four kinds and I filed only two of them — the
narrative (three review docs) and the intent (fourteen beads). **The
current-state facts are unfiled**, and that is the gap that matters, for a
specific mechanical reason:

`CLAUDE.md`'s work-finding precedence says use `scripts/truth ready`, not `bd
ready`, because the former is the latter *filtered by premise validity* —
issues standing on dead facts are HELD. My fourteen beads currently stand on
**no premises at all**. So they can never be HELD, and nothing will notice
when a finding stops being true.

That matters more here than in a normal backlog, because **these findings are
designed to become false.** "Accessories are dropped at the seam" stops being
true the day item 5 lands. Without `tr-` claims and premise links, a later
session reads a stale bead description as current fact — which is precisely
the decay mode `docs/spec-convention.md` was written to stop ("prose has no
tripwire").

**The concrete recommendation, in order:**

1. **File a `tr-` claim per load-bearing finding**, using the evidence
   commands already recorded in Appendices A, B, C and D of the three review
   documents. Those appendices exist for exactly this — each is a
   one-line, re-runnable `grep` with a stated expected result, which is what
   `truth claim` needs. Roughly ten claims: the four P0s, plus N8's signature
   gap, N9's vocabulary split, N10's NL default, N12's orphan set, N14's
   no-consumer fact, and the reachability-gate absence.
2. **Premise-link the beads to those claims** — `scripts/truth premise
   kuchnie-h45 tr-xxxxxxx`. The verb takes an external tracker id directly,
   so no `wk-` twins are needed. This is the step that makes `scripts/truth
   ready` correct for this work.
3. **Keep the three review documents as narrative** — they are already in the
   right place (`docs/reviews/`, house convention, `doc-health` clean). Do
   *not* migrate their reasoning into bead descriptions; auditability of the
   ledger is a function of its size (ADR-002's refusal list).
4. **Write one ADR only if item 12 proceeds** — introducing `BoardSpec`/
   `EdgeSpec` as the domain's material identity is a genuine architectural
   decision that future work will need the *reasoning* for, and accepted ADRs
   are immutable, so it belongs there rather than in a bead.
5. **Do not** create a markdown checklist or TODO file for the backlog. The
   table above is a snapshot for human reading; the beads are the queue, and
   duplicating them in markdown creates a second source of truth that will
   silently diverge — the exact failure this repo's ledger exists to prevent.

**Executed 2026-08-02.** Steps 1 and 2 are done: eleven `tr-` claims filed
(each VERIFIED, each with a re-runnable evidence command and an `agree`
verdict carrying the basis), and eleven premise links wired from the beads to
the facts they stand on. `scripts/truth doctor` reports 0 failures on premise
integrity, and the beads now resolve through
`bash scripts/truth-bd-adapter.sh | scripts/truth ready --stdin` — which is
the invocation to use, because the native work kernel otherwise outranks the
`bd` default (the precedence trap in `docs/beads-integration-guide.md` §2).

Claim → bead map:

| Claim | Fact | Premised bead |
|---|---|---|
| `tr-2cf9b72c` | material crosses the seam as three name strings only | `kuchnie-h45` |
| `tr-4476e4d8` | ERP `Material` has no thickness field | `kuchnie-h45` |
| `tr-bcb00b34` | accessories discarded at the seam | `kuchnie-b2u` |
| `tr-80cab110` | four unprovenanced PLN literals | `kuchnie-5q3` |
| `tr-436bdf4f` | two decomposers unreachable from the ERP | `kuchnie-lm8` |
| `tr-a4a767a6` | drawer-system vocabulary split | `kuchnie-lm8` |
| `tr-d11749e8` | NL never set by the adapter | `kuchnie-lm8` |
| `tr-0151520f` | `DrawerSystem` ABC lacks `runner_y_mm` | `kuchnie-27b` |
| `tr-7a4ed70d` | three ERP modules have zero importers | `kuchnie-lh2` |
| `tr-8f62bd63` | `materials` has no production consumer | `kuchnie-05p` |
| `tr-46f1ea3c` | purchasing generators have no caller | `kuchnie-ubc.1` |

Each claim carries a 180-day TTL on its `--scope-ok` override, so the
quantifier judgment ("no", "zero", "only") is re-asked rather than trusted
forever. Steps 3–5 stand as written: the review documents remain the
narrative, one ADR when `BoardSpec` proceeds, and no markdown checklist.

**One caveat on execution.** Filing claims is cheap; *retracting* them is
human-only (`TRUTH_HUMAN=1` plus a typed-id confirmation). So claims should be
filed only for facts that are (a) verified by a re-runnable command and (b)
expected to be superseded by a repair rather than found wrong. All ten above
qualify — every one has a recorded command and a positive control — but that
is why this step is a recommendation awaiting a nod, not something I did
unprompted.
