"""Kitchen config parser — pure Python, no bpy dependency.

Loads JSON config, validates it, converts mm to meters for Blender.
"""

import json
from pathlib import Path

# Default settings (mm)
DEFAULTS = {
    "baseBodyHeight": 720,
    "baseDepth": 560,
    "wallHeight": 720,
    "wallDepth": 300,
    "tallHeight": 2000,
    "tallDepth": 560,
    "plinthHeight": 120,
    "plinthSetback": 60,
    "counterThickness": 30,
    "counterOverhangFront": 20,
    "counterOverhangEnd": 30,
    "wallMountHeight": 1400,
    # Gap semantics:
    #   cabinetGap  = space between carcass boxes (usually 0mm, flush)
    #   frontGap    = visible gap between door/drawer fronts (usually 2-3mm)
    # Legacy 'gap' is treated as 'frontGap' for backward compatibility.
    "cabinetGap": 0,
    "frontGap": 2,
}

# Cabinet types and their level
CABINET_LEVELS = {
    "base-door": "base",
    "base-door-double": "base",
    "base-drawers": "base",
    "base-drawer-door": "base",
    "base-sink": "base",
    "corner-blind": "base",
    "corner-diagonal": "base",
    "wall-door": "upper",
    "wall-door-double": "upper",
    "wall-drawers": "upper",
    "wall-glass": "upper",
    "wall-lift-up": "upper",
    "tall-oven": "tall",
    "tall-fridge": "tall",
    "tall-pantry": "tall",
    "filler": "base",
}


def load_config(path: str) -> dict:
    """Load and validate a kitchen config from JSON file."""
    with open(path) as f:
        config = json.load(f)

    _apply_defaults(config)
    _validate(config)
    return config


def _apply_defaults(config: dict) -> None:
    """Fill in missing settings with defaults.

    Handles backward compatibility:
    - Old 'gap' setting is mapped to 'frontGap'
    - New 'cabinetGap' and 'frontGap' take precedence over old 'gap'
    """
    settings = config.setdefault("settings", {})

    # Backward compatibility: migrate old 'gap' to new semantics
    if "gap" in settings and "frontGap" not in settings:
        settings["frontGap"] = settings["gap"]
    if "gap" in settings and "cabinetGap" not in settings:
        settings["cabinetGap"] = 0  # Old configs assumed carcass gap = 0

    # Apply defaults for any remaining missing keys
    for key, value in DEFAULTS.items():
        settings.setdefault(key, value)


def _validate(config: dict) -> None:
    """Validate config structure and values."""
    if "runs" not in config:
        raise ValueError("Config must have 'runs' array")

    for i, run in enumerate(config["runs"]):
        if "base" not in run and "upper" not in run and "tall" not in run:
            raise ValueError(f"Run {i} must have at least one of: base, upper, tall")

        for section in ("base", "upper", "tall"):
            for j, cab in enumerate(run.get(section, [])):
                _validate_cabinet(cab, i, section, j, config["settings"])


def _validate_cabinet(cab: dict, run_idx: int, section: str, cab_idx: int,
                      settings: dict) -> None:
    """Validate a single cabinet config."""
    if "type" not in cab:
        raise ValueError(f"Run {run_idx}/{section}/{cab_idx}: missing 'type'")

    cab_type = cab["type"]
    if cab_type not in CABINET_LEVELS:
        raise ValueError(
            f"Run {run_idx}/{section}/{cab_idx}: unknown type '{cab_type}'"
        )

    if "width" not in cab:
        raise ValueError(f"Run {run_idx}/{section}/{cab_idx}: missing 'width'")

    if cab["width"] <= 0:
        raise ValueError(
            f"Run {run_idx}/{section}/{cab_idx}: width must be > 0"
        )

    if cab_type == "corner-blind":
        bd = cab.get("blindDepth", 300)
        if bd >= cab["width"]:
            raise ValueError(
                f"Run {run_idx}/{section}/{cab_idx}: "
                f"blindDepth ({bd}) must be < width ({cab['width']})"
            )


def calculate_run_positions(run: dict, settings: dict) -> list[dict]:
    """Calculate x positions for each cabinet in a run (in mm).

    Uses cabinetGap (carcass-to-carcass spacing) for positioning.
    frontGap is used only for door/drawer front geometry (in geometry_builder).

    Returns list of dicts with cabinet config + computed x position.
    """
    positions = []
    x = 0
    # Use cabinetGap for carcass positioning (not frontGap)
    gap = settings.get("cabinetGap", 0)

    for cab in run.get("base", []):
        positions.append({**cab, "x_mm": x, "level": "base"})
        x += cab["width"] + gap

    return positions


def calculate_upper_positions(run: dict, settings: dict) -> list[dict]:
    """Calculate x positions for upper cabinets in a run (in mm).

    Uses cabinetGap (carcass-to-carcass spacing) for positioning.
    """
    positions = []
    x = 0
    # Use cabinetGap for carcass positioning (not frontGap)
    gap = settings.get("cabinetGap", 0)

    for cab in run.get("upper", []):
        positions.append({**cab, "x_mm": x, "level": "upper"})
        x += cab["width"] + gap

    return positions


def mm_to_m(mm: float) -> float:
    """Convert millimeters to meters."""
    return mm / 1000.0
