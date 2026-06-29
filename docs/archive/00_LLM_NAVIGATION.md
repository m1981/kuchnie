# 00 — LLM Navigation Index

> **AGENT: READ THIS ENTIRE FILE BEFORE RESPONDING. IT IS SHORT.**
>
> This file exists so any LLM session — fresh or stale — can answer "where do I look for X?" in one hop.
>
> If your answer would contradict this file, your answer is wrong. Re-read this file.

---

## 0. Who You Are (Agent Role Statement)

You are assisting a **solo developer + carpenter** in Wrocław, Poland, building a kitchen design and manufacturing system. The system is composed of **five bounded contexts** (apps). The developer is using LLMs to write code. You are one of those LLMs.

You will follow the **anti-hallucination rules** at the bottom of this file. You will **not invent** terms, contexts, or features. You will **read before you write**.

---

## 0.1 Repository Layout (read this first)

This project spans **two physical repositories**:

| Repo | Role | Touch policy |
|---|---|---|
| `/Users/michal/PycharmProjects/kuchnie/` | **Project root.** Contains all our planning (`docs/`, `features/`) and all our code (`src/kuchnie_core/`, `kitchen-cad/`, `kitchen-app/`, `catalog/`, future `kitchen-render/`). All path references in specs and ADRs are relative to **this directory**. | Owned. Edit freely. |
| `/Users/michal/PycharmProjects/home_builder_5/` | **External Blender addon.** Community-maintained third-party plugin. Lives in its own git repo. | **READ-ONLY.** Never edit. See Rule 4. |

> When a spec says `src/kuchnie_core/foo.py`, it means `/Users/michal/PycharmProjects/kuchnie/src/kuchnie_core/foo.py`. Never `home_builder_5/src/...` (no such path exists).

Note: `kuchnie/docs/` also contains a **legacy planning set** (`00-brief.md`, `ROADMAP.md`, `adr/001-008-*.md`, `design-concerns.md`) from earlier work. Those are historical context. The canonical current planning is the numbered files (`00_LLM_NAVIGATION.md` through `05_*.md`, `GLOSSARY.md`, `PHASES.md`) and the per-feature folders in `features/`.

---

## 1. The Map (where every kind of information lives)

| Question | Read this file | Section/Anchor |
|---|---|---|
| How is the system structured? | `docs/01_architecture.md` | High-level layers, plugin internals |
| What patterns did we steal from commercial CAD? | `docs/02_pattern_analysis.md` | Pattern matrix |
| Where does a new pattern/feature physically live? | `docs/03_implementation_placement.md` | Decision matrix + per-pattern verdict |
| How do we work? Process? Templates? | `docs/04_solo_dev_process.md` | Bounded contexts + workflow |
| What does a TERM mean? | `docs/GLOSSARY.md` | Alphabetical, with "Not to be confused with" |
| What features exist? What state? | `features/INDEX.md` | Table of all features |
| Why was an architectural decision made? | `features/F00X/adr.md` | One ADR per feature |
| What is the next thing to build? | `docs/PHASES.md` | Find current phase → first `proposed` feature |
| How do I write a new feature? | Copy `features/TEMPLATE/` | Fill `spec.md`, etc. |
| What's "done" for the current phase? | `docs/PHASES.md` | Gate criteria checklist |

---

## 2. The Five Bounded Contexts (memorize the names)

| Context | Repo location | Owns the words |
|---|---|---|
| **Catalog** | `catalog/` | Decor, Edge, Pairing, Producer, Variant |
| **Domain Core** | `src/kuchnie_core/` | Kitchen, Row, CabinetInstance, ConstructionMethod, Recipe, Panel, SubAssembly |
| **CAD / Manufacturing** | `kitchen-cad/` | DrillPoint, EdgeBand, CutPiece, MachiningFeature, CSV/DXF export |
| **Web Configurator** | `kitchen-app/` | Project, CabinetUI, RowUI, BOM, CostEstimate |
| **Render Adapter** | `kitchen-render/` (new in F007) | Scene, WallPlacement, Texture, RenderPreset |
| **Blender Plugin (external)** | `home_builder_5/` (separate repo, untouched) | Its own vocabulary; not exposed to our domain |

> When you see a term, look up which context owns it. The same word in different contexts means different things. **Cross-context translation lives in adapters, never in concepts.**

---

## 3. Anti-Hallucination Rules (NON-NEGOTIABLE)

These rules are why this file exists. Violating them generates drift that costs the solo dev real time.

### Rule 1 — Glossary or Stop

If a domain term is not in `docs/GLOSSARY.md`, **stop and ask the user**. Do not invent a meaning. Do not borrow a meaning from another project.

### Rule 2 — Feature Folder or Doesn't Exist

If a feature is not in `features/INDEX.md`, **it does not exist yet**. Do not assume it exists. Do not propose code that depends on it. Propose creating the feature folder first.

### Rule 3 — Single Context per Feature

If your proposed change touches **more than one bounded context**, you have either:
- Misidentified the primary context (re-read § 2), or
- The feature is wrongly scoped (apply the Change Locality Test in `04_solo_dev_process.md`).

