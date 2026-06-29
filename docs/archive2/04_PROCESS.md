# Solo Dev Working Method — Anti-Drift Process for an LLM-Augmented Workflow

> **Purpose:** Keep one developer + multiple LLM sessions from drifting on a multi-subsystem kitchen-design system. Every feature must have a single entry point that an LLM agent can find in ≤ 2 hops.
>
> **Companion docs:** `00_README.md` (system overview), `01_DECISIONS.md` (architectural decisions), `05_PATTERN_GOLD.md` (CAD/CAM patterns), `06_AUDIT_EVIDENCE.md` (cold-execution evidence base for `01_DECISIONS.md`).
>
> **Reading time:** 15 minutes. **Setup time:** 1 day. **Payoff:** every feature thereafter.

---

## 0. MANDATORY Pre-Planning Checklist (added 2026-06-29)

**Before any architectural diagram, spec, or feature plan, the LLM session MUST execute the following. Three audit misses in this project's history (see `06_AUDIT_EVIDENCE.md`) were all caused by skipping this.**

```
1. ls $PROJECT_ROOT
2. For each sibling directory, count Python LOC:
     find $DIR -name '*.py' -not -path '*/.venv/*' -not -path '*/__pycache__/*' \
       -not -path '*/node_modules/*' | xargs wc -l | tail -1
3. For every dir > 1000 LOC:
     a. pysum $DIR > /tmp/audit/${dir}_pysum.md
     b. py-diagram $DIR --format token --skip __pycache__ tests > /tmp/audit/${dir}_diagram.txt
     c. head -40 $DIR/README.md  (if present)
     d. grep -E '^class (Cabinet|Material|Panel|Recipe|Kitchen|Decor)' $DIR -r
     e. Note the import direction with the rest of the system:
          grep -rln 'from kuchnie_core\|from kitchen_cad\|from kitchen_plugin\|from compositor' $DIR
4. The phrases "I assume this is empty", "external", "out of scope",
   "scaffolding only" are FORBIDDEN without evidence from step 3.
5. No planning artifact (architecture diagram, spec, ADR, roadmap) may be
   written until steps 1-3 have been completed and documented in the chat.
```

