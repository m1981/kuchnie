"""Bill of Materials — aggregates panels + accessories into a costed summary.

Batch-only: call calculate_bom() when the user explicitly requests it,
not on every keystroke.
"""

from dataclasses import dataclass, field

from .model import DecompositionResult, EdgeBand, PanelRole, WorktopSegment


def _edge_material_key(band: EdgeBand) -> str:
    """G11: Construct edge band material key for BOM grouping.

    Format: "{material}_{thickness_mm}[x{width_mm}][_{catalog_code}]"
    This ensures edge bands with different thicknesses, purchase widths,
    or catalog codes produce separate BOM lines for ordering clarity.
    Width is part of purchase identity (e.g. Egger 23mm vs a
    Kronospan-partner 22mm band for the same 18mm board) but is
    supplier/decor-dependent, so it is only appended when known
    (``band.width_mm`` truthy) — core never derives it.
    """
    base = f"{band.material}_{band.thickness_mm:.1f}"
    if band.width_mm:
        base = f"{base}x{band.width_mm:.0f}"
    if band.catalog_edge_code:
        return f"{base}_{band.catalog_edge_code}"
    return base


@dataclass
class BOMItem:
    description: str
    category: str        # "panel", "edge_band", "accessory", "worktop", "worktop_cutout"
    material: str
    quantity: int
    unit: str            # "szt", "mb"
    # unit_price is the per-LINE price (a panel's area×rate, an edge run's
    # or worktop segment's length×rate), NOT a rate per `unit` — total is
    # unit_price × quantity, never × measure as well.
    unit_price: float = 0.0
    total: float = 0.0
    # ADR-015: calculate_bom is the ONE geometry→quantity fold; downstream
    # views (kitchen-erp buckets, variant purchasing lines) aggregate these
    # two fields instead of re-walking panels.
    role: PanelRole | None = None   # parent panel's role; None for accessories
    measure: float = 0.0            # trade quantity: m² (panel), lm (edge_band), szt (accessory)


@dataclass
class BOM:
    cabinet_id: str
    items: list[BOMItem] = field(default_factory=list)
    total_cost: float = 0.0


def calculate_bom(
    result: DecompositionResult,
    board_prices: dict[str, float] | None = None,
    edge_prices: dict[str, float] | None = None,
) -> BOM:
    """Build a BOM from a decomposition result.

    board_prices:  { "swiss_krono.U119_VL": 45.00 }  (PLN per m²)
    edge_prices:   { "ABS_swiss_krono.U119_VL": 1.20 }  (PLN per m)
    """
    bom = BOM(cabinet_id=result.cabinet_id)
    board_prices = board_prices or {}
    edge_prices = edge_prices or {}

    # --- Panels ---
    for panel in result.panels:
        area_m2 = (panel.width_mm * panel.height_mm) / 1_000_000
        price_m2 = board_prices.get(panel.material, 0.0)
        panel_cost = round(price_m2 * area_m2 * panel.quantity, 2)

        bom.items.append(BOMItem(
            description=(
                f"{panel.name} "
                f"({panel.width_mm:.0f}×{panel.height_mm:.0f}×{panel.thickness_mm})"
            ),
            category="panel",
            material=panel.material,
            quantity=panel.quantity,
            unit="szt",
            unit_price=round(price_m2 * area_m2, 2),
            total=panel_cost,
            role=panel.role,
            measure=area_m2 * panel.quantity,
        ))

        # Edge banding (band.length_mm already set by catalog)
        for edge_name, band in panel.banded_edges.items():
            length_m = band.length_mm / 1000
            # G11: material key includes thickness and catalog code for ordering
            edge_material_key = _edge_material_key(band)
            price_m = edge_prices.get(edge_material_key, edge_prices.get(band.material, 0.0))
            edge_cost = round(price_m * length_m * panel.quantity, 2)

            bom.items.append(BOMItem(
                description=f"Oklejanie {edge_name} → {panel.name}",
                category="edge_band",
                material=edge_material_key,
                quantity=panel.quantity,
                unit="mb",
                unit_price=round(price_m * length_m, 2),
                total=edge_cost,
                role=panel.role,
                measure=length_m * panel.quantity,
            ))

    # --- Accessories ---
    for acc in result.accessories:
        bom.items.append(BOMItem(
            description=acc.name,
            category="accessory",
            material=acc.type,
            quantity=acc.quantity,
            unit="szt",
            unit_price=acc.unit_price,
            total=round(acc.unit_price * acc.quantity, 2),
            measure=float(acc.quantity),
        ))

    bom.total_cost = round(sum(i.total for i in bom.items), 2)
    return bom


def worktop_bom_items(
    worktops: list[WorktopSegment],
    worktop_prices: dict[str, float] | None = None,
    cutout_prices: dict[str, float] | None = None,
) -> list[BOMItem]:
    """Fold worktop segments into BOM items (wk-4c37f4ee).

    Laminate pricing model: length × PLN-per-lm rate for the segment's
    material, plus a per-piece charge for each named cutout (zlew, plyta,
    ...). Stone worktops are quoted externally and never pass through
    here — a material missing from worktop_prices simply prices at 0,
    same convention as boards in calculate_bom.

    worktop_prices:  { "egger.F2060_ST87": 120.00 }  (PLN per lm)
    cutout_prices:   { "zlew": 80.00, "plyta": 60.00 }  (PLN per piece)
    """
    worktop_prices = worktop_prices or {}
    cutout_prices = cutout_prices or {}

    items: list[BOMItem] = []
    for seg in worktops:
        length_m = seg.length_mm / 1000
        price_lm = worktop_prices.get(seg.material, 0.0)
        items.append(BOMItem(
            description=(
                f"Blat {seg.row_id} "
                f"({seg.length_mm:.0f}×{seg.depth_mm:.0f}×{seg.thickness_mm})"
            ),
            category="worktop",
            material=seg.material,
            quantity=1,
            unit="mb",
            unit_price=round(price_lm * length_m, 2),
            total=round(price_lm * length_m, 2),
            measure=length_m,
        ))
        for cutout in seg.cutouts:
            price = cutout_prices.get(cutout, 0.0)
            items.append(BOMItem(
                description=f"Wycięcie {cutout} → blat {seg.row_id}",
                category="worktop_cutout",
                material=cutout,
                quantity=1,
                unit="szt",
                unit_price=price,
                total=round(price, 2),
                measure=1.0,
            ))
    return items
