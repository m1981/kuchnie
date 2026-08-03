# Agent Guide — kuchnie-core

Read this before making changes. It's short on purpose.

> **Session start:** open `STATUS.md` (generated dashboard, five PM
> questions — §3 names the next work and its start commands), then
> `scripts/truth ready`. **Vocabulary:** any unknown term or letter code
> (L/G/M/R/UC/P families) → `docs/GLOSSARY.md`; if it's not there, ask —
> never invent a meaning.

---

## Project at a glance

Kitchen cabinet decomposition engine. Takes YAML cabinet definitions, produces physical panels with dimensions, edge banding, and machining operations. Outputs: BOM, cut list CSV, intermediate JSON.

**One sentence**: YAML → `CabinetInstance` → `decompose()` → `Panel[]` → CSV / JSON / BOM

---

## Session order

1. `bd prime` — **automatic**, injected by the `SessionStart` hook in
   `.claude/settings.json`. Carries the beads context and the persistent
   memories. Nothing to do.
2. `STATUS.md` — the generated dashboard, five PM questions; §3 names the next
   work and its start commands.
3. **`bash scripts/truth-bd-adapter.sh | scripts/truth ready --stdin`** — NOT
   `bd ready`. This is `bd ready` filtered by premise validity: issues standing
   on stale or diverged facts are HELD. The plain `bd ready` will hand you work
   built on a dead fact. The adapter form is needed because the native work
   kernel otherwise outranks the `bd` default (see
   `docs/beads-integration-guide.md` §2).
4. Do the work. Claim with `bd update <id> --claim`.
5. `git push` — the content gates fire on their own
   (`scripts/pre-push-checks.sh`: spec-health, doc-health, exercise-gate and
   all four domain suites, ~40 s, blocking). It also prints, without blocking,
   how many claims need your judgment and how many beads are flagged human.

`scripts/session-close.sh` is the fuller survival gate and is invoked by no
code — run it by hand when ending a substantial session.

## Reading rules — bounded reads (QB-013)

**Never let a bounded read support an unbounded claim.** If your conclusion
contains *never*, *none*, *empty*, *all*, or *does not exist*, the read behind
it must be unfiltered.

Three failures of this shape occurred in one session on 2026-08-03:

- `bd close A B` piped through `tail -1` showed only the second confirmation.
  The first bead silently did not close, leaving a P1 item blocked by finished
  work. **After any state-changing command, verify by re-query — never by
  reading its output.**
- `grep -A 4 "^on:"` truncated a workflow trigger block and produced a
  published finding that a gate "has never run". It carries two triggers.
  **Before asserting absence, read the whole block.**
- `grep -c 'unverified'` matched the word inside claim *text* rather than the
  status column. **Anchor on the field or column, never the bare substring**,
  and run a positive control you know matches.

## Which documents to read, and when

Read by default: this file, `STATUS.md`, `scripts/truth ready`, and
`docs/GLOSSARY.md` for any unknown term. That is the whole entry protocol.

**Do NOT read the verification-doctrine documents unless you are deciding
about the verification machinery itself** —
`docs/reviews/agentic-verification-doctrine-2026-08-03.md`,
`verification-system-scratch-design-2026-08-03.md`, and the ~6,000 lines under
`docs/reviews/sources/`. They are for whoever changes how the ledger and gates
work, not for whoever builds a decomposer. Loading them costs a large slice of
context and biases toward meta-work: the session that produced them spent more
time on ledger healing than on code integration.

If you are resuming feature work, `docs/reviews/session-handoff-2026-08-03.md`
is the one-page substitute for all of it.

## Truth ledger

This project keeps a truth ledger. Before relying on a repository fact,
check it: `scripts/truth list --live`.

**File a fact only if it will outlive the work you are about to do.**

- **Do file** facts about the world outside the repo — owner-confirmed rates,
  manufacturer geometry, standards. Use `--ttl-days N` instead of `--paths`.
  These are testimony: they do not churn, and other work genuinely stands on
  them.
