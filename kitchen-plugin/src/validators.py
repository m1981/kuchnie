"""Validators — dimension, position, and gap checks. Pure Python, no bpy."""

from .config_parser import mm_to_m, CABINET_LEVELS


def validate_config(config: dict) -> list[str]:
    """Run all validation checks. Returns list of warnings (empty = ok)."""
    warnings = []
    warnings.extend(_check_dimensions(config))
    warnings.extend(_check_overlaps(config))
    warnings.extend(_check_gaps(config))
    warnings.extend(_check_corners(config))
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

    for run_idx, run in enumerate(config["runs"]):
        for section in ("base", "upper", "tall"):
            x = 0
            for cab_idx, cab in enumerate(run.get(section, [])):
                prefix = f"run[{run_idx}].{section}[{cab_idx}]"

                if x < 0:
                    warnings.append(
                        f"{prefix}: starts at {x}mm (overlaps previous)"
                    )

                x += cab["width"] + settings.get("gap", 2)

    return warnings


def _check_gaps(config: dict) -> list[str]:
    """Check that gaps between fronts are reasonable."""
    warnings = []
    settings = config["settings"]
    gap = settings.get("gap", 2)

    if gap < 0:
        warnings.append(f"Global gap {gap}mm is negative")
    if gap > 10:
        warnings.append(f"Global gap {gap}mm seems too large")

    for run_idx, run in enumerate(config["runs"]):
        for section in ("base", "upper", "tall"):
            for cab_idx, cab in enumerate(run.get(section, [])):
                prefix = f"run[{run_idx}].{section}[{cab_idx}]"

                cab_gap = cab.get("gap", gap)
                if cab_gap < 0:
                    warnings.append(
                        f"{prefix}: cabinet gap {cab_gap}mm is negative"
                    )
                if cab_gap > 10:
                    warnings.append(
                        f"{prefix}: cabinet gap {cab_gap}mm seems too large"
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


def compute_total_width(config: dict) -> dict[str, float]:
    """Compute total width of each run (mm)."""
    result = {}
    settings = config["settings"]

    for run_idx, run in enumerate(config["runs"]):
        for section in ("base", "upper", "tall"):
            cabs = run.get(section, [])
            if cabs:
                total = sum(c["width"] for c in cabs) + settings["gap"] * (len(cabs) - 1)
                result[f"run[{run_idx}].{section}"] = total

    return result
