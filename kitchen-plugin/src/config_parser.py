"""Kitchen config parser — pure Python, no bpy dependency.

Loads JSON config, validates it, converts mm to meters for Blender.
"""

import json
from pathlib import Path

# Schema versioning
SUPPORTED_VERSIONS = {"1.0", "1.1"}
CURRENT_VERSION = "1.1"

# Default settings (mm, except offsets which are in meters)
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
    # Tolerance offsets (meters):
    #   frontOffset     = how far door/drawer fronts protrude from cabinet face
    #   clearanceOffset = small gap for geometric clearance (blind corners, etc.)
    "frontOffset": 0.001,     # 1mm
    "clearanceOffset": 0.001, # 1mm
    # Construction parameters (mm):
    #   corpusThickness = thickness of carcass board (chipboard)
    #   frontThickness  = thickness of front panel (MDF/chipboard)
    #   backThickness   = thickness of back panel (HDF)
    #   grooveOffset    = distance from rear edge to back panel groove
    #   frontOverlay    = how much front overlaps carcass edges
    "corpusThickness": 18,
    "frontThickness": 19,
    "backThickness": 3,
    "grooveOffset": 10,
    "frontOverlay": 2,
}

# Drawer validation constants
MIN_DRAWER_HEIGHT = 30   # mm - minimum practical drawer height
MAX_DRAWER_COUNT = 6     # maximum number of drawers in one cabinet

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
    # Version validation
    version = config.get("version", "1.0")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported config version: '{version}'. "
            f"Supported versions: {sorted(SUPPORTED_VERSIONS)}"
        )

    if "runs" not in config:
        raise ValueError("Config must have 'runs' array")

    # Validate settings
    _validate_settings(config.get("settings", {}))

    # Validate materials
    for name, mat in config.get("materials", {}).items():
        _validate_material(name, mat)

    for i, run in enumerate(config["runs"]):
        if "base" not in run and "upper" not in run and "tall" not in run:
            raise ValueError(f"Run {i} must have at least one of: base, upper, tall")

        for section in ("base", "upper", "tall"):
            for j, cab in enumerate(run.get(section, [])):
                _validate_cabinet(cab, i, section, j, config["settings"])


def _validate_settings(settings: dict) -> None:
    """Validate construction and other settings."""
    # Construction parameter validation
    construction_params = {
        "corpusThickness": (10, 30),   # 10-30mm is reasonable
        "frontThickness": (10, 30),    # 10-30mm is reasonable
        "backThickness": (2, 10),      # 2-10mm is reasonable
        "grooveOffset": (5, 20),       # 5-20mm is reasonable
        "frontOverlay": (0, 10),       # 0-10mm is reasonable
    }

    for param, (min_val, max_val) in construction_params.items():
        if param in settings:
            value = settings[param]
            if value <= 0:
                raise ValueError(
                    f"Setting '{param}' must be > 0, got {value}"
                )
            if value < min_val or value > max_val:
                raise ValueError(
                    f"Setting '{param}' must be between {min_val} and {max_val}mm, "
                    f"got {value}"
                )


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

    # Validate drawers
    if cab_type in ("base-drawers", "wall-drawers"):
        _validate_drawers(cab, run_idx, section, cab_idx, settings)

    # Validate drawer-door combo
    if cab_type == "base-drawer-door":
        drawer_h = cab.get("drawerHeight", 150)
        if drawer_h < MIN_DRAWER_HEIGHT:
            raise ValueError(
                f"Run {run_idx}/{section}/{cab_idx}: "
                f"drawerHeight ({drawer_h}mm) is too small (min {MIN_DRAWER_HEIGHT}mm)"
            )
        max_h = settings.get("baseBodyHeight", 720)
        if drawer_h >= max_h:
            raise ValueError(
                f"Run {run_idx}/{section}/{cab_idx}: "
                f"drawerHeight ({drawer_h}mm) exceeds carcass height ({max_h}mm)"
            )


