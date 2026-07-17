"""Kitchen-level operations — aggregate panels, accessories, BOM across rows.

This module sits above the decomposer: it iterates over rows and cabinets,
collects DecompositionResults, and provides kitchen-wide views.
"""

from __future__ import annotations


from .bom import BOM, calculate_bom, worktop_bom_items
from .decomposer import decompose
from .model import (
    Accessory,
    DecompositionResult,
    Kitchen,
    Panel,
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
    worktop_prices: dict[str, float] | None = None,
    cutout_prices: dict[str, float] | None = None,
) -> BOM:
    """One BOM for the entire kitchen (all cabinets summed), plus the
    worktop positions: per-lm laminate lines with per-piece cutout charges
    (wk-4c37f4ee; stone worktops are quoted externally)."""
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

def validate_rows(kitchen: Kitchen) -> list[str]:
    """Check that all cabinets fit in their rows.  Returns list of errors.

    Extended with the today-feasible slice of the playbook Phase-8 gate
    (docs/l-kitchen-design-playbook.md §6; first design-legality rules of
    the buildability verdict, wk-89a668a2):

    * G1 — one worktop line per run: base cabinets (plinth > 0) in a row
      must share total height_mm.
    * G6 — plinth line unbroken: base cabinets in a row must share
      plinth_height_mm.
    * width advisory — run composition uses standard widths
      (KitchenStandards; corner cabinets exempt — they follow their own
      1000–1300 rule; wall irregularity is absorbed by one filler at the
      wall end). Prefixed "advisory:" — it flags, it does not fail.

    G2/G3/G4/G5/G7 of the gate need model support the Row does not carry
    yet (L-adjacency, appliance positions, cutout positions) and stay
    with wk-89a668a2.
    """
    from .standards import KitchenStandards

    errors: list[str] = []
    std = KitchenStandards()
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

        base = [c for c in row.cabinets if c.plinth_height_mm > 0]
        heights = {c.height_mm for c in base}
        if len(heights) > 1:
            errors.append(
                f"Row '{row.label}': G1 — worktop line broken, base cabinet "
                f"heights differ {sorted(heights)}mm (playbook Phase 1: one "
                f"height line per run)"
            )
        plinths = {c.plinth_height_mm for c in base}
        if len(plinths) > 1:
            errors.append(
                f"Row '{row.label}': G6 — plinth line broken, plinth heights "
                f"differ {sorted(plinths)}mm"
            )
        for c in row.cabinets:
            if "narozna" in c.type:
                continue
            if not std.is_standard_width(c.width_mm):
                errors.append(
                    f"advisory: Row '{row.label}': cabinet {c.id} width "
                    f"{c.width_mm}mm is non-standard (playbook Phase 4: "
                    f"standard widths only; absorb wall irregularity with "
                    f"one filler at the wall end)"
                )
    return errors
