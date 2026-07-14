# Requirements assessment — fresh outside review (2026-07-14)

> Reader: Michał deciding whether/how to add a user-goal (sea-level)
> requirements layer | Enables: acting on an uncontaminated ISO
> 29148/Cockburn review of the requirements landscape — what exists under
> other names, what altitude is missing, and a right-sized migration path |
> Update-trigger: never — point-in-time review; supersede with a newer
> review file

Produced by a fresh session (system specification engineer role, no prior
project context) on Michał's concern: "I didn't express functional
requirements: user goals, in/out-of-scope lists, fully-dressed use cases;
no features/epics organization." Verbatim report follows.

---

## 1. What actually exists (survey results)

The repo has far more requirements engineering than its author believes —
it is just wearing other names:

| Artifact found | What it is in 29148/Cockburn terms | Altitude |
|---|---|---|
| `docs/specs/process-coverage.md` (L1) | System scope + boundary definition + out-of-scope list; compressed ConOps negotiated with the stakeholder | **Kite** |
| Feature specs (12, per `docs/spec-convention.md`) | Requirements items with pre-written verifiable acceptance criteria; `spec-health.sh` mechanically fails specs standing on dead facts — textbook 29148 §5.2.5 verifiability, better enforced than most professional SRSs | Fish |
| ADRs 001–014 | Design decisions with alternatives considered | Fish |
| `docs/features-current-state.md` | As-built functional spec with strict status vocabulary, already organized by actor perspective | Fish |
| `docs/capability-map.csv` | ISO 25010 functional-completeness matrix, cells cite evidence ids | Fish |
| E2E goldens (`exercises/*/GOLDEN.md`) | Use-case *instances* — acceptance scenarios without the generalized use case above them | Clam/fish |
| Truth ledger + bd twins | Work items, premise-gated readiness; `roadmap-map.csv` stage column is the only upward trace | Clam |
| Pinned tests, key formulas | Detailed functional requirements as executable assertions | Clam |

One impostor: `kitchen-cam/docs/specs/user-context.md` is a raw pasted chat
transcript sitting in a specs directory — ironically the closest thing to a
user-goals document. Archive or rewrite it.

## 2. Assessment — the altitude profile

| Cockburn level | State |
|---|---|
| Cloud (why the business exists) | Implicit only (L1 Intent + memory note); one paragraph would fix it. Minor gap |
| Kite (business processes) | **Exists and is good** — the L1 stage map with in/out decisions |
| **Sea (user goals)** | **Missing. The real gap.** Nothing states: actor X, in situation Y, achieves goal Z — and what happens when it goes wrong. No actors, no triggers, no extensions |
| Fish (subfunctions) | Abundant: specs, ADRs, capability map |
| Clam (detail) | Exemplary: formulas in tests, goldens, evidence commands |

The profile is an hourglass with the middle missing: excellent kite,
world-class clam, hollow sea.

**Where the missing sea level already hurts:** G8 (drawer order, scrap-risk,
kuchnie-92j) is precisely an extension clause that was never written —
"3a. order ambiguous → system rejects or normalizes". It was found
empirically by an exercise instead of analytically by a use case. Same for
the missing single buildability verdict (tr-00421995) — an unwritten main-
scenario step. Cockburn's dictum that *extensions are where the
requirements hide* is demonstrated live in this repo's own gap log.

**Is the self-diagnosis accurate?** Half right, half too harsh:
- "No in/out-of-scope lists" — factually wrong; process-coverage.md is one
  of the cleanest scope artifacts in a small project. But they are
  feature-shaped, not goal-shaped.
- "No fully-dressed use cases" — correct; zero exist.
- "No vertical slices" — too harsh; golden-first exercises ARE deliberate
  vertical slicing.
- "No methodology" — false; development-process.md §6 is a coherent,
  mechanically-gated methodology.

Net: the disease is not disorganization — it is a **missing altitude level
(sea)** and a **missing upward trace** (work items point at stages, not at
user goals).

## 3. Proposed right-sized structure

### 3.1 Actors (Michał's hats) and goals

| Actor | Goals the system evidently serves |
|---|---|
| Salesperson (stage 1) | Client decor session on realistic preview → decor selection set |
| Surveyor (stage 2) | Capture a measurement visit attached to a project |
| Designer (stages 3–4) | Room → cabinet layout the production side consumes without re-typing |
| Production engineer (stages 4, 6–8) | Frozen design → trusted cut list, drilling, DXF pack |
| Purchaser (stages 5, 9) | Order exactly the boards/edging/hardware a job needs at current prices |
| Assembler (stage 8, later) | Assemble each cabinet from a per-cabinet sheet |

Secondary: Client, cutting & edging service (stage-6 CSV contract IS its
interest codified), supplier, and the AI agent as maintenance actor.

### 3.2 Use-case inventory — who gets full dress

Fully dressed only where extensions carry money/scrap risk (5):

1. **UC-2 Produce the production pack** (Production engineer) — the central
   flow; worked example below
2. **UC-1 Quote a kitchen** (Salesperson/Designer) — estimate-grade,
   distinct from UC-2