- **Do file** durable properties that no gate covers yet.
- **Do NOT file a fact that describes a defect you are about to fix.** That
  fact is engineered to become false the day your own bead lands, and it costs
  a verdict, an invalidation and a manual retraction to say so. The defect
  belongs in a bead; the fix belongs in a gate that turns green.

Measured 2026-08-02: eleven defect-describing claims were filed in one
session; two were retracted within 24 hours and the rest are due to die as
their own beads ship. See `docs/reviews/session-handoff-2026-08-03.md` §4.

```
scripts/truth claim "<fact>" --class VERIFIED --evidence-cmd "<cmd>" --paths "<glob,glob>" --tier P1
```

The evidence command must be able to FAIL when the sentence is false: it must
read every path in `--paths`, avoid `grep -n` (line numbers drift), and
produce byte-identical output on three consecutive runs.
Never edit `.truth/claims.jsonl` directly; status changes are new records.
Full documentation: `.truth/README.md`.

**Beads precedence:** this repo also runs Beads (`bd`, section below). To find
work, use `scripts/truth ready` — NOT `bd ready` — it is `bd ready` filtered by
premise validity; issues standing on stale/diverged facts are HELD. Full loop:
`docs/beads-integration-guide.md`.

---

## Feature specs (start here when the user describes a new feature)

When the user starts talking about a **new feature** — or any change bigger
than a bug fix — do this BEFORE designing or writing code:

1. **Find or create the spec.** Check `<component>/docs/specs/` (and root
   `docs/specs/`); if none matches, classify the component against
   `docs/templates/spec-archetypes.md` (six recurring types — domain
   library, data service, interactive GUI, integration adapter, pipeline,
   cross-cutting) and start from the matching blank in `docs/templates/`,
   then draft per `docs/spec-convention.md` — section contract, and the
   one rule: *facts appear only as ledger ids, never as prose*.
2. **Verify the ground it stands on.** Facts the feature depends on →
   verify each and file as `tr-` claims; cite the ids under Ground truths.
   Facts already claimed → cite the existing id, don't re-file.
3. **File the work.** `scripts/truth issue "<title>" --premise tr-...`
   (+ Beads twin via `bd create` while the A/B trial runs); cite under Work.
   `bd create` alone loses premise tracking — only the truth issue HOLDs
   work when the facts under it die.
4. **Write Acceptance now.** Draft the `done --claim` texts the finished
   work will file — scoped to what an evidence command can show.
5. **Gate on health.** `bash scripts/spec-health.sh` — a FAIL means the spec
   stands on a dead fact: renegotiate the spec with the user, don't code.

Resuming a discussed feature in a fresh session: read its spec, run
spec-health, and `scripts/truth ready` — the three together restore the
full picture (intent, fact validity, unblocked work).

---

## Component roster (monorepo)

This repo hosts 6 components. `kuchnie_core` is the pure-Python domain hub; every other component depends on it, never the other way. Roles and boundaries are codified in ADRs 009–011.

| Component | Role | AGENTS.md | Defining ADR |
|---|---|---|---|
| `kuchnie-core/` | **Domain hub** — Kitchen, Panel, decomposition, BOM, standards, validator. Pure Python. Imported by everyone. | this file | 001, 002, 003 |
| `catalog/` | Material catalog service — Kronospan/Egger decors, worktops, pairings, availability. FastAPI + SQLite. | `catalog/AGENTS.md` *(todo)* | 008 |
| `krono-compositor-mvp/` | **Sales tool (Stage 1)** — first-visit 2.5D previews + decor picker + screenshots. FastAPI + OpenCV + Alpine.js. | `krono-compositor-mvp/AGENTS.md` *(todo)* | 011 |
| `kitchen-erp/` *(renamed per ADR-011)* | **BOM · cost · purchasing · rules admin · ops UI.** Reflex + SQLModel. Consumes `kuchnie_core` for domain computations. | `kitchen-erp/AGENTS.md` *(todo)* | 011 |
| `kitchen-cam/` *(renamed per ADR-010)* | **CAM enrichment** — machining ops (System32, hinges, handles), DXF for CNC shop. Downstream consumer of `kuchnie_core`. | `kitchen-cam/AGENTS.md` | 010 |
| `home-builder-adapter/` *(renamed per ADR-009)* | **Blender scene extractor** — walks `home_builder_5` `.blend` tree → `kuchnie_core.Kitchen`. The pipeline's `bpy`-dependent component (krono-compositor's standalone `gen_kitchen.py` renderer also imports `bpy`). | `home-builder-adapter/AGENTS.md` *(todo)* | 009 |

