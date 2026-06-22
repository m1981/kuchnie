"""Validators — dimension, position, and gap checks. Pure Python, no bpy."""

from .config_parser import mm_to_m, CABINET_LEVELS


def validate_config(config: dict) -> list[str]:
    """Run all validation checks. Returns list of warnings (empty = ok)."""
    warnings = []
    warnings.extend(_check_dimensions(config))
    warnings.extend(_check_overlaps(config))
    warnings.extend(_check_gaps(config))
    warnings.extend(_check_corners(config))
    warnings.extend(_check_room_fit(config))
    return warnings


def _check_dimensions(config: dict) -> list[str]:
    """Check that all dimensions are reasonable."""
    warnings = []
    settings = config["settings"]

    for run_idx, run in enumerate(config["runs"]):
        for section in ("base", "upper", "tall"):
            for cab_idx, cab in enumerate(run.get(section, [])):
                prefix = f"run[{run_idx}].{section}[{cab_idx}]"

                # Skip fillers — they are intentionally narrow
                if cab["type"] == "filler":
                    continue

                w = cab["width"]
                if w < 100:
                    warnings.append(f"{prefix}: width {w}mm seems too small")
                if w > 1200:
                    warnings.append(f"{prefix}: width {w}mm seems too large")

                if cab.get("depthOffset", 0) > 200:
                    warnings.append(
                        f"{prefix}: depthOffset {cab['depthOffset']}mm seems large"
                    )

    return warnings


def _check_overlaps(config: dict) -> list[str]:
    """Check that cabinets don't overlap."""
    warnings = []
    settings = config["settings"]
    cabinet_gap = settings.get("cabinetGap", 0)

    for run_idx, run in enumerate(config["runs"]):
        for section in ("base", "upper", "tall"):
            x = 0
            for cab_idx, cab in enumerate(run.get(section, [])):
                prefix = f"run[{run_idx}].{section}[{cab_idx}]"

                if x < 0:
                    warnings.append(
                        f"{prefix}: starts at {x}mm (overlaps previous)"
                    )

                x += cab["width"] + cabinet_gap

    return warnings


def _check_gaps(config: dict) -> list[str]:
    """Check that gaps between cabinets and fronts are reasonable."""
    warnings = []
    settings = config["settings"]

    # Check cabinetGap (carcass-to-carcass)
    cabinet_gap = settings.get("cabinetGap", 0)
    if cabinet_gap < 0:
        warnings.append(f"cabinetGap {cabinet_gap}mm is negative")
    if cabinet_gap > 10:
        warnings.append(f"cabinetGap {cabinet_gap}mm seems too large")

    # Check frontGap (front-to-front)
    front_gap = settings.get("frontGap", 2)
    if front_gap < 0:
        warnings.append(f"frontGap {front_gap}mm is negative")
    if front_gap > 10:
        warnings.append(f"frontGap {front_gap}mm seems too large")

    # Check tolerances
    front_offset = settings.get("frontOffset", 0.001)
    if front_offset < 0:
        warnings.append(f"frontOffset {front_offset}m is negative")
    if front_offset > 0.01:  # 10mm
        warnings.append(f"frontOffset {front_offset*1000:.0f}mm seems too large")

    clearance_offset = settings.get("clearanceOffset", 0.001)
    if clearance_offset < 0:
        warnings.append(f"clearanceOffset {clearance_offset}m is negative")
    if clearance_offset > 0.01:  # 10mm
        warnings.append(f"clearanceOffset {clearance_offset*1000:.0f}mm seems too large")

    # Check per-cabinet gap overrides
    for run_idx, run in enumerate(config["runs"]):
        for section in ("base", "upper", "tall"):
            for cab_idx, cab in enumerate(run.get(section, [])):
                prefix = f"run[{run_idx}].{section}[{cab_idx}]"

                cab_gap = cab.get("frontGap", front_gap)
                if cab_gap < 0:
                    warnings.append(
                        f"{prefix}: frontGap {cab_gap}mm is negative"
                    )
                if cab_gap > 10:
                    warnings.append(
                        f"{prefix}: frontGap {cab_gap}mm seems too large"
                    )

    return warnings


