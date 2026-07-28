# Spec: kitchen-erp survey pack — structured Phase-0 capture with a 2→3 gate

> Reader: whoever implements or reviews the measurement-visit capture on the
> project spine | Enables: knowing which named artifact kinds make a survey
> pack complete and how the stage 2→3 transition refuses an incomplete one |
> Update-trigger: the required-kind list changes, the stage vocabulary
> changes, or the playbook's Phase-0 input list changes

Serves: UC-12 (capture a measurement visit into a survey pack — this spec is
its system-side goal), UC-11 phase 0 (the pack is UC-11's Phase-0
precondition).

## Intent

The playbook's Phase-0 rule: missing input = redesign later. Today the spine
stores attachments (ArtifactRef) with free-form kinds, so nothing
distinguishes a complete survey pack from a folder of photos — and design
(stage 3) can start on missing inputs. This spec makes the survey pack a
first-class, checkable thing: a fixed enumeration of named ArtifactRef kinds
plus a completeness checklist, wired into `Project.transition_stage` so the
2→3 move refuses an incomplete pack and names what is missing. It lives in
kitchen-erp because the pack is spine data, not geometry.

**Non-goals**: no geometry capture — room geometry stays in Blender/hb5 per
the stage-2 boundary in `docs/specs/process-coverage.md` ("attachments
only"); no parsing/OCR of appliance model sheets (the sheet is archived
verbatim, its cutout dims are read by a human until gate G4 work says
otherwise); no survey mobile app or form UI beyond the existing project
record surfaces; no backfill obligation for legacy projects already past
stage 2.

### Purpose & scope

kitchen-erp is the canonical source for **survey-pack composition and
completeness status** per project. It is explicitly not the source for room
geometry (hb5 owns that, per ADR-009 — `docs/adr/009-*.md`) nor for
appliance dimension truth (the manufacturer sheet itself is; the pack only
guarantees the sheet is on file).

### Data model

Named ArtifactRef kinds (the `kind` column of the existing ArtifactRef
table — additive vocabulary, no schema migration):

| Kind | Content archived | Playbook Phase-0 item |
|---|---|---|
| `survey_dims` | wall dimensions + diagonals (sketch/PDF/photo) | walls, diagonals |
| `survey_media` | media points: water, drain, gas, sockets, duct | media points |
| `survey_appliance_sheet` | one manufacturer model sheet per appliance | appliance models |
| `survey_user_profile` | user height, elbow height, handedness | user height/handedness |
| `survey_budget` | budget bracket agreed with the client | budget bracket |

A `REQUIRED_SURVEY_KINDS` constant in `kitchen_erp.core` enumerates the five
kinds above. Completeness = the project carries at least one ArtifactRef of
each required kind. `survey_appliance_sheet` may repeat (one per appliance);
the checklist counts the kind as covered from the first sheet — per-appliance
coverage is gate G4's later concern, not this pack's.

### API contract

Model-level operations, not HTTP (the ERP is a Reflex app over these):

| Operation | Trigger | Returns | Failure modes |
|---|---|---|---|
| `Project.add_artifact(kind, path)` | surveyor attaches an item | ArtifactRef (existing method, unchanged) | unchanged |
| `survey_pack_missing(project)` | UI checklist render; transition guard | list of missing required kinds (empty = complete) | — |
| `Project.transition_stage("3_layout_design")` | operator advances the project | stage advances | `StageTransitionError` naming the missing kinds when the pack is incomplete; existing unknown/backward refusals unchanged |

### Business / validation rules

- The 2→3 refusal is the point: a project at `2_pomiar` with a missing
  required kind does not reach `3_layout_design`. Other transitions are
  untouched by this spec.
- Artifacts are archived verbatim and append-only (matching the Offer
  `source_ref` discipline); replacing a wrong scan means adding a new
  ArtifactRef, not editing one.
- The checklist renders in the project record so the surveyor sees the gap
  during the visit, not at the transition.

### Non-functional requirements

Local single-user SQLite via the existing spine; completeness is a simple
kind-set query — no latency or availability budget beyond the ERP's own.
Freshness: a pack describes one measurement visit; a re-measure appends new
artifacts (history preserved).

### Migration / versioning policy

Kinds are additive strings — adding an optional kind costs nothing. Growing
`REQUIRED_SURVEY_KINDS` is a policy change: it must update this spec and
considers projects mid-stage (a project already at stage ≥3 is not
retroactively blocked).

### Test / acceptance strategy

`kitchen-erp/tests/test_survey_pack.py`: fixture project — transition
refusal while incomplete (missing kinds named), then pass once the five
kinds are attached; `survey_pack_missing` covered for empty/partial/full
packs. SC wiring at implementation (SC- markers and the .sc.txt manifest
are minted when the tests exist, per the wtuu precedent).

## Decisions

- `docs/adr/011-*.md` — kitchen-erp owns the spine/ops artifacts (stage 2).
- `docs/adr/034-l-layout-model-rebuilt-minimal-in-core.md` — the pack feeds
  design-phase data needs without becoming a geometry model.

## Ground truths

- tr-e51ef4fd — Project spine with stage vocabulary, ArtifactRef table and
  forward-only `transition_stage` (the machinery this spec extends).

## Work

- wk-cc39b1b0 — Survey pack: named ArtifactRef kinds + completeness checklist, 2→3 transition refuses an incomplete pack (Stage 1, review §C)

## Acceptance

Pre-written `done --claim` texts, scoped to evidence commands:

- "kitchen-erp defines REQUIRED_SURVEY_KINDS (survey_dims, survey_media,
  survey_appliance_sheet, survey_user_profile, survey_budget) and
  survey_pack_missing reports which required kinds a project still lacks;
  pinned by kitchen-erp/tests/test_survey_pack.py" (`wk-cc39b1b0`)
- "Project.transition_stage from 2_pomiar to 3_layout_design raises
  StageTransitionError naming the missing survey kinds for an incomplete
  pack and advances once the pack is complete; pinned by refusal-then-pass
  fixtures in kitchen-erp/tests/test_survey_pack.py" (`wk-cc39b1b0`)

## Verification & Validation

Verification: fixture-driven contract tests for the refusal and the
checklist, per the API contract table — oracle carried by `wk-cc39b1b0`
(`--accept-cmd`); intended accept command:
`.venv/bin/python -m pytest kitchen-erp/tests/test_survey_pack.py -q`.

Validation: the pack's field usefulness is judged on project P1's real
measurement visit (does the checklist match what the room actually
demanded) — attestation pending; when the operator files it (UNVERIFIED,
`--ttl-days`), edit this line to cite the id. Until then this spec is
verified at the contract level, not yet validated.

Residual (accepted, not closable): "a checklist-complete pack whose
artifacts are individually wrong — a misread tape measure passes the kind
gate"
