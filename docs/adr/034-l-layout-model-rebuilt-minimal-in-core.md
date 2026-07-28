# ADR-034: L-layout model rebuilt minimally in kuchnie-core

> Reader: anyone about to give the live domain positions, legs or a corner —
> or tempted to resurrect the retired layout classes | Enables: building the
> L-layout model in the right place (kuchnie_core, against the existing
> validator manifest contract) without re-litigating rebuild-vs-recover |
> Update-trigger: the manifest contract in `kuchnie_core/validator.py`
> changes, or a genuine need appears that the minimal value objects cannot
> carry

## Status

Accepted 2026-07-29 (operator decision, review §F risk 1 — PM lean
confirmed). Settles the "resurrect vs rebuild" question raised by
`docs/reviews/domain-pm-review-2026-07-28.md`; executed by the Stage 1–2
roadmap rows (L-layout model, adapter position extraction r4). Extends
ADR-012's model-extension discipline; respects ADR-009's editor boundary.

## Context

The live domain `Kitchen`/`Row` is flat: a `Row` is a label plus wall
W/H plus a cabinet list — no positions, no corner link, no leg
adjacency. The playbook (`docs/l-kitchen-design-playbook.md`) needs
legs, a corner and positions for Phases 2–5, and buildability gates
G2/G3/G4/G5/G7 sit permanently SKIPPED for want of exactly that data.

Two ghosts of a richer model exist:

1. `kuchnie_core.validator.check_run_continuity` (with
   `validate_manifest`) already validates a **geometry manifest** — runs
   with `start/end_position_mm`, `direction`, `turn`, L/I-shape — that
   nothing in the repo produces. The validator half of the model exists
   and is tested (tr-167da3d5 pins the end-to-end run on the reference
   manifests).
2. `home-builder-adapter/src/kitchen/__pycache__/` holds bytecode-only
   `Wall`/`Run`/`Layout`/`LayoutEngine` classes. Their source lives in
   the external, retired plugin-era project (pre-ADR-009; its name is on
   the forbidden-names list and deliberately not written here). The
   source is outside this repo, unaudited, and was written for an editor
   we no longer build.

## Decision

**Rebuild minimally in `kuchnie_core` — the retired plugin-era model is
not resurrected.** Concretely:

- New minimal **value objects** in `kuchnie_core` (spec:
  `kuchnie-core/docs/specs/l-layout-model.md`): `Run` gains start/end
  position, direction and a corner link; `Kitchen` gains leg adjacency.
  A value-object's worth of code, not a CAD kernel.
- The **existing validator manifest contract is the target**: the model
  emits the geometry manifest that `check_run_continuity` /
  `validate_manifest` in `kuchnie_core/validator.py` already validate.
  The contract is not redesigned to fit the model; the model is built to
  fit the contract.
- **No editor, no CAD kernel, no geometry engine.** hb5 stays the layout
  editor per ADR-009 (`docs/adr/009-*.md`); the repo owns the extracted
  truth only.
- The `__pycache__` bytecode is never decompiled, imported or ported;
  its presence confers nothing. It can be atticed when the adapter
  drops the directory.
- Flat-`Kitchen` loads stay back-compatible: positions and legs are
  additive, and a Kitchen without them keeps validating as today.

## Consequences

- The one hole feeding the parked gates closes cheaply: G2 (corner
  fillers), G3 (collision walkthrough), G4 (appliance-sheet data
  carriage), G5 (the data a human checklist reads — see ADR-035) and G7
  (worktop joint) unpark **progressively** as the model plus its
  producers land, SKIP remaining honest whenever data is genuinely
  absent (tr-65aa5969's verdict shape is unchanged).
- **Adapter extraction r4 becomes the producer**: per-cabinet world
  position + wall assignment from hb5 cages → two Runs + a corner
  (spec: `home-builder-adapter/docs/specs/adapter-position-extraction.md`),
  extending the extraction-fidelity lineage instead of a parallel
  family.
- Rebuilding costs re-deriving corner width consumption and run
  chaining from the playbook rather than inheriting them — accepted:
  the old model was plugin-era, editor-shaped, and its source is
  unreachable from this repo anyway.
- Anything the minimal model refuses to carry (zones-as-entities, room
  walls, doors/windows, traffic paths) stays out until a gate or an
  emitted document demonstrably needs it.