3. **UC-4 Order materials for a job** (Purchaser) — mostly unbuilt
   (wk-593a317b, G11, G13); dressing it now IS the requirements work
4. **UC-3 Run a first-visit decor session** (Salesperson + Client)
5. **UC-6 Open and thread a project** (all hats) — the Project spine
   (wk-02a62298); dressing it defines "artifact reference" per stage

Casual (one line each): price-file import, mirror refresh, catalog
maintenance, handover archive, assemble-from-sheet (defer), worktop BOM
position (subfunction of UC-1/UC-4, not a goal).

### 3.3 Worked example — UC-2 fully dressed (abridged; steps marked)

Primary actor: Production engineer · Scope: kuchnie system (hb5 + cutting
service external) · Level: sea · Trigger: design freeze.
Stakeholders: owner (no scrap — severity rule: wrong drill row > missing
BOM line; margin), cutting service (stage-6 CSV contract, grain), client,
supplier (SKU-resolvable lines).
Minimal guarantees: no partial artifact mistaken for complete; every hand
re-entry GapLogged; nothing emitted for undecomposable types.
Success guarantees: rozrys + CNC/DXF + priced BOM from ONE decomposition of
ONE Kitchen object, validation passed.

Main success scenario (⚠ = not yet supported):
1. Adapter extracts cabinet envelopes from .blend — tr-3bb325f8
2. System identifies type + config from the scene — ⚠ wk-81a47ab8
3. Michał completes parameters; system normalizes drawer order regardless
   of entry direction — ⚠ G8 / kuchnie-92j
4. Decompose to panels (dims, edging, grain, ops) — flagship types ok,
   door/wall partial (capability-map.csv)
5. System issues a single buildability verdict — ⚠ tr-00421995
6. Emit rozrys per stage-6 contract — ok; Długość-orientation decision open
7. Emit CNC list + per-panel DXF — ok for flagship types
8. Priced BOM by role + rules engine — ok; ⚠ G13 hardware understated,
   G11 edging not orderable
9. Upload to e-rozkrój / send DXF — out of system by design

Extensions: 2a undecomposable type → ERP estimate line, excluded from
rozrys with marker (⚠ exclusion not enforced) · 3a NL/height violation →
validate() rejects (ok) · 4a decor unresolvable → hand step, gap-logged ·
5a verdict FAIL → no artifacts, findings by scrap-severity (⚠) · 6a grain
pins orientation (ok, tr-15d48651) · 8a unpriced material → flag lines
instead of silent under-quote (⚠ flagging missing).

Note: steps 2, 3, 5 and extensions 2a/5a/8a are EXACTLY the open backlog.
The use case doesn't add work — it gives existing work its requirement, and
shows the buildability verdict is a main-scenario step, not a P3 cleanup.

### 3.4 Taxonomy stack — wiring, not bureaucracy

```
Actor + goal   → docs/specs/use-cases.md    (ONE file: actor table, 5 dressed + casual list)
Use case UC-N  → feature spec "Serves: UC-N" line
Feature spec   → wk-/kuchnie-* work items   (existing)
Work item      → commit / pinned test / tr- (existing, excellent)
```

- `roadmap-map.csv` gains a `uc` column → dashboard gets a
  "roadmap by user goal" view for free
- `spec-health.sh` gains one WARN: feature spec with no `Serves: UC-` line
- **Do NOT** add bd epics/parents (feature spec already plays the epic
  role; two homes fork), **do NOT** write a separate SRS (the union of
  existing artifacts IS the SRS, and it is gated)

### 3.5 Migration path

1. `docs/specs/use-cases.md` — actor table + casual list (~1h, mostly
   extraction). Archive user-context.md in the same commit. Unblocks a
   routing vocabulary: "which UC does this serve?"
2. Fully dress **UC-2** with real ids. Unblocks re-prioritization by
   requirement (G8 + buildability verdict sit ON the main success scenario
   of the central flow — arguably above their current P2/P3).
3. Fully dress **UC-4** BEFORE the purchasing epic starts + wire the `uc`
   column and spec-health WARN. Cheapest requirements work in the plan:
   extensions like "unknown SKU in price file" and "edging must be
   orderable (G11)" written before implementation.

## 4. Verdict

Directionally right, materially too harsh — and the implied prescription
(adopt a methodology, build an epic hierarchy) would treat the wrong
disease. The repo has stronger fish/clam-level requirements discipline than
most funded teams. What it genuinely lacks is Cockburn's sea level — named
actors, goal-shaped use cases, systematically examined extensions — which
is why failure-path requirements keep being discovered at the
saw-simulation stage instead of on paper. Ranked: (1) write
`docs/specs/use-cases.md` (actor table, 5 dressed + casual list) under the
existing ledger-wired convention and let it be where feature routing
starts; (2) dress UC-2 and UC-4 first — their extensions are literally the
open scrap-risk and margin-risk backlog — then re-rank bd priorities
against the main success scenario; (3) wire upward traceability
mechanically (uc column, `Serves:` line, one spec-health WARN) and refuse
the rest of the ceremony: no bd epics, no separate SRS, no per-UC files
beyond the five that earn full dress.
