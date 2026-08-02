# Refactor plan: whole-codebase architecture review, rounds 0–1 (2026-08-02)

> Reader: whoever picks up architecture work in a future session, or Michał
> deciding which of these to fund | Enables: resuming a paused four-round
> architecture review without re-deriving it, and executing the four repairs
> it already justifies | Update-trigger: a listed repair ships (then its
> section is history, not plan), a listed question is answered by the owner,
> or rounds 2–3 run and add findings

**Status: PARTIAL.** This captures a three-expert panel review
(kitchen-design technologist / CAD-CAM workflow architect / software
architect) that ran **rounds 0 and 1 of four**. Rounds 2 (inside-component
module graphs, data-flow, domain-model vocabulary) and 3 (collaboration
diagrams, hotspot table, test-shadow map) have **not** run. The findings
below are therefore real but not exhaustive — do not read the absence of a
finding as a clean bill of health for any component.

> **Round 2 has since run (partial):
> `architecture-review-round-2-2026-08-02.md`.** It carries the six
> architecture diagrams, adds findings N1–N7 (the ERP↔core seam drops
> accessories; `decompose_dolna_legrabox` and `decompose_dolna_narozna_slepa`
> are unreachable from kitchen-erp; a latent plinth double-count that arms
> when that is fixed), asks Q5, and **answers three open items from this
> document** — see its §5. Read both before executing any repair below; the
> merged execution order lives in its §7. Round 3 still has not run.

**Evidence labels used throughout:**
`CONFIRMED` — a verification command was run this session against the live
repo, and the command is recorded in Appendix A.
`OBSERVED` — read directly in a cited file:line.
`INFERRED` — likely, from a named signal, but not proven.
`NEEDS-BODY` — answerable only by reading code not yet read.

---

## 0. The one-paragraph verdict

The dependency rule holds, and it is not an accident. `kuchnie_core` imports
no framework, no web layer, no ORM, no `bpy` — a repo-wide grep for
`reflex|sqlmodel|fastapi|bpy|urllib|cv2|requests` across the whole package
returns exactly one hit, `materials/sqlite_repository.py:16: import sqlite3`,
and that module implements the `MaterialCatalog` Protocol declared beside it
(`CONFIRMED`, Appendix A.1). Every other component points inward:
kitchen-erp, kitchen-cam and home-builder-adapter all import `kuchnie_core`
and it imports none of them. The intent is even written down in the code —
`kuchnie-core/src/kuchnie_core/kitchen.py:96-98`: *"kuchnie-core defines its
own carrier so the dependency stays one-way (ERP imports core, never the
reverse)."* This is the strongest structural property in the repo and the
thing every repair below must avoid damaging.

What the rule does not protect is the **payload**. Identity-bearing material
data is flattened to a display string on the way into the domain, and then
re-invented from a hardcoded table on the way out to purchasing documents —
and the purchasing-document chain that would consume it has no production
caller at all. That is where the four P0s live.

---

## 1. Findings and repair instructions

### P0-1 — Material identity is destroyed at the ERP→core seam, then guessed back

**Evidence.** `kitchen-erp/kitchen_erp/core/domain_adapter.py:62-64` passes
three display strings into the domain:

```python
body_material=corpus_mat.name,
back_material=defaults.back_mat.name,
front_material=front_mat.name,
```

The `Material` row those came from carries far more identity than that:
`catalog_variant_id` (the catalog-service-owned identity,
`core/models.py:100`), `brand`, `category`, `sheet_size_m2`, `has_woodgrain`.
None of it crosses (`OBSERVED`). `Material` has **no thickness field at all**
(`CONFIRMED`, A.2) — thickness survives the round trip only because the
decomposer stamps `Panel.thickness_mm` and `purchasing._material_meta` reads
it back off the panels.

