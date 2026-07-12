#!/usr/bin/env python3
"""E2E D60 LEGRABOX — production leg (wk-641a80a8).

Input:  generated/extracted-kitchen.json (from blender_leg.py)
Output: generated/rozrys.csv, generated/bom.csv, generated/cnc-d60.txt,
        generated/golden-diff.txt

Every GAP: block is data the pipeline could not carry and a human had to
re-enter — the ergonomics measurement this exercise exists for.
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
GAPS: list[str] = []


def gap(msg: str) -> None:
    print(f"GAP: {msg}")
    GAPS.append(msg)


def build_instance() -> CabinetInstance:
    p = GEN / "extracted-kitchen.json"
    ext = None
    if p.exists():
        kitchen = json.loads(p.read_text())
        ext = kitchen["rows"][0]["cabinets"][0]

    if ext:
        width, height = ext["width_mm"], ext["height_mm"]
        depth, plinth = ext["depth_mm"], ext.get("plinth_height_mm", 100)
    else:
        width, height, depth, plinth = 600, 820, 560, 100
        gap("no extracted JSON — dimensions hand-entered")

    if ext is not None and not ext.get("drawers"):
        gap("extraction dropped the 3-drawer stack (openings ARE stored in "
            "the scene: Splitter Vertical/Opening N cages, Dim Z 140/254/254 "
            "— adapter does not read them; wk-81a47ab8)")
    gap("cabinet type re-entered by hand: extraction maps BASE -> "
        "dolna_drzwiowa; dolna_legrabox unreachable from a scene (E2)")
    gap("LEGRABOX spec re-entered by hand: system, height codes M/C/C, "
        "NL500, 40kg (E3)")
    gap("materials re-entered by hand: extraction emits 'unassigned' "
        "(ADR-008 by design, E4) — hb5 scene DID carry the decor split "
        "(fronts walnut finish vs ply interior) but no resolver maps hb5 "
        "materials to catalog decors")
    gap("front heights re-entered by hand as designed (140/287/287): hb5 "
        "stores OPENING sizes and its US overlay model produced fronts "
        "163.8/268.8/279.4 — designer front-height intent is not "
        "expressible via hb5 knobs (needs front->opening translation "
        "in the adapter write path)")

    drawers = [
        {"id": f"S{i+1}", "height_code": c, "nl": 500, "capacity_kg": 40,
         "wysokosc": h}
        for i, (c, h) in enumerate([("M", 140), ("C", 287), ("C", 287)])
    ]
    fronts = [
        {"id": f"F{i+1}", "typ": "szufladowy", "powiazany": f"S{i+1}"}
        for i in range(3)
    ]
    return CabinetInstance(
        id="D60S3",
        type="dolna_legrabox",
        description="e2e D60 (extracted envelope + hand re-entry)",
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
    for p in result.panels:
        if not p.machining_ops:
            continue
        lines.append(f"== {p.name.upper()} ({p.height_mm:g} x {p.width_mm:g}"
                     f" x {p.thickness_mm}) ==")
        for op in p.machining_ops:
            if op.type == "groove":
                lines.append(f"  GROOVE szer.{op.width_mm:g} gl.{op.depth_mm:g}"
                             f" os X={op.x_mm:g} dl.{op.length_mm:g} {op.note}")
            else:
                lines.append(
                    f"  {op.type.upper()} D{op.diameter_mm:g} gl.{op.depth_mm:g}"
                    f" X={op.x_mm:g} Y={op.y_mm:g} [{op.drill_type or '-'}]"
                    f" {op.note}")
        lines.append("")
    (GEN / "cnc-d60.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# Golden tables from GOLDEN.md §3 — (name, h, w, th, qty, material, grain)
GOLDEN_PANELS = [
    ("Bok lewy", 720, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
    ("Bok prawy", 720, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
    ("Dno", 564, 560, 18, 1, "PLYTA_BIALA_18", "brak"),
    ("Trawers przedni", 564, 100, 18, 1, "PLYTA_BIALA_18", "brak"),
    ("Trawers tylny", 564, 100, 18, 1, "PLYTA_BIALA_18", "brak"),
    ("Plecy", 698, 578, 3, 1, "HDF_BIALA_3", "brak"),
    ("Front M", 140, 596, 18, 1, "K5307_18", "pion"),
    ("Front C", 287, 596, 18, 2, "K5307_18", "pion"),
    ("Szuflada dno", 490, 503, 16, 3, "PLYTA_BIALA_16", "brak"),
    ("Szuflada tyl M", 63, 500, 16, 1, "PLYTA_BIALA_16", "brak"),
    ("Szuflada tyl C", 148, 500, 16, 2, "PLYTA_BIALA_16", "brak"),
    ("Cokol", 97, 596, 18, 1, "PLYTA_BIALA_18", "brak"),
]


def diff_vs_golden(result) -> None:
    """Compare generated panels against GOLDEN.md by (h, w, th) multiset."""
    gen = []
    for p in result.panels:
        for _ in range(p.quantity):
            gen.append((round(p.height_mm), round(p.width_mm),
                        p.thickness_mm, p.material,
                        p.grain or "brak", p.name))
    gold = []
    for name, h, w, th, qty, mat, grain in GOLDEN_PANELS:
        for _ in range(qty):
            gold.append((h, w, th, mat, grain, name))

    lines = ["golden vs generated — panel-by-panel (dims h x w x th)", ""]
    unmatched_gen = list(gen)
    for g in gold:
        # exact dims match first, then dims-only (material naming drift)
        exact = next((x for x in unmatched_gen if x[:3] == g[:3]), None)
        if exact:
            unmatched_gen.remove(exact)
            notes = []
            if exact[3] != g[3]:
                notes.append(f"material {exact[3]} != {g[3]}")
            if exact[4] != g[4]:
                notes.append(f"grain {exact[4]} != {g[4]}")
            status = "MATCH" if not notes else "MATCH-dims (" + "; ".join(notes) + ")"
            lines.append(f"  {status:<45} {g[5]} {g[0]}x{g[1]}x{g[2]}")
        else:
            near = next((x for x in unmatched_gen
                         if x[2] == g[2] and abs(x[0]-g[0]) <= 4
                         and abs(x[1]-g[1]) <= 4), None)
            if near:
                unmatched_gen.remove(near)
                lines.append(f"  DELTA  golden {g[5]} {g[0]}x{g[1]}x{g[2]} -> "
                             f"generated {near[5]} {near[0]}x{near[1]}x{near[2]}")
            else:
                lines.append(f"  MISSING in generated: {g[5]} {g[0]}x{g[1]}x{g[2]} {g[3]}")
    for x in unmatched_gen:
        lines.append(f"  EXTRA in generated: {x[5]} {x[0]}x{x[1]}x{x[2]} {x[3]}")

    lines += ["", "hand re-entry gaps this run:"] + [f"  - {g}" for g in GAPS]
    text = "\n".join(lines) + "\n"
    (GEN / "golden-diff.txt").write_text(text, encoding="utf-8")
    print(text)


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
    diff_vs_golden(result)
    print(f"panels={len(result.panels)} accessories={len(result.accessories)}")


if __name__ == "__main__":
    main()
