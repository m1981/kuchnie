"""Derive cutting panels (formatki) from a CorpusSpec.

Naming convention — all dimensions in mm:
  W = external width   H = external height   D = external depth
  T = panel thickness  G = back groove depth  BT = back thickness
"""

from __future__ import annotations

from kitchen_cad.models import (
    CorpusSpec,
    EdgeBand,
    EdgeSide,
    Panel,
    PanelRole,
)


def _edge_material(spec: CorpusSpec) -> str:
    return spec.edge_material


def _side_panels(spec: CorpusSpec) -> list[Panel]:
    """Left and right side panels: D × H × T.

    Banded edges: top (visible above base / below wall) and
    front (visible from the front of the cabinet).
    """
    edges = [
        EdgeBand(side=EdgeSide.TOP, material=_edge_material(spec)),
        EdgeBand(side=EdgeSide.LEFT, material=_edge_material(spec)),
    ]
    left = Panel(
        id=f"{spec.id}-BOK-L",
        role=PanelRole.LEFT_SIDE,
        width=spec.depth,
        height=spec.height,
        thickness=spec.panel_thickness,
        material=spec.material_corpus,
        edges=list(edges),
    )
    right = Panel(
        id=f"{spec.id}-BOK-P",
        role=PanelRole.RIGHT_SIDE,
        width=spec.depth,
        height=spec.height,
        thickness=spec.panel_thickness,
        material=spec.material_corpus,
        edges=list(edges),
    )
    return [left, right]


def _horizontal_panels(spec: CorpusSpec) -> list[Panel]:
    """Top and bottom panels: (W-2T) × (D-G) × T.

    Banded edge: front only.
    """
    inner_w = spec.width - 2 * spec.panel_thickness
    inner_d = spec.depth - spec.back_groove_depth
    edges = [
        EdgeBand(side=EdgeSide.LEFT, material=_edge_material(spec)),
    ]
    top = Panel(
        id=f"{spec.id}-GORA",
        role=PanelRole.TOP,
        width=inner_w,
        height=inner_d,
        thickness=spec.panel_thickness,
        material=spec.material_corpus,
        edges=list(edges),
    )
    bottom = Panel(
        id=f"{spec.id}-DNO",
        role=PanelRole.BOTTOM,
        width=inner_w,
        height=inner_d,
        thickness=spec.panel_thickness,
        material=spec.material_corpus,
        edges=list(edges),
    )
    return [top, bottom]


def _shelf_panels(spec: CorpusSpec) -> list[Panel]:
    """Shelves: (W-2T) × (D-G-37) × T.

    37 mm deducted for System 32 front offset on side panels.
    """
    inner_w = spec.width - 2 * spec.panel_thickness
    shelf_d = spec.depth - spec.back_groove_depth - 37
    edges = [
        EdgeBand(side=EdgeSide.LEFT, material=_edge_material(spec)),
    ]
    shelves = []
    for i, pos in enumerate(spec.shelves):
        shelves.append(Panel(
            id=f"{spec.id}-POL{i+1}",
            role=PanelRole.SHELF,
            width=inner_w,
            height=shelf_d,
            thickness=spec.panel_thickness,
            material=spec.material_corpus,
            edges=list(edges),
        ))
    return shelves


def _back_panel(spec: CorpusSpec) -> Panel:
    """Back panel (HDF): (W-2T) × H × BT.  No edge banding."""
    inner_w = spec.width - 2 * spec.panel_thickness
    return Panel(
        id=f"{spec.id}-PLECY",
        role=PanelRole.BACK,
        width=inner_w,
        height=spec.height,
        thickness=spec.back_thickness,
        material=spec.material_back,
        edges=[],
    )


def _door_fronts(spec: CorpusSpec) -> list[Panel]:
    """Door front(s): full-width or split.

    Single door:  (W - 2*gap) × (H - 2*gap)
    Two doors:    each (W - 3*gap) / 2 × (H - 2*gap)
    All four edges banded.
    """
    if not spec.doors:
        return []

    n = len(spec.doors)
    g = spec.front_gap
    h = spec.height - 2 * g

    all_edges = [
        EdgeBand(side=s, material=_edge_material(spec))
        for s in EdgeSide
    ]

    if n == 1:
        w = spec.width - 2 * g
        return [Panel(
            id=f"{spec.id}-F1",
            role=PanelRole.FRONT_DOOR,
            width=w,
            height=h,
            thickness=spec.panel_thickness,
            material=spec.material_front,
            edges=list(all_edges),
        )]
    else:
        # n doors side by side: (W - (n+1)*gap) / n
        w = (spec.width - (n + 1) * g) / n
        return [
            Panel(
                id=f"{spec.id}-F{i+1}",
                role=PanelRole.FRONT_DOOR,
                width=w,
                height=h,
                thickness=spec.panel_thickness,
                material=spec.material_front,
                edges=list(all_edges),
            )
            for i in range(n)
        ]


def _drawer_fronts(spec: CorpusSpec) -> list[Panel]:
    """Drawer front(s): equally sized, filling available height.

    Available height = H - 2*gap - (n-1)*gap
    Each front height = available / n
    """
    if not spec.drawers:
        return []

    n = len(spec.drawers)
    g = spec.front_gap
    total_gap = 2 * g + (n - 1) * g  # top + bottom + between
    h_each = (spec.height - total_gap) / n
    w = spec.width - 2 * g

    all_edges = [
        EdgeBand(side=s, material=_edge_material(spec))
        for s in EdgeSide
    ]

    return [
        Panel(
            id=f"{spec.id}-F{i+1}",
            role=PanelRole.FRONT_DRAWER,
            width=w,
            height=h_each,
            thickness=spec.panel_thickness,
            material=spec.material_front,
            edges=list(all_edges),
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_panels(spec: CorpusSpec) -> list[Panel]:
    """Calculate all cutting panels for a given corpus specification.

    Returns a flat list of Panel objects ready for CSV / DXF generation.
    """
    panels: list[Panel] = []
    panels.extend(_side_panels(spec))
    panels.extend(_horizontal_panels(spec))
    panels.extend(_shelf_panels(spec))
    panels.append(_back_panel(spec))
    panels.extend(_door_fronts(spec))
    panels.extend(_drawer_fronts(spec))
    return panels
