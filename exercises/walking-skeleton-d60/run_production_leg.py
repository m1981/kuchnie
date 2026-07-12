#!/usr/bin/env python3
"""Walking skeleton D60 — production leg (wk-9f1ad053).

Input:  generated/extracted-kitchen.json (from the Blender leg), or nothing.
Output: generated/rozrys.csv, generated/bom.csv, generated/cnc-d60.txt

Every block marked GAP: is data the pipeline could not supply and a human
had to re-enter — the ergonomics measurement this exercise exists for.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "kuchnie-core" / "src"))

from kuchnie_core.model import CabinetInstance, GrainAxis, Panel  # noqa: E402
from kuchnie_core.decomposer import decompose  # noqa: E402

GEN = HERE / "generated"


def load_extracted_cabinet() -> dict | None:
    p = GEN / "extracted-kitchen.json"
    if not p.exists():
        return None
    kitchen = json.loads(p.read_text())
    return kitchen["rows"][0]["cabinets"][0]


def build_instance() -> CabinetInstance:
    ext = load_extracted_cabinet()
    if ext:
        width = ext["width_mm"]
        height = ext["height_mm"]
        depth = ext["depth_mm"]
        plinth = ext.get("plinth_height_mm", 100)
        drawer_heights = [d.get("wysokosc") for d in ext.get("drawers", [])]
        source = "extracted-kitchen.json"
    else:
        width, height, depth, plinth = 600, 820, 560, 100
        drawer_heights = [140, 287, 287]
        source = "hand-entered (no Blender leg output)"

    # GAP: extraction has no drawer-capable type mapping — everything BASE
    # arrives as dolna_drzwiowa; the type must be re-entered by hand.
    cab_type = "dolna_legrabox"

    # GAP: extraction carries opening heights only; LEGRABOX system,
    # height codes, NL and capacity must be re-entered by hand.
    codes = ["M", "C", "C"]  # top->bottom fronts 140/287/287
    if len(drawer_heights) != 3:
        drawer_heights = [140, 287, 287]
    drawers = [
        {"id": f"S{i+1}", "height_code": c, "nl": 500, "capacity_kg": 40,
         "wysokosc": h}
        for i, (c, h) in enumerate(zip(codes, drawer_heights))
    ]
    fronts = [
        {"id": f"F{i+1}", "typ": "szufladowy", "powiazany": f"S{i+1}"}
        for i in range(3)
    ]

    # GAP: extraction leaves materials 'unassigned' (ADR-008 by design) but
    # there is no resolution step between adapter and decompose — decor and
    # board assignment is a hand step.
    return CabinetInstance(
        id="D60S3",
        type=cab_type,
        description=f"walking skeleton D60 ({source})",
        width_mm=width,
        height_mm=height,
        depth_mm=depth,
        body_material="PLYTA_BIALA_18",
        back_material="HDF_BIALA_3",
        front_material="K5307_18",
        thickness_back_mm=3,
        plinth_height_mm=plinth,
        drawers=drawers,
        fronts=fronts,
        edge_banding_type="abs",
    )


def write_rozrys(panels: list[Panel]) -> None:
    grain_label = {GrainAxis.HEIGHT: "pion", GrainAxis.WIDTH: "poziom", None: "brak"}
    rows = ["Lp;Element;Dlugosc [mm];Szerokosc [mm];Grubosc [mm];Ilosc;"
            "Material;Uslojenie;Okl. przod;Okl. tyl;Okl. lewa;Okl. prawa;Uwagi"]
    for i, p in enumerate(panels, 1):
        eb = {s: (p.banded_edges.get(s).material if p.banded_edges.get(s) else "")
              for s in ("front", "back", "left", "right")}
        rows.append(
            f"{i};{p.name};{p.height_mm:g};{p.width_mm:g};{p.thickness_mm};"
            f"{p.quantity};{p.material};{grain_label.get(p.grain, p.grain)};"
            f"{eb['front']};{eb['back']};{eb['left']};{eb['right']};"
            f"role={p.role.value if p.role else 'brak'}"
        )
    (GEN / "rozrys.csv").write_text("\n".join(rows) + "\n", encoding="utf-8-sig")


def write_bom(result) -> None:
    area: dict[str, float] = {}
    for p in result.panels:
        area[p.material] = area.get(p.material, 0) + \
            p.width_mm * p.height_mm / 1e6 * p.quantity
    edge: dict[str, float] = {}
    for p in result.panels:
        for eb in p.banded_edges.values():
            edge[eb.material] = edge.get(eb.material, 0) + \
                eb.length_mm / 1000 * p.quantity
    rows = ["Kategoria;Pozycja;Ilosc;Jm;Uwagi"]
    for m, a in area.items():
        rows.append(f"Plyta;{m};{a:.3f};m2;netto")
    for m, l in edge.items():
        rows.append(f"Obrzeze;{m};{l:.2f};mb;")
    for acc in result.accessories:
        rows.append(f"Okucia;{acc.name};{acc.quantity};szt/kpl;{acc.type}")
    (GEN / "bom.csv").write_text("\n".join(rows) + "\n", encoding="utf-8-sig")


def write_cnc(result) -> None:
    lines = ["CNC — D60S3 LEGRABOX (wygenerowane z decompose())",
             "X od przedniej krawedzi, Y od dolnej krawedzi.", ""]
    any_ops = False
    for p in result.panels:
        if not p.machining_ops:
            continue
        any_ops = True
        lines.append(f"== {p.name.upper()} ({p.height_mm:g} x {p.width_mm:g}"
                     f" x {p.thickness_mm}) ==")
        for op in p.machining_ops:
            lines.append(
                f"  {op.type.upper()} D{op.diameter_mm:g} gl.{op.depth_mm:g}"
                f" X={op.x_mm:g} Y={op.y_mm:g} [{op.drill_type or '-'}]"
                f" {op.note}"
            )
        lines.append("")
    if not any_ops:
        lines.append("(brak operacji w decompozycji)")
    grooves = [op for p in result.panels for op in p.machining_ops
               if op.type in ("groove", "dado", "rabbet")]
    if not grooves:
        lines.append("UWAGA GAP: brak frezu wpustu HDF w decompozycji — "
                     "wpust nie jest modelowany jako MachiningOp.")
    (GEN / "cnc-d60.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    GEN.mkdir(exist_ok=True)
    cab = build_instance()
    errors = cab.validate()
    if errors:
        print("validate():", errors)
    result = decompose(cab)
    write_rozrys(result.panels)
    write_bom(result)
    write_cnc(result)
    print(f"panels={len(result.panels)} accessories={len(result.accessories)}")
    print("wrote generated/rozrys.csv, bom.csv, cnc-d60.txt")


if __name__ == "__main__":
    main()
