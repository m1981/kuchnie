"""Variant pricing + the drawer-axis budget walk (UC-1 ext 1a).

Spec: kitchen-erp/docs/specs/drawer-substitution.md (SC-drsub-003,
SC-drsub-005, SC-drsub-006). The comparison board's substitution story:
the client's budget lands below "od", the owner walks one axis at a
time until a variant fits or the axis is honestly exhausted.

Two functions, deliberately DB-free:

* ``price_variant`` prices one derivation's BOM lines against a plain
  ``{line name: unit price}`` price book the caller assembles from its
  price sources (material mirror, hardware catalog). A line the book
  does not know stays IN the result flagged ``priced=False`` and marks
  the whole price ``incomplete`` -- the UC-1 ext 2a pattern
  (quote_range's canvas rule), never a silent omission.
* ``walk_drawer_axis`` walks the drawer-system axis of a DRAFT variant:
  candidates come only from ``DrawerSystemFactory`` (the catalog-
  verified registry -- nothing free-typed can enter, and
  ``Variant.set_overrides`` refuses anything outside it anyway), each
  is re-derived and priced in both widelka tiers, and the result is
  always explicit: a fitting candidate, or ``no_fit_on_axis`` with the
  full candidate record. Termination is structural -- the registry is
  finite. The walk PROPOSES; applying the winning override is the
  board's action, so the variant's own axis is restored before return.

"Both tiers" here is the widelka od/do brutto pair (owner parameters
2026-08-02: od = net x 0.95 x VAT, do = net x 1.15 x VAT, rounded to
100 zl -- quote_range's constants, imported not re-spelled), and the
budget fit test is ``od_brutto <= budget``: UC-1 ext 1a triggers when
the budget is below "od", so "od" reaching the budget is the fit.
"""
from __future__ import annotations

from dataclasses import dataclass

from kuchnie_core import DrawerSystemFactory

from .models import Variant
from .quote_range import (
    VAT_RATE,
    WIDELKA_DO_MARGIN,
    WIDELKA_OD_MARGIN,
    round_to_100,
)
from .variant_derivation import DerivedArtifacts, derive_variant


@dataclass(frozen=True)
class PricedLine:
    """One BOM line met with the price book. ``priced=False`` means the
    book had no entry: the line still renders, flagged (UC-1 ext 2a)."""
    name: str
    qty: float
    unit: str
    unit_price: float | None
    total_net: float | None
    priced: bool


@dataclass(frozen=True)
class VariantPrice:
    """One derivation priced in both widelka tiers."""
    variant_name: str
    drawer_system: str
    lines: tuple[PricedLine, ...]
    total_net: float          # priced lines only; incomplete says so loudly
    incomplete: bool          # any unpriced line (never silently omitted)
    od_brutto: float
    do_brutto: float


def price_variant(
    artifacts: DerivedArtifacts, price_book: dict[str, float]
) -> VariantPrice:
    """Price a derived artifact set line by line against ``price_book``."""
    lines: list[PricedLine] = []
    total = 0.0
    for bom_line in artifacts.bom_lines:
        unit_price = price_book.get(bom_line.name)
        if unit_price is None:
            lines.append(PricedLine(bom_line.name, bom_line.qty,
                                    bom_line.unit, None, None, False))
            continue
        line_total = bom_line.qty * unit_price
        total += line_total
        lines.append(PricedLine(bom_line.name, bom_line.qty, bom_line.unit,
                                unit_price, round(line_total, 2), True))
    return VariantPrice(
        variant_name=artifacts.variant_name,
        drawer_system=artifacts.parameters.drawer_system,
        lines=tuple(lines),
        total_net=round(total, 2),
        incomplete=any(not line.priced for line in lines),
        od_brutto=round_to_100(total * WIDELKA_OD_MARGIN * VAT_RATE),
        do_brutto=round_to_100(total * WIDELKA_DO_MARGIN * VAT_RATE),
    )


@dataclass(frozen=True)
class AxisCandidate:
    """One registry system tried by the walk. A candidate whose stack
    the substitution rejects (SC-drsub-004's ValueError) is carried
    with its reason -- never dropped from the record."""
    system: str
    price: VariantPrice | None    # None when rejected
    rejected: bool
    rejection_reason: str | None


@dataclass(frozen=True)
class AxisWalkResult:
    """The walk's explicit outcome: a fit, or no-fit with the full
    candidate record. There is no silent shape."""
    axis: str
    budget_brutto: float
    candidates: tuple[AxisCandidate, ...]   # buildable cheapest-first, rejected last
    fit: AxisCandidate | None
    no_fit_on_axis: bool


def walk_drawer_axis(
    variant: Variant, budget_brutto: float, price_book: dict[str, float]
) -> AxisWalkResult:
    """Walk the drawer-system axis of a DRAFT variant against a budget.

    Raises whatever ``Variant.set_overrides`` raises on a non-draft
    variant (the walk mutates the axis candidate by candidate through
    the one sanctioned doorway, and restores it before returning).
    """
    original = variant.drawer_system
    candidates: list[AxisCandidate] = []
    try:
        for system in DrawerSystemFactory.list_ids():   # the registry, only
            variant.set_overrides(drawer_system=system)
            try:
                artifacts = derive_variant(variant)
            except ValueError as err:
                # A stack this system cannot build: carried, not swallowed.
                candidates.append(AxisCandidate(system, None, True, str(err)))
                continue
            candidates.append(
                AxisCandidate(system, price_variant(artifacts, price_book),
                              False, None))
    finally:
        variant.set_overrides(drawer_system=original)

    candidates.sort(key=lambda c: (c.rejected,
                                   c.price.od_brutto if c.price else 0.0))
    fit = next((c for c in candidates
                if not c.rejected and c.price.od_brutto <= budget_brutto),
               None)
    return AxisWalkResult(
        axis="drawer_system",
        budget_brutto=budget_brutto,
        candidates=tuple(candidates),
        fit=fit,
        no_fit_on_axis=fit is None,
    )
