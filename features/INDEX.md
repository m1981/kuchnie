# Features Index

> **LLM Agents: Start Here.**
>
> For any question about a feature, open `features/F00X/spec.md` first, then `adr.md` if architectural reasoning is needed.
>
> If a feature is not in the table below, **it does not exist yet**. Propose creating its folder before discussing implementation.

---

## Status Legend

| Symbol | Meaning |
|---|---|
| 🔵 | In progress |
| ⏳ | Proposed (not started) |
| ✅ | Done (gate-criterion passed) |
| 🛑 | Blocked (see `status.md`) |
| ❌ | Cancelled / superseded |

---

## Feature Table

| ID | Title | Phase | Primary Context | Touches | Status | Spec | ADR |
|---|---|---|---|---|---|---|---|
| F001 | Construction Method | 1 | Core | Core, CAD (consumer) | 🔵 | [spec](F001-construction-method/spec.md) | [adr](F001-construction-method/adr.md) |
| F002 | Recipe Engine | 2 | Core + CAD | Core, CAD | ⏳ | [spec](F002-recipe-engine/spec.md) | [adr](F002-recipe-engine/adr.md) |
| F003 | Template Registry | 3 | Core | Core | ⏳ | [spec](F003-template-registry/spec.md) | [adr](F003-template-registry/adr.md) |
| F004 | Validation Gates | 4 | Core | Core | ⏳ | [spec](F004-validation-gates/spec.md) | [adr](F004-validation-gates/adr.md) |
| F005 | Material Resolver | 5 | Catalog + Core | Catalog, Core | ⏳ | [spec](F005-material-resolver/spec.md) | [adr](F005-material-resolver/adr.md) |
| F006 | Web Sidebar | 6 | Web | Web | ⏳ | — | — |
| F007 | Blender Adapter | 7 | Render | Render (NEW context) | ⏳ | [spec](F007-blender-adapter/spec.md) | [adr](F007-blender-adapter/adr.md) |
| F008 | CLI Cut List / DXF | 8 | CAD | CAD | ⏳ | [spec](F008-cli-export/spec.md) | [adr](F008-cli-export/adr.md) |

---

## Current Focus

**🔵 F001 — Construction Method** (Phase 1)

Read this before doing anything else: `features/F001-construction-method/spec.md`

---

## Backlog (post-v1.0, NOT a TODO list)

Things that have come up but are explicitly **out of scope** for v1.0. Capturing here prevents re-discovery and prevents agents from proposing them prematurely.

| Idea | Why deferred |
|---|---|
| Multi-room projects | v1.0 = one kitchen per project |
| Island cabinets | Out of scope per use case |
| Slanted walls | Out of scope per use case |
| Nesting optimization | CNC company does this |
| Auth / multi-user | Solo developer, local use |
| Mobile-native app | Web on iPad is sufficient |
| AR / VR preview | Not in v1.0 budget |
| Solid wood doors with grain matching | Not in v1.0 budget |
| Curved cabinets | Out of scope per use case |
| LED routing / electrical layout | LED grooves only, not full electrical |

---

## How to Add a New Feature

1. **Stop.** Is it actually a new feature, or an addition to an existing one? Adding to an existing feature is usually wrong (it's scope creep). Default: create a new feature.

2. **Pick the next ID.** If the last feature is F008, your new one is F009.

3. **Create the folder.**
   ```
   cp -r features/TEMPLATE features/F009-<short-slug>
   ```

4. **Fill `spec.md`.** Use the Job Story format. Pick the **primary bounded context** (one only). Run the Change Locality Test.

5. **Update this `INDEX.md`** — add a row to the table with status `⏳`.

6. **Update `docs/PHASES.md`** — assign the feature to a phase, or mark it as backlog if it's post-v1.0.

7. **Commit.** Message: `feature: add F009 — <title>`.

8. **Do not start coding** until the spec is reviewed (by you, or by another LLM session reading the spec cold and confirming it makes sense).

---

## How to Close a Feature

1. All checkboxes in `tasks.md` are ticked.
2. `status.md` updated: `status: done`, `completed: <date>`.
3. `docs/GLOSSARY.md` contains every new term the feature introduced.
4. ADR is `Accepted` (if one exists).
5. The relevant phase's gate criteria in `docs/PHASES.md` are re-checked — does this feature complete the phase?
6. Update this `INDEX.md` — change status to ✅.
7. Commit. Message: `feature: close F009 — <title>`.

---

## Cross-references

- **Phases & gates:** `docs/PHASES.md`
- **Placement decisions:** `docs/03_implementation_placement.md`
- **Process rules:** `docs/04_solo_dev_process.md`
- **Glossary:** `docs/GLOSSARY.md`
- **Template:** `features/TEMPLATE/`
