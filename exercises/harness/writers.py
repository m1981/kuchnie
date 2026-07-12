"""Production-output writers: rozrys.csv, bom.csv, cnc.txt.

Extracted from the walking-skeleton production legs so every exercise emits
the same pinned rozrys contract (Lp;Element;Dlugosc;Szerokosc;Grubosc;
Ilosc;Material;Uslojenie;Okleina x4;Uwagi) and comparable BOM/CNC shapes.
"""
from __future__ import annotations

from pathlib import Path

from kuchnie_core.model import GrainAxis

_GRAIN_LABEL = {GrainAxis.HEIGHT: "pion", GrainAxis.WIDTH: "poziom", None: "brak"}

ROZRYS_HEADER = ("Lp;Element;Dlugosc [mm];Szerokosc [mm];Grubosc [mm];Ilosc;"
                 "Material;Uslojenie;Okl. przod;Okl. tyl;Okl. lewa;Okl. prawa;Uwagi")


def write_rozrys(panels, path: str | Path) -> Path:
    rows = [ROZRYS_HEADER]
    for i, p in enumerate(panels, 1):
        eb = {s: (p.banded_edges.get(s).material if p.banded_edges.get(s) else "")
              for s in ("front", "back", "left", "right")}
        rows.append(
            f"{i};{p.name};{p.height_mm:g};{p.width_mm:g};{p.thickness_mm};"
            f"{p.quantity};{p.material};{_GRAIN_LABEL.get(p.grain, p.grain)};"
            f"{eb['front']};{eb['back']};{eb['left']};{eb['right']};"
            f"role={p.role.value if p.role else 'brak'}"
        )
    out = Path(path)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8-sig")
    return out


def write_bom(result, path: str | Path) -> Path:
    area: dict[str, float] = {}
    edge: dict[str, float] = {}
    for p in result.panels:
        area[p.material] = area.get(p.material, 0) + \
            p.width_mm * p.height_mm / 1e6 * p.quantity
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
    out = Path(path)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8-sig")
    return out


def write_cnc(result, path: str | Path, title: str = "") -> Path:
    lines = [f"CNC — {title or result.cabinet_id} (wygenerowane z decompose())",
             "X od przedniej krawedzi, Y od dolnej krawedzi.", ""]
    any_ops = False
    for p in result.panels:
        if not p.machining_ops:
            continue
        any_ops = True
        lines.append(f"== {p.name.upper()} ({p.height_mm:g} x {p.width_mm:g}"
                     f" x {p.thickness_mm}) ==")
        for op in p.machining_ops:
            if op.type in ("groove", "dado", "rabbet"):
                lines.append(f"  {op.type.upper()} szer.{op.width_mm:g}"
                             f" gl.{op.depth_mm:g} os X={op.x_mm:g}"
                             f" dl.{op.length_mm:g} {op.note}")
            else:
                lines.append(
                    f"  {op.type.upper()} D{op.diameter_mm:g} gl.{op.depth_mm:g}"
                    f" X={op.x_mm:g} Y={op.y_mm:g} [{op.drill_type or '-'}]"
                    f" {op.note}")
        lines.append("")
    if not any_ops:
        lines.append("(brak operacji w decompozycji)")
    out = Path(path)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
