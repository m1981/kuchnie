# Implementation Plan: Manifest-First Pipeline

## Context

The kitchen plugin generates I/L/U kitchen layouts from JSON configs via
Blender. Cabinets are "not looking correct" and the current inspection
pipeline (OBJ/glTF re-parsing) is lossy, indirect, and can't trace
problems back to their source.

**Goal:** Replace the indirect OBJ/glTF inspection pipeline with a direct
JSON manifest that captures exact geometry from bpy, includes expected-vs-
actual validation, and is readable by both LLM agents and humans.

---

## Current State

```
  config → layout → geometry_builder (bpy) → OBJ/glTF → inspection scripts → JSON
                                                  ↑
                                          6 lossy steps
                                          before validation
```

**Problems:**
- OBJ has no units (hardcoded `*1000` heuristic)
- Coordinate system detection is fragile guesswork
- Multi-object index remapping bug in OBJ parsing
- glTF Y-up → Z-up conversion is an extra failure point
- Inspection scripts can't trace back to which build step broke
- Expected dimensions hardcoded in Python scripts
- Validation is disconnected from geometry generation

---

## Target State

```
  config → layout → geometry_builder (bpy) → JSON manifest → validator → report
                                                     ↓
                                              .blend (visual only)
                                              OBJ/glTF (optional interop)
```

**Benefits:**
- Units explicit in manifest (`"units": "meters"`)
- Coordinate system documented once
- Local + world coordinates, exact transforms
- Expected-vs-actual validation inline
- Layout metadata (runs, turns, directions) preserved
- LLM agent reads plain JSON — no format parsing
- Validation happens at the source, not after export

---

## Phases

### Phase 1: Geometry Manifest Export (Layer 4)

**Goal:** Replace `geometry_inspector.py` and `geometry_validator.py` with a
single, enhanced manifest exporter.

#### Step 1.1: Create `src/geometry_manifest.py`

New file. Primary output of every build.

```
Functions:
  export_manifest(objects, path, settings, config) → dict
  _extract_object(obj, settings) → dict
  _build_layout_metadata(config) → dict
  _compute_expected_dims(obj_name, settings) → dict
  _classify_object(name) → str
  _validate_object(obj_data, expected) → dict

Output: manifest JSON (v2.0 schema)
```

**Key improvements over existing `geometry_inspector.py`:**
- Add `world_bounds` (not just local)
- Add `expected_dimensions_mm` per object
- Add `validation` dict per object (inline pass/fail)
- Add `layout` section with run metadata
- Add `construction` section with board thicknesses
- Add `validation_summary` at top level
- Add `source_config` path reference

#### Step 1.2: Create `src/manifest_validator.py`

New file. Reads manifest, runs checks.

```
Functions:
  validate_manifest(manifest) → ValidationResult
  check_dimensions(obj, tolerance_mm) → list[Issue]
  check_overlaps(objects) → list[Issue]
  check_clearances(objects, min_clearance_mm) → list[Issue]
  check_vertex_count(obj) → list[Issue]
  check_standard_widths(objects, settings) → list[Issue]
  check_run_continuity(layout) → list[Issue]
```

**Note:** This module reads the manifest dict — no bpy dependency. Can run
standalone or as part of the build pipeline.

#### Step 1.3: Create `schemas/manifest_v2.schema.json`

JSON Schema for the manifest format. Enables:
- Schema validation in tests
- Auto-documentation for LLM agents
- CI checks: reject malformed manifests

```
Required fields:
  format, version, units, coordinate_system,
  settings, layout, objects, validation_summary

Each object requires:
  name, type, classification, level, parent,
  transform, local_bounds, local_dimensions_mm,
  world_bounds, world_dimensions_mm,
  vertex_count, face_count, validation
```

#### Step 1.4: Update `src/main.py`

```python
# Change: --export-inspect becomes --export-manifest (default: ON)
# Add: --validate flag (runs manifest_validator after export)
# Keep: --export-obj, --export-gltf, --export-blend as optional

# New flow in main():
manifest = export_manifest(objects, manifest_path, settings, config)
if args["validate"]:
    issues = validate_manifest(manifest)
    print_validation_report(issues)
```

**File changes:**
- `src/main.py` — add manifest export, make it default behavior
- Remove `--export-inspect` and `--export-manifest` flags (manifest always exports)
- Add `--validate` flag
- Keep `--export-obj`, `--export-gltf`, `--export-blend` as optional

---

### Phase 2: Test the Manifest Pipeline

**Goal:** Ensure the manifest captures correct geometry and validation works.

#### Step 2.1: Create `tests/test_manifest_schema.py`

