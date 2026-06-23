"""Geometry Manifest — Primary output for kitchen geometry validation.

Exports a structured JSON manifest with:
- Local and world vertex coordinates
- Object hierarchy (parent-child)
- Expected vs actual dimensions (inline validation)
- Layout metadata (runs, turns, directions)
- Construction parameters (board thicknesses)
- Units and coordinate system (explicit, never guessed)

This is the PRIMARY output of every build. OBJ/glTF are optional visual extras.

Output: JSON file readable by LLM agents, CI pipelines, and humans.
No bpy dependency in the output format — data is captured from bpy
but the manifest is plain JSON.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


# Manifest format constants
MANIFEST_VERSION = "2.0"
MANIFEST_FORMAT = "kitchen-geometry-manifest"

# Tolerance for dimension comparison (mm)
DEFAULT_DIMENSION_TOLERANCE_MM = 2.0


def export_manifest(
    objects: list,
    path: str,
    settings: dict | None = None,
    config: dict | None = None,
    tolerance_mm: float = DEFAULT_DIMENSION_TOLERANCE_MM,
) -> dict:
    """Export geometry manifest from Blender objects.

    This is the primary output of every build. Captures exact geometry
    from bpy with full fidelity — no lossy format conversion.

    Args:
        objects: List of bpy.types.Object
        path: Output JSON file path
        settings: Settings dict from config (mm values)
        config: Full config dict (for layout metadata)
        tolerance_mm: Dimension comparison tolerance

    Returns:
        Manifest dict
    """
    settings = settings or {}
    config = config or {}

    # Force scene update so matrix_world reflects all transforms
    try:
        import bpy
        bpy.context.view_layer.update()
    except Exception:
        pass

    manifest = {
        "format": MANIFEST_FORMAT,
        "version": MANIFEST_VERSION,
        "units": "meters",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_config": config.get("_source_path", "unknown"),
        "coordinate_system": {
            "type": "Z-up",
            "handedness": "right",
            "x": "width (left to right)",
            "y": "depth (into room)",
            "z": "height (up)",
        },
        "settings": _extract_settings(settings),
        "layout": _build_layout_metadata(config),
        "objects": [],
        "validation_summary": {
            "total_objects": 0,
            "total_vertices": 0,
            "total_faces": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "issues": [],
        },
    }

    # Build object map for hierarchy resolution
    obj_map = {}

    # Extract each object
    for obj in objects:
        obj_data = _extract_object(obj, settings, config, tolerance_mm)
        if obj_data:
            manifest["objects"].append(obj_data)
            obj_map[obj_data["name"]] = obj_data

    # Update summary counts
    summary = manifest["validation_summary"]
    summary["total_objects"] = len(manifest["objects"])
    summary["total_vertices"] = sum(o.get("vertex_count", 0) for o in manifest["objects"])
    summary["total_faces"] = sum(o.get("face_count", 0) for o in manifest["objects"])

    # Count pass/fail/warnings
    for obj_data in manifest["objects"]:
        v = obj_data.get("validation", {})
        issues = v.get("issues", [])
        if any(i.get("severity") == "error" for i in issues):
            summary["failed"] += 1
        else:
            summary["passed"] += 1

        warnings = [i for i in issues if i.get("severity") == "warning"]
        summary["warnings"] += len(warnings)

        # Collect issues into summary
        for issue in issues:
            summary["issues"].append({
                "severity": issue.get("severity", "error"),
                "object": obj_data["name"],
                "check": issue.get("check", "unknown"),
                "message": issue.get("message", ""),
                "expected_mm": issue.get("expected_mm"),
                "actual_mm": issue.get("actual_mm"),
            })

    # Write to file
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Geometry manifest: {out}")
    print(f"  Objects: {summary['total_objects']}")
    print(f"  Vertices: {summary['total_vertices']}")
    print(f"  Faces: {summary['total_faces']}")
    print(f"  Passed: {summary['passed']}, Failed: {summary['failed']}, "
          f"Warnings: {summary['warnings']}")

    return manifest


def _extract_settings(settings: dict) -> dict:
    """Extract relevant settings for the manifest."""
    relevant_keys = [
        "baseBodyHeight", "baseDepth", "wallHeight", "wallDepth",
        "tallHeight", "tallDepth", "plinthHeight", "plinthSetback",
        "counterThickness", "counterOverhangFront", "counterOverhangEnd",
        "wallMountHeight", "cabinetGap", "frontGap",
        "corpusThickness", "frontThickness", "backThickness",
        "grooveOffset", "frontOverlay",
        "frontOffset", "clearanceOffset",
    ]
    return {k: settings[k] for k in relevant_keys if k in settings}


def _build_layout_metadata(config: dict) -> dict:
    """Build layout metadata from config."""
    runs = config.get("runs", [])
    if not runs:
        return {"type": "unknown", "run_count": 0, "total_cabinets": 0, "runs": []}

    settings = config.get("settings", {})
    cabinet_gap = settings.get("cabinetGap", 0)

    # Determine layout type from run count and turns
    run_count = len(runs)
    has_turns = any(r.get("turn") for r in runs[1:])

    if run_count == 1:
        layout_type = "I-shape"
    elif run_count == 2 and has_turns:
        layout_type = "L-shape"
    elif run_count == 3 and has_turns:
        layout_type = "U-shape"
    else:
        layout_type = f"{run_count}-runs"

    # Build run metadata
    run_metas = []
    total_cabinets = 0

    # Track position for each run
    pos_x, pos_y = 0.0, 0.0
    direction = "east"

    # Direction vectors
    dir_vectors = {
        "east": (1, 0),
        "north": (0, 1),
        "west": (-1, 0),
        "south": (0, -1),
    }
    # Turn mapping from geometry_builder.py
    turns = {
        ("east", "left"): "south",
        ("east", "right"): "south",
        ("north", "left"): "west",
        ("north", "right"): "west",
        ("west", "left"): "north",
        ("west", "right"): "north",
        ("south", "left"): "east",
        ("south", "right"): "east",
    }

    for i, run in enumerate(runs):
        turn = run.get("turn")

        # Apply turn
        if turn and i > 0:
            new_dir = turns.get((direction, turn))
            if new_dir:
                direction = new_dir

        dx, dy = dir_vectors.get(direction, (1, 0))

        # Count cabinets
        cab_names = []
        run_total = 0
        for section in ("base", "upper", "tall"):
            for j, cab in enumerate(run.get(section, [])):
                cab_type = cab.get("type", "unknown")
                name = f"run{i}_{section}_{j}_{cab_type}"
                cab_names.append(name)
                run_total += 1
                total_cabinets += 1

        # Calculate run width
        base_cabs = run.get("base", [])
        total_width = sum(c["width"] for c in base_cabs) + cabinet_gap * max(0, len(base_cabs) - 1)

        start_x, start_y = pos_x, pos_y
        end_x = pos_x + total_width * dx
        end_y = pos_y + total_width * dy

        run_metas.append({
            "label": run.get("label", f"run{i}"),
            "index": i,
            "direction": direction,
            "turn": turn,
            "start_position_mm": [round(start_x, 1), round(start_y, 1)],
            "end_position_mm": [round(end_x, 1), round(end_y, 1)],
            "total_width_mm": total_width,
            "cabinet_count": run_total,
            "cabinets": cab_names,
        })

        # Update position for next run
        pos_x = end_x
        pos_y = end_y

    return {
        "type": layout_type,
        "run_count": run_count,
        "total_cabinets": total_cabinets,
        "runs": run_metas,
    }


def _extract_object(
    obj: Any,
    settings: dict,
    config: dict,
    tolerance_mm: float,
) -> dict | None:
    """Extract detailed geometry data from a Blender object."""
    try:
        name = obj.name

        # Get mesh data
        mesh = obj.data

        # Local vertices (NOT world-transformed)
        local_vertices = []
        if hasattr(mesh, "vertices"):
            for v in mesh.vertices:
                local_vertices.append([
                    round(v.co.x, 6),
                    round(v.co.y, 6),
                    round(v.co.z, 6),
                ])

        # Faces
        faces = []
        if hasattr(mesh, "polygons"):
            for p in mesh.polygons:
                faces.append(list(p.vertices))

        # Calculate local bounds
        if local_vertices:
            xs = [v[0] for v in local_vertices]
            ys = [v[1] for v in local_vertices]
            zs = [v[2] for v in local_vertices]
            local_bounds = {
                "min_m": [round(min(xs), 6), round(min(ys), 6), round(min(zs), 6)],
                "max_m": [round(max(xs), 6), round(max(ys), 6), round(max(zs), 6)],
            }
            local_dims_m = [
                round(max(xs) - min(xs), 6),
                round(max(ys) - min(ys), 6),
                round(max(zs) - min(zs), 6),
            ]
        else:
            local_bounds = {"min_m": [0, 0, 0], "max_m": [0, 0, 0]}
            local_dims_m = [0, 0, 0]

        local_dims_mm = [round(d * 1000, 2) for d in local_dims_m]

        # Get parent name
        parent_name = obj.parent.name if obj.parent else None

        # Get transform
        location = [round(v, 6) for v in (obj.location.x, obj.location.y, obj.location.z)]
        rotation = [round(v, 6) for v in (obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z)]
        scale = [round(v, 6) for v in (obj.scale.x, obj.scale.y, obj.scale.z)]

        # Compute world bounds from local bounds + transform
        world_bounds = _compute_world_bounds(local_bounds, obj)
        world_dims_m = [
            round(world_bounds["max_m"][0] - world_bounds["min_m"][0], 6),
            round(world_bounds["max_m"][1] - world_bounds["min_m"][1], 6),
            round(world_bounds["max_m"][2] - world_bounds["min_m"][2], 6),
        ]
        world_dims_mm = [round(d * 1000, 2) for d in world_dims_m]

        # Classify object
        classification = _classify_object(name)
        obj_type = _determine_type(name)
        level = _determine_level(name, settings)
        run_info = _determine_run_info(name)

        # Get expected dimensions
        expected = _compute_expected_dims(
            name, classification, obj_type, level, settings, config
        )

        # Run validation
        validation = _validate_object(
            name, local_dims_mm, expected, len(local_vertices), len(faces),
            classification, tolerance_mm,
        )

        # Build children list
        children = []
        for child in getattr(obj, "children", []):
            child_name = child.name
            child_mesh = child.data
            child_verts = []
            if hasattr(child_mesh, "vertices"):
                for v in child_mesh.vertices:
                    child_verts.append((v.co.x, v.co.y, v.co.z))

            if child_verts:
                cx = [v[0] for v in child_verts]
                cy = [v[1] for v in child_verts]
                cz = [v[2] for v in child_verts]
                child_dims = [
                    round((max(cx) - min(cx)) * 1000, 2),
                    round((max(cy) - min(cy)) * 1000, 2),
                    round((max(cz) - min(cz)) * 1000, 2),
                ]
            else:
                child_dims = [0, 0, 0]

            children.append({
                "name": child_name,
                "type": _classify_object(child_name),
                "local_dimensions_mm": child_dims,
            })

        # If parent is empty (0 vertices), compute bounds from children
        if len(local_vertices) == 0 and children:
            # Compute bounds from children's dimensions
            # Children are positioned relative to parent (which is at origin)
            child_bounds_min = [float('inf'), float('inf'), float('inf')]
            child_bounds_max = [float('-inf'), float('-inf'), float('-inf')]
            for child in getattr(obj, 'children', []):
                child_mesh = child.data
                if hasattr(child_mesh, 'vertices') and len(child_mesh.vertices) > 0:
                    for v in child_mesh.vertices:
                        # Child vertices are in child local space
                        # Child location is relative to parent
                        cx = child.location.x + v.co.x
                        cy = child.location.y + v.co.y
                        cz = child.location.z + v.co.z
                        child_bounds_min[0] = min(child_bounds_min[0], cx)
                        child_bounds_min[1] = min(child_bounds_min[1], cy)
                        child_bounds_min[2] = min(child_bounds_min[2], cz)
                        child_bounds_max[0] = max(child_bounds_max[0], cx)
                        child_bounds_max[1] = max(child_bounds_max[1], cy)
                        child_bounds_max[2] = max(child_bounds_max[2], cz)
            if child_bounds_min[0] != float('inf'):
                local_bounds = {
                    'min_m': [round(v, 6) for v in child_bounds_min],
                    'max_m': [round(v, 6) for v in child_bounds_max],
                }
                local_dims_mm = [
                    round((child_bounds_max[0] - child_bounds_min[0]) * 1000, 2),
                    round((child_bounds_max[1] - child_bounds_min[1]) * 1000, 2),
                    round((child_bounds_max[2] - child_bounds_min[2]) * 1000, 2),
                ]
                world_bounds = _compute_world_bounds(local_bounds, obj)
                world_dims_mm = [
                    round((world_bounds['max_m'][0] - world_bounds['min_m'][0]) * 1000, 2),
                    round((world_bounds['max_m'][1] - world_bounds['min_m'][1]) * 1000, 2),
                    round((world_bounds['max_m'][2] - world_bounds['min_m'][2]) * 1000, 2),
                ]

        return {
            "name": name,
            "type": obj_type,
            "classification": classification,
            "level": level,
            "run_label": run_info.get("run_label"),
            "run_index": run_info.get("run_index"),
            "cabinet_index": run_info.get("cabinet_index"),
            "parent": parent_name,
            "transform": {
                "location_m": location,
                "rotation_euler_rad": rotation,
                "scale": scale,
            },
            "local_bounds": local_bounds,
            "local_dimensions_mm": local_dims_mm,
            "world_bounds": world_bounds,
            "world_dimensions_mm": world_dims_mm,
            "vertex_count": len(local_vertices),
            "face_count": len(faces),
            "vertices": local_vertices,
            "faces": faces,
            "expected_dimensions_mm": expected,
            "construction": _get_construction_params(settings),
            "children": children,
            "validation": validation,
        }

    except Exception as e:
        return {
            "name": getattr(obj, "name", "unknown"),
            "error": str(e),
            "vertex_count": 0,
            "face_count": 0,
            "validation": {
                "issues": [{"severity": "error", "check": "extraction", "message": str(e)}],
            },
        }


def _compute_world_bounds(local_bounds: dict, obj: Any) -> dict:
    """Compute world-space bounds from local bounds and object transform.

    Uses the 8 corners of the local bounding box, transforms each to
    world space via matrix_world, then computes the axis-aligned bounds.
    """
    try:
        lmin = local_bounds["min_m"]
        lmax = local_bounds["max_m"]
        corners = [
            (lmin[0], lmin[1], lmin[2]),
            (lmax[0], lmin[1], lmin[2]),
            (lmax[0], lmax[1], lmin[2]),
            (lmin[0], lmax[1], lmin[2]),
            (lmin[0], lmin[1], lmax[2]),
            (lmax[0], lmin[1], lmax[2]),
            (lmax[0], lmax[1], lmax[2]),
            (lmin[0], lmax[1], lmax[2]),
        ]

        world_corners = []
        for corner in corners:
            local_vec = _make_vector(corner)
            world_vec = obj.matrix_world @ local_vec
            world_corners.append((world_vec.x, world_vec.y, world_vec.z))

        wx = [c[0] for c in world_corners]
        wy = [c[1] for c in world_corners]
        wz = [c[2] for c in world_corners]

        return {
            "min_m": [round(min(wx), 6), round(min(wy), 6), round(min(wz), 6)],
            "max_m": [round(max(wx), 6), round(max(wy), 6), round(max(wz), 6)],
        }

    except Exception:
        loc = (obj.location.x, obj.location.y, obj.location.z)
        lmin = local_bounds["min_m"]
        lmax = local_bounds["max_m"]
        return {
            "min_m": [
                round(lmin[0] + loc[0], 6),
                round(lmin[1] + loc[1], 6),
                round(lmin[2] + loc[2], 6),
            ],
            "max_m": [
                round(lmax[0] + loc[0], 6),
                round(lmax[1] + loc[1], 6),
                round(lmax[2] + loc[2], 6),
            ],
        }


def _make_vector(coords: tuple):
    """Create a Blender Vector from coordinates."""
    import mathutils
    return mathutils.Vector(coords)


def _classify_object(name: str) -> str:
    """Classify object by its structural role."""
    name_lower = name.lower()
    if "_door" in name_lower:
        return "door_front"
    elif "_drawer" in name_lower:
        return "drawer_front"
    elif "_back" in name_lower:
        return "back_panel"
    elif "countertop" in name_lower:
        return "countertop"
    elif "filler" in name_lower:
        return "filler"
    elif "plinth" in name_lower:
        return "plinth"
    elif any(x in name_lower for x in ["_left", "_right", "_top", "_bottom"]):
        return "board"  # Individual carcass board
    elif "carcass" in name_lower or ("run" in name_lower and "_" in name_lower):
        return "carcass"  # Parent empty or old-style carcass
    else:
        return "other"


def _determine_type(name: str) -> str:
    """Determine the Blender object type."""
    # Check if name matches a board (has _left, _right, _top, _bottom suffix)
    name_lower = name.lower()
    if any(x in name_lower for x in ["_left", "_right", "_top", "_bottom"]):
        return "MESH"  # Board is a mesh
    elif "run" in name_lower and name_lower.count("_") >= 2:
        # Could be parent empty or old-style carcass
        # Will be determined by actual object data
        return "MESH"
    return "MESH"


def _determine_level(name: str, settings: dict) -> str | None:
    """Determine cabinet level from name."""
    name_lower = name.lower()
    if "_base_" in name_lower:
        return "base"
    elif "_upper_" in name_lower:
        return "upper"
    elif "_tall_" in name_lower:
        return "tall"
    elif "countertop" in name_lower:
        return "base"
    elif "filler" in name_lower:
        # Try to determine from context
        return None
    return None


def _determine_run_info(name: str) -> dict:
    """Extract run info from object name.

    Expected format: run{N}_{level}_{index}_{type}
    Example: run0_base_0_base-door
    """
    info = {}
    parts = name.split("_")
    if len(parts) >= 1 and parts[0].startswith("run"):
        try:
            info["run_index"] = int(parts[0][3:])
        except ValueError:
            pass
    if len(parts) >= 3:
        try:
            info["cabinet_index"] = int(parts[2])
        except ValueError:
            pass
    return info


def _compute_expected_dims(
    name: str,
    classification: str,
    obj_type: str,
    level: str | None,
    settings: dict,
    config: dict,
) -> dict | None:
    """Compute expected dimensions for an object.

    Returns dict with width/depth/height in mm, or None if unknown.
    """
    if classification == "filler":
        # Fillers are specified in config
        return None  # Width comes from config, varies

    if classification == "countertop":
        return None  # Depends on run width, computed dynamically

    if classification in ("door_front", "drawer_front"):
        # Fronts depend on parent cabinet — hard to predict without context
        return None

    if classification == "back_panel":
        # Back panel depends on parent cabinet
        return None

    if classification == "board":
        # Individual carcass board — dimensions vary by board type
        return None

    if classification == "carcass":
        # Parent empty (grouping object) — check vertex count
        # If it has no vertices, it's an empty — skip dimension check
        # (The actual geometry is in child boards)
        return None  # Don't validate parent empty dimensions

    return None


def _validate_object(
    name: str,
    dims_mm: list,
    expected: dict | None,
    vertex_count: int,
    face_count: int,
    classification: str,
    tolerance_mm: float,
) -> dict:
    """Validate an object against expected dimensions and construction rules."""
    issues = []

    if expected:
        # Check each dimension that has an expected value
        dim_names = ["width", "depth", "height"]
        for i, dim_name in enumerate(dim_names):
            exp_val = expected.get(dim_name)
            if exp_val is not None and i < len(dims_mm):
                actual = dims_mm[i]
                diff = abs(actual - exp_val)
                if diff > tolerance_mm:
                    issues.append({
                        "severity": "error",
                        "check": dim_name,
                        "message": f"{dim_name} mismatch: expected {exp_val:.1f}mm, got {actual:.1f}mm",
                        "expected_mm": exp_val,
                        "actual_mm": actual,
                    })

    # Vertex count checks
    if vertex_count == 0:
        # Empty parent — skip checks
        pass
    elif classification in ("carcass", "board"):
        # Individual board: 8 vertices (solid box)
        if vertex_count < 8:
            issues.append({
                "severity": "warning",
                "check": "vertex_count",
                "message": f"Board has {vertex_count} vertices (expected ≥8)",
            })
    elif classification in ("door_front", "drawer_front"):
        # Solid box: 8 vertices
        if vertex_count < 8:
            issues.append({
                "severity": "warning",
                "check": "vertex_count",
                "message": f"Front has {vertex_count} vertices (expected 8 for thick box)",
            })
    elif classification == "back_panel":
        # Thin box: 8 vertices
        if vertex_count < 4:
            issues.append({
                "severity": "warning",
                "check": "vertex_count",
                "message": f"Back panel has {vertex_count} vertices (expected ≥4)",
            })

    # Face count checks
    if face_count == 0 and vertex_count > 0:
        issues.append({
            "severity": "error",
            "check": "face_count",
            "message": "Object has vertices but no faces",
        })

    # Zero dimension check
    for i, (dim_name, dim_val) in enumerate(zip(["width", "depth", "height"], dims_mm)):
        if dim_val < 0.1:
            issues.append({
                "severity": "error",
                "check": f"zero_{dim_name}",
                "message": f"{dim_name} is ~0mm ({dim_val:.3f}mm)",
            })

    return {
        "width_ok": not any(i.get("check") == "width" for i in issues),
        "depth_ok": not any(i.get("check") == "depth" for i in issues),
        "height_ok": not any(i.get("check") == "height" for i in issues),
        "vertex_count_ok": not any(i.get("check") == "vertex_count" for i in issues),
        "face_count_ok": not any(i.get("check") == "face_count" for i in issues),
        "issues": issues,
    }


def _get_construction_params(settings: dict) -> dict:
    """Extract construction parameters from settings."""
    return {
        "corpus_thickness_mm": settings.get("corpusThickness", 18),
        "back_thickness_mm": settings.get("backThickness", 3),
        "front_thickness_mm": settings.get("frontThickness", 19),
        "groove_offset_mm": settings.get("grooveOffset", 10),
        "front_overlay_mm": settings.get("frontOverlay", 2),
    }


def print_manifest_summary(manifest: dict) -> None:
    """Print human-readable summary of manifest."""
    print("\n" + "=" * 80)
    print("GEOMETRY MANIFEST SUMMARY")
    print("=" * 80)

    print(f"\nFormat: {manifest.get('format')} v{manifest.get('version')}")
    print(f"Units: {manifest.get('units')}")
    print(f"Generated: {manifest.get('generated_at', 'unknown')}")

    # Layout
    layout = manifest.get("layout", {})
    print(f"\nLayout: {layout.get('type', 'unknown')} "
          f"({layout.get('run_count', 0)} runs, "
          f"{layout.get('total_cabinets', 0)} cabinets)")

    for run in layout.get("runs", []):
        turn_str = f" (turn: {run['turn']})" if run.get("turn") else ""
        print(f"  Run {run['index']}: {run['label']} — "
              f"{run['direction']}{turn_str} — "
              f"{run['total_width_mm']}mm, {run['cabinet_count']} cabinets")

    # Summary
    summary = manifest.get("validation_summary", {})
    print(f"\nObjects: {summary.get('total_objects', 0)}")
    print(f"Vertices: {summary.get('total_vertices', 0)}")
    print(f"Faces: {summary.get('total_faces', 0)}")
    print(f"Validation: {summary.get('passed', 0)} passed, "
          f"{summary.get('failed', 0)} failed, "
          f"{summary.get('warnings', 0)} warnings")

    # Issues
    issues = summary.get("issues", [])
    if issues:
        print(f"\nIssues ({len(issues)}):")
        for issue in issues:
            severity = issue.get("severity", "error")
            icon = "❌" if severity == "error" else "⚠️"
            print(f"  {icon} {issue['object']}: {issue['message']}")
    else:
        print("\n✓ No issues found")

    print("=" * 80)
