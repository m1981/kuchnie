"""Bill of Materials — aggregates panels + accessories into a costed summary.

Batch-only: call calculate_bom() when the user explicitly requests it,
not on every keystroke.
"""

from dataclasses import dataclass, field

from .model import DecompositionResult


@dataclass
class BOMItem:
    description: str
    category: str        # "panel", "edge_band", "accessory"
    material: str
    quantity: int
    unit: str            # "szt", "mb"
    unit_price: float = 0.0
    total: float = 0.0


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
        ))

        # Edge banding (band.length_mm already set by catalog)
        for edge_name, band in panel.banded_edges.items():
            length_m = band.length_mm / 1000
            price_m = edge_prices.get(band.material, 0.0)
            edge_cost = round(price_m * length_m * panel.quantity, 2)

            bom.items.append(BOMItem(
                description=f"Oklejanie {edge_name} → {panel.name}",
                category="edge_band",
                material=band.material,
                quantity=panel.quantity,
                unit="mb",
                unit_price=round(price_m * length_m, 2),
                total=edge_cost,
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
        ))

    bom.total_cost = round(sum(i.total for i in bom.items), 2)
    return bom