```python
def test_manifest_has_required_fields()
def test_manifest_units_are_meters()
def test_manifest_coordinate_system_is_z_up()
def test_manifest_version_is_2()
def test_manifest_layout_matches_config()
def test_all_objects_have_validation()
def test_validation_summary_counts_match()
```

#### Step 2.2: Create `tests/test_manifest_objects.py`

```python
def test_carcass_has_16_vertices()
def test_back_panel_is_thin()
def test_door_has_8_vertices()
def test_filler_dimensions_match_config()
def test_countertop_has_overhangs()
def test_local_and_world_bounds_differ_for_rotated_objects()
```

#### Step 2.3: Create `tests/test_manifest_validation.py`

```python
def test_dimensions_within_tolerance_pass()
def test_dimensions_outside_tolerance_fail()
def test_overlap_detection()
def test_clearance_check()
def test_standard_width_check()
def test_run_direction_continuity()
```

#### Step 2.4: Create `tests/test_manifest_layout.py`

```python
def test_i_shape_has_one_run()
def test_l_shape_has_two_runs_with_turn()
def test_u_shape_has_three_runs_with_turns()
def test_run_positions_chain_correctly()
def test_cabinet_list_in_run_matches_config()
```

---

### Phase 3: Standalone Validation Script

**Goal:** LLM agent or CI can validate a manifest without Blender.

#### Step 3.1: Create `scripts/validate_manifest.py`

```python
# Usage:
#   python scripts/validate_manifest.py output/meshes/l_shape_manifest.json
#   python scripts/validate_manifest.py --schema schemas/manifest_v2.schema.json
#
# No bpy dependency. Pure stdlib + json.
#
# Output:
#   - Schema validation (structure)
#   - Dimension checks (per object)
#   - Overlap detection (world bounds intersection)
#   - Clearance checks (walkway ≥ 900mm)
#   - Standard width compliance
#   - Summary: N passed, M failed, K warnings
```

#### Step 3.2: Create `scripts/summarize_manifest.py`

Human/LLM-friendly summary of a manifest.

```python
# Usage:
#   python scripts/summarize_manifest.py output/meshes/l_shape_manifest.json
#
# Output:
#   L-shape kitchen: 2 runs, 12 cabinets
#   Run 1 (back wall, east): 3550mm — 6 cabinets
#   Run 2 (left wall, south): 1850mm — 4 cabinets
#
#   Dimensions: 12/12 OK
#   Overlaps: none
#   Warnings: 1 (filler vertex count)
```

---

### Phase 4: Clean Up Old Pipeline

**Goal:** Remove deprecated inspection scripts, update docs.

#### Step 4.1: Remove deprecated scripts

| File | Action | Reason |
|---|---|---|
| `scripts/analyze_reference_obj.py` | Delete | Replaced by manifest validation |
| `scripts/convert_obj_to_gltf.py` | Delete | Not needed (manifest is direct) |
| `scripts/analyze_gltf_v2.py` | Delete | Replaced by manifest validation |
| `scripts/compare_with_reference.py` | Delete | Replaced by inline validation |
| `scripts/validate_obj.py` | Delete | Replaced by manifest validation |
| `src/geometry_inspector.py` | Delete | Replaced by `geometry_manifest.py` |
| `src/geometry_validator.py` | Delete | Replaced by `manifest_validator.py` |

#### Step 4.2: Update main.py references

- Remove imports of deleted modules
- Remove `--export-inspect` and `--export-manifest` flags
- Manifest exports unconditionally (or with `--no-manifest` to skip)

#### Step 4.3: Update docs

| File | Change |
|---|---|
| `docs/README.md` | Update reading guide, add manifest docs |
| `docs/geometry-inspection-tools.md` | Rewrite: manifest-based workflow |
| `docs/3d-format-strategy.md` | Add note: manifest supersedes format inspection |

---

### Phase 5: Harden the Generator

**Goal:** Use the manifest to find and fix the actual cabinet bugs.

#### Step 5.1: Run manifest on all configs

```bash
for config in configs/ref_*.json; do
    blender --background --python src/main.py -- "$config" --validate
done
```

Collect all validation failures. Categorize:
- **Dimension mismatches** → fix `geometry_builder.py` or `cabinet_geometry.py`
- **Position errors** → fix `geometry_builder.py` turn/rotation logic
- **Overlap issues** → fix `layout.py` gap handling or `geometry_builder.py` positioning
- **Vertex count issues** → fix mesh construction in `geometry_builder.py`

#### Step 5.2: Add expected-vs-actual tolerance tests

For each config, add a test that:
1. Runs the build
2. Reads the manifest
3. Asserts all dimensions within 2mm tolerance
4. Asserts no overlaps
5. Asserts all validation passes

