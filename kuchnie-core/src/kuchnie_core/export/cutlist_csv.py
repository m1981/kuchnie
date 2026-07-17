"""Cut list CSV export — panels aggregated across the whole kitchen.

Output format: semicolon-separated, compatible with Polish cut-list
optimizers (e-rozrys, e-rozkroj).

NOTE: exact column order may need adjustment once you paste a sample
e-rozrys export for me to match.  The aggregation and edge-banding
logic here is correct; only the column mapping is pluggable.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from ..kitchen import all_panels
from ..model import GrainAxis, Kitchen, Panel


# ── Aggregated row ──────────────────────────────────────────────

@dataclass
class CutPiece:
    """One unique piece in the cut list (possibly qty > 1)."""
    nr: int
    name: str
    material: str
    thickness_mm: int
    width_mm: float
    height_mm: float
    quantity: int
    edge_front: bool
    edge_back: bool
    edge_left: bool
    edge_right: bool
    grain: str | None    # GrainAxis value or None (no grain constraint)
    source: str          # cabinet ID(s) this piece came from


# ── Aggregation ─────────────────────────────────────────────────

def _edge_key(panel: Panel) -> tuple[bool, bool, bool, bool]:
    """Which edges are banded?  Used as part of the aggregation key."""
    return (
        "front" in panel.banded_edges,
        "back" in panel.banded_edges,
        "left" in panel.banded_edges,
        "right" in panel.banded_edges,
    )


def aggregate_panels(panels: list[Panel]) -> list[CutPiece]:
    """Group identical panels and sum quantities.

    Two panels are identical when they share: material, thickness,
    rounded width, rounded height, and edge-banding pattern.
    """
    groups: dict[tuple, dict] = {}

    for p in panels:
        # Round to 0.1 mm to avoid float drift
        w = round(p.width_mm, 1)
        h = round(p.height_mm, 1)
        edges = _edge_key(p)
        key = (p.material, p.thickness_mm, w, h, edges, p.grain)

        if key not in groups:
            groups[key] = {
                "name": p.name,
                "qty": 0,
                "edges": edges,
                "sources": [],
            }
        groups[key]["qty"] += p.quantity
        groups[key]["sources"].append(p.id.split("_")[0])  # cabinet prefix

    pieces: list[CutPiece] = []
    for nr, (key, data) in enumerate(groups.items(), start=1):
        mat, thick, w, h, edges, grain = key
        pieces.append(CutPiece(
            nr=nr,
            name=data["name"],
            material=mat,
            thickness_mm=thick,
            width_mm=w,
            height_mm=h,
            quantity=data["qty"],
            edge_front=edges[0],
            edge_back=edges[1],
            edge_left=edges[2],
            edge_right=edges[3],
            grain=grain,
            source=", ".join(sorted(set(data["sources"]))),
        ))

    return pieces


# ── CSV generation ──────────────────────────────────────────────

HEADER = [
    "Nr", "Nazwa", "Materiał", "Grubość",
    "Długość", "Szerokość", "Ilość", "Usłojenie",
    "Okle_P", "Okle_T", "Okle_L", "Okle_R",
    "Szafka", "Uwagi",
]


# Usłojenie column values: grain along the cabinet-vertical axis is "pion",
# along the horizontal axis "poziom", unconstrained (uni decors, HDF) "brak".
_GRAIN_LABEL = {GrainAxis.HEIGHT: "pion", GrainAxis.WIDTH: "poziom", None: "brak"}


def _yn(b: bool) -> str:
    return "TAK" if b else "NIE"


def pieces_to_csv(pieces: list[CutPiece]) -> str:
    """Render cut pieces to a semicolon-separated CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\n")
    writer.writerow(HEADER)
    for p in pieces:
        writer.writerow([
            p.nr,
            p.name,
            p.material,
            p.thickness_mm,
            f"{p.width_mm:.1f}",
            f"{p.height_mm:.1f}",
            p.quantity,
            _GRAIN_LABEL.get(p.grain, p.grain),
            _yn(p.edge_front),
            _yn(p.edge_back),
            _yn(p.edge_left),
            _yn(p.edge_right),
            p.source,
            "",
        ])
    return buf.getvalue()


def export_cutlist_csv(
    kitchen: Kitchen,
    path: str | Path,
    verdict: "BuildabilityVerdict | None" = None,
) -> Path:
    """Aggregate all panels in the kitchen and write a cut-list CSV.

    Emission is gated on the buildability verdict (UC-2 ext 5a): a FAILED
    verdict raises BuildabilityError and nothing is written. Pass a
    precomputed ``verdict`` to skip re-running the gates.
    """
    from ..buildability import require_buildable

    require_buildable(kitchen, verdict=verdict)
    panels = all_panels(kitchen)
    pieces = aggregate_panels(panels)
    csv_text = pieces_to_csv(pieces)
    p = Path(path)
    p.write_text(csv_text, encoding="utf-8-sig")  # BOM for Excel compat
    return p
