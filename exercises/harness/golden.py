"""Golden cutlist: parsing and grain-aware diff vs a decomposition.

The golden lives in <exercise>/golden/panels.csv (schema in
docs/e2e-exercise-convention.md). Diff semantics:

* dims compare on (Dlugosc, Szerokosc, Grubosc), rounded to 1 mm;
* Uslojenie 'brak'  -> panel may rotate: Dlugosc/Szerokosc unordered;
* 'pion'/'poziom'   -> orientation is part of the cutting contract;
* material / grain mismatches on dimension-matched panels are reported as
  notes, not failures (naming drift is a known-gap class, e.g. G9);
* near-misses within `tol_mm` are reported as DELTA with both readings.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

GRAIN_VALUES = ("brak", "pion", "poziom")


@dataclass(frozen=True)
class GoldenPanel:
    element: str
    dlugosc: float
    szerokosc: float
    grubosc: float
    ilosc: int
    material: str
    uslojenie: str = "brak"

    def __post_init__(self) -> None:
        if self.uslojenie not in GRAIN_VALUES:
            raise ValueError(
                f"{self.element}: Uslojenie '{self.uslojenie}' not in {GRAIN_VALUES}")


def read_golden_panels(path: str | Path) -> list[GoldenPanel]:
    """Parse golden/panels.csv (semicolon-separated, header row)."""
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f, delimiter=";"):
            rows.append(GoldenPanel(
                element=rec["Element"].strip(),
                dlugosc=float(rec["Dlugosc"]),
                szerokosc=float(rec["Szerokosc"]),
                grubosc=float(rec["Grubosc"]),
                ilosc=int(rec["Ilosc"]),
                material=rec["Material"].strip(),
                uslojenie=(rec.get("Uslojenie") or "brak").strip() or "brak",
            ))
    return rows


# One physical piece: (dl, sz, th, material, grain, label)
_Piece = tuple[float, float, float, str, str, str]

_GRAIN_LABEL = {"height": "pion", "width": "poziom", None: "brak"}


def pieces_from_decomposition(result) -> list[_Piece]:
    """Expand a DecompositionResult into per-piece tuples.

    Rozrys convention: Dlugosc <- height_mm, Szerokosc <- width_mm.
    """
    out: list[_Piece] = []
    for p in result.panels:
        grain = _GRAIN_LABEL.get(p.grain, p.grain or "brak")
        for _ in range(p.quantity):
            out.append((round(p.height_mm, 1), round(p.width_mm, 1),
                        round(float(p.thickness_mm), 1),
                        p.material, grain, p.name))
    return out


def pieces_from_golden(panels: list[GoldenPanel]) -> list[_Piece]:
    out: list[_Piece] = []
    for g in panels:
        for _ in range(g.ilosc):
            out.append((round(g.dlugosc, 1), round(g.szerokosc, 1),
                        round(g.grubosc, 1), g.material, g.uslojenie, g.element))
    return out


def _dims_equal(golden: _Piece, gen: _Piece) -> bool:
    if golden[2] != gen[2]:
        return False
    if golden[4] == "brak":  # rotatable: unordered dims
        return {golden[0], golden[1]} == {gen[0], gen[1]} and \
            sorted((golden[0], golden[1])) == sorted((gen[0], gen[1]))
    return (golden[0], golden[1]) == (gen[0], gen[1])


def _dims_near(golden: _Piece, gen: _Piece, tol: float) -> bool:
    if golden[2] != gen[2]:
        return False
    a = sorted((golden[0], golden[1]))
    b = sorted((gen[0], gen[1]))
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


@dataclass
class DiffResult:
    lines: list[str]
    matched: int = 0
    deltas: int = 0
    missing: int = 0
    extra: int = 0

    @property
    def clean(self) -> bool:
        return self.deltas == self.missing == self.extra == 0

    def text(self) -> str:
        summary = (f"summary: {self.matched} match, {self.deltas} delta, "
                   f"{self.missing} missing, {self.extra} extra")
        return "\n".join([*self.lines, "", summary]) + "\n"


def diff_panels(golden: list[GoldenPanel], result, tol_mm: float = 4.0) -> DiffResult:
    """Compare a decomposition against the golden, piece by piece."""
    gold = pieces_from_golden(golden)
    gen = pieces_from_decomposition(result)
    d = DiffResult(lines=[
        "golden vs generated — piece by piece (Dlugosc x Szerokosc x Grubosc)",
        "",
    ])
    remaining = list(gen)
    for g in gold:
        hit = next((x for x in remaining if _dims_equal(g, x)), None)
        if hit:
            remaining.remove(hit)
            notes = []
            if hit[3] != g[3]:
                notes.append(f"material {hit[3]} != {g[3]}")
            if hit[4] != g[4]:
                notes.append(f"grain {hit[4]} != {g[4]}")
            status = "MATCH" if not notes else f"MATCH-dims ({'; '.join(notes)})"
            d.lines.append(f"  {status:<48} {g[5]} {g[0]:g}x{g[1]:g}x{g[2]:g}")
            d.matched += 1
            continue
        near = next((x for x in remaining if _dims_near(g, x, tol_mm)), None)
        if near:
            remaining.remove(near)
            d.lines.append(
                f"  DELTA  golden {g[5]} {g[0]:g}x{g[1]:g}x{g[2]:g} -> "
                f"generated {near[5]} {near[0]:g}x{near[1]:g}x{near[2]:g}")
            d.deltas += 1
        else:
            d.lines.append(
                f"  MISSING in generated: {g[5]} {g[0]:g}x{g[1]:g}x{g[2]:g} {g[3]}")
            d.missing += 1
    for x in remaining:
        d.lines.append(f"  EXTRA in generated: {x[5]} {x[0]:g}x{x[1]:g}x{x[2]:g} {x[3]}")
        d.extra += 1
    return d
