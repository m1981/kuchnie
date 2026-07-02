This is the freeze plan referenced by TEST-BASELINE-2026-07.md. Prompts 0–1 of the original plan
(rescue, trust audit) were executed in prior sessions; this file contains
the consolidated remainder.

You are finishing the freeze of the kuchnie monorepo. Earlier freeze steps
(rescue, test baseline, trust audit, decisions D1–D8) are committed through
7886922. This prompt contains ALL remaining work. Rules: (1) every factual
claim cites the command that proved it; (2) record state, don't redesign —
no code-logic changes, no test fixes, no refactors; (3) one commit per
numbered part; (4) if anything is ambiguous, stop and ask before acting.

─────────────────────────────────────────────────────────────────────────────
PART 0 — Persist this plan (fixes a dangling reference)
─────────────────────────────────────────────────────────────────────────────
docs/freeze/TEST-BASELINE-2026-07.md line ~22 references "the freeze plan",
which was never committed. Save THIS ENTIRE PROMPT verbatim as
docs/freeze/FREEZE-PLAN.md with a 3-line header: "This is the freeze plan
referenced by TEST-BASELINE-2026-07.md. Prompts 0–1 of the original plan
(rescue, trust audit) were executed in prior sessions; this file contains
the consolidated remainder." Commit: docs(freeze): persist freeze plan.

─────────────────────────────────────────────────────────────────────────────
PART 1 — MIGRATION-STATUS.md at repo root
─────────────────────────────────────────────────────────────────────────────
Record execution status of ADR-008–012 so no future session re-derives it.
Table columns: ADR | commitment | status (DONE / PENDING / NOT-STARTED /
DRIFTED) | evidence | next action. Verify each row yourself; known facts to
confirm and include:


ADR-012: fully DONE — §1/§2 commits 1603017+9a3748a, §3 d536f69,
§4 4621102, §5 ea7dc65, §6 e3c0492. 663/663 root tests pass
(docs/freeze/TEST-BASELINE-2026-07.md).
ADR-010 deletion queue: PENDING but UNBLOCKED by ADR-012 completion.
Evidence: kitchen-cam baseline shows 13 xpass — tests expected to fail on
missing field parity now pass. Deleted trio still present:
kitchen_cam/{models,panel_calculator,csv_generator}.py (verify with ls).
machining.py still imports kitchen_cam.models (verify with grep).
ADR-011: rename DONE; old BOM path NOT deleted (verify: Cabinet.
calculate_cost, set_use_new_bom, non-_new trace methods in
kitchen_erp/ui/state.py); kuchnie_core integration NOT-STARTED (verify:
no kuchnie_core import anywhere in kitchen-erp/, excluding .venv).
ADR-009: mostly DONE; DRIFTED: home-builder-adapter/pyproject.toml
still name="kitchen-generator", dependencies=[] despite importing
kuchnie_core (fixed in Part 2 — cross-reference it).
ADR-008: catalog is source of truth; list the surviving parallel material
stores and their ADR-declared fates: kitchen-erp Material table (→ mirror,
per ADR-011), krono catalog_db.py (frozen, contradicts ADR-008, needs the
krono-promotion decision).


Add sections: "Paused mid-step" (exact next command/file per PENDING item);
"Known contradictions" (repo reality violating accepted ADRs); "Findings not
recorded in any ADR": (a) home-builder-adapter has ZERO tests — old suite
deleted in commit 8da1a61 "Phase d", only tests/init.py survived rename;
new extract.py/cli.py (~500 LOC) never tested; (b) kitchen-erp suite broken
mid-ADR-011 (baseline N2/N3: HARDWARE_RULES import error, 13 SQLAlchemy
errors, 3 failures); (c) Pydantic design tension — schema.py uses BaseModel
at the YAML boundary vs ADR-012-12a "no Pydantic" rationale; dep now
declared (D1), keep-or-refactor is a resume decision.

Commit: docs: MIGRATION-STATUS at freeze point.

