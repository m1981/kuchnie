"""Edge banding CSV export — one row per banded edge, per panel.

Companion to ``cutlist_csv``. Where ``cutlist_csv`` aggregates unique
formatki for the sheet-cutter, this export enumerates every physical
edge that needs to be banded, so the edging operator has an explicit
worklist (panel_id, side, length, material).

Output format matches the rest of the CAM toolchain:
  * semicolon-delimited (Polish CNC / e-rozrys convention)
  * UTF-8 with BOM  (Excel/LibreOffice friendly)
  * ``\n`` line terminator (deterministic across platforms)

Migrated from ``kitchen_cad/kitchen_cam.csv_generator.generate_edging_csv``
per ADR-010. The old function operated on the (now-deprecated) local
``kitchen_cam.models.Panel`` with ``edges: list[EdgeBand(side, material)]``.
This version operates on the canonical ``kuchnie_core.model.Panel`` whose
``banded_edges`` is a dict keyed by side name ("front" | "back" | "left" |
"right").

Edge length comes from ``EdgeBand.length_mm`` — the decomposer stores the
true strip length there (a carcass side panel's "front" edge runs along the
panel HEIGHT, which no dimension rule keyed on side names can know). Only
when a band carries no length (0 / legacy producers) do we fall back to the
old derivation rule:

  * ``front`` / ``back``  edge runs along ``width_mm``
  * ``left``  / ``right`` edge runs along ``height_mm``
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from ..kitchen import all_panels
from ..model import Kitchen, Panel


# ── Types ───────────────────────────────────────────────────────

# Edge sides that run along the panel WIDTH_mm dimension.
_WIDTH_EDGES: frozenset[str] = frozenset({"front", "back"})


@dataclass
class EdgingRow:
    """One row in the edge-banding worklist."""
    panel_id: str
    panel_name: str
    side: str          # "front" | "back" | "left" | "right"
    length_mm: float
    material: str
    thickness_mm: float


# ── Length rule ─────────────────────────────────────────────────

def _edge_length_mm(panel: Panel, side: str) -> float:
    """Return the physical length (mm) of ``side`` on ``panel``.

    ``front`` and ``back`` edges run along ``panel.width_mm``.
    ``left`` and ``right`` edges run along ``panel.height_mm``.
    """
    if side in _WIDTH_EDGES:
        return panel.width_mm
    return panel.height_mm


# ── Rows ────────────────────────────────────────────────────────

def collect_edging_rows(panels: list[Panel]) -> list[EdgingRow]:
    """Enumerate every banded edge across ``panels``.

    Panels with no banding are silently skipped. Rows preserve the
    insertion order of ``panels`` and, within a panel, iteration order
    of ``banded_edges`` (Python dict insertion order).
    """
    rows: list[EdgingRow] = []
    for p in panels:
        for side, band in p.banded_edges.items():
            rows.append(EdgingRow(
                panel_id=p.id,
                panel_name=p.name,
                side=side,
                length_mm=band.length_mm or _edge_length_mm(p, side),
                material=band.material,
                thickness_mm=band.thickness_mm,
            ))
    return rows


# ── CSV ─────────────────────────────────────────────────────────

HEADER = [
    "Panel_ID", "Nazwa", "Krawędź", "Długość_mm", "Materiał", "Grubość_mm",
]


def rows_to_csv(rows: list[EdgingRow]) -> str:
    """Render edging rows to a semicolon-separated CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\n")
    writer.writerow(HEADER)
    for r in rows:
        writer.writerow([
            r.panel_id,
            r.panel_name,
            r.side,
            f"{r.length_mm:.1f}",
            r.material,
            f"{r.thickness_mm:.1f}",
        ])
    return buf.getvalue()


def export_edging_csv(
    kitchen: Kitchen,
    path: str | Path,
    verdict: "BuildabilityVerdict | None" = None,
) -> Path:
    """Enumerate all banded edges across ``kitchen`` and write CSV.

    Returns the written path (matches ``export_cutlist_csv`` signature).
    Emission is gated on the buildability verdict (UC-2 ext 5a): a FAILED
    verdict raises BuildabilityError and nothing is written.
    """
    from ..buildability import require_buildable

    require_buildable(kitchen, verdict=verdict)
    rows = collect_edging_rows(all_panels(kitchen))
    csv_text = rows_to_csv(rows)
    out = Path(path)
    out.write_text(csv_text, encoding="utf-8-sig")  # BOM for Excel compat
    return out
