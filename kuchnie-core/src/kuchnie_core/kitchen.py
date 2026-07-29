"""Kitchen-level operations — aggregate panels, accessories, BOM across rows.

This module sits above the decomposer: it iterates over rows and cabinets,
collects DecompositionResults, and provides kitchen-wide views.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    verdict: "BuildabilityVerdict | None" = None,
) -> BOM:
    """One BOM for the entire kitchen (all cabinets summed), plus the
    worktop positions: per-lm laminate lines with per-piece cutout charges
    (wk-4c37f4ee; stone worktops are quoted externally).

    Emission is gated on the buildability verdict (UC-2 ext 5a): a FAILED
    verdict raises BuildabilityError — no purchase list for a kitchen that
    would scrap board. Pass a precomputed ``verdict`` to skip re-running
    the gates.
    """
    from .buildability import require_buildable

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

@dataclass(frozen=True)
class HeightSet:
    """Decided per-project height lines (playbook Phase 1), supplied by
    the consumer that stores them (kitchen-erp ProjectDefaults,
    wk-5b929a7c) — kuchnie-core defines its own carrier so the dependency
    stays one-way (ERP imports core, never the reverse).

    worktop_height_mm: the decided worktop line, floor to worktop top.
    worktop_thickness_mm: top thickness used to read a leg's actual line
        off its base carcasses (plinth + carcass + top); playbook default
        38 — the model's WorktopSegment carries per-row geometry, this is
        the project-line convention.
    """
    worktop_height_mm: float | None = None
    worktop_thickness_mm: float = 38.0


def row_findings(
    kitchen: Kitchen, heights: HeightSet | None = None
) -> list["Finding"]:
    """The design-legality slice of the buildability gate, structured
    (wk-acc8e094): each rule emits a Finding with its gate id, severity
    and offending ref — buildability buckets these directly, no string
    parsing. ``validate_rows`` renders the same findings as strings.

    Rules (today-feasible playbook Phase-8 slice, wk-89a668a2):

    * FIT  — cabinets fit their rows (blocking).
    * G1   — one worktop line per run: base cabinets (plinth > 0) in a
      row must share total height_mm (blocking). With a ``heights``
      set supplied (wk-5b929a7c), G1 ADDITIONALLY compares each row's
      (leg's) worktop line — plinth + carcass + top thickness — against
      the decided ``worktop_height_mm`` and reports a diverging leg
      (finding, not exception; ``heights=None`` keeps exactly today's
      behaviour).
    * G6   — plinth line unbroken: base cabinets in a row must share
      plinth_height_mm (blocking).
    * WSTD — run composition uses standard widths (KitchenStandards;
      corner cabinets exempt — they follow their own 1000–1300 rule;
      wall irregularity is absorbed by one filler at the wall end).
      Advisory — it flags, it does not fail.

    G2/G3/G4/G5/G7 of the gate need model support the Row does not carry
    yet (L-adjacency, appliance positions, cutout positions) and stay
    with wk-89a668a2.
    """
    from .buildability import ADVISORY, BLOCKING, Finding
    from .standards import KitchenStandards

    findings: list[Finding] = []
    std = KitchenStandards()
    for row in kitchen.rows:
        used = row.used_width_mm()
        if used > row.wall_width_mm:
            findings.append(Finding(
                "FIT", BLOCKING,
                f"Row '{row.label}': cabinets use {used}mm "
                f"but wall is only {row.wall_width_mm}mm",
                row.label,
            ))
        remaining = row.remaining_mm()
        if remaining < 0:
            findings.append(Finding(
                "FIT", BLOCKING,
                f"Row '{row.label}': {-remaining}mm overflows the wall",
                row.label,
            ))

        base = [c for c in row.cabinets if c.plinth_height_mm > 0]
        carcass_heights = {c.height_mm for c in base}
        if len(carcass_heights) > 1:
            findings.append(Finding(
                "G1", BLOCKING,
                f"Row '{row.label}': G1 — worktop line broken, base cabinet "
                f"heights differ {sorted(carcass_heights)}mm (playbook "
                f"Phase 1: one height line per run)",
                row.label,
            ))
        if (heights is not None
                and heights.worktop_height_mm is not None and base):
            decided = heights.worktop_height_mm
            top = heights.worktop_thickness_mm
            lines = sorted({
                c.plinth_height_mm + c.height_mm + top for c in base
            })
            # 1e-3mm tolerance: absorbs float noise while staying far
            # below carpentry precision (wk-5b929a7c red-team finding —
            # sub-micron divergences rendered self-identical messages).
            diverging = [line for line in lines
                         if abs(line - decided) > 1e-3]
            if diverging:
                findings.append(Finding(
                    "G1", BLOCKING,
                    f"Row '{row.label}': G1 — worktop line off the decided "
                    f"project line: plinth + carcass + {top:g}mm top gives "
                    f"{', '.join(f'{line:g}' for line in diverging)}mm, "
                    f"decided worktop_height_mm is {decided:g}mm (playbook "
                    f"Phase 1: one project-wide line across legs; "
                    f"720 carcass + 100..150 plinth + 38 top ⇒ 850..910)",
                    row.label,
                ))
        plinths = {c.plinth_height_mm for c in base}
        if len(plinths) > 1:
            findings.append(Finding(
                "G6", BLOCKING,
                f"Row '{row.label}': G6 — plinth line broken, plinth heights "
                f"differ {sorted(plinths)}mm",
                row.label,
            ))
        for c in row.cabinets:
            if "narozna" in c.type:
                continue
            if not std.is_standard_width(c.width_mm):
                findings.append(Finding(
                    "WSTD", ADVISORY,
                    f"advisory: Row '{row.label}': cabinet {c.id} width "
                    f"{c.width_mm}mm is non-standard (playbook Phase 4: "
                    f"standard widths only; absorb wall irregularity with "
                    f"one filler at the wall end)",
                    c.id,
                ))
    return findings


def validate_rows(
    kitchen: Kitchen, heights: HeightSet | None = None
) -> list[str]:
    """Display layer over ``row_findings`` — same rules, rendered as the
    flat strings the UI and older callers expect (wk-acc8e094).
    ``heights`` is threaded through unchanged (wk-5b929a7c)."""
    return [f.message for f in row_findings(kitchen, heights)]