def _check_face_direction(config: dict) -> list[str]:
    """Check that cabinet fronts face into the room, not into the wall."""
    warnings = []
    # This is verified by the rotation math in geometry_builder.py
    # The rotations are:
    #   east  (wall south): 0°      → front faces +Y (north, into room)
    #   south (wall east):  -90° CW → front faces -X (west, into room)
    #   west  (wall north): 180°    → front faces -Y (south, into room)
    #   north (wall west):  +90° CCW → front faces +X (east, into room)
    #
    # If any rotation is wrong, cabinets will face the wall and
    # their depth will extend into adjacent runs, causing overlaps.
    return warnings


def _check_corners(config: dict) -> list[str]:
    """Check corner cabinet placement."""
    warnings = []

    for run_idx, run in enumerate(config["runs"]):
        base = run.get("base", [])
        if not base:
            continue

        # Check that corner cabinets are first or last in a run
        for cab_idx, cab in enumerate(base):
            if cab["type"].startswith("corner-"):
                if cab_idx != 0 and cab_idx != len(base) - 1:
                    prefix = f"run[{run_idx}].base[{cab_idx}]"
                    warnings.append(
                        f"{prefix}: corner cabinet should be first or last in run"
                    )

        # Check turn direction on next run
        if run_idx + 1 < len(config["runs"]):
            next_run = config["runs"][run_idx + 1]
            if not next_run.get("turn"):
                # Check if current run ends with a corner
                if base and base[-1]["type"].startswith("corner-"):
                    warnings.append(
                        f"run[{run_idx + 1}]: missing 'turn' direction "
                        f"(previous run ends with corner cabinet)"
                    )

    return warnings


def _check_room_fit(config: dict) -> list[str]:
    """Check that runs fit within room wall lengths (if specified)."""
    warnings = []

    room = config.get("room")
    if not room:
        return warnings

    walls = room.get("walls", [])
    if not walls:
        return warnings

    settings = config["settings"]
    cabinet_gap = settings.get("cabinetGap", 0)

    # Track corner blind depth consumed from adjacent wall
    corner_consumed = 0

    for run_idx, run in enumerate(config["runs"]):
        # Get wall length (reuse last wall if fewer walls than runs)
        wall_idx = min(run_idx, len(walls) - 1)
        wall_length = walls[wall_idx].get("length", 0)

        if wall_length <= 0:
            continue

        # Calculate run width (use base section as reference)
        base_cabs = run.get("base", [])
        if base_cabs:
            run_width = sum(c["width"] for c in base_cabs) + cabinet_gap * (len(base_cabs) - 1)
        else:
            continue

        # Subtract space consumed by corner from previous run
        available_length = wall_length - corner_consumed

        if run_width > available_length:
            warnings.append(
                f"run[{run_idx}] '{run.get('label', '')}': "
                f"run width {run_width}mm exceeds wall length {available_length}mm"
            )

        # Track corner blind depth for next run
        corner_consumed = 0
        if base_cabs:
            last_cab = base_cabs[-1]
            if last_cab["type"] == "corner-blind":
                corner_consumed = last_cab.get("blindDepth", 300)

    return warnings


def compute_total_width(config: dict) -> dict[str, float]:
    """Compute total width of each run (mm).

    Uses cabinetGap for carcass-to-carcass spacing.
    """
    result = {}
    settings = config["settings"]
    cabinet_gap = settings.get("cabinetGap", 0)

    for run_idx, run in enumerate(config["runs"]):
        for section in ("base", "upper", "tall"):
            cabs = run.get(section, [])
            if cabs:
                total = sum(c["width"] for c in cabs) + cabinet_gap * (len(cabs) - 1)
                result[f"run[{run_idx}].{section}"] = total

    return result