Default response when in doubt: "This appears to touch contexts A and B. Should we split it into two features, or is one of them just a consumer of a published contract?"

### Rule 4 — Plugin is External, Not Driven

The Blender plugin at `home_builder_5/` is a **community-maintained third-party addon in a separate repo**. We do not edit it, extend it, drive it, or import from it. Per F007's accepted ADR, our render adapter (`kitchen-render/`) uses standalone `bpy` scripts and builds its own scene — it does **not** load the plugin, feed it `kitchen_config.yaml`, or touch its config.

If a user asks you to "add X to the plugin," your first response is: "`home_builder_5/` is external and untouched. Can this live in `kuchnie_core`, `kitchen-cad`, or `kitchen-render` instead? Per F007 ADR and `03_implementation_placement.md`, the plugin is not part of our system."

### Rule 5 — Pure Python in Core

`src/kuchnie_core/` has **no Blender imports, no Reflex imports, no FastAPI imports**. It is pure Python + Pydantic + PyYAML. If your proposed code in core imports `bpy` or `reflex`, it belongs in another context.

### Rule 6 — Read Before You Write

Before generating code for a feature, read **in this order**:
1. `docs/GLOSSARY.md` — for the terms involved
2. `features/F00X/spec.md` — for the scope
3. `features/F00X/adr.md` — for the decision (if accepted)
4. `docs/03_implementation_placement.md` — for the placement rule

If any of these don't exist for the feature you're being asked about, **say so and propose creating them first**.

### Rule 7 — Mention Affected Glossary Terms

When you propose new code that introduces a new domain class or concept, your response **must include**: "This introduces the following new term(s): [X, Y]. Please add to `docs/GLOSSARY.md` in this commit." Don't let the developer forget.

### Rule 8 — Status File is Truth

If `features/F00X/status.md` says `status: blocked`, do not propose implementation steps for F00X. Propose unblocking steps. If it says `status: done`, do not modify the implementation without proposing a new feature (F00Y) that supersedes it.

---

## 4. Quick Decision Trees

### "User asks me to add a feature"

```
1. Is it in features/INDEX.md?
   ├── YES → open features/F00X/spec.md and proceed
   └── NO  → propose: "Let's create features/F0NN-<name>/ from TEMPLATE/.
                       I'll draft spec.md based on your description."

2. Does it touch > 1 bounded context?
   ├── YES → apply Rule 3. Re-scope or split.
   └── NO  → identify primary context per § 2.

3. Are the terms in GLOSSARY.md?
   ├── YES → proceed
   └── NO  → apply Rule 1. Add terms first.

4. Is there an ADR?
   ├── YES (accepted) → follow the decision
   ├── YES (proposed) → ask if it's been decided
   └── NO  → ask if this needs one (architectural? cross-context? irreversible?)
```

### "User asks 'where should X go?'"

```
1. Open docs/03_implementation_placement.md
2. Find the matching pattern in § Decision Matrix
3. If no match, fall back to:
   - Domain truth? → kuchnie_core
   - Manufacturing output? → kitchen-cad
   - User-facing UI? → kitchen-app
   - 3D render? → render adapter (NOT plugin internals)
   - Material data? → catalog/
```

### "User asks 'what does X mean?'"

```
1. Open docs/GLOSSARY.md
2. If X is there → quote the definition + file of record
3. If X is NOT there → ask: "I don't see X in the glossary.
   Should we add it? In which bounded context?"
```

---

## 5. What You DO NOT Do

Explicit list to prevent helpful-but-wrong behavior:

- ❌ Do not propose splitting `kuchnie_core` into multiple packages without an ADR.
- ❌ Do not propose adding a database to `kuchnie_core` (it's pure Python + files).
- ❌ Do not propose adding async/await to `kuchnie_core` (synchronous by design).
- ❌ Do not propose modifying files inside `home_builder_5/` (the plugin).
- ❌ Do not propose new bounded contexts (we have five; that is the design).
- ❌ Do not propose "let's also do Y while we're at it" — apply MoSCoW from feature spec.
- ❌ Do not propose RFCs or design docs separate from ADRs.
- ❌ Do not propose Docker / Kubernetes / cloud deploy for v1.0 (solo dev, local).
- ❌ Do not invent file paths. If a file isn't referenced in docs, ask before assuming.

---

## 6. The One Rule Above All

> **Every commit must leave the docs in a consistent state.**
> - New term in code → entry in `GLOSSARY.md`
> - Cross-context decision → ADR in `features/F00X/adr.md`
> - Feature done → `status.md` updated
> - Phase complete → `PHASES.md` checklist signed off

If your proposed commit would violate this, your proposal is incomplete. Add the doc changes to the same commit.

---

## 7. Where to Start Right Now

1. Read `docs/GLOSSARY.md` (5 min).
2. Read `features/INDEX.md` (2 min).
3. Read `docs/PHASES.md` to know the current phase (3 min).
4. Open the `proposed` feature in the current phase: read its `spec.md`.
5. Ask: "I've read the navigation, glossary, index, phases, and F00X spec. Ready for instructions."

That's the bootstrap. Don't skip it.