def _validate_material(name: str, mat: dict) -> None:
    """Validate a material definition."""
    # Color is required
    if "color" not in mat:
        raise ValueError(f"Material '{name}': missing 'color'")

    color = mat["color"]
    if not isinstance(color, list) or len(color) not in (3, 4):
        raise ValueError(
            f"Material '{name}': color must be [R,G,B] or [R,G,B,A], "
            f"got {len(color)} elements"
        )

    for i, v in enumerate(color):
        if not 0 <= v <= 1:
            channel = "RGBA"[i]
            raise ValueError(
                f"Material '{name}': color[{i}] ({channel}) = {v} must be 0-1"
            )

    # Optional PBR properties
    if "roughness" in mat:
        r = mat["roughness"]
        if not 0 <= r <= 1:
            raise ValueError(
                f"Material '{name}': roughness = {r} must be 0-1"
            )

    if "metallic" in mat:
        m = mat["metallic"]
        if not 0 <= m <= 1:
            raise ValueError(
                f"Material '{name}': metallic = {m} must be 0-1"
            )

    if "alpha" in mat:
        a = mat["alpha"]
        if not 0 <= a <= 1:
            raise ValueError(
                f"Material '{name}': alpha = {a} must be 0-1"
            )

    if "emission" in mat:
        e = mat["emission"]
        if not 0 <= e <= 1:
            raise ValueError(
                f"Material '{name}': emission = {e} must be 0-1"
            )


def _validate_drawers(cab: dict, run_idx: int, section: str, cab_idx: int,
                      settings: dict) -> None:
    """Validate drawer configuration."""
    prefix = f"Run {run_idx}/{section}/{cab_idx}"
    drawers = cab.get("drawers", 3)
    front_gap = settings.get("frontGap", 2)

    if section == "base":
        max_h = settings.get("baseBodyHeight", 720)
    else:  # upper
        max_h = settings.get("wallHeight", 720)

    if isinstance(drawers, int):
        # Count validation
        if drawers < 1:
            raise ValueError(f"{prefix}: drawers count must be >= 1, got {drawers}")
        if drawers > MAX_DRAWER_COUNT:
            raise ValueError(
                f"{prefix}: drawers count must be <= {MAX_DRAWER_COUNT}, got {drawers}"
            )
        # Check if equal-height drawers fit
        total_gap = front_gap * (drawers - 1)
        min_drawer_h = (max_h - total_gap) / drawers
        if min_drawer_h < MIN_DRAWER_HEIGHT:
            raise ValueError(
                f"{prefix}: {drawers} drawers with {front_gap}mm gaps "
                f"would result in {min_drawer_h:.0f}mm per drawer (min {MIN_DRAWER_HEIGHT}mm)"
            )
    elif isinstance(drawers, list):
        # Array validation
        if len(drawers) < 1:
            raise ValueError(f"{prefix}: drawers array must not be empty")
        if len(drawers) > MAX_DRAWER_COUNT:
            raise ValueError(
                f"{prefix}: drawers array length must be <= {MAX_DRAWER_COUNT}"
            )

        for i, h in enumerate(drawers):
            if h < MIN_DRAWER_HEIGHT:
                raise ValueError(
                    f"{prefix}: drawer[{i}] height ({h}mm) is too small "
                    f"(min {MIN_DRAWER_HEIGHT}mm)"
                )
            if h >= max_h:
                raise ValueError(
                    f"{prefix}: drawer[{i}] height ({h}mm) exceeds "
                    f"carcass height ({max_h}mm)"
                )

        total = sum(drawers) + front_gap * (len(drawers) - 1)
        if total > max_h:
            raise ValueError(
                f"{prefix}: drawer heights ({sum(drawers)}mm) + "
                f"gaps ({front_gap * (len(drawers) - 1)}mm) = {total}mm "
                f"exceed carcass height ({max_h}mm)"
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