**External (not in this repo):**

- `/Users/michal/PycharmProjects/home_builder_5` — third-party licensed Blender addon used for interactive kitchen layout (Stage 2). Untouched per F007 Rule 4. Its scene tree is the input to `home-builder-adapter/`.

**Who owns what user-facing artifact** (route new feature specs by this):
quotes, pricing, BOM, purchasing, ops UI → `kitchen-erp` · first-visit
visuals & decor previews → `krono-compositor-mvp` · CNC/DXF outputs →
`kitchen-cam` · material/decor/pairing data → `catalog` · scene extraction
→ `home-builder-adapter` · decomposition/domain rules → `kuchnie-core`.

**Dependency direction:** every peripheral component imports `kuchnie_core`. No cycles. `kuchnie_core` imports only stdlib + Pydantic + PyYAML.

**Workflow stages:** Sales → Design (`home_builder_5`) → Extract (`home-builder-adapter`) → Refine + BOM (`kitchen-erp`) → CAM (`kitchen-cam`).

---

## Architecture (3 rules)

1. **Panel is the atom.** Not the cabinet. Everything above panels is organizational. Everything on panels (edges, machining ops) is decoration. (`ADR-001`)

2. **Construction method ≠ Cabinet instance.** The catalog (`catalog.py`) knows HOW to decompose. The model (`model.py`) knows WHAT was configured. The decomposer connects them. (`ADR-002`)

3. **Kitchen is the unit of work.** Serialize, render, export — always at kitchen level, never individual cabinets. (`ADR-003`)

---

## File map

```
kuchnie-core/src/kuchnie_core/
├── model.py          Dataclasses. No logic. No imports from other modules.
├── catalog.py        Decompose functions per cabinet type. Imports model only.
├── decomposer.py     Thin dispatcher: type → catalog function. 20 lines.
├── bom.py            Panels + accessories → costed BOM.
├── legrabox.py       LEGRABOX-specific catalog data + drawer decomposer.
├── loader.py         YAML → model. Adapter, no business logic.
├── kitchen.py        Kitchen-level aggregation (all_panels, kitchen_bom, validate).
├── serialize.py      Kitchen ↔ JSON. The intermediate format contract.
├── export/           CSV, DXF, etc. One file per output format.
```

**Dependency direction**: `export/` → `kitchen.py` → `decomposer.py` → `catalog.py` → `model.py`
Never import downward. `model.py` imports nothing from this package.

---

## Adding a cabinet type (step by step)

1. Write a `decompose_<type>(cab: CabinetInstance) -> DecompositionResult` function in `catalog.py` (or a dedicated module like `legrabox.py` for complex types)
2. Register in `TYPE_REGISTRY` dict at the bottom of `catalog.py`
3. Create a fixture YAML in `fixtures/`
4. Write tests that verify:
   - Panel count
   - Each panel's width, height, thickness
   - Edge banding (which edges, which material)
   - Machining ops (type, position, diameter)
   - Accessories (type, quantity)
5. Run `pytest -v` — all tests must pass

---

## Implementing a spec'd feature (TDD)

The entry point for any new feature is § "Feature specs" above — arrive
here with a spec and a claimed `wk-` issue, then:

1. **Write the test first** (what should happen?)
2. **Write the code** (make the test pass)
3. **Check existing tests** still pass (`pytest -v`)
4. **Document the decision** if it's non-obvious → `docs/adr/NNN-<slug>.md`
5. **Append to CHANGELOG.md** under today's date
6. **Close the work**: `scripts/truth done <wk-id> --basis "..." --claim ...`
   using the spec's Acceptance texts (+ `bd close <twin>` while the A/B runs)

---