```python
def test_ref_i_shape_manifest_passes_validation():
    config = load_config("configs/ref_i_shape.json")
    objects = build_kitchen(config)
    manifest = export_manifest(objects, settings=config["settings"])
    result = validate_manifest(manifest)
    assert result.failed == 0, result.issues

def test_ref_l_shape_manifest_passes_validation():
    # Same pattern
    ...

def test_ref_u_shape_manifest_passes_validation():
    # Same pattern
    ...
```

#### Step 5.3: Fix generator bugs found by manifest

The manifest will pinpoint exactly which object has wrong dimensions and
what the expected values are. Fix in `geometry_builder.py` or
`cabinet_geometry.py`, re-run, check manifest again.

---

## Implementation Order

```
  Week 1:
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 1.1  Create geometry_manifest.py                       │  2 days
  │ Step 1.2  Create manifest_validator.py                      │  1 day
  │ Step 1.3  Create manifest_v2.schema.json                    │  0.5 day
  │ Step 1.4  Update main.py                                    │  0.5 day
  └─────────────────────────────────────────────────────────────┘

  Week 2:
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 2.1  test_manifest_schema.py                           │  0.5 day
  │ Step 2.2  test_manifest_objects.py                          │  0.5 day
  │ Step 2.3  test_manifest_validation.py                       │  0.5 day
  │ Step 2.4  test_manifest_layout.py                           │  0.5 day
  │ Step 3.1  scripts/validate_manifest.py                      │  0.5 day
  │ Step 3.2  scripts/summarize_manifest.py                     │  0.5 day
  └─────────────────────────────────────────────────────────────┘

  Week 3:
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 4.1  Remove deprecated scripts                         │  0.5 day
  │ Step 4.2  Update main.py references                         │  0.5 day
  │ Step 4.3  Update docs                                       │  0.5 day
  │ Step 5.1  Run manifest on all configs, collect failures     │  0.5 day
  │ Step 5.2  Add tolerance tests for each config               │  1 day
  │ Step 5.3  Fix generator bugs                                │  2-3 days
  └─────────────────────────────────────────────────────────────┘
```

**Total: ~3 weeks** (can compress to 2 if Phases 4 and 5 overlap)

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Manifest misses data that OBJ/glTF had | Keep OBJ/glTF export as optional; compare outputs during transition |
| Schema gets out of sync with code | JSON Schema + schema validation in tests catches drift |
| bpy changes break manifest export | bpy-dependent tests skipped in CI, run manually before release |
| Validation is too strict / too loose | Tolerance values configurable in manifest; adjust based on real data |
| LLM agent can't parse manifest | Manifest is plain JSON; add `summarize_manifest.py` for text output |

---

## Success Criteria

1. **Every build produces a manifest** — no special flags needed
2. **Manifest has zero unit ambiguity** — `"units": "meters"` always present
3. **All objects have inline validation** — pass/fail per dimension check
4. **Validation summary catches known issues** — the "cabinets not looking correct" bugs are surfaced as structured errors with expected/actual values
5. **Standalone validator works without bpy** — `python scripts/validate_manifest.py manifest.json`
6. **All existing tests still pass** — no regressions
7. **New manifest tests pass** — schema, objects, validation, layout
8. **Deprecated scripts removed** — no more OBJ/glTF inspection scripts

---

## File Inventory

### New Files

| File | Layer | Purpose |
|---|---|---|
| `src/geometry_manifest.py` | 4 | Manifest export (primary output) |
| `src/manifest_validator.py` | 4 | Manifest validation checks |
| `schemas/manifest_v2.schema.json` | — | JSON Schema for manifest format |
| `scripts/validate_manifest.py` | — | Standalone validation (no bpy) |
| `scripts/summarize_manifest.py` | — | Human/LLM summary of manifest |
| `tests/test_manifest_schema.py` | — | Schema compliance tests |
| `tests/test_manifest_objects.py` | — | Object detail tests |
| `tests/test_manifest_validation.py` | — | Validation logic tests |
| `tests/test_manifest_layout.py` | — | Layout metadata tests |

### Modified Files

| File | Change |
|---|---|
| `src/main.py` | Add manifest export (default), add `--validate`, remove old flags |
| `docs/README.md` | Update reading guide |
| `docs/geometry-inspection-tools.md` | Rewrite for manifest workflow |

### Deleted Files

| File | Reason |
|---|---|
| `scripts/analyze_reference_obj.py` | Replaced by manifest validation |
| `scripts/convert_obj_to_gltf.py` | Not needed |
| `scripts/analyze_gltf_v2.py` | Replaced by manifest validation |
| `scripts/compare_with_reference.py` | Replaced by inline validation |
| `scripts/validate_obj.py` | Replaced by manifest validation |
| `src/geometry_inspector.py` | Replaced by `geometry_manifest.py` |
| `src/geometry_validator.py` | Replaced by `manifest_validator.py` |
