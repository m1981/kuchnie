"""Generic Panel → DXF writer — the output consumer for ``machining_ops``.

Takes any ``kuchnie_core.model.Panel`` (with whatever drill ops the
decomposer and the drilling macros put on it) and renders a flat CNC-ready
drawing: panel outline plus one circle per drill op, routed onto a layer
named after the op's ``drill_type`` (ADR-012 §2) so the CNC post-processor
can assign tools per layer.

Unlike ``legrabox_side_panel.py`` (a standalone generator that re-computes
its own geometry), this module draws EXACTLY what the model says — it adds
no positions of its own. That keeps a single source of truth for drilling
geometry: kuchnie_core + kitchen_cam.machining.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from kuchnie_core.model import Panel

# drill_type → DXF layer (name, ACI colour). Unclassified ops land on DRILL.
_LAYERS: dict[str, tuple[str, int]] = {
    "system32":     ("SYSTEM32", 1),      # red
    "shelf_pin":    ("SHELF_PIN", 3),     # green
    "hinge_cup":    ("HINGE_CUP", 5),     # blue
    "hinge_screw":  ("HINGE_SCREW", 4),   # cyan
    "runner_screw": ("RUNNER_SCREW", 6),  # magenta
    "handle":       ("HANDLE", 2),        # yellow
}
_DEFAULT_LAYER = ("DRILL", 7)             # white/black
_OUTLINE_LAYER = ("OUTLINE", 7)


def _layer_for(drill_type: str) -> tuple[str, int]:
    return _LAYERS.get(drill_type, _DEFAULT_LAYER)


def panel_to_dxf(panel: Panel, path: str | Path) -> Path:
    """Render ``panel`` (outline + drill ops) to a DXF file.

    Coordinates follow the MachiningOp convention: origin at the panel's
    bottom-left, viewed from the machined face. Returns the written path.
    """
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()

    used = {_OUTLINE_LAYER} | {
        _layer_for(op.drill_type) for op in panel.machining_ops
    }
    for name, colour in sorted(used):
        if name not in doc.layers:
            doc.layers.add(name, color=colour)

    msp.add_lwpolyline(
        [(0, 0), (panel.width_mm, 0),
         (panel.width_mm, panel.height_mm), (0, panel.height_mm)],
        close=True,
        dxfattribs={"layer": _OUTLINE_LAYER[0]},
    )

    for op in panel.machining_ops:
        if op.type != "drill":
            continue  # grooves/rabbets need path geometry — future work
        layer, _ = _layer_for(op.drill_type)
        msp.add_circle(
            center=(op.x_mm, op.y_mm),
            radius=op.diameter_mm / 2,
            dxfattribs={"layer": layer},
        )

    out = Path(path)
    doc.saveas(out)
    return out
