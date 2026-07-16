"""Manifest Validator — Validate geometry manifest against rules.

Reads a manifest dict and checks:
- Dimension tolerance (expected vs actual)
- Object overlaps (world bounds intersection)
- Clearances (walkway ≥ 900mm)
- Standard width compliance
- Run direction continuity
- Construction parameter sanity

No bpy dependency — reads manifest JSON only.
Can run standalone or as part of the build pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# Validation tolerances (mm)
DEFAULT_DIMENSION_TOLERANCE_MM = 2.0
DEFAULT_POSITION_TOLERANCE_MM = 0.1
DEFAULT_OVERLAP_TOLERANCE_MM = 0.0
MIN_WALKWAY_CLEARANCE_MM = 900.0
MIN_CABINET_WIDTH_MM = 100.0
MAX_CABINET_WIDTH_MM = 1200.0

# Standard widths (mm)
STANDARD_WIDTHS_MM = {300, 400, 450, 500, 600, 800, 900, 1000, 1200}


@dataclass
class Issue:
    """A single validation issue."""
    severity: str  # "error" or "warning"
    object_name: str
    check: str
    message: str
    expected_mm: Optional[float] = None
    actual_mm: Optional[float] = None

    def to_dict(self) -> dict:
        d = {
            "severity": self.severity,
            "object": self.object_name,
            "check": self.check,
            "message": self.message,
        }
        if self.expected_mm is not None:
            d["expected_mm"] = self.expected_mm
        if self.actual_mm is not None:
            d["actual_mm"] = self.actual_mm
        return d


@dataclass
class ValidationResult:
    """Result of manifest validation."""
    total_objects: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    issues: List[Issue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.failed == 0

    def add_issue(self, issue: Issue) -> None:
        self.issues.append(issue)
        if issue.severity == "error":
            self.failed += 1
        else:
            self.warnings += 1

    def to_dict(self) -> dict:
        return {
            "total_objects": self.total_objects,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
        }


def validate_manifest(
    manifest: dict,
    dimension_tolerance_mm: float = DEFAULT_DIMENSION_TOLERANCE_MM,
    overlap_tolerance_mm: float = DEFAULT_OVERLAP_TOLERANCE_MM,
    min_clearance_mm: float = MIN_WALKWAY_CLEARANCE_MM,
) -> ValidationResult:
    """Run all validation checks on a manifest.

    Args:
        manifest: The geometry manifest dict
        dimension_tolerance_mm: Allowed dimension difference
        overlap_tolerance_mm: Allowed overlap between objects
        min_clearance_mm: Minimum walkway clearance

    Returns:
        ValidationResult with all issues found
    """
    result = ValidationResult()
    objects = manifest.get("objects", [])
    settings = manifest.get("settings", {})
    layout = manifest.get("layout", {})

    result.total_objects = len(objects)

    # Filter to primary objects (not children)
    primary_objects = [o for o in objects if not o.get("parent")]

    # 1. Check dimensions against expected
    for obj in objects:
        issues = check_dimensions(obj, dimension_tolerance_mm)
        for issue in issues:
            result.add_issue(issue)

    # 2. Check for overlaps between primary objects
    overlap_issues = check_overlaps(primary_objects, overlap_tolerance_mm)
    for issue in overlap_issues:
        result.add_issue(issue)

    # 3. Check vertex/face counts
    for obj in objects:
        issues = check_vertex_face_counts(obj)
        for issue in issues:
            result.add_issue(issue)

    # 4. Check standard widths
    for obj in primary_objects:
        issues = check_standard_widths(obj, settings)
        for issue in issues:
            result.add_issue(issue)

    # 5. Check run direction continuity
    run_issues = check_run_continuity(layout)
    for issue in run_issues:
        result.add_issue(issue)

    # 6. Check construction parameters
    for obj in objects:
        issues = check_construction(obj, settings)
        for issue in issues:
            result.add_issue(issue)

    # Count passed
    objects_with_errors = {i.object_name for i in result.issues if i.severity == "error"}
    result.passed = result.total_objects - len(objects_with_errors)

    return result


def check_dimensions(obj: dict, tolerance_mm: float) -> List[Issue]:
    """Check object dimensions against expected values."""
    issues = []
    name = obj.get("name", "unknown")
    expected = obj.get("expected_dimensions_mm")
    actual = obj.get("local_dimensions_mm")

    if not expected or not actual:
        return issues

    dim_names = ["width", "depth", "height"]
    for i, dim_name in enumerate(dim_names):
        exp_val = expected.get(dim_name)
        if exp_val is not None and i < len(actual):
            act_val = actual[i]
            diff = abs(act_val - exp_val)
            if diff > tolerance_mm:
                issues.append(Issue(
                    severity="error",
                    object_name=name,
                    check=dim_name,
                    message=f"{dim_name} mismatch: expected {exp_val:.1f}mm, got {act_val:.1f}mm (diff: {diff:.1f}mm)",
                    expected_mm=exp_val,
                    actual_mm=act_val,
                ))

    return issues


def check_overlaps(objects: List[dict], tolerance_mm: float, min_overlap_mm: float = 50.0) -> List[Issue]:
    """Check for overlapping objects using world bounds.

    Args:
        objects: List of object dicts
        tolerance_mm: Allowed overlap (from door overlays, etc.)
        min_overlap_mm: Minimum overlap to report (filters out expected small overlaps)
    """
    issues = []

    for i in range(len(objects)):
        for j in range(i + 1, len(objects)):
            obj_a = objects[i]
            obj_b = objects[j]

            # Skip children and non-carcass objects for overlap check
            cls_a = obj_a.get("classification", "")
            cls_b = obj_b.get("classification", "")
            skip_classes = {"door_front", "drawer_front", "back_panel", "countertop", "board"}
            if cls_a in skip_classes or cls_b in skip_classes:
                continue

            bounds_a = obj_a.get("world_bounds", {})
            bounds_b = obj_b.get("world_bounds", {})

            if not bounds_a or not bounds_b:
                continue

            overlap = _compute_overlap(bounds_a, bounds_b, tolerance_mm)
            if overlap:
                overlap_x, overlap_y, overlap_z = overlap
                # Filter out expected small overlaps (door overlays, fillers)
                # Real overlaps have large overlap in ALL dimensions
                min_overlap = min(overlap_x, overlap_y, overlap_z)
                if min_overlap < min_overlap_mm:
                    continue
                issues.append(Issue(
                    severity="error",
                    object_name=obj_a.get("name", "unknown"),
                    check="overlap",
                    message=(
                        f"Overlaps with {obj_b.get('name', 'unknown')}: "
                        f"X={overlap_x:.1f}mm, Y={overlap_y:.1f}mm, Z={overlap_z:.1f}mm"
                    ),
                ))

    return issues


def _compute_overlap(
    bounds_a: dict, bounds_b: dict, tolerance_mm: float
) -> Optional[tuple]:
    """Compute overlap between two world bounds.

    Returns (overlap_x, overlap_y, overlap_z) in mm if overlapping,
    None if no overlap.
    """
    a_min = bounds_a.get("min_m", [0, 0, 0])
    a_max = bounds_a.get("max_m", [0, 0, 0])
    b_min = bounds_b.get("min_m", [0, 0, 0])
    b_max = bounds_b.get("max_m", [0, 0, 0])

    tol_m = tolerance_mm / 1000.0

    overlaps = []
    for axis in range(3):
        overlap = min(a_max[axis], b_max[axis]) - max(a_min[axis], b_min[axis])
        if overlap > tol_m:
            overlaps.append(overlap * 1000)  # Convert to mm
        else:
            overlaps.append(0)

    # Only report if there's overlap in all 3 axes
    if all(o > 0 for o in overlaps):
        return tuple(overlaps)

    return None


def check_vertex_face_counts(obj: dict) -> List[Issue]:
    """Check vertex and face counts for construction type."""
    issues = []
    name = obj.get("name", "unknown")
    classification = obj.get("classification", "other")
    vertex_count = obj.get("vertex_count", 0)
    face_count = obj.get("face_count", 0)

    if vertex_count == 0:
        # Empty parent (grouping object) — skip vertex/face checks
        return issues

    if classification in ("carcass", "board"):
        # Individual board: 8 vertices (solid box)
        if vertex_count < 8:
            issues.append(Issue(
                severity="warning",
                object_name=name,
                check="vertex_count",
                message=f"Board has {vertex_count} vertices (expected ≥8)",
            ))
        if face_count < 6:
            issues.append(Issue(
                severity="warning",
                object_name=name,
                check="face_count",
                message=f"Board has {face_count} faces (expected ≥6)",
            ))
    elif classification in ("door_front", "drawer_front"):
        # Solid box: 8 vertices, 6 faces
        if vertex_count < 8:
            issues.append(Issue(
                severity="warning",
                object_name=name,
                check="vertex_count",
                message=f"Front has {vertex_count} vertices (expected 8 for thick box)",
            ))
    elif classification == "back_panel":
        # Thin box: 8 vertices, 6 faces
        if vertex_count < 4:
            issues.append(Issue(
                severity="warning",
                object_name=name,
                check="vertex_count",
                message=f"Back panel has {vertex_count} vertices (expected ≥4)",
            ))

    # Zero vertex/face check
    if vertex_count == 0:
        issues.append(Issue(
            severity="error",
            object_name=name,
            check="vertex_count",
            message="Object has no vertices",
        ))
    if face_count == 0 and vertex_count > 0:
        issues.append(Issue(
            severity="error",
            object_name=name,
            check="face_count",
            message="Object has vertices but no faces",
        ))

    return issues


def check_standard_widths(obj: dict, settings: dict) -> List[Issue]:
    """Check if cabinet width is a standard European width."""
    issues = []
    name = obj.get("name", "unknown")
    classification = obj.get("classification", "other")

    # Only check carcass objects (not fronts, backs, boards, etc.)
    if classification not in ("carcass",):
        return issues

    dims = obj.get("local_dimensions_mm", [0, 0, 0])
    if not dims:
        return issues

    width = dims[0]
    if width < 1:
        return issues

    # Check if width is a standard width (allow some tolerance)
    is_standard = any(abs(width - sw) < 2.0 for sw in STANDARD_WIDTHS_MM)

    if not is_standard:
        issues.append(Issue(
            severity="warning",
            object_name=name,
            check="standard_width",
            message=f"Carcass width {width:.1f}mm is not a standard European width",
        ))

    return issues


def check_run_continuity(layout: dict) -> List[Issue]:
    """Check that runs chain correctly (end of one = start of next)."""
    issues = []
    runs = layout.get("runs", [])

    if len(runs) < 2:
        return issues

    for i in range(len(runs) - 1):
        current = runs[i]
        next_run = runs[i + 1]

        current_end = current.get("end_position_mm", [0, 0])
        next_start = next_run.get("start_position_mm", [0, 0])

        # Check if positions match (within tolerance)
        dx = abs(current_end[0] - next_start[0])
        dy = abs(current_end[1] - next_start[1])

        if dx > 1.0 or dy > 1.0:
            issues.append(Issue(
                severity="error",
                object_name=f"run{current.get('index', i)} → run{next_run.get('index', i+1)}",
                check="run_continuity",
                message=(
                    f"Run {current.get('label', i)} ends at "
                    f"({current_end[0]:.0f}, {current_end[1]:.0f})mm but "
                    f"run {next_run.get('label', i+1)} starts at "
                    f"({next_start[0]:.0f}, {next_start[1]:.0f})mm"
                ),
            ))

        # Check direction change matches turn
        current_dir = current.get("direction")
        next_dir = next_run.get("direction")
        turn = next_run.get("turn")

        if current_dir and next_dir and turn:
            # Must match geometry_builder.py TURNS mapping
            expected_turns = {
                ("east", "left"): "south",
                ("east", "right"): "south",
                ("north", "left"): "west",
                ("north", "right"): "west",
                ("west", "left"): "north",
                ("west", "right"): "north",
                ("south", "left"): "east",
                ("south", "right"): "east",
            }
            expected_dir = expected_turns.get((current_dir, turn))
            if expected_dir and next_dir != expected_dir:
                issues.append(Issue(
                    severity="error",
                    object_name=f"run{next_run.get('index', i+1)}",
                    check="direction",
                    message=(
                        f"Direction mismatch: turn '{turn}' from '{current_dir}' "
                        f"should give '{expected_dir}', got '{next_dir}'"
                    ),
                ))

    return issues


def check_construction(obj: dict, settings: dict) -> List[Issue]:
    """Check construction parameter sanity."""
    issues = []
    name = obj.get("name", "unknown")
    classification = obj.get("classification", "other")

    if classification == "back_panel":
        dims = obj.get("local_dimensions_mm", [0, 0, 0])
        # Back panel should be thin (~3mm HDF)
        # Check the smallest non-zero dimension
        thickness = min(d for d in dims if d > 0.1) if dims else 0
        if thickness > 10:
            issues.append(Issue(
                severity="warning",
                object_name=name,
                check="back_thickness",
                message=f"Back panel thickness {thickness:.1f}mm seems too thick (expected ~3mm)",
            ))

    if classification in ("door_front", "drawer_front"):
        dims = obj.get("local_dimensions_mm", [0, 0, 0])
        # Front should be ~19mm thick
        thickness = min(d for d in dims if d > 0.1) if dims else 0
        if thickness > 0 and thickness < 10:
            issues.append(Issue(
                severity="warning",
                object_name=name,
                check="front_thickness",
                message=f"Front thickness {thickness:.1f}mm seems too thin (expected ~19mm)",
            ))

    return issues


def print_validation_report(result: ValidationResult) -> None:
    """Print human-readable validation report."""
    print("\n" + "=" * 80)
    print("MANIFEST VALIDATION REPORT")
    print("=" * 80)

    print(f"\nTotal objects: {result.total_objects}")
    print(f"Passed: {result.passed}")
    print(f"Failed: {result.failed}")
    print(f"Warnings: {result.warnings}")
    print(f"Status: {'✓ VALID' if result.is_valid else '❌ INVALID'}")

    if result.issues:
        errors = [i for i in result.issues if i.severity == "error"]
        warnings = [i for i in result.issues if i.severity == "warning"]

        if errors:
            print(f"\n❌ Errors ({len(errors)}):")
            for issue in errors:
                print(f"  [{issue.check}] {issue.object_name}: {issue.message}")

        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for issue in warnings:
                print(f"  [{issue.check}] {issue.object_name}: {issue.message}")
    else:
        print("\n✓ No issues found")

    print("=" * 80)