─────────────────────────────────────────────────────────────────────────────
PART 2 — Mechanical fixes (metadata/docs only; skip any that turn out done)
─────────────────────────────────────────────────────────────────────────────
2a. home-builder-adapter/pyproject.toml: name → "home-builder-adapter";
description per ADR-009 ("Blender scene → kuchnie_core.Kitchen
extractor"); add kuchnie-core dependency (path/workspace form the repo
tooling supports — if unclear which, ask); comment noting bpy is the
host-provided heavy dependency per ADR-009.
2b. kitchen-erp/pyproject.toml: real description; move pytest to dev deps;
fix coverage source = ["kitchen_erp "] trailing space.
2c. krono-compositor-mvp/pyproject.toml: fix source = ["src "] trailing
space; replace placeholder author "Your Name".
2d. Root README.md (new): one-paragraph purpose; component table
(component | type | role per ADR-011 stage table | freeze status);
read order for new sessions (AGENTS.md → RESUME.md →
MIGRATION-STATUS.md → docs/adr/); pointer to docs/freeze/.
2e. Header block at top of each component README (catalog, kitchen-erp,
kitchen-cam, home-builder-adapter, krono-compositor-mvp; create a
minimal README for kuchnie_core at src/ if none):
> Type: <A–F> | Status: frozen 2026-07 (see /MIGRATION-STATUS.md) |     Role: <one line> | ADRs: <binding numbers>
Types: kuchnie_core=A, kitchen-cam=A, catalog=C, kitchen-erp=D,
krono-compositor-mvp=C(+F script), home-builder-adapter=F.
Do not otherwise rewrite READMEs (kitchen-cam's stays STALE-stamped).
2f. docs/adr/README.md (new, ~6 lines): numbering policy — root docs/adr/
NNN = cross-component; catalog/docs/adr/ NNN = catalog-internal; cite
as "ADR-008" vs "catalog-ADR-002". Plus: pending decisions are referred
to by TOPIC label ("ADR candidate: <topic>"), numbers assigned only at
acceptance.
2g. Apply that policy: in docs/freeze/RESUME-MENU.md (and anywhere else),
replace "ADR-013 (candidate)" with "ADR candidate: pydantic-boundary" —
two different decisions currently both claim number 013 (the other is
krono-promotion).
One commit per item, chore:/docs: prefixes.

─────────────────────────────────────────────────────────────────────────────
PART 3 — RESUME.md at repo root (write last)
─────────────────────────────────────────────────────────────────────────────
Audience: a zero-context future session. Under 120 lines. Verify every path
you reference exists. Absorb docs/freeze/RESUME-MENU.md into this file, then
replace RESUME-MENU.md's body with one line pointing here (no duplicate
menus).


Read order: AGENTS.md → this file → MIGRATION-STATUS.md →
docs/freeze/DOC-TRUST-REPORT.md → the ADR of the resumed workstream.
Three-sentence state summary (source: MIGRATION-STATUS.md).
Resume menu, priority order:
(1) Execute ADR-010/012 deletion queue — UNBLOCKED; rewire
kitchen_cam/machining.py to kuchnie_core imports, delete the
deprecated trio, rewrite their tests; the 13 xpasses confirm parity.
(2) Repair kitchen-erp tests + delete old BOM path per ADR-011
(calculate_cost / use_new_bom / non-_new trace methods).
(3) ADR-011 follow-up: BOMGenerator → kuchnie_core.decompose();
Material table becomes catalog mirror.
(4) Write tests for home-builder-adapter extract.py/cli.py (currently
zero tests — see MIGRATION-STATUS).
(5) DECISION — ADR candidate: krono-promotion (rename off -mvp, route
catalog_db.py to catalog service per ADR-008).
(6) DECISION — ADR candidate: pydantic-boundary.
(7) Post-(1): rewrite kitchen-cam README/ROADMAP/specs (D4);
post-(3): rename kitchen-erp recipes to "cost recipes" (D5).
DO-NOT list: no features on kitchen_cam.{models,panel_calculator,
csv_generator} (deprecated, ADR-010/012); no extending the old BOM path
(ADR-011); no extending krono catalog_db.py (ADR-008); never modify
external home_builder_5; don't trust STALE-stamped docs; environment
notes — catalog/.venv lacks pytest (use root venv), clean the 23
orphaned .pyc under home-builder-adapter/tests/pycache.
Trust rule verbatim: "ADRs record decisions, not state. For state, read
MIGRATION-STATUS.md and verify with the commands it lists. Any
document's claim about code is stale until re-verified in your session."


Commit: docs: RESUME.md — freeze re-entry point.

─────────────────────────────────────────────────────────────────────────────
PART 4 — Close
─────────────────────────────────────────────────────────────────────────────
git tag -f freeze-2026-07 -m "development pause; entry: RESUME.md" on the
final commit. Confirm git status --porcelain is empty.

Final output: list of all commits made (hash + one line), the tag's new
target, and the full text of RESUME.md.
