# Spec: home-builder-adapter position extraction r4 — two Runs + corner from an hb5 scene

> Reader: whoever extends the extractor to carry positions, or debugs a
> two-leg scene that flattened | Enables: reading the hb5→kuchnie translation
> boundary for positions and wall assignment without re-deriving it from
> `extract.py` | Update-trigger: hb5 changes its cage/property vocabulary,
> the L-layout model changes shape, or a mapping row is found wrong

Serves: UC-2 (production pack — step 1 extraction, hook), UC-11 phases 2–5
(extracted positions are what the zone/corner/run phases stand on).

## Intent

`cabinets_to_kitchen` today flattens a whole hb5 scene into one Row with
wall dims inferred by summing cabinet widths — world positions and wall
membership are read from the scene and then thrown away. Round 4 of the
extraction-fidelity lineage keeps them: per-cabinet world position + wall
assignment from hb5 cage objects, emitting two Runs + a corner link for a
two-wall scene instead of one flattened Row. The adapter stays an ACL: it
translates hb5's vocabulary into the kuchnie-core L-layout model
(`kuchnie-core/docs/specs/l-layout-model.md`) and produces the geometry
manifest the validator already checks. Zero new machinery — this extends
extract.py where r2/r3 already work.

**NOTE — fixture first:** the P1 hb5 scene arrives later; implementation
starts on a **synthetic L-scene fixture** (two perpendicular walls, a
corner-blind + one cabinet per leg), which then becomes the regression
fixture when P1's real scene lands beside it.

**Non-goals**: no write-back to hb5 (read-only boundary, revisited per
`docs/pattern-conformance.md` row 10 criteria); no room/door/window
extraction; no zone inference (a designer decision, not scene data); no
layout repair — a geometrically inconsistent scene is reported, not fixed.

### External dependency pin

home_builder_5 Blender addon, present at the pinned local path
(tr-bd0ba211), exercised through the harness which records hb5 path + SHA
and Blender binary + version in `run-manifest.json` per run
(tr-380842e6). Owned by an external author; changes arrive silently on
update — the pin plus manifest is the notice mechanism.

### Translation map

| External field/concept | Internal field | Notes |
|---|---|---|
| cabinet cage `matrix_world` translation | cabinet world position → position along its `Run` | Blender metres → mm, existing conversion conventions |
| cabinet cage rotation (Z) | `Run.direction` membership (which wall the cabinet faces) | quantized to `east/north/west/south`; the manifest's direction vocabulary |
| grouping of cages by shared wall line + direction | one `Run` per wall, `start/end_position_mm` from member extremes | replaces the single "Extracted Row" |
| perpendicular Run pair meeting at extremes | `CornerLink` (two Run ids, `turn`) | corner cabinet identified by type mapping (dolna_narozna_slepa) |
| `obj.dimensions` / explicit dim props | `CabinetInstance.width/height/depth_mm` | existing r1–r3 behaviour, unchanged |
| toe-kick property | `plinth_height_mm` | existing, unchanged |
| drawer stack (bottom-up) | `CabinetInstance.drawers` | existing r2 behaviour, unchanged (G8 order contract) |

This table is the contract; a new column lands here before it lands in
code.

### Boundary direction

Read-only. hb5 is the editor (ADR-009, `docs/adr/009-*.md`); the adapter
extracts truth after design. Write-back is a standing non-goal revisited
per pattern-conformance row 10 (a real need, named, twice).

### Divergence handling

- Scene with one wall: one Run, no corner link — the r3 behaviour, kept
  back-compatible (flat consumers unaffected per ADR-034's clause).
- Cages whose positions chain into a gap/overlap beyond tolerance: the
  manifest is still emitted and `check_run_continuity` reports it — the
  adapter does not repair geometry, the validator names the fault.
- Missing/unknown cage properties: recorded as named findings in the
  harness GapLog (strict mode escalates), matching r2's discipline.
- More than two walls: out of scope for r4 — emitted as runs without a
  corner link plus a named GapLog finding, not a crash.

### Compatibility watch

`run-manifest.json` pins repo SHA, hb5 path + SHA and Blender version on
every harness run (tr-380842e6) — a mapping break after an hb5 update is
attributable to the recorded delta. The extraction test suite doubles as
the compatibility probe.

### Regression contract

Golden-master: the synthetic L-scene fixture (this spec's NOTE) run
through the harness L-scenario with `--strict`; later, P1's real hb5
scene is committed beside it as the second fixture. The existing
walking-skeleton-d60 golden guards the one-wall path against regression.

## Decisions

- `docs/adr/034-l-layout-model-rebuilt-minimal-in-core.md` — adapter r4 is
  the producer of the rebuilt model's manifest.
- `docs/adr/009-*.md` — hb5 owns placement; the adapter is the ACL.
- `docs/adr/035-playbook-operating-decisions.md` — G5 stays a human
  checklist: r4's job ends at faithful positions on the plan-sheet data;
  triangle/landing legality is attested per project, not extracted.

## Ground truths

- tr-bd0ba211 — hb5 addon present at the pinned path (the external
  system exists — dependency-pin row).
- tr-239065a8 — extraction derives cabinet envelopes from cages (bbox →
  mm, toe kick) — the rows marked "existing, unchanged" above.
- tr-380842e6 — harness r2: runner chains the legs and writes the
  toolchain manifest; GapLog + strict mode (the regression/watch
  machinery this spec leans on).

## Work

Extends the extraction-fidelity lineage — wk-81a47ab8 (r2, closed) and
wk-cd815fba (r3, open) are Work context, not this spec's implementers:

- wk-cc0daf81 — Adapter position extraction r4: per-cabinet world position + wall assignment from hb5 cages, two-wall scene emits two Runs + corner link on a synthetic L-scene fixture (Stage 1, review §C)

## Acceptance

Pre-written `done --claim` texts, scoped to evidence commands:

- "home-builder-adapter extraction carries per-cabinet world position and
  wall assignment from hb5 cage objects, and a two-wall synthetic L-scene
  extracts into two Runs joined by a corner link whose manifest passes
  check_run_continuity; proven by the harness L-scenario in strict mode
  without hand re-entry" (`wk-cc0daf81`)
- "a one-wall scene still extracts into a single Run with unchanged
  downstream results, covered by the existing walking-skeleton-d60 golden
  alongside the L-scenario" (`wk-cc0daf81`)

## Verification & Validation

Verification: consumer-driven contract tests against the translation map,
executed as the harness L-scenario golden run — oracle carried by
`wk-cc0daf81` (`--accept-cmd`); intended accept command:
`.venv/bin/python exercises/harness/runner.py walking-skeleton-L --strict`
(validation-kind oracle per ADR-014, consistent with the harness runner
convention). SC wiring at implementation (SC- markers + .sc.txt when the
scenario and tests exist, per the wtuu precedent).

Validation: r4 run against project P1's real hb5 scene when it arrives
(field mapping judged against the room, not the fixture) — attestation
pending; when the operator files it (UNVERIFIED, `--ttl-days`), edit this
line to cite the id. The per-project G5 human-checklist attestation
(ADR-035) is filed on the plan artifacts derived from these positions —
per project, not here.

Residual (accepted, not closable): "the third party's future — an hb5
update changing cage vocabulary is detected by the pinned manifest and
probes, never prevented"
