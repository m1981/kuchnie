"""LEGRABOX drawer system — catalog data and decomposition.

Sources:
  - Blum Catalogue 2024/2025 (pages 198–253, 728–731)
  - User's PDF analysis (DQBQRY, DQBMJY, DQBNYM planning sheets)

All dimensions in mm unless noted.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Accessory, MachiningOp, Panel


# ── Height codes ────────────────────────────────────────────────

@dataclass
class LegraboxHeight:
    """One LEGRABOX height code (N/M/K/C/F)."""
    code: str
    side_height_mm: float       # drawer side metal wall height
    back_panel_height_mm: float # chipboard back panel cutting height (confirmed from Blum)
    min_install_height_mm: float # minimum cabinet internal height needed


HEIGHTS: dict[str, LegraboxHeight] = {
    "N": LegraboxHeight("N", 66.5, 39,   50),
    "M": LegraboxHeight("M", 90.5, 63,   68),   # 63 from Blum catalogue
    "K": LegraboxHeight("K", 128.5, 101, 106),
    "C": LegraboxHeight("C", 177, 148,   155),   # 148 confirmed DQBQRY
    "F": LegraboxHeight("F", 241, 212,   220),   # 212 from Blum catalogue
}


# ── Nominal lengths (NL) ────────────────────────────────────────

# Height × NL availability  (True = available)
NL_MATRIX: dict[str, dict[int, bool]] = {
    "N": {270: False, 300: False, 350: False, 400: True,  450: True,
          500: True,  550: True,  600: False, 650: False},
    "M": {270: True,  300: True,  350: True,  400: True,  450: True,
          500: True,  550: True,  600: True,  650: True},
    "K": {270: False, 300: True,  350: True,  400: True,  450: True,
          500: True,  550: True,  600: True,  650: False},
    "C": {270: True,  300: True,  350: True,  400: True,  450: True,
          500: True,  550: True,  600: True,  650: True},
    "F": {270: False, 300: False, 350: False, 400: True,  450: True,
          500: True,  550: True,  600: True,  650: True},
}

VALID_NL = [270, 300, 350, 400, 450, 500, 550, 600, 650]

# Capacity × NL  (kg)
CAPACITY_NL: dict[int, list[int]] = {
    40: [270, 300, 350, 400, 450, 500, 550, 600],
    70: [450, 500, 550, 600, 650],
}


# ── Dimension formulas ──────────────────────────────────────────

RUNNER_CLEARANCE_PER_SIDE_MM = 13  # LEGRABOX runner + clearance


def lw(kb: int, side_thickness: int = 0) -> int:
    """Lichte Weite (clear width available for drawer box).

    KB = cabinet internal width (between carcass inner faces).
    LW = KB − 2 × 13mm  (runner + clearance per side).

    The side_thickness parameter is accepted for API compatibility but
    not used — Blum's LW is determined by runner clearance, not by the
    carcass side panel thickness.  Always verify against Blum's official
    LW/KB table for your exact runner.
    """
    return kb - 2 * RUNNER_CLEARANCE_PER_SIDE_MM


def back_panel_width(lw_val: int) -> int:
    """Chipboard back panel width = LW − 38."""
    return lw_val - 38


def base_panel_width(lw_val: int) -> int:
    """Drawer base (bottom) panel width = LW − 35."""
    return lw_val - 35


def runner_screw_first_offset() -> int:
    """First runner screw distance from cabinet front edge."""
    return 46


def base_panel_depth(nl: int) -> int:
    """Drawer base depth = NL − 10  (chipboard back variant).

    For steel back variant: NL − 21  (not used in PoC).
    """
    return nl - 10


def drawer_internal_width(lw_val: int) -> int:
    """Drawer box internal width = LW − 49."""
    return lw_val - 49


def drawer_internal_depth(nl: int) -> int:
    """Drawer box internal depth = NL − 10  (chipboard back)."""
    return nl - 10


# ── Runner screw positions ──────────────────────────────────────

# Blum publishes these per NL on the runner itself (pre-punched).
# First screw is at 46mm from front edge, then 32mm pitch clusters.
# The big spans are NL-specific lookups.
#
# For the PoC we encode first-screw + a few representative positions.
# The user fills in the complete chart from their PDF when ready.

RUNNER_SCREW_POSITIONS: dict[int, list[float]] = {
    # NL: [screw offsets from front edge, in mm]
    # First screw always ≈46mm from cabinet front edge.
    # Remaining positions: from Blum's pre-punched marks.
    # TODO: fill in exact values from Blum Montageanleitung per NL
    400: [46, 78, 110, 302],
    450: [46, 78, 110, 350],
    500: [46, 78, 110, 398],
    550: [46, 78, 110, 446],
    600: [46, 78, 110, 494],
}


# ── Validation ──────────────────────────────────────────────────

def validate_height_nl(height_code: str, nl: int) -> list[str]:
    """Check that the height × NL combination is valid."""
    errors: list[str] = []
    if height_code not in HEIGHTS:
        errors.append(f"Unknown height code: {height_code!r}")
        return errors
    if nl not in VALID_NL:
        errors.append(f"Invalid NL: {nl}. Valid: {VALID_NL}")
        return errors
    if not NL_MATRIX.get(height_code, {}).get(nl, False):
        errors.append(
            f"LEGRABOX {height_code} not available with NL={nl}"
        )
    return errors


def validate_capacity(nl: int, capacity_kg: int) -> list[str]:
    """Check that the NL supports the requested carrying capacity."""
    errors: list[str] = []
    if capacity_kg not in CAPACITY_NL:
        errors.append(f"Unknown capacity: {capacity_kg}kg. Valid: 40, 70")
        return errors
    if nl not in CAPACITY_NL[capacity_kg]:
        errors.append(
            f"{capacity_kg}kg capacity not available with NL={nl}. "
            f"Available NLs: {CAPACITY_NL[capacity_kg]}"
        )
    return errors


# ── Drawer box decomposition ────────────────────────────────────

def decompose_drawer_box(
    cabinet_id: str,
    drawer_id: str,
    kb: int,
    nl: int,
    height_code: str,
    side_thickness: int,
    base_material: str = "plyta_16mm",
    back_material: str = "plyta_16mm",
    base_thickness: int = 16,
    back_thickness: int = 16,
) -> tuple[list[Panel], list[MachiningOp]]:
    """Decompose one LEGRABOX drawer into board-cut panels + runner ops.

    Returns:
      panels:  drawer back + drawer base (the two board-cut parts)
      ops:     runner mounting drill positions for ONE side panel
               (apply to both left and right carcass sides)

    The metal drawer sides, runners, and clips are purchased accessories
    (not panels) — tracked separately.
    """
    ht = HEIGHTS[height_code]
    lw_val = lw(kb, side_thickness)

    back_w = back_panel_width(lw_val)   # LW − 38
    back_h = ht.back_panel_height_mm

    base_w = base_panel_width(lw_val)   # LW − 35
    base_d = base_panel_depth(nl)       # NL − 10

    panels = [
        Panel(
            id=f"{cabinet_id}_drawer_{drawer_id}_back",
            name=f"Szuflada {drawer_id} — tył",
            material=back_material,
            thickness_mm=back_thickness,
            width_mm=back_w,
            height_mm=back_h,
            banded_edges={},
            quantity=1,
        ),
        Panel(
            id=f"{cabinet_id}_drawer_{drawer_id}_base",
            name=f"Szuflada {drawer_id} — dno",
            material=base_material,
            thickness_mm=base_thickness,
            width_mm=base_w,
            height_mm=base_d,
            banded_edges={},
            quantity=1,
        ),
    ]

    # Runner mounting screws — on each carcass side panel
    screw_offsets = RUNNER_SCREW_POSITIONS.get(nl, [46, 78, 110])
    ops: list[MachiningOp] = []
    for y in screw_offsets:
        ops.append(MachiningOp(
            type="drill",
            x_mm=0,   # x position on side panel = depth-inset, set by caller
            y_mm=y,   # distance from front edge of side panel
            diameter_mm=5,
            depth_mm=0,  # through-hole for Euro screw
            note=f"LEGRABOX {height_code} runner screw (NL={nl})",
        ))

    return panels, ops


# ── Runner accessory ────────────────────────────────────────────

def make_runner_accessory(
    cabinet_id: str,
    drawer_id: str,
    height_code: str,
    nl: int,
    capacity_kg: int = 40,
    colour: str = "SW-M",
    motion: str = "BLUMOTION S",
) -> Accessory:
    """Create an Accessory entry for a LEGRABOX runner set."""
    ht = HEIGHTS[height_code]
    part_nr = f"LEGRABOX {height_code} NL{nl} {capacity_kg}kg {colour}"
    return Accessory(
        id=f"{cabinet_id}_runner_{drawer_id}",
        name=f"{part_nr} ({motion})",
        type="runner",
        quantity=1,
    )