## Documentation conventions

| What | Where | Staleness-proof because |
|---|---|---|
| "We chose X because Y" | `docs/adr/NNN-*.md` | Immutable. New decision = new ADR. |
| "The formula is Z" | Docstring + test assertion | Test fails if code drifts. |
| "What changed" | `CHANGELOG.md` | Append-only. Historical fact. |
| "How to use this" | Module docstring at top of file | Reviewed with code. |
| "How the system works" | `AGENTS.md` (this file) | Keep under 200 lines. Update when architecture changes. |

**Never write a separate doc that restates what the code does.** If the code is clear and tested, it IS the documentation.

### File naming

- **kebab-case**: `configurator-api.md`, `wall-centric-model.md`
- **SCREAMING_SNAKE**: `README.md`, `CHANGELOG.md`, `AGENTS.md` only
- **Numbered**: ADRs (`001-*.md`) and vision (`00-*.md`) only
- **English**: file names in English, content can be Polish
- Full rules: `docs/file-naming-convention.md`

---

## Testing conventions

- **One test file per concern**: `test_K01_decomposition.py`, `test_legrabox.py`, `test_serialize.py`
- **Test names describe behavior**: `test_drawer_box_back_dimensions`, not `test_legrabox_3`
- **Assertions show the formula**: `assert back.width_mm == 700  # LW−38 = 738−38`
- **Fixture YAMLs in `fixtures/`**: one per cabinet type, one per kitchen layout
- **Run `pytest -v` before every commit**
- **E2E exercises are golden-first**: see `docs/e2e-exercise-convention.md`;
  scaffold a scenario with `.venv/bin/python exercises/harness/scaffold.py
  <name>`, run it with `.venv/bin/python exercises/harness/runner.py <name>`
  (writes a toolchain manifest); shared helpers live in `exercises/harness/`
- **Session lifecycle is gated**: `docs/development-process.md` — end every
  session with `bash scripts/session-close.sh` (refuses on dirty tree,
  claimed work, gate failures); `bash scripts/exercise-gate.sh` guards the
  flagship exercise baseline after decomposer/extraction changes; priorities
  are bd data, never handoff prose

---

## Conventions

- **Units**: always mm. Field names end with `_mm`: `width_mm`, `depth_mm`, `diameter_mm`
- **Coordinate system on panels**: x = left edge, y = bottom/front edge, viewed from machined face
- **Edge banding**: only edges that ARE banded appear in `banded_edges` dict. Absent = not banded.
- **Machining ops**: only ops that exist appear in `machining_ops` list. Empty list = no machining.
- **YAML keys**: Polish (user-facing). **Model fields**: English (engine-facing). Loader is the adapter.
- **JSON intermediate format**: self-contained (no external references), versioned (`"version": "1.0"`)

---

## What NOT to do

- Don't put panel dimensions in `CabinetInstance` — that's the catalog's job
- Don't import `catalog.py` from `model.py` — dependency goes one way
- Don't write a doc that restates code — write a test instead
- Don't edit an old ADR — write a new one that supersedes it
- Don't hardcode material thicknesses — use the YAML or Blum spec defaults
- Don't aggregate panels in the decomposer — aggregation happens in `export/`

---

## Documentation governance

> Source: DOC-GOVERNANCE-KIT Layer 0 — historical; fully merged here, the
> kit file itself no longer exists.

1. **Evidence protocol.** Every repo-state claim in any doc or review is tagged
   `VERIFIED(cmd)` / `INFERRED(basis)` / `UNVERIFIED`. Hedging is not a
   substitute for the tag.
2. **New-doc gate.** No new `.md` without three answers in the file header:
   `Reader:`, `Enables:`, `Update-trigger:`. Empty answer = don't write the
   doc.
3. **New-component gate.** No new top-level package without an accepted ADR
   stating purpose, why existing components can't absorb it, and lifespan.
   Run a duplication scan first. This rule would have prevented the
   kitchen-cam fork.
4. **Review output contract.** Audits/reviews are: 3-line TL;DR → 2–4 P0
   findings with evidence → one matrix → unknowns → one question. No praise
   without a named trade-off.
