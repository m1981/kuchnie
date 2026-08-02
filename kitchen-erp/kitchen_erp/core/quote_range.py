# kitchen_erp/core/quote_range.py
"""Rough-quote canvas widelka + per-type labor pricing (wk-224f3712 /
wk-59b943b1, owner-merged scopes, decision 2026-08-02).

UC-1 threshold 1 (docs/specs/use-cases.md § UC-1 steps 1-4, screens.md's
Canvas row): at the client's table, before any hb5 decomposition exists,
the canvas prices itself TWICE -- tier "standard" (melamine, Tandembox,
standard hinges) and tier "komfort" (upper decors, LEGRABOX, soft-close)
-- and shows an od-do widelka (range), never a point estimate.

Two module families need two different pricing strategies at this
threshold (no decomposition yet, wk-224f3712's "approximate pragmatically"
note):

* BUILDABLE_MODULE_KINDS -- cabinets kuchnie_core/BOMGenerator can already
  cost from materials (corpus/front/back/edge + hardware). The "standard"
  tier IS that existing material-cost baseline; "komfort" adds a rough
  per-drawer / per-door delta (KOMFORT_*_DELTA constants below) standing
  in for legrabox-vs-tandembox and soft-close-vs-standard-hinge, without
  building full decomposition-per-tier (that is threshold 2's job, once a
  real hb5 design exists).
* EQUIPMENT_MODULE_KINDS / CORNER_MODULE_KINDS -- non-decomposable modules
  (dishwasher, oven, hood, cargo/karuzela, ...) that only ever get a flat
  per-type price, both tiers seeded from the same number until admin
  differentiates komfort (owner decision 2026-08-02). Their flat rate
  covers montaż, so they carry NO separate labor line (see
  labor_category_for below) -- unlike buildable modules, priced by
  Cennik nakładów (per-type labor, replacing Project.labor_markup).

A module type with NO price-book entry is never silently omitted or
zero-counted quietly: the line is flagged `priced=False` and the whole
widelka is marked `incomplete=True` (UC-1 ext 2a, screens.md's Canvas
acceptance test). Price freshness (TTL, SZACUNEK badge) reuses
price_import.py's existing PriceFreshness/QuoteFreshness/freshness_display
machinery (tr-4afef6fb) -- no separate widening is added here.

QuoteRange is the widelka stored on the Project spine as the first
calibration datapoint (UC-1 step 4, tr-e51ef4fd), comparable later to an
Offer.total_net once a real offer exists (purchasing-variants.md).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlmodel import Field, Session, SQLModel, select

from .bom_generator import BOMGenerator
from .models import Cabinet, Project, ProjectDefaults
from .price_import import (
    PRICE_TTL_DAYS,
    PriceFreshness,
    QuoteFreshness,
    quote_freshness_for_project,
)

# --- Module classification (KEY POINTERS, owner-confirmed 2026-08-02) ----

# Decomposable modules: priced from the existing material-cost baseline
# (BOMGenerator), NOT from the flat price book.
BUILDABLE_MODULE_KINDS: frozenset[str] = frozenset({
    "BASE_CABINET", "DRAWER_BASE", "SINK_BASE", "WALL_CABINET",
    "FILLER", "SIDE_PANEL",
})

# Non-decomposable fixed equipment: flat per-type price from the estimate-
# line price book, both tiers. No labor line -- flat rate covers montaż.
EQUIPMENT_MODULE_KINDS: frozenset[str] = frozenset({
    "DISHWASHER", "OVEN", "COOKTOP", "HOOD", "COUNTERTOP", "SINK", "FAUCET",
})

# Corner mechanisms (cargo/karuzela, UC-1 step 2's other "non-decomposable
# modules" example). Not yet an instantiable Cabinet.module_kind on the
# canvas (no add_equipment spec creates one today) -- listed here so the
# price book / labor cennik already cover them the day they land, per the
# module-type -> labor mapping in the work item.
CORNER_MODULE_KINDS: frozenset[str] = frozenset({
    "CARGO", "CAROUSEL", "CORNER_BASE",
})

# Estimate-grade tier-delta constants (threshold-1 pragmatic approximation,
# wk-224f3712's "KEY POINTERS" note) -- admin-editable seeds welcome later.
# Applied ON TOP OF the existing material-cost baseline for buildable
# modules: standard tier = the baseline as-is (tandembox_antaro + standard
# hinges is what ProjectDefaults/BOMGenerator already price); komfort tier
# = baseline + these deltas, standing in for legrabox-vs-tandembox and
# soft-close-vs-standard-hinge without a full per-tier decomposition.
KOMFORT_DRAWER_SYSTEM_DELTA_PER_DRAWER: float = 180.0  # legrabox vs tandembox, per drawer
KOMFORT_HINGE_DELTA_PER_DOOR: float = 25.0             # soft-close vs standard hinge, per door

# Cennik nakładów (owner-confirmed 2026-08-02): per-module labor seed,
# REPLACES Project.labor_markup x1.50 in the canvas total everywhere this
# module is wired in (ui/state.py's canvas total + "Robocizna" cost-trace
# row). labor_markup stays on the Project model, unused by this math.
LABOR_RATE_SEED: dict[str, float] = {
    "drawer": 400.0,
    "corner": 350.0,
    "door": 250.0,
    "plain": 150.0,
}

# Estimate-line price book seed (owner-confirmed 2026-08-02): BOTH tiers
# start at the same number -- the hardcoded UI defaults that already lived
# in ui/state.py's add_equipment specs -- so the owner differentiates
# komfort later in admin. Kept here as the single source of truth; specs
# in ui/state.py should read from EstimateLinePrice, not re-hardcode these.
EQUIPMENT_PRICE_SEED: dict[str, float] = {
    "DISHWASHER": 1399.0,
    "OVEN": 1999.0,
    "COOKTOP": 1499.0,
    "HOOD": 788.0,
    "COUNTERTOP": 215.0,
    "SINK": 679.0,
    "FAUCET": 199.0,
}

# Widelka math (owner-confirmed 2026-08-02):
#   od = round_to_100(standard_total_net * 0.95 * 1.23)
#   do = round_to_100(komfort_total_net * 1.15 * 1.23)
WIDELKA_OD_MARGIN: float = 0.95
WIDELKA_DO_MARGIN: float = 1.15
VAT_RATE: float = 1.23


def round_to_100(value: float) -> float:
    """Round-half-up to the nearest 100 (money rounding; avoids Python's
    round()-half-to-even surprising a zloty figure). Pinned examples live
    in test_quote_range.py."""
    return math.floor(value / 100.0 + 0.5) * 100.0


# --- Price-book tables (SQLModel; admin-editable later, owner decision) --

class EstimateLinePrice(SQLModel, table=True):
    """Flat-rate estimate line per module_kind (wk-224f3712), both tiers.
    valid_from drives the same TTL/freshness grading as SupplierPrice
    (price_import.PRICE_TTL_DAYS) -- reused, not reimplemented."""
    module_kind: str = Field(primary_key=True)
    standard_price: float
    komfort_price: float
    valid_from: date


class LaborRate(SQLModel, table=True):
    """Cennik nakładów: one flat labor price per module-type category
    (wk-59b943b1). Categories are the vocabulary returned by
    labor_category_for: "drawer" | "corner" | "door" | "plain"."""
    category: str = Field(primary_key=True)
    price: float
    valid_from: date


class QuoteRange(SQLModel, table=True):
    """The widelka stored on the project spine as the first calibration
    datapoint (UC-1 step 4), comparable to a later Offer.total_net. A new
    table (not an ALTER on an existing one), so SQLModel.metadata.create_all
    picks it up without an _ensure_*_schema migration (ui/state.py:132-190
    pattern is for additive columns on tables that already exist)."""
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", ondelete="CASCADE")
    od_brutto: float
    do_brutto: float
    standard_total_net: float
    komfort_total_net: float
    module_count: int
    incomplete: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)


def seed_defaults(session: Session, *, as_of: date | None = None) -> None:
    """Seed both price books once, if empty -- same "seed on first boot"
    convention as load_mock_data's material mirror bootstrap. valid_from =
    the seeding date, so freshness/TTL starts counting from today, exactly
    like a normal price import (owner decision 2026-08-02)."""
    as_of = as_of or date.today()
    if session.exec(select(EstimateLinePrice)).first() is None:
        for module_kind, price in EQUIPMENT_PRICE_SEED.items():
            session.add(EstimateLinePrice(
                module_kind=module_kind,
                standard_price=price,
                komfort_price=price,
                valid_from=as_of,
            ))
    if session.exec(select(LaborRate)).first() is None:
        for category, price in LABOR_RATE_SEED.items():
            session.add(LaborRate(category=category, price=price, valid_from=as_of))
    session.commit()


# --- Labor mapping (module type -> labor cennik category) ----------------

def labor_category_for(module_kind: str, door_count: int, drawer_count: int) -> str | None:
    """module type -> labor mapping (owner-confirmed 2026-08-02):
    DRAWER_BASE -> drawer; corner kinds -> corner; BASE_CABINET/
    WALL_CABINET/SINK_BASE WITH DOORS -> door; FILLER/SIDE_PANEL -> plain;
    fixed-equipment kinds get NO labor line (their flat rate covers
    montaż). Returns None when no labor line applies."""
    if module_kind == "DRAWER_BASE":
        return "drawer"
    if module_kind in CORNER_MODULE_KINDS:
        return "corner"
    if module_kind in {"BASE_CABINET", "WALL_CABINET", "SINK_BASE"}:
        return "door" if door_count > 0 else None
    if module_kind in {"FILLER", "SIDE_PANEL"}:
        return "plain"
    return None  # equipment kinds and anything unrecognized: no labor line


def _labor_rate(session: Session, category: str | None) -> float:
    if category is None:
        return 0.0
    row = session.get(LaborRate, category)
    return row.price if row else 0.0


# --- Per-module pricing ---------------------------------------------------

@dataclass
class QuoteLine:
    cabinet_id: int | None
    cabinet_name: str
    module_kind: str
    standard_price: float
    komfort_price: float
    priced: bool  # False = no price-book entry (UC-1 ext 2a)
    labor_category: str | None
    labor_amount: float
    price_freshness: PriceFreshness | None = None  # None for buildable/unpriced lines


def price_module(
    cabinet: Cabinet,
    defaults: ProjectDefaults | None,
    session: Session,
    *,
    as_of: date,
) -> QuoteLine:
    """Price one canvas module for the widelka. Buildable kinds use the
    existing material-cost baseline (BOMGenerator) + a komfort delta;
    everything else looks up the flat estimate-line price book."""
    module_kind = cabinet.module_kind
    labor_category = labor_category_for(module_kind, cabinet.door_count, cabinet.drawer_count)
    labor_amount = _labor_rate(session, labor_category)

    if module_kind in BUILDABLE_MODULE_KINDS:
        if defaults is None:
            return QuoteLine(
                cabinet_id=cabinet.id, cabinet_name=cabinet.name, module_kind=module_kind,
                standard_price=0.0, komfort_price=0.0, priced=False,
                labor_category=labor_category, labor_amount=labor_amount,
            )
        try:
            baseline = BOMGenerator(cabinet, defaults).generate().cost
        except ValueError:
            # No recipe for this module_kind -- unpriced, never silently 0.
            return QuoteLine(
                cabinet_id=cabinet.id, cabinet_name=cabinet.name, module_kind=module_kind,
                standard_price=0.0, komfort_price=0.0, priced=False,
                labor_category=labor_category, labor_amount=labor_amount,
            )
        komfort = (
            baseline
            + cabinet.drawer_count * KOMFORT_DRAWER_SYSTEM_DELTA_PER_DRAWER
            + cabinet.door_count * KOMFORT_HINGE_DELTA_PER_DOOR
        )
        return QuoteLine(
            cabinet_id=cabinet.id, cabinet_name=cabinet.name, module_kind=module_kind,
            standard_price=baseline, komfort_price=komfort, priced=True,
            labor_category=labor_category, labor_amount=labor_amount,
        )

    # Non-decomposable (equipment/corner) and anything unrecognized: the
    # flat estimate-line price book is the only source of truth.
    price_row = session.get(EstimateLinePrice, module_kind)
    if price_row is None:
        return QuoteLine(
            cabinet_id=cabinet.id, cabinet_name=cabinet.name, module_kind=module_kind,
            standard_price=0.0, komfort_price=0.0, priced=False,
            labor_category=labor_category, labor_amount=labor_amount,
        )
    age_days = (as_of - price_row.valid_from).days
    status = "fresh" if age_days <= PRICE_TTL_DAYS else "stale"
    freshness = PriceFreshness(
        material_id=None,
        material_name=f"{cabinet.name} ({module_kind})",
        valid_from=price_row.valid_from,
        age_days=age_days,
        status=status,
    )
    return QuoteLine(
        cabinet_id=cabinet.id, cabinet_name=cabinet.name, module_kind=module_kind,
        standard_price=price_row.standard_price, komfort_price=price_row.komfort_price,
        priced=True, labor_category=labor_category, labor_amount=labor_amount,
        price_freshness=freshness,
    )


# --- Whole-canvas widelka --------------------------------------------------

@dataclass
class QuoteRangeResult:
    lines: list[QuoteLine] = field(default_factory=list)
    standard_total_net: float = 0.0
    komfort_total_net: float = 0.0
    labor_total: float = 0.0
    incomplete: bool = False  # True if any line unpriced (UC-1 ext 2a)
    module_count: int = 0
    od_brutto: float = 0.0
    do_brutto: float = 0.0
    freshness: QuoteFreshness = field(default_factory=lambda: QuoteFreshness(grade="estimate", lines=[]))


def labor_total_for_cabinets(session: Session, cabinets: list[Cabinet]) -> float:
    """Sum the cennik nakładów across a set of cabinets -- the REPLACEMENT
    for Project.labor_markup in both the canvas total and the "Robocizna"
    cost-trace row (owner decision 2026-08-02)."""
    total = 0.0
    for cab in cabinets:
        category = labor_category_for(cab.module_kind, cab.door_count, cab.drawer_count)
        total += _labor_rate(session, category)
    return total


def compute_quote_range(
    session: Session, project: Project, *, as_of: date | None = None
) -> QuoteRangeResult:
    """Price the whole canvas twice (standard/komfort) and derive the
    od-do widelka (UC-1 steps 2-4). Freshness merges the existing
    material-price grading (quote_freshness_for_project, tr-4afef6fb) with
    the price-book lines' own ages -- one SZACUNEK badge covering every
    price the widelka stands on, no separate widening added."""
    as_of = as_of or date.today()
    lines = [
        price_module(cab, project.defaults, session, as_of=as_of)
        for cab in project.cabinets
    ]

    standard_total = sum(l.standard_price for l in lines if l.priced)
    komfort_total = sum(l.komfort_price for l in lines if l.priced)
    labor_total = sum(l.labor_amount for l in lines)
    standard_total += labor_total
    komfort_total += labor_total

    incomplete = any(not l.priced for l in lines)

    module_price_lines = [l.price_freshness for l in lines if l.price_freshness is not None]
    material_freshness = quote_freshness_for_project(session, project, as_of=as_of)
    combined_lines = list(material_freshness.lines) + module_price_lines
    grade = "current" if combined_lines and all(l.status == "fresh" for l in combined_lines) else "estimate"
    freshness = QuoteFreshness(grade=grade, lines=combined_lines)

    return QuoteRangeResult(
        lines=lines,
        standard_total_net=standard_total,
        komfort_total_net=komfort_total,
        labor_total=labor_total,
        incomplete=incomplete,
        module_count=len(lines),
        od_brutto=round_to_100(standard_total * WIDELKA_OD_MARGIN * VAT_RATE),
        do_brutto=round_to_100(komfort_total * WIDELKA_DO_MARGIN * VAT_RATE),
        freshness=freshness,
    )


# --- Persistence: the widelka as a project-spine calibration datapoint ---

def save_quote_range(session: Session, project: Project, result: QuoteRangeResult) -> QuoteRange:
    """Store the widelka on the project spine (UC-1 step 4, tr-e51ef4fd) --
    the "zapisz widelkę" action. Append-only like Offer: a later widelka
    (e.g. re-quoted after a canvas edit) is a new row, never an overwrite,
    so the calibration history stays intact."""
    quote_range = QuoteRange(
        project_id=project.id,
        od_brutto=result.od_brutto,
        do_brutto=result.do_brutto,
        standard_total_net=result.standard_total_net,
        komfort_total_net=result.komfort_total_net,
        module_count=result.module_count,
        incomplete=result.incomplete,
    )
    session.add(quote_range)
    session.commit()
    session.refresh(quote_range)
    return quote_range


def latest_quote_range(session: Session, project_id: int) -> QuoteRange | None:
    """The most recently saved widelka for a project, or None if never
    saved yet."""
    return session.exec(
        select(QuoteRange)
        .where(QuoteRange.project_id == project_id)
        .order_by(QuoteRange.created_at.desc(), QuoteRange.id.desc())  # type: ignore[union-attr]
    ).first()


def widelka_display(od_brutto: float, do_brutto: float) -> str:
    """"od X do Y zł brutto" -- the display string owner-confirmed
    2026-08-02, VAT 23% already folded into od/do by compute_quote_range.
    Thousands separated with a space (Polish convention: 18 400)."""
    return f"od {od_brutto:,.0f} do {do_brutto:,.0f} zł brutto".replace(",", " ")
