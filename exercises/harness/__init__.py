"""Shared harness for golden-first e2e exercises.

Convention: docs/e2e-exercise-convention.md. Modules:

  gaps     — GapLog (hand re-entry / workaround logging, the ergonomics metric)
  golden   — golden panels.csv parsing + grain-aware diff vs a decomposition
  writers  — rozrys / BOM / CNC writers from a DecompositionResult
  hb5      — Blender-side helpers (import only inside Blender; needs bpy)
  scaffold — CLI: create a new exercise directory from templates

The two pre-harness exercises (walking-skeleton-d60, e2e-d60-legrabox) are
claim-watched artifacts and stay as-is; new scenarios start from scaffold.
"""
