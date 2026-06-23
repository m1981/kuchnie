# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

### Changed — BREAKING

- **Carcass construction: hollow box → 4 separate boards**
    - Each cabinet carcass is now 4 separate solid boxes (left, right, top, bottom)
    - 1mm technical gap between all boards — no shared surfaces
    - Each board: 8 vertices, 6 faces (was: 16 vertices, 17 faces for hollow box)
    - Manifest output: carcass now has child objects classified as `"board"`
    - Parent empty groups all boards for a cabinet

- **Door/drawer front position: back → front**
    - Fronts now positioned at Y=0 (front of cabinet) instead of Y=depth (back)
    - Fixes fronts appearing at the wrong end of the cabinet

- **Manifest classification: new `"board"` type**
    - Individual carcass panels are classified as `"board"` (was: `"carcass"`)
    - Parent empties remain `"carcass"` but have 0 vertices
    - Schema `manifest_v2.schema.json` updated with `"board"` enum value

### Added

- **Manifest-first pipeline** (primary output for every build)
    - `src/geometry_manifest.py` — JSON manifest export
    - `src/manifest_validator.py` — dimension, overlap, clearance checks
    - `schemas/manifest_v2.schema.json` — JSON Schema for manifest format
    - `scripts/validate_manifest.py` — standalone validation (no bpy)
    - `scripts/summarize_manifest.py` — LLM/human-friendly summary

- **Carcass construction details**
    - Board dimension tables in docs
    - Construction rules (butt joints, technical gaps)
    - Overlap detection with 50mm minimum threshold

### Removed

- **Deprecated inspection scripts** (replaced by manifest pipeline)
    - `scripts/analyze_reference_obj.py`
    - `scripts/convert_obj_to_gltf.py`
    - `scripts/analyze_gltf_v2.py`
    - `scripts/compare_with_reference.py`
    - `scripts/validate_obj.py`
    - `src/geometry_inspector.py`
    - `src/geometry_validator.py`

### Fixed

- Door/drawer fronts placed at back of cabinet instead of front
- Carcass missing floor face, inner side faces, and ceiling face
- Manifest not capturing vertex/face data (arrays were empty)
- World bounds not reflecting rotation transforms
- Validator turn mapping mismatch with geometry_builder.py
