# Spec: kitchen-erp height parameter set — per-project working heights on ProjectDefaults

> Reader: whoever implements the project-level height lines or wires G1
> across legs | Enables: storing the playbook Phase-1 heights (worktop,
> wall-unit line, tall line) once per project with the elbow derivation, and
> knowing who consumes them | Update-trigger: the elbow formula or default
> band changes in the playbook, ProjectDefaults changes shape, or a new
> consumer joins G1

Serves: UC-11 phase 1 (fix working heights before zones — the playbook's
"heights → zones → corner → widths" starts here).

## Intent

The playbook fixes working heights once per project (Phase 1): worktop
height derived from the user's elbow, wall-unit line, tall line. The repo
has the carcass math (`ConstructionMethod`: 720 carcass, plinth, reveals)
but nothing stores per-project lines — so layout has nothing to consume and
G1 can check consistency within a row but not against the project's decided
lines across both legs. This spec adds the height parameter set to the
existing `ProjectDefaults` (one row per project already), derived from the
survey pack's user profile, consumed by `validate_rows`/G1 across legs.
Pro-tool analog: PRO100/Winner set installation heights once per job;
Polyboard cascades job parameters — trivial to add, high leverage.

**Non-goals**: no per-cabinet height overrides (a cabinet diverging from
the line is G1's finding, not a parameter); no carcass-math ownership
(`ConstructionMethod` keeps the 720/plinth/reveal arithmetic — this set
stores the decided lines, not how a carcass meets them); no ergonomic
advisor UI beyond showing the derivation.

### Purpose & scope

kitchen-erp's `ProjectDefaults` is the canonical source for **the decided
per-project height lines**. It is explicitly not the source for carcass
construction math (`kuchnie_core.construction.ConstructionMethod` is) nor
for the measured elbow height itself (the survey pack's
`survey_user_profile` artifact is — this set records the derivation from
it).

### Data model

Additive fields on `ProjectDefaults` (SQLModel, additive migration):

| Field | Meaning | Default / rule |
|---|---|---|
| `elbow_height_mm` | measured user elbow height (from the survey pack) | nullable; without it the band default applies |
| `worktop_height_mm` | decided worktop line | elbow formula: worktop = elbow − 100..150; default band 850..910 (= 720 carcass + 100..150 plinth + 38 top) |
| `wall_line_mm` | wall-unit bottom line | decided per project |
| `tall_line_mm` | tall/column top line (one continuous top line, playbook Phase 5) | decided per project |

Derivation helper `derive_worktop_height(elbow_mm)` returns the formula
band midpoint with the chosen offset recorded; a decided
`worktop_height_mm` outside 850..910 without a recorded elbow derivation
renders as a warning in the project record (the operator can still decide
it — bodies differ).

### API contract

Model-level operations (Reflex UI sits on top):

| Operation | Trigger | Returns | Failure modes |
|---|---|---|---|
| `derive_worktop_height(elbow_mm, offset_mm=...)` | operator enters elbow from the survey pack | height in mm; offset outside 100..150 raises `ValueError` | named error, not clamping |
| `ProjectDefaults` load/save | project setup | the three lines + elbow persisted | existing spine semantics |
| `validate_rows(kitchen, heights=...)` (kuchnie-core consumer) | buildability verdict run | G1 findings when a leg's worktop line diverges from the project line | finding, not exception — verdict machinery decides severity |

### Business / validation rules

- The elbow formula and the 850..910 default band are playbook
  design-practice values: encoded here as the derivation and the warning
  band, cited from the playbook rather than duplicated elsewhere.
- G1-across-legs: with the height set present, G1 compares BOTH legs'
  worktop lines against `worktop_height_mm` (not merely intra-row
  consistency); without a height set G1 keeps today's behaviour — additive,
  not breaking.
- Heights are decided at Phase 1 and changed consciously: an edit after
  stage 4 renders a project-record warning (decomposition already consumed
  them).

### Non-functional requirements

Four numeric columns on an existing one-row-per-project table — no
latency/availability budget beyond the ERP's own. Freshness: the set is
decided once per project; the survey pack artifact remains the measured
source if re-derivation is needed.

### Migration / versioning policy

Additive nullable columns — existing projects load with the band default
behaviour and today's G1 semantics. Renaming or repurposing a line field
is a breaking change requiring a consumer sweep (validate_rows, UI,
future elevation sheets) and a spec update.

### Test / acceptance strategy

`kitchen-erp/tests/test_height_parameters.py`: derivation fixtures
(elbow 990 → 840..890 band), offset refusal, persistence round-trip, and
the G1-across-legs consumption path against a two-leg fixture kitchen.
SC wiring at implementation (SC- markers + .sc.txt when the tests exist,
per the wtuu precedent).

## Decisions

- `docs/adr/011-*.md` — kitchen-erp owns per-project ops data (the spine
  this set rides).
- `docs/adr/002-construction-method-separation.md` — carcass math stays in
  `ConstructionMethod`; this set stores decided lines only.
- `docs/adr/034-l-layout-model-rebuilt-minimal-in-core.md` — the two-leg
  G1 consumer this set feeds arrives with the L-layout model.

## Ground truths

- tr-e51ef4fd — Project spine (ProjectDefaults hangs off Project;
  transition/stage machinery this set rides).
- tr-23661434 — `validate_rows` encodes G1 worktop-line consistency (the
  consumer that gains the across-legs form).

## Work

- wk-0bc4d5c4 — Height parameter set on ProjectDefaults: worktop/wall-line/tall-line with elbow derivation, consumed by validate_rows G1 across legs (Stage 1, review §C)

## Acceptance

Pre-written `done --claim` texts, scoped to evidence commands:

- "ProjectDefaults carries elbow_height_mm, worktop_height_mm,
  wall_line_mm and tall_line_mm, and derive_worktop_height applies the
  elbow minus 100..150 formula with the 850..910 default band, refusing an
  out-of-band offset; pinned by
  kitchen-erp/tests/test_height_parameters.py" (`wk-0bc4d5c4`)
- "validate_rows consumes a supplied height parameter set and G1 reports a
  leg whose worktop line diverges from the decided worktop_height_mm
  line, covered by a two-leg fixture in
  kitchen-erp/tests/test_height_parameters.py" (`wk-0bc4d5c4`)

## Verification & Validation

Verification: derivation + consumption contract tests per the API
contract table — oracle carried by `wk-0bc4d5c4` (`--accept-cmd`);
intended accept command:
`.venv/bin/python -m pytest kitchen-erp/tests/test_height_parameters.py -q`.

Validation: project P1's heights derived from a real measured elbow and
judged at the fitting (does the band suit the client's body) —
attestation pending; when the operator files it (UNVERIFIED,
`--ttl-days`), edit this line to cite the id.

Residual (accepted, not closable): "a correctly-stored wrong decision —
heights the client approved on paper and regrets at the hob"