Downstream, `core/purchasing.py:272-278` reconstructs producer, decor,
structure and waste class from `BOARD_DECOR_CATALOG`, a four-entry literal
dict keyed on code-style strings (`"PLYTA_BIALA_18"`, `"plyta_16mm"`,
`"K5307_18"`, `"HDF_BIALA_3"`). So the join that has to work in production is
string equality between a **user-editable database column** (`Material.name`,
editable in the admin UI at `ui/admin_state.py:282`) and a **hardcoded dict**.

**Why it matters.** *Expert 1 (kitchen technologist):* a board you can
actually order needs decor code + structure + thickness + sheet format.
Three of those four are reconstructed rather than carried, and one of them
(thickness) does not exist on the ERP side at all. *Expert 2 (CAD/CAM):* this
is the cardinal sin — data re-typed between pipeline stages instead of
flowing. *Expert 3 (architect):* primitive obsession; the domain has an
identity here and the type system is carrying a `str`.

**Repair instruction.**
1. Introduce a `BoardSpec` value object in `kuchnie_core` (frozen dataclass,
   English names, explicit units): `catalog_variant_id`, `producer`, `decor`,
   `structure`, `thickness_mm`, `sheet_format`, `is_directional`. It is a
   *value object*, not an entity — no identity beyond its fields, immutable.
2. Widen `CabinetInstance`'s material fields to accept it. Keep `str`
   accepted for one release so the existing YAML loader and ~700 core tests
   are not broken in the same change; normalise `str` → `BoardSpec` at the
   `CabinetInstance.__post_init__` boundary with a lookup, and log where the
   lookup falls back.
3. Add `thickness_mm` and `structure` to the ERP `Material` table (migration
   + admin UI fields) and populate them in `material_mirror.refresh_material_mirror`
   from the catalog payload, which already owns those facts.
4. Delete `BOARD_DECOR_CATALOG` once `BoardSpec` reaches `board_order_rows` —
   it becomes a projection of data that travelled, not a re-derivation.
5. `Panel.material` then carries the `BoardSpec`, so `_material_meta`'s
   "first-seen thickness" heuristic disappears too.

**Effort L · Risk medium · Blast radius: `domain_adapter`, `purchasing`,
`model.CabinetInstance`, `catalog.py` decomposers, ERP migration, and the
d60 golden files (which will need regenerating — expect a deliberate golden
roll, per the truth-ledger convention).**

**First concrete step (small, safe, standalone):** add `thickness_mm` and
`structure` to `Material` + the mirror, with tests. That alone makes the ERP
side able to *express* the identity, and is independently useful before any
core change.

---

### P0-2 — The purchasing-document chain has no production caller

**Evidence.** `board_order_rows`, `edging_order_rows` and
`hardware_order_rows` are referenced repo-wide only by
`kitchen-erp/tests/test_purchasing_order_docs.py`, `CHANGELOG.md`, and
`all-signatures.md` (`CONFIRMED`, A.3). No UI action, no CLI, no service
function calls them. The golden test builds a `CabinetInstance` **by hand**
(`test_purchasing_order_docs.py:76`, `body_material="PLYTA_BIALA_18"`),
bypassing `to_kuchnie_core` entirely.

