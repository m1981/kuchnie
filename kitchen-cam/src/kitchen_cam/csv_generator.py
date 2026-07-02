"""Generate CSV files for CNC cutting and edge banding orders.

.. deprecated:: ADR-010
    Replaced by ``kuchnie_core.export.cutlist_csv`` (aggregated cut list,
    Polish headers, UTF-8-SIG) and ``kuchnie_core.export.edging_csv``
    (per-edge worklist). Both preserve the semicolon-delimited format.
    This module remains in-tree only because ``kitchen-cam`` panel
    calculator (also deprecated) still emits ``kitchen_cam.models.Panel``
    instances. Deletion is BLOCKED by ADR-012. DO NOT add new features here.

Output format: semicolon-delimited UTF-8 (standard for Polish CNC centres).
"""

from __future__ import annotations

import csv
from pathlib import Path

from kitchen_cam.models import EdgeBand, EdgeSide, Panel


# ---------------------------------------------------------------------------
# Edge length mapping
# ---------------------------------------------------------------------------

def _edge_length(panel: Panel, edge: EdgeBand) -> float:
    """Return the length (mm) of a banded edge on a panel.

    TOP/BOTTOM edges run along the panel width.
    LEFT/RIGHT edges run along the panel height.
    """
    if edge.side in (EdgeSide.TOP, EdgeSide.BOTTOM):
        return panel.width
    return panel.height


# ---------------------------------------------------------------------------
# Cutting CSV
# ---------------------------------------------------------------------------

_CUTTING_HEADER = [
    "id", "role", "width", "height", "thickness", "material", "quantity", "edges",
]


def generate_cutting_csv(panels: list[Panel], path: Path) -> Path:
    """Write a semicolon-delimited cutting list CSV.

    Parameters
    ----------
    panels : list[Panel]
        Panels with calculated dimensions (from calculate_panels).
    path : Path
        Output file path.

    Returns
    -------
    Path to the written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(_CUTTING_HEADER)

        for p in panels:
            edge_str = ",".join(e.side.value for e in p.edges)
            writer.writerow([
                p.id,
                p.role.value,
                f"{p.width:g}",
                f"{p.height:g}",
                f"{p.thickness:g}",
                p.material,
                p.quantity,
                edge_str,
            ])

    return path


# ---------------------------------------------------------------------------
# Edging CSV
# ---------------------------------------------------------------------------

_EDGING_HEADER = ["panel_id", "edge", "length_mm", "material"]


def generate_edging_csv(panels: list[Panel], path: Path) -> Path:
    """Write a semicolon-delimited edge banding list CSV.

    One row per banded edge.  Panels with no banding are omitted.

    Parameters
    ----------
    panels : list[Panel]
        Panels with edge banding info.
    path : Path
        Output file path.

    Returns
    -------
    Path to the written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(_EDGING_HEADER)

        for p in panels:
            for edge in p.edges:
                length = _edge_length(p, edge)
                writer.writerow([
                    p.id,
                    edge.side.value,
                    f"{length:g}",
                    edge.material,
                ])

    return path
