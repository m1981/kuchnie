"""Kitchen-level operations — aggregate panels, accessories, BOM across rows.

This module sits above the decomposer: it iterates over rows and cabinets,
collects DecompositionResults, and provides kitchen-wide views.
"""

from __future__ import annotations

from collections import defaultdict

from .bom import BOM, calculate_bom
from .decomposer import decompose
from .model import (
    Accessory,
    CabinetInstance,
    DecompositionResult,
    Kitchen,
    Panel,
    Row,
)


# ── Per-cabinet decomposition cache ─────────────────────────────

def decompose_kitchen(kitchen: Kitchen) -> dict[str, DecompositionResult]:
    """Decompose every cabinet in every row.  Returns {cabinet_id: result}."""
    results: dict[str, DecompositionResult] = {}
    for row in kitchen.rows:
        for cab in row.cabinets:
            results[cab.id] = decompose(cab)
    return results


# ── Flat aggregations ───────────────────────────────────────────

def all_panels(kitchen: Kitchen) -> list[Panel]:
    """Flat list of every panel across all cabinets, all rows."""
    panels: list[Panel] = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            panels.extend(decompose(cab).panels)
    return panels


def all_accessories(kitchen: Kitchen) -> list[Accessory]:
    """Flat list of every accessory across all cabinets, all rows."""
    accs: list[Accessory] = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            accs.extend(decompose(cab).accessories)
    return accs


# ── Aggregated BOM ──────────────────────────────────────────────

def kitchen_bom(
    kitchen: Kitchen,
    board_prices: dict[str, float] | None = None,
    edge_prices: dict[str, float] | None = None,
) -> BOM:
    """One BOM for the entire kitchen (all cabinets summed)."""
    all_items = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            result = decompose(cab)
            cab_bom = calculate_bom(result, board_prices, edge_prices)
            all_items.extend(cab_bom.items)

    bom = BOM(cabinet_id=kitchen.project_name or "kitchen")
    bom.items = all_items
    bom.total_cost = round(sum(i.total for i in all_items), 2)
    return bom


# ── Row validation ──────────────────────────────────────────────

def validate_rows(kitchen: Kitchen) -> list[str]:
    """Check that all cabinets fit in their rows.  Returns list of errors."""
    errors: list[str] = []
    for row in kitchen.rows:
        used = row.used_width_mm()
        if used > row.wall_width_mm:
            errors.append(
                f"Row '{row.label}': cabinets use {used}mm "
                f"but wall is only {row.wall_width_mm}mm"
            )
        remaining = row.remaining_mm()
        if remaining < 0:
            errors.append(
                f"Row '{row.label}': {-remaining}mm overflows the wall"
            )
    return errors
