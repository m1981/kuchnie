"""Kitchen-level operations — aggregate panels, accessories, BOM across rows.

This module sits above the decomposer: it iterates over rows and cabinets,
collects DecompositionResults, and provides kitchen-wide views.
"""

from __future__ import annotations

from .bom import BOM, calculate_bom, worktop_bom_items
from .buildability import (
    BuildabilityVerdict,
    HeightSet,
    require_buildable,
    row_findings,
)
from .decomposer import decompose
from .model import (
    Accessory,
    DecompositionResult,
    Kitchen,
    Panel,
)

# HeightSet and row_findings moved to the gate layer (kuchnie-5un): a rule
# set belongs with the gates that run it, and the move is what lets this
# module depend on buildability at the top of the file instead of both
# modules reaching into each other from inside function bodies. Imported
# here (not merely re-exported) because ``validate_rows`` uses them — and
# ``from kuchnie_core.kitchen import HeightSet, row_findings``, the
# historic path, keeps resolving.


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
    worktop_prices: dict[str, float] | None = None,
    cutout_prices: dict[str, float] | None = None,
    verdict: BuildabilityVerdict | None = None,
) -> BOM:
    """One BOM for the entire kitchen (all cabinets summed), plus the
    worktop positions: per-lm laminate lines with per-piece cutout charges
    (wk-4c37f4ee; stone worktops are quoted externally).

    Emission is gated on the buildability verdict (UC-2 ext 5a): a FAILED
    verdict raises BuildabilityError — no purchase list for a kitchen that
    would scrap board. Pass a precomputed ``verdict`` to skip re-running
    the gates.
    """
    require_buildable(kitchen, verdict=verdict)
    all_items = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            result = decompose(cab)
            cab_bom = calculate_bom(result, board_prices, edge_prices)
            all_items.extend(cab_bom.items)

    all_items.extend(worktop_bom_items(kitchen.worktops, worktop_prices, cutout_prices))

    bom = BOM(cabinet_id=kitchen.project_name or "kitchen")
    bom.items = all_items
    bom.total_cost = round(sum(i.total for i in all_items), 2)
    return bom


# ── Row validation ──────────────────────────────────────────────

def validate_rows(
    kitchen: Kitchen, heights: HeightSet | None = None
) -> list[str]:
    """Display layer over ``row_findings`` — same rules, rendered as the
    flat strings the UI and older callers expect (wk-acc8e094).
    ``heights`` is threaded through unchanged (wk-5b929a7c)."""
    return [f.message for f in row_findings(kitchen, heights)]