**Why it matters.** The goldens pin the *CSV formatting* of the purchasing
documents byte-for-byte, which is genuinely valuable — but the seam that
would feed them in production (`Material.name` → `BOARD_DECOR_CATALOG`) is
never exercised by any test. Combined with P0-1, the first real project that
reaches purchasing will hit `KeyError` on an unmapped material. The code
raises deliberately there (`purchasing.py:271` comment: *"a silently-wrong
purchasing doc is worse than a loud KeyError"*) — that instinct is right, and
it is aimed at an untested join. *Expert 1:* in a subcontracting shop the
formatki order **is** the primary purchasing artifact; a stage-5 pipeline
that cannot emit it is not done.

**Repair instruction.** Do P0-1 first — wiring this before identity travels
just cements the string join. Then:
1. Add `purchasing_docs_for_project(session, project) -> tuple[str, str, str]`
   in `kitchen-erp/kitchen_erp/core/`, composing per-cabinet
   `DecompositionResult`s exactly as `variant_derivation.derive_variant`
   already does (do not open a second composition path — read that function
   first and reuse it).
2. Register the emitted CSVs as `ArtifactRef` rows (`kind="board_order_csv"`
   etc.) — the spine already models this (`core/models.py:221-230`).
3. Add one integration test that goes **project row → CSV**, not
   hand-built `CabinetInstance` → CSV. This is the test that does not exist
   today.

**Effort M · Risk low · Blast radius: kitchen-erp only.**

**First concrete step:** read `variant_derivation.derive_variant` and write
down whether it already composes the multi-cabinet result these generators
need. If it does, this is a wiring job, not a design job.

---

### P0-3 — Four PLN literals bypass the entire price-freshness apparatus

**Evidence.** `kitchen-erp/kitchen_erp/core/bom_generator.py` (`OBSERVED`):

| Line | Item | Price | Provenance |
|---|---|---|---|
| 158 | CNC Service: Cutting & Nesting | 15.00 PLN/m² | none |
| 166 | CNC Service: Edgebanding PUR | 4.50 PLN/lm | none |
| 196 | Plinth board (cokół) | 25.00 PLN/lm | none |
| 205 | Plinth seal (uszczelka) | 3.50 PLN/lm | none |

The same component runs `SupplierPrice` (append-only price history),
`PRICE_TTL_DAYS`, `assess_quote_freshness` and
`quote_freshness_for_project`, and grades a quote estimate-vs-offer on price
age. These four numbers have no supplier, no `valid_from`, no owner
attribution and no date.

**Why it matters.** *Expert 1 is blunt here:* in a one-person shop that
subcontracts cutting, the cutting-service rate per m² is **the** primary
purchasing number — and it is the one number in the system with no
provenance. A quote can be graded "fresh" by the freshness gate while these
four literals silently carry it. Panel rule 4 applies: business numbers
belong to the shop owner.

**Repair instruction.**
1. Move all four into `SupplierPrice` rows (supplier = the cutting service /
   the plinth supplier) seeded through the normal price-import path, so they
   inherit freshness grading automatically.
2. If they must stay as defaults for un-seeded projects, put them in one
   named constants block with `# ASSUMPTION — owner confirmation pending
   <date>` and make `assess_quote_freshness` *report* their use, so an
   estimate that leans on them cannot be graded offer-grade.
3. Ask the owner for the current real rates before either (see Question Q2).

**Effort S · Risk low · Blast radius: `bom_generator`, `quote_range`
totals, `price_import` freshness output. Quote figures will move — expect
`test_quote_range` / `test_calculations` assertions to need updating with
the owner's real numbers.**

**First concrete step:** ask the owner Q2. Do not pick replacement numbers
yourself — Expert 3 owns the shape, never the facts.

---

### P0-4 — Construction math living in the translation layer

**Evidence.** `domain_adapter.py` (`OBSERVED`):

```python
PLINTH_HEIGHT_MM = 100.0   # line 27
FRONT_GAP_MM = 3.0         # line 28
...
side_h = cabinet.height_mm - PLINTH_HEIGHT_MM          # line 46
front_h = (side_h - FRONT_GAP_MM * (n + 1)) / n        # line 47
drawers.append({"id": f"S{i}", "typ": "tandembox", ...}) # line 49
```

Meanwhile `kuchnie_core.construction.ConstructionMethod` already owns
`front_reveal`, `drawer_front_width`, `door_height`, `door_width` — and
`DrawerSystemFactory` exists with LEGRABOX / TANDEMBOX / MERIVOBOX
implementations, plus a `Variant` drawer-system override axis. The adapter
hardcodes `"tandembox"` for every drawer base regardless.

**Why it matters.** *Expert 2:* this is Polyboard's core lesson inverted —
construction method ≠ cabinet instance, and it certainly isn't adapter code.
Every future construction-rule change now has two homes, and the adapter's
copy is the one no `ConstructionMethod` test covers. *Expert 1:* the drawer
front-height division also needs checking against the real reveal
convention — an equal-division formula with a uniform 3 mm gap is a
*plausible* shop convention, not a verified one (`ASSUMPTION`).

**Repair instruction.**
1. Move the drawer-front-height split into a `ConstructionMethod` method
   (e.g. `drawer_front_heights(cabinet_height_mm, plinth_mm, count) ->
   list[float]`) and have the adapter call it. The adapter's only job is
   translation: ERP row → domain instance, no arithmetic.
2. Route the drawer system through `DrawerSystemFactory` / the `Variant`
   override instead of the `"tandembox"` literal.
3. Delete `PLINTH_HEIGHT_MM` / `FRONT_GAP_MM` from the adapter once the
   method owns them; if ERP genuinely has a different plinth default, it
   belongs on `ProjectDefaults`, not in a translation module.

**Effort M · Risk low-medium · Blast radius: `domain_adapter`,
`construction.py`, drawer-base BOM quantities (front area changes if the
reveal convention turns out to differ — check goldens).**

**First concrete step:** confirm the reveal convention with the owner
(Question Q3) *before* moving the formula, so the move and any correction
are separable commits.

---

### P1-1 — `has_woodgrain` is written, displayed, and never read

**Evidence** (`CONFIRMED`, A.4). `Material.has_woodgrain` is populated by
`material_mirror` from the catalog, editable in the admin UI
(`ui/admin_state.py:189, 266, 282`), and asserted in
`tests/test_material_mirror.py:76-77`. But `SheetMaterialStrategy` is only
ever constructed as `SheetMaterialStrategy()` in production code
(`purchasing.py:184-185`) — the `has_woodgrain` constructor parameter is
never passed, because `get_strategy_for_material(material_category: str)`
takes only a category and has no access to the material row. The single
production consumer of "is this decor directional?" is instead
`WASTE_BY_CLASS` (`purchasing.py:226-231`), keyed off the hardcoded
`BOARD_DECOR_CATALOG` from P0-1.

So the same physical fact — this decor has a grain direction, nesting cannot
rotate it 90°, waste goes up — is stored in two places, mirrored from the
catalog into one of them, and read from the *other* one.

**Repair instruction.** Fold into P0-1: `BoardSpec.is_directional` becomes
the single carrier, sourced from the catalog, consumed by both the waste
class and the nesting strategy. Then either wire `get_strategy_for_material`
to take a `Material` (not a category string) or delete the unused
`has_woodgrain` constructor arg. Do not leave both.

**Effort S (as part of P0-1) · Risk low.**

---

### P1-2 — Nine function-local imports are cycle-breakers, not lazy loads

**Evidence** (`OBSERVED`). In `kuchnie_core`:

- `kitchen.py:71` imports `buildability.require_buildable`; `kitchen.py:137`
  imports `buildability.{ADVISORY, BLOCKING, Finding}`
- `buildability.py:162` imports `kitchen.row_findings`;
  `buildability.py:44` imports `kitchen.HeightSet` under `TYPE_CHECKING`
- `buildability.py:196, 213, 239, 253` import `catalog`, `legrabox`,
  `decomposer`, `validator`
- `catalog.py:596` imports `legrabox`; `serialize.py:102` imports `loader`

In kitchen-erp: `core/models.py:467` imports `core/survey.py`, which imports
`core/models.py` at line 16.

`kitchen.py` ↔ `buildability.py` and `models.py` ↔ `survey.py` are genuine
mutual module dependencies; the deferred imports exist to make Python
tolerate them.

**Why it matters.** Modest today — the code works and the pattern is
consistent. But it means the layering *inside* core is not acyclic, so
"which module may depend on which" has no enforceable answer, and each new
gate or aggregation makes the knot slightly tighter. *Expert 3 explicitly
flags this as the lowest-urgency P1:* it is a real smell with a cheap fix,
not an emergency.

**Repair instruction.** Extract the shared vocabulary into a leaf module.
`Finding`, `GateStatus`, `ADVISORY`, `BLOCKING` are a *shared language*
between the aggregation layer and the gate layer, not the property of
either. Put them in `kuchnie_core/findings.py` with no intra-package imports,
have both `kitchen.py` and `buildability.py` import it at module top level,
and move `row_findings` to sit with the gates it belongs to (it is a rule
set, not an aggregation). Same shape for `survey.py`: the policy function is
fine importing the model, so invert — have `transition_stage` take the
missing-list as a parameter, or move the check to the caller.

**Effort S · Risk low · Blast radius: import lines only; no behaviour
change. Verify with the full core suite, which is large enough to catch a
mistake here.**

---

## 2. Questions for the owner

Answer these before executing the repairs they gate — they are facts, and
per panel rule 3 the architect does not invent facts.

**Q1 (gates P0-2).** Are `board_order_rows` / `edging_order_rows` /
`hardware_order_rows` intended as the real purchasing output for a live
project — in which case P0-2 is a missing wire and P0-1 blocks it — or were
they built as a golden-file spike against the d60 exercise, with the
production path deliberately deferred?

**Q2 (gates P0-3).** What are the current real rates, and from whom, as of
which date: cutting/nesting per m², PUR edgebanding per lm, plinth board per
lm, plinth seal per lm? If any of these are still guesses, say so — they
will be labelled ASSUMPTION in code rather than silently priced.

**Q3 (gates P0-4).** For a drawer base: is the drawer-front height genuinely
an equal division of (carcass height − plinth) with a uniform 3 mm gap
above, between and below? Or does the shop use a different reveal at the top
/ bottom, or fixed front heights per LEGRABOX height code?

**Q4 (scopes P0-1).** Should `BoardSpec` identity be keyed on the catalog's
`catalog_variant_id`, or on producer + decor + structure + thickness? The
first is cleaner but couples the domain to the catalog service's id scheme;
the second is orderable-by-inspection and survives the catalog being
replaced. *Panel recommendation: the second, with `catalog_variant_id`
carried alongside as a non-identifying reference.*

---

## 3. Leave it alone

Things that look refactorable and should not be touched, with the reason
refactoring buys nothing:

- **`ui/state.py` at 1146 lines and `kitchen_erp.py` at 784.** These are
  Reflex state and view code. Reflex state classes are framework-shaped —
  splitting them fights the framework's `rx.State` model and buys testability
  the domain layer already provides. Revisit only if domain logic is found
  *inside* them (rounds 2–3 will check; `state.py:536`'s local import of
  `get_strategy_for_material` is the one suspicious signal so far).
- **`kuchnie_core/catalog.py` at 1021 lines.** It is a registry of
  per-cabinet-type decomposition functions with a flat dispatch table
  (`decomposer.py:13`). Long, but each function is one cabinet type and adding
  a type means adding a function — the file grows linearly and honestly.
  Splitting it into modules per type would add import ceremony without
  reducing any single unit of reasoning. Expert 2 notes this is exactly how
  Polyboard-class systems organise construction methods.
- **The dict-based `validate_manifest` alongside the typed `Kitchen`.** It
  looks like a duplicate geometry representation and may be one — but whether
  it is a legitimate wire-format seam (Blender / home-builder side) is
  `NEEDS-BODY` and listed for round 2. Do not "unify" them before that
  question is answered.
- **`BOARD_DECOR_CATALOG` raising `KeyError` on an unmapped material.** The
  loud failure is correct and should survive P0-1. Only the *table* goes
  away; the refusal to emit a silently-wrong purchasing document stays.

---

## 4. Resuming the review

Rounds 2 and 3 were not run. To resume, the panel's next steps were:

**Round 2 — inside each component, three angles:** (a) module dependency
graphs for `kuchnie_core` and `kitchen-erp/core`; (b) data-flow view tracing
design → panels → operations → documents, marking every place data is
re-derived rather than flowed; (c) domain-model view — entities vs value
objects vs aggregates, plus the ubiquitous-language check. Vocabulary drift
already spotted and worth starting from: `typ`/`type`, `dekor`/`decor`, and
`material` meaning three different things (a `Material` DB row, a
`Panel.material` code string, an edge-band material string).

**Round 3 — collaboration & hotspots:** sequence diagrams for the 2–3
load-bearing use cases, then the hotspot table ranked by blast radius (god
modules, long parameter lists, concrete cross-boundary dependencies, cyclic
imports, orphan modules, test-shadow map).

**The five bodies round 2 wanted read first:**

1. `kitchen-erp/kitchen_erp/core/variant_derivation.py` → `derive_variant`
   (the second artifact chain — also the prerequisite for P0-2)
2. `kuchnie-core/src/kuchnie_core/catalog.py` → `decompose_dolna_legrabox`
   (the richest decomposition; where ops and accessories attach)
3. `kuchnie-core/src/kuchnie_core/bom.py` → `calculate_bom` (the ADR-015
   single fold)
4. `kitchen-erp/kitchen_erp/ui/state.py` → `_module_ui`,
   `open_project_cost_trace` (how the UI reaches the domain)
5. `kuchnie-core/src/kuchnie_core/validator.py` → `validate_manifest`
   (dict seam, or second geometry model?)

**Suggested execution order for the repairs**, independent of the remaining
review rounds:

1. Q2 → P0-3 (small, isolated, removes an untracked-price hazard from every
   quote)
2. P1-2 (small, no behaviour change, makes the core layering enforceable)
3. P0-1 step 1 only — `Material.thickness_mm` + `structure` + mirror (small,
   standalone, useful regardless)
4. Q3 → P0-4 (medium, unblocks correct drawer geometry)
5. Q4 → P0-1 in full (large; the golden roll is the expensive part)
6. Q1 → P0-2 (medium; only meaningful after P0-1)

---

## Appendix A — verification commands run this session

Recorded so a future session can re-check rather than re-trust. Run from
the repo root.

**A.1 — core purity** (expect exactly one hit, `sqlite_repository.py:16`):

```bash
grep -rn "import" kuchnie-core/src/kuchnie_core/*.py kuchnie-core/src/kuchnie_core/*/*.py \
  | grep -E "requests|sqlite3|fastapi|reflex|sqlmodel|bpy|urllib|cv2"
```

**A.2 — ERP `Material` has no thickness** (expect no output):

```bash
grep -n "thickness" kitchen-erp/kitchen_erp/core/models.py
```

**A.3 — purchasing docs have no production caller** (expect only tests,
`CHANGELOG.md`, `all-signatures.md`):

```bash
grep -rn "board_order_rows" . --include="*.py" --include="*.md" \
  | grep -v __pycache__ | grep -v "core/purchasing.py"
```

**A.4 — `has_woodgrain` never reaches the waste strategy** (expect every
production `SheetMaterialStrategy(` call site to be argument-free):

```bash
grep -rn "SheetMaterialStrategy(" --include="*.py" . | grep -v __pycache__
```

**A.5 — cross-component import direction** (expect no output; must match
`import` lines only — a plain substring grep here returns docstring and
comment noise, because core's docstrings legitimately *name* the components
that consume it):

```bash
grep -rnE "^\s*(from|import)\s+.*(kitchen_erp|kitchen_cam|compositor|catalog\.api|catalog\.repositories)" \
  kuchnie-core/src/kuchnie_core/ | grep -v __pycache__
```

**A.6 — the `materials` ↔ catalog-service coupling is by database file, not
by code.** `materials/sqlite_repository.py:9` and `materials/__init__.py:13`
both document usage as `SqliteMaterialCatalog("catalog/db/catalog.db")` —
i.e. `kuchnie_core.materials` reads the catalog service's SQLite file
directly, with no import and no HTTP call between them. Nothing enforces
that the schema the repository expects matches the schema
`catalog/db/engine.py:init_schema` creates. Flagged for round 2; not yet a
finding, because whether this path is live is `NEEDS-BODY`.

```bash
grep -rn "catalog/db/catalog.db" kuchnie-core/src/kuchnie_core/
```
