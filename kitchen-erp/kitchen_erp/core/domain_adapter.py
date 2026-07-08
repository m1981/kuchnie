"""ADR-011 phase 2 — kitchen-erp consumes kuchnie_core as the domain hub.

`to_kuchnie_core` maps an erp `Cabinet` row onto a `kuchnie_core.CabinetInstance`
so panel geometry comes from the canonical construction methods in the hub's
TYPE_REGISTRY. Pricing stays in erp: `quantities_from_decomposition` folds the
decomposition back into the m2/lm quantities that `BOMGenerator` prices.

Module kinds without a registered construction method (appliances, fillers,
panels) return None and `BOMGenerator` falls back to the recipe formulas.
"""
from dataclasses import dataclass

from kuchnie_core.model import CabinetInstance, DecompositionResult, PanelRole

from .models import Cabinet, ProjectDefaults

# erp module_kind -> kuchnie_core TYPE_REGISTRY key. Only carcass cabinets the
# domain hub knows how to build; everything else stays on recipe formulas.
ERP_KIND_TO_DOMAIN: dict[str, str] = {
    "BASE_CABINET": "dolna_drzwiowa",
    "WALL_CABINET": "gorna_drzwiowa",
    "DRAWER_BASE": "dolna_szufladowa",
}

# Construction constants shared with kuchnie_core defaults
PLINTH_HEIGHT_MM = 100.0
FRONT_GAP_MM = 3.0


def to_kuchnie_core(cabinet: Cabinet, defaults: ProjectDefaults) -> CabinetInstance | None:
    """Map an erp Cabinet to a domain CabinetInstance, or None if the module
    kind has no construction method in the hub."""
    domain_type = ERP_KIND_TO_DOMAIN.get(cabinet.module_kind)
    if domain_type is None:
        return None

    front_mat = cabinet.override_front_mat or defaults.front_mat

    fronts: list[dict] = []
    drawers: list[dict] = []
    if domain_type == "dolna_szufladowa":
        n = cabinet.drawer_count
        if n > 0:
            side_h = cabinet.height_mm - PLINTH_HEIGHT_MM
            front_h = (side_h - FRONT_GAP_MM * (n + 1)) / n
            for i in range(1, n + 1):
                drawers.append({"id": f"S{i}", "typ": "tandembox", "wysokosc": front_h})
                fronts.append({"id": f"F{i}", "typ": "szufladowy", "powiazany": f"S{i}"})
    else:
        for i in range(1, cabinet.door_count + 1):
            fronts.append({"id": f"D{i}", "typ": "drzwiowy_lewy"})

    return CabinetInstance(
        id=f"erp-{cabinet.id or cabinet.name or 'unsaved'}",
        type=domain_type,
        description=cabinet.name or cabinet.module_kind,
        width_mm=round(cabinet.width_mm),
        height_mm=round(cabinet.height_mm),
        depth_mm=round(cabinet.depth_mm),
        body_material=defaults.corpus_mat.name,
        back_material=defaults.back_mat.name,
        front_material=front_mat.name,
        fronts=fronts,
        drawers=drawers,
    )


@dataclass
class DomainQuantities:
    """m2/lm totals folded from a decomposition — the units BOMGenerator prices."""
    corpus_m2: float = 0.0
    back_m2: float = 0.0
    front_m2: float = 0.0
    corpus_edge_lm: float = 0.0
    front_edge_lm: float = 0.0


_FRONT_ROLES = {PanelRole.FRONT_DOOR, PanelRole.FRONT_DRAWER}


def quantities_from_decomposition(result: DecompositionResult) -> DomainQuantities:
    q = DomainQuantities()
    for panel in result.panels:
        area_m2 = panel.width_mm * panel.height_mm / 1e6 * panel.quantity
        edge_lm = sum(eb.length_mm for eb in panel.banded_edges.values()) / 1000 * panel.quantity
        if panel.role is PanelRole.BACK:
            q.back_m2 += area_m2
        elif panel.role in _FRONT_ROLES:
            q.front_m2 += area_m2
            q.front_edge_lm += edge_lm
        else:
            q.corpus_m2 += area_m2
            q.corpus_edge_lm += edge_lm
    return q
