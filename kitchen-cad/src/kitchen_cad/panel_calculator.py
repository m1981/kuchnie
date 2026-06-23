"""Derive cutting panels (formatki) from a CorpusSpec.

Naming convention — all dimensions in mm:
  W = external width   H = external height   D = external depth
  T = panel thickness  G = back groove depth  BT = back thickness
"""

from __future__ import annotations

from kitchen_cad.models import (
    SYSTEM32_OFFSET,
    BaseDoorConfig,
    BaseDrawerConfig,
    CabinetConfig,
    CornerBlindConfig,
    CorpusSpec,
    EdgeBand,
    EdgeSide,
    Panel,
    PanelRole,
)


def _edge_material(spec: CorpusSpec) -> str:
    return spec.edge_material


def _side_panels(spec: CorpusSpec) -> list[Panel]:
    """Left and right side panels: D × H × T."""
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
    """Top and bottom panels: (W-2T) × (D-G) × T."""
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


def _shelf_panels(spec: CorpusSpec, shelf_positions: list[float]) -> list[Panel]:
    """Shelves: (W-2T) × (D-G-SYSTEM32_OFFSET) × T."""
    inner_w = spec.width - 2 * spec.panel_thickness
    shelf_d = spec.depth - spec.back_groove_depth - SYSTEM32_OFFSET
    edges = [
        EdgeBand(side=EdgeSide.LEFT, material=_edge_material(spec)),
    ]
    shelves = []
    for i, pos in enumerate(shelf_positions):
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


def _door_fronts(spec: CorpusSpec, door_hinge_counts: list[int]) -> list[Panel]:
    """Door front(s) with gap calculation."""
    if not door_hinge_counts:
        return []

    n = len(door_hinge_counts)
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


def _drawer_fronts(spec: CorpusSpec, drawer_count: int) -> list[Panel]:
    """Drawer front(s): equally sized, filling available height."""
    if drawer_count == 0:
        return []

    g = spec.front_gap
    total_gap = 2 * g + (drawer_count - 1) * g
    h_each = (spec.height - total_gap) / drawer_count
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
        for i in range(drawer_count)
    ]


# ---------------------------------------------------------------------------
# Variant-specific calculators
# ---------------------------------------------------------------------------

def _calculate_base_door(spec: CorpusSpec, config: BaseDoorConfig) -> list[Panel]:
    """Standard base cabinet with doors and shelves."""
    panels: list[Panel] = []
    panels.extend(_side_panels(spec))
    panels.extend(_horizontal_panels(spec))
    panels.extend(_shelf_panels(spec, config.shelves))
    panels.append(_back_panel(spec))
    panels.extend(_door_fronts(spec, config.doors))
    return panels


def _calculate_base_drawer(spec: CorpusSpec, config: BaseDrawerConfig) -> list[Panel]:
    """Base cabinet with drawers only."""
    panels: list[Panel] = []
    panels.extend(_side_panels(spec))
    panels.extend(_horizontal_panels(spec))
    panels.append(_back_panel(spec))
    panels.extend(_drawer_fronts(spec, len(config.drawers)))
    return panels


def _calculate_corner_blind(spec: CorpusSpec, config: CornerBlindConfig) -> list[Panel]:
    """Corner blind cabinet — L-shaped body with one visible front.

    The cabinet has:
    - Standard left side panel (full depth)
    - Shortened right side panel (depth = second_width)
    - Extended bottom/top panels (width = W + second_width - T)
    - Blind panel (filler) on the open side
    - One door on the visible side
    """
    panels: list[Panel] = []

    # --- Side panels ---
    # The "main" side (opposite the corner extension) is full depth
    # The "corner" side is shortened to second_width
    edges_full = [
        EdgeBand(side=EdgeSide.TOP, material=_edge_material(spec)),
        EdgeBand(side=EdgeSide.LEFT, material=_edge_material(spec)),
    ]
    edges_short = [
        EdgeBand(side=EdgeSide.TOP, material=_edge_material(spec)),
        EdgeBand(side=EdgeSide.LEFT, material=_edge_material(spec)),
    ]

    if config.corner_side.value == "left":
        # Front is on the RIGHT side of the cabinet
        # Left side panel = full depth, Right side panel = shortened
        main_side = Panel(
            id=f"{spec.id}-BOK-L",
            role=PanelRole.LEFT_SIDE,
            width=spec.depth,
            height=spec.height,
            thickness=spec.panel_thickness,
            material=spec.material_corpus,
            edges=list(edges_full),
        )
        corner_side = Panel(
            id=f"{spec.id}-BOK-P",
            role=PanelRole.RIGHT_SIDE,
            width=config.second_width,
            height=spec.height,
            thickness=spec.panel_thickness,
            material=spec.material_corpus,
            edges=list(edges_short),
        )
    else:
        # Front is on the LEFT side
        # Right side panel = full depth, Left side panel = shortened
        main_side = Panel(
            id=f"{spec.id}-BOK-P",
            role=PanelRole.RIGHT_SIDE,
            width=spec.depth,
            height=spec.height,
            thickness=spec.panel_thickness,
            material=spec.material_corpus,
            edges=list(edges_full),
        )
        corner_side = Panel(
            id=f"{spec.id}-BOK-L",
            role=PanelRole.LEFT_SIDE,
            width=config.second_width,
            height=spec.height,
            thickness=spec.panel_thickness,
            material=spec.material_corpus,
            edges=list(edges_short),
        )
    panels.extend([main_side, corner_side])

    # --- Horizontal panels (extended width) ---
    # Width = main width + second_width - one panel thickness (they share a corner)
    extended_w = spec.width + config.second_width - spec.panel_thickness
    inner_d = spec.depth - spec.back_groove_depth
    edges_horiz = [
        EdgeBand(side=EdgeSide.LEFT, material=_edge_material(spec)),
    ]
    panels.append(Panel(
        id=f"{spec.id}-GORA",
        role=PanelRole.TOP,
        width=extended_w - 2 * spec.panel_thickness,
        height=inner_d,
        thickness=spec.panel_thickness,
        material=spec.material_corpus,
        edges=list(edges_horiz),
    ))
    panels.append(Panel(
        id=f"{spec.id}-DNO",
        role=PanelRole.BOTTOM,
        width=extended_w - 2 * spec.panel_thickness,
        height=inner_d,
        thickness=spec.panel_thickness,
        material=spec.material_corpus,
        edges=list(edges_horiz),
    ))

    # --- Shelves ---
    panels.extend(_shelf_panels(spec, config.shelves))

    # --- Back panel ---
    panels.append(_back_panel(spec))

    # --- Door front (single door on visible side) ---
    panels.extend(_door_fronts(spec, config.doors))

    return panels


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_panels(spec: CorpusSpec) -> list[Panel]:
    """Calculate all cutting panels for a given corpus specification.

    Dispatches to the appropriate variant calculator based on spec.config.type.
    """
    config = spec.config

    if isinstance(config, BaseDoorConfig):
        return _calculate_base_door(spec, config)
    elif isinstance(config, BaseDrawerConfig):
        return _calculate_base_drawer(spec, config)
    elif isinstance(config, CornerBlindConfig):
        return _calculate_corner_blind(spec, config)
    else:
        raise ValueError(f"Unknown cabinet config type: {type(config).__name__}")