**Why this is mandatory.** Directory names are unreliable signals:
- `kitchen-plugin/` is NOT a Blender addon — it's a 10K-LOC standalone Python project. (Audit miss #1.)
- `krono-compositor-mvp/` was missed entirely until specifically queried. (Audit miss #2.)
- `catalog/`, `kitchen-app/`, `kitchen-cad/` all looked like "empty scaffolding" — they have 6–8K LOC each. (Audit miss #3.)

If you violate this rule and produce a planning artifact, that artifact is **automatically wrong** and must be discarded.

---

## 1. What from the Methods List Actually Applies

You gave a long menu. Here's the honest filter for a solo dev with LLM agents.

### ✅ Keep — high ROI for solo dev

| Method | Why it fits |
|---|---|
| **Bounded Contexts** | You already have 5 apps. Without this, "Cabinet" means 3 different things and LLMs hallucinate. |
| **Context Mapping** | Forces you to name *how* apps talk (sync? event? file?). |
| **Subdomain Classification** (Core / Supporting / Generic) | Solo dev cannot build everything. This tells you what to buy/skip. |
| **Ubiquitous Language Glossary** | The #1 anti-drift artifact for LLM-augmented work. |
| **Job Stories** ("When… I want to… so I can…") | Outcome-driven; resists UI-creep. |
| **Change Locality Test** | The solo dev's friend: "If I edit > 1 app for this feature, the scope is wrong." |
| **Data Ownership Rule** | Stops you from writing to the same data from 3 apps. |
| **ADR (lightweight, 1 page)** | Future-you and future-LLMs need to know *why*. |
| **C4 Container view** | One diagram, always up-to-date, no fluff. |
| **MoSCoW per phase** | Forces cuts when you inevitably scope-creep. |

### ⚠️ Adapt — useful but trim hard

| Method | How to adapt |
|---|---|
| **Use Case Analysis** | Keep the *scope* line ("subsystem of record") — drop the rest. You already wrote 3 use cases; that's plenty for v1.0. |
| **Shape Up appetite** | Use the 6-week ceiling as a *forcing function*, not a process. If a feature can't fit, cut. |
| **C4 below Container** | Skip Component/Code diagrams. The code IS the diagram. |

### ❌ Drop — overkill or anti-pattern for solo

| Method | Why drop |
|---|---|
| **Event Storming** | Needs ≥ 3 stakeholders. Solo storming is just brainstorming with stickies. |
| **Conway's Law / Team Topologies** | You are one team. The "law" trivially holds. |
| **SAFe / Spotify / SoR squads** | Enterprise scaffolding for problems you don't have. |
| **Two-Pizza Test** | N/A. |
| **RFCs (heavy)** | An ADR *is* your RFC. Don't run two systems. |
| **User Story Mapping (full board)** | Job Stories + your 3 use cases cover this. |
| **Decompose by Transaction Boundary** | You have one ACID boundary per app already (SQLite, files). |

---

## 2. The Four Artifacts You Need (and Nothing Else)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1.  CONTEXT MAP            (one page, one diagram)             │
│  2.  UBIQUITOUS LANGUAGE    (one glossary, MD table)            │
│  3.  FEATURE FOLDER         (one per feature: spec + ADR + tasks)│
│  4.  PHASE GATE CHECKLIST   (one per phase, signed off by you)  │
│                                                                 │
│  Everything else is noise.                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Bounded Contexts — Name the Five Apps

Each app is a **bounded context**. Inside, words have one meaning. Across boundaries, translate.

| Context | Code Location | Ubiquitous Language | Core/Supporting/Generic |
|---|---|---|---|
| **Catalog** | `catalog/` | Decor, Edge, Pairing, Producer, Variant | **Generic** (data import only — buy/use vendor data) |
| **Domain Core** | `src/kuchnie_core/` | Kitchen, Row, CabinetInstance, ConstructionMethod, Recipe, Panel, SubAssembly | **Core** ← your competitive advantage |
| **CAD / Manufacturing** | `kitchen-cad/` | Panel, DrillPoint, EdgeBand, CutPiece, MachiningFeature | **Core** (CSV/DXF for Polish CNC = no SaaS for this) |
| **Web Configurator** | `kitchen-app/` | Project, CabinetUI, RowUI, BOM, CostEstimate | **Supporting** (necessary but commoditized — Reflex is fine) |
| **3D Engineering Render** | `kitchen-plugin/` | Cabinet (placement), Wall, Room, Layout, CabinetGeometry, ManifestValidator | **Supporting** (Blender does the work; we own the scene setup) |
| **2.5D Live Render** | `krono-compositor-mvp/` | SceneCompositor, ZoneConfig, Pass | **Core** (real-time decor swap is the killer feature for UC1) |

> `home_builder_5/` is **external** — a sibling community-maintained Blender addon, GPL-licensed, **not in v1.0 scope**. See note at the end of § 0.

### Why this classification matters for a solo dev

- **Core (Domain + CAD):** Spend your engineering time here. This is what makes you faster/cheaper than competitors using PRO100.
- **Supporting (Web + Renderer):** Use frameworks (Reflex, Blender). Don't reinvent.
- **Generic (Catalog):** Pure import job. Write once, forget.

> **Rule:** When in doubt about where to spend a week → spend it on Core. If you're spending a week on Generic, something is wrong.

---

## 4. The Context Map (Stable Diagram, Living Doc)

```
                       ┌──────────────────────────────────┐
                       │       CATALOG (Generic)          │
                       │     Decors, Edges, Pairings      │
                       └────────────────┬─────────────────┘
                                        │
                                        │  Published Language
                                        │  (decor_id, edge_id — stable IDs)
                                        │
              ┌─────────────────────────▼─────────────────────────┐
              │             DOMAIN CORE (Core)                    │
              │             src/kuchnie_core/                     │
              │                                                   │
              │   • Kitchen, Row, CabinetInstance                 │
              │   • ConstructionMethod, Recipe, Template          │
              │   • SubAssembly, Panel, MaterialRef               │
              │   • Validation Gates 1-4                          │
              │                                                   │
              │   ── PUBLISHED LANGUAGE ──                        │
              │   kitchen_config.yaml schema (v1.0)               │
              └───┬───────────────────┬──────────────────┬────────┘
                  │                   │                  │
       Customer/  │       Customer/   │      Customer/   │
       Supplier   │       Supplier    │      Supplier    │
                  │                   │                  │
        ┌─────────▼─────┐    ┌────────▼──────┐    ┌──────▼─────────┐
        │  CAD (Core)   │    │  WEB (Support)│    │ RENDER (Support│
        │ kitchen-cad/  │    │ kitchen-app/  │    │  + Blender)    │
        │               │    │               │    │                │
        │ Conformist    │    │ Conformist    │    │ ACL (adapter)  │
        │ to core       │    │ to core       │    │ shields plugin │
        │               │    │               │    │ from your model│
        └───────────────┘    └───────────────┘    └────────────────┘
```

### Relationship Semantics (write these down once, never argue again)

| Edge | Pattern | Means |
|---|---|---|
| Catalog → Core | **Published Language** | Catalog publishes stable decor/edge IDs. Core never modifies catalog data. |
| Core → CAD | **Customer/Supplier (Conformist)** | CAD accepts core's model as-is. No translation. |
| Core → Web | **Customer/Supplier (Conformist)** | Web accepts core's model as-is. UI types wrap, don't redefine. |
| Core → 3D Render | **Customer/Supplier** | kitchen-plugin imports `kuchnie_core.Cabinet`/`Layout`, builds bpy scene from them. |
| Core → 2.5D Render | **Adapter** | `kuchnie_core.render.composite()` POSTs to compositor's FastAPI; subprocess for the offline bake. |
| Web ↔ Core | **Shared Kernel** (you only) | Same Python process, shared types via `kuchnie_core`. |

---

## 5. Ubiquitous Language Glossary (Anti-Hallucination Tool)

**Why this is the single most important file for LLM-augmented work:** LLM agents will *invent* meanings if you don't fix them. Put this file in every context window.

### Glossary template — fill once, keep alive

`docs/GLOSSARY.md`:

```markdown
# Ubiquitous Language

> When you see a term below, this is what it means **in this repo**.
> If you want a different meaning, you are in a different bounded context.
> Cross-context translation lives in adapters, not in concepts.

## Cabinet
- **Context:** Domain Core
- **Definition:** A `CabinetInstance` — placed instance of a `CabinetTemplate`
  with concrete dimensions, construction method, materials, and sub-assemblies.
- **Not to be confused with:**
  - `CabinetTemplate` (the "macro" / type definition)
  - `CabinetUI` (Web context — a wrapper for display)
  - Blender's `Cabinet` class (plugin context — geometry node container)
- **File of record:** `src/kuchnie_core/model.py::CabinetInstance`

## Construction Method
- **Context:** Domain Core
- **Definition:** Reusable specification of HOW a cabinet is built —
  thicknesses, joinery, back attachment, overlays. Independent of WHAT cabinet.
- **File of record:** `src/kuchnie_core/construction.py::ConstructionMethod`
- **ADR:** `features/F001-construction-method/adr.md`

## Panel
- **Context:** Domain Core (definition), CAD (manufacturing)
- **Definition:** A single rectangular piece of board with dimensions, material,
  edge banding, and machining operations. The atomic manufacturing unit.
- **File of record:** `src/kuchnie_core/model.py::Panel`

## Decor
- **Context:** Catalog
- **Definition:** A surface finish (e.g., "Kronospan U112 PM"). Identified by
  `decor_id` (str). Other contexts reference by ID only.
- **File of record:** `catalog/docs/architecture/02-pydantic-models.py::Decor`

## Row
- **Context:** Domain Core, Web
- **Definition:** A linear sequence of cabinets along one wall. v1.0 excludes
  islands and slanted walls.
- **File of record:** `src/kuchnie_core/model.py::Row`

## Recipe
- **Context:** Domain Core
- **Definition:** Declarative panel-derivation definition for a cabinet template.
  Stored as YAML, evaluated by `kitchen-cad`'s formula engine.
- **File of record:** `src/kuchnie_core/recipes/*.yaml`

## Sub-assembly
- **Context:** Domain Core
- **Definition:** A composable group inside a cabinet (drawer box, door pair,
  shelf bank). Contains panels + accessories.
- **File of record:** `src/kuchnie_core/model.py::SubAssembly`

## Project
- **Context:** Web only
- **Definition:** A customer engagement — name, address, kitchen, status.
- **NOT in Domain Core.** Core knows only `Kitchen`.

## (continue this list as terms appear)
```

> **Rule:** When you commit a new domain class, add it to the glossary in the same commit. No exceptions.

---

## 6. Feature Workflow — One Folder per Feature

Every feature gets a folder. LLM agents find everything in one place.

```
features/
├── INDEX.md                          ← table of all features + status
├── TEMPLATE/                         ← copy this to start a new feature
│   ├── spec.md
│   ├── adr.md
│   ├── tasks.md
│   └── status.md
├── F001-construction-method/
│   ├── spec.md                       ← Job Story + scope + acceptance
│   ├── adr.md                        ← Architectural decision + rejected alts
│   ├── tasks.md                      ← Checklist
│   └── status.md                     ← Current state (machine-readable)
├── F002-recipe-engine/
└── F003-template-registry/
```

### 6.1 Feature Spec Template (`spec.md`)

```markdown
# F00X — <Feature Name>

## Job Story
**When** I am [situation],
**I want to** [motivation/action],
**So I can** [outcome].

## Bounded Context
- **Primary:** <Catalog | Core | CAD | Web | Render>
- **Touched (with reason):** <list, must be ≤ 2 — see Change Locality Test>

## Subdomain Classification
- [ ] Core (competitive advantage)
- [ ] Supporting (necessary, commoditized)
- [ ] Generic (buy/skip)

## Data Ownership
- **Writes:** <which context owns the canonical write>
- **Reads:** <which contexts read projections>

## Scope (MoSCoW)
- **Must:**
  - …
- **Should:**
  - …
- **Could:**
  - …
- **Won't (this iteration):**
  - …

## Change Locality Test
- [ ] One context's code is edited.
- [ ] At most one published contract change (schema/event/API).
- [ ] If both fail → **STOP. Re-scope.**

## Acceptance
- [ ] Glossary updated.
- [ ] ADR written.
- [ ] Tests in primary context.
- [ ] Context map updated (if relationship changed).

## Out of Scope
- Explicitly list what this feature does NOT do.
- Anti-drift: prevents next LLM session from "helpfully" expanding scope.

## References
- Pattern: <link to 02_pattern_analysis.md section>
- Placement: <link to 03_implementation_placement.md section>
- Glossary terms introduced: [Term1, Term2]
```

### 6.2 ADR Template (`adr.md`) — 1 page max

```markdown
# ADR — F00X — <Decision>

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Superseded by F00Y

## Context
2-4 sentences. Why is this decision needed now?

## Decision
The thing we will do. Imperative voice.

## Alternatives Considered
| Option | Why rejected |
|---|---|
| A | … |
| B | … |

## Consequences
- **Positive:** …
- **Negative:** …
- **Neutral:** …

## Affected Files (canonical)
- `src/kuchnie_core/...`
- `features/F00X/...`

## LLM Hints
- When asked about <topic>, point here.
- Related ADRs: F00A, F00B.
```

### 6.3 Tasks (`tasks.md`)

```markdown
# F00X Tasks

## Implementation
- [ ] Define model in `src/kuchnie_core/...`
- [ ] Add to glossary: `Term1`
- [ ] Tests in `tests/core/...`
- [ ] Update `kitchen_config.yaml` schema
- [ ] Migrate existing YAML examples

## Cross-context impact (if any)
- [ ] CAD: read new field in `panel_calculator.py`
- [ ] Web: surface in Reflex state

## Done means
- [ ] All tests pass.
- [ ] Glossary committed.
- [ ] ADR accepted.
- [ ] `status.md` set to `done`.
- [ ] Phase gate checklist updated (if phase-completing).
```

### 6.4 Status (`status.md`) — Machine-readable

```yaml
feature_id: F001
title: "Construction Method as first-class entity"
status: in_progress   # proposed | in_progress | done | blocked | superseded
started: 2026-06-28
completed: null
blocked_by: []
supersedes: []
superseded_by: null
primary_context: kuchnie_core
touched_contexts: [kuchnie_core]
phase: 1
adr_status: accepted
glossary_terms: [ConstructionMethod, JoineryType, BackType]
```

> **Why YAML for status?** An LLM agent (or your future tool) can grep all `status.md` files to build a project dashboard without parsing prose.

---

## 7. The `features/INDEX.md` — LLM Entry Point

Single table, regenerable from `status.md` files.

```markdown
# Features Index

> **LLM Agents: Start Here.**
> For any question about a feature, open `features/F00X/spec.md` first,
> then `adr.md` if architectural reasoning is needed.

| ID | Title | Phase | Primary Context | Status | Spec | ADR |
|---|---|---|---|---|---|---|
| F001 | Construction Method | 1 | kuchnie_core | in_progress | [spec](F001-construction-method/spec.md) | [adr](F001-construction-method/adr.md) |
| F002 | Recipe Engine | 2 | kuchnie_core + cad | proposed | [spec](F002-recipe-engine/spec.md) | — |
| F003 | Template Registry | 3 | kuchnie_core | proposed | [spec](F003-template-registry/spec.md) | — |
| F004 | Validation Gates | 4 | kuchnie_core | proposed | [spec](F004-validation-gates/spec.md) | — |
| F005 | Material Resolver | 5 | catalog + core | proposed | [spec](F005-material-resolver/spec.md) | — |
| F006 | Web Sidebar | 6 | kitchen-app | proposed | [spec](F006-web-sidebar/spec.md) | — |
| F007 | Blender Adapter | 7 | render-adapter | proposed | [spec](F007-blender-adapter/spec.md) | — |
| F008 | CLI Cut List / DXF | 8 | kitchen-cad | proposed | [spec](F008-cli-export/spec.md) | — |
```

---

## 8. Phase Gates — What "Done" Means per Phase

From `03_implementation_placement.md`, you have an 8-week phased roadmap. Each phase ends with a **gate** — a checklist you sign off before starting the next.

`docs/PHASES.md`:

```markdown
# Phase Gates

## Phase 1 — Domain Foundations (Week 1)
**Goal:** `ConstructionMethod` and refactored `CabinetInstance` exist.

### Gate criteria (all must be true before Phase 2)
- [ ] F001 status = done
- [ ] Glossary has: ConstructionMethod, JoineryType, BackType, SubAssembly
- [ ] `kitchen_config.yaml` v1.0 schema published in `docs/schemas/`
- [ ] Round-trip test: load YAML → Pydantic → dump YAML → byte-identical
- [ ] One worked example: `examples/kitchen_nowak.yaml`
- [ ] `01_architecture.md` Context Map reflects new entities

## Phase 2 — Recipe Engine (Week 2)
**Goal:** YAML recipes drive panel calculation. `eval()` removed.

### Gate criteria
- [ ] F002 status = done
- [ ] At least 5 recipes converted: base_door_single, base_drawer_3, wall_door,
      tall_pantry, corner_diagonal
- [ ] `asteval` (or equivalent) replaces `eval()` in `recipe_loader.py`
- [ ] Each recipe has a unit test against a fixture cabinet
- [ ] Performance: 100 cabinets compute in < 2s

## Phase 3 — Templates (Week 3)
…
```

> **Rule:** Do not start Phase N+1 until Phase N gate is green. No exceptions for "small leftover work."

---

## 9. LLM Navigation Index — "Looking for X? Go to Y"

Put this at `docs/00_LLM_NAVIGATION.md` so it's read first.

```markdown
# LLM Navigation Index

> **Agents: read this before answering any question.**

## "How is the system structured?"
→ `docs/01_architecture.md` (high-level + plugin internals)

## "What patterns are used and why?"
→ `docs/02_pattern_analysis.md` (Polyboard / Winner Flex / etc.)

## "Where does a new feature/pattern live?"
→ `docs/03_implementation_placement.md` (decision matrix)

## "How do we work? What's the process?"
→ `docs/04_solo_dev_process.md` (this file family)

## "What does <term> mean?"
→ `docs/GLOSSARY.md`

## "What features exist? What's their state?"
→ `features/INDEX.md`, then `features/F00X/status.md`

## "Why was decision X made?"
→ `features/F00X/adr.md`

## "What's the next thing to build?"
→ `docs/PHASES.md` → find current phase → find first `proposed` feature

## "How do I write a new feature?"
→ Copy `features/TEMPLATE/` to `features/F0NN-name/`, fill in spec.md

## "Where is the boundary between Catalog and Core?"
→ `docs/04_solo_dev_process.md` § Context Map

## "Can the plugin change to support X?"
→ Almost certainly NO. The plugin is a renderer. See `03_implementation_placement.md` § "What goes INTO the Blender plugin"

## Anti-Hallucination Rules
1. If a term isn't in `GLOSSARY.md`, **ask the user** — do not invent.
2. If a feature isn't in `features/INDEX.md`, it does not exist yet.
3. If two contexts seem to claim the same data, **stop and read § Data Ownership** in this file.
4. Never propose code that touches > 1 bounded context without first consulting the Change Locality Test.
```

---

## 10. The Five Anti-Patterns You Will Hit (Solo Dev Edition)

| Anti-pattern | Solo-dev symptom | Cure |
|---|---|---|
| **God subsystem** | `kitchen-app` accumulates everything because Reflex is easy. | Apply Data Ownership Rule. If `kitchen-app` writes domain data, it's wrong. |
| **Process-shaped subsystems** | Building a "BOMService" because BOM is one workflow. | Capability mapping — BOM lives in `kuchnie_core` (capability), not its own service. |
| **Distributed monolith** | One feature touches 3 apps + plugin. | Change Locality Test. Re-scope. |
| **Shared database as integration** | Reflex app and CLI both write to same SQLite. | One writer per data store. CLI reads via core, doesn't share writes. |
| **Feature-by-LLM-committee** | Each LLM session re-decides the architecture. | Glossary + ADRs in the prompt context. ALWAYS. |

---

## 11. The Decision Cheat Sheet — Tape This to Your Monitor

When a new feature arrives, in order:

```
1. Glossary check: are the terms defined? If no → define first, code later.

2. Bounded context: which ONE context primarily owns this?
   (If the answer is "two", you're describing two features.)

3. Subdomain: is this Core / Supporting / Generic?
   • Core      → invest, write tests, make it excellent.
   • Supporting → use a framework, ship pragmatic.
   • Generic    → buy / use existing / skip.

4. Data ownership: which context writes the canonical data?
   That context owns the feature. Period.

5. Change locality: edit ONE context + ONE contract change.
   If you can't, re-scope.

6. MoSCoW the scope. Cut "Should" to "Could" first; cut "Could" to "Won't" next.

7. Open features/TEMPLATE/, create features/F0NN/, fill spec.md.

8. Write ADR (1 page) IF the decision is architectural (cross-context,
   irreversible, or rejecting an obvious alternative).
   For purely local choices, skip the ADR.

9. Implement. Update glossary in the same commit as new types.

10. Tick the phase gate checklist if this feature completes a phase.
```

---

## 12. What This Process Gives You (and What It Costs)

### Gains

- **LLM agents have one entry point** (`docs/00_LLM_NAVIGATION.md`) and a glossary that prevents hallucination.
- **Drift is auditable** — every change traces back to a feature folder, an ADR, and a glossary entry.
- **Solo dev cognitive load is bounded** — you only need to keep 4 artifacts in mind at any time.
- **Onboarding a contractor later** takes ~ 1 day (read 5 docs + glossary, then pick a feature folder).

### Costs

- **~ 30 min per feature in process overhead** (spec + ADR + glossary). Acceptable if features take days.
- **You will be tempted to skip the glossary update.** Don't. That's where drift starts.
- **First feature feels heavy.** Phase 1 will take 1.5x longer than Phase 2 because you're building the muscle.

---

## 13. Bootstrap Checklist (Day 1, Before Any Code)

Do these in order. Each takes < 1 hour.

- [ ] Create `docs/GLOSSARY.md` with the 8 terms in § 5 above.
- [ ] Create `docs/00_LLM_NAVIGATION.md` from § 9 above.
- [ ] Create `docs/PHASES.md` with the 8 phases from `03_implementation_placement.md`.
- [ ] Create `features/INDEX.md` with the 8 feature rows from § 7 above.
- [ ] Create `features/TEMPLATE/` with the four files from § 6 above.
- [ ] Create `features/F001-construction-method/` from the template.
- [ ] Fill `features/F001/spec.md` using your Phase 1 plan.
- [ ] Commit. **Now** write code.

---

## 14. What I'm NOT Recommending (and Why)

To be explicit, so future LLM sessions don't reintroduce them:

- **No epic/sprint hierarchy.** You have phases and features. Two levels are enough.
- **No story points.** Days/hours is fine for one person.
- **No standups, retros, ceremonies.** You'll know if you're stuck.
- **No separate "RFC" process.** ADRs are your RFCs.
- **No C4 Component or Code diagrams.** The code is the diagram.
- **No event storming.** You're not discovering a domain; you've already analyzed it (docs 01-03).
- **No microservices.** Your 5 "apps" are processes on one machine. Keep it that way.

---

## 15. The One Rule Above All Others

> **Every commit must leave the docs in a consistent state.**
> If you introduce a term, it's in the glossary.
> If you make a cross-context decision, it's in an ADR.
> If a feature is done, its `status.md` says so.
>
> An LLM agent reading the repo at any commit should see a *coherent* system,
> not a half-thought.

This is the only discipline that matters. Everything else in this document exists to make this rule easy to follow.