5. **Diagram labels.** Every architecture diagram is captioned `OBSERVED`
   (each arrow grep-verified) or `PROPOSED`. No unlabeled arrows.
6. **Freshness ritual.** At every freeze or quarter boundary, rerun the trust
   audit (`docs/freeze/FREEZE-PLAN.md`, Prompt 1 pattern) and re-stamp.
   STALE stamps are removed only by rewriting against code.

Trigger moments: session start → read order · new .md → gate 2 ·
new component → gate 3 · any review → contract 4 · new diagram → rule 5 ·
freeze/quarter → ritual 6.

Enforced by: Layer 1 (pre-commit hook, `scripts/check-governance.sh`) and
Layer 2 (LLM semantic gate, `scripts/llm-doc-gate.sh`, manual for now).

---

## Key formulas (reference, verified by tests)

| Formula | Source | Test |
|---|---|---|
| Carcass side height = cabinet_height − plinth_height | Standard | `test_side_dimensions` |
| Bottom width = cabinet_width − 2 × side_thickness | Standard | `test_bottom_dimensions` |
| Back width = cabinet_width − 2 × side + 2 × groove | Standard | `test_back_dimensions` |
| LEGRABOX LW = KB − 2 × 13mm | Blum DQBQRY | `test_lw_formula` |
| Drawer back = LW − 38 wide × back_height tall | Blum | `test_drawer_box_back_dimensions` |
| Drawer base = LW − 35 wide × NL−10 deep | Blum | `test_drawer_box_base_dimensions` |
| Drawer box panels = 16mm chipboard | Blum | `test_drawer_box_back_dimensions` |
| Runner first screw = 46mm from front | Blum | `test_drawer_box_first_screw_position` |

If a formula changes, update the function, the test, and the ADR (as a new ADR, not editing the old one).

---

## Current state

- 3 cabinet types: `dolna_szufladowa`, `gorna_drzwiowa`, `dolna_legrabox`
- 84 tests passing
- LEGRABOX: C height fully verified, M/F heights from catalogue (not yet PDF-confirmed)
- Runner screw positions: partial (PoC values, full table needed from Blum Montageanleitung)

---

## Doc routing (what to update when)

| Change | Update | Skip |
|--------|--------|------|
| New feature | `CHANGELOG.md` + relevant spec | `vision/` |
| Bug fix | `CHANGELOG.md` only | Everything else |
| Formula change | Spec + test + `CHANGELOG.md` | `architecture/` |
| Schema change | Spec + ADR + `CHANGELOG.md` | `vision/` |
| New decision | `docs/adr/NNN-*.md` | — |
| Config change | `home-builder-adapter/docs/` config docs (currently archived) + `CHANGELOG.md` | `vision/` |

**Max 3 doc files per change.** If more, you're over-documenting.

Full routing: `docs/doc-routing.md`

---

## When stuck

1. Read the relevant ADR in `docs/adr/`
2. Read the test that verifies the behavior you're changing
3. Read the fixture YAML to understand the input shape
4. Run `pytest -v` to see what's currently passing

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:970c3bf2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN BEADS CODEX SETUP: generated by bd setup codex -->
## Beads Issue Tracker

Use Beads (`bd`) for durable task tracking in repositories that include it. Use the `beads` skill at `.agents/skills/beads/SKILL.md` (project install) or `~/.agents/skills/beads/SKILL.md` (global install) for Beads workflow guidance, then use the `bd` CLI for issue operations.

### Quick Reference

```bash
bd ready                # Find available work
bd show <id>            # View issue details
bd update <id> --claim  # Claim work
bd close <id>           # Complete work
bd prime                # Refresh Beads context
```

### Rules

- Use `bd` for all task tracking; do not create markdown TODO lists.
- Run `bd prime` when Beads context is missing or stale. Codex 0.129.0+ can load Beads context automatically through native hooks; use `/hooks` to inspect or toggle them.
- Keep persistent project memory in Beads via `bd remember`; do not create ad hoc memory files.

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.
<!-- END BEADS CODEX SETUP -->
