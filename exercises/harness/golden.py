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

from .labels import grain_label as _grain_label

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


def pieces_from_decomposition(result) -> list[_Piece]:
    """Expand a DecompositionResult into per-piece tuples.

    Rozrys convention: Dlugosc <- height_mm, Szerokosc <- width_mm.
    """
    out: list[_Piece] = []
    for p in result.panels:
        grain = _grain_label(p.grain)
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


def _distance(golden: _Piece, gen: _Piece) -> float:
    a = sorted((golden[0], golden[1]))
    b = sorted((gen[0], gen[1]))
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def diff_panels(golden: list[GoldenPanel], result, tol_mm: float = 4.0) -> DiffResult:
    """Compare a decomposition against the golden, piece by piece.

    Matching is two-pass, deterministic: (1) exact dims claim their piece
    first, so a near-miss can never steal an exact partner; (2) remaining
    pairs within tol_mm are matched globally in ascending-distance order —
    closest pairs pair first, avoiding the greedy first-fit mispairing of
    same-thickness panels that sit within tolerance of each other.
    """
    gold = pieces_from_golden(golden)
    gen = pieces_from_decomposition(result)
    d = DiffResult(lines=[
        "golden vs generated — piece by piece (Dlugosc x Szerokosc x Grubosc)",
        "",
    ])
    remaining = list(gen)
    unresolved: list[_Piece] = []

    # pass 1 — exact dims (grain-aware rotation)
    outcome: dict[int, str] = {}
    for gi, g in enumerate(gold):
        hit = next((x for x in remaining if _dims_equal(g, x)), None)
        if hit:
            remaining.remove(hit)
            notes = []
            if hit[3] != g[3]:
                notes.append(f"material {hit[3]} != {g[3]}")
            if hit[4] != g[4]:
                notes.append(f"grain {hit[4]} != {g[4]}")
            status = "MATCH" if not notes else f"MATCH-dims ({'; '.join(notes)})"
            outcome[gi] = f"  {status:<48} {g[5]} {g[0]:g}x{g[1]:g}x{g[2]:g}"
            d.matched += 1
        else:
            unresolved.append(g)
            outcome[gi] = ""  # filled by pass 2 / missing

    # pass 2 — near misses, globally closest-first
    pairs = sorted(
        ((_distance(g, x), gi, g, x)
         for gi, g in enumerate(gold) if outcome[gi] == ""
         for x in remaining if _dims_near(g, x, tol_mm)),
        key=lambda t: t[0],
    )
    taken_g: set[int] = set()
    for dist, gi, g, x in pairs:
        if gi in taken_g or x not in remaining:
            continue
        remaining.remove(x)
        taken_g.add(gi)
        outcome[gi] = (f"  DELTA  golden {g[5]} {g[0]:g}x{g[1]:g}x{g[2]:g} -> "
                       f"generated {x[5]} {x[0]:g}x{x[1]:g}x{x[2]:g}")
        d.deltas += 1

    for gi, g in enumerate(gold):
        if outcome[gi] == "":
            outcome[gi] = (f"  MISSING in generated: "
                           f"{g[5]} {g[0]:g}x{g[1]:g}x{g[2]:g} {g[3]}")
            d.missing += 1
        d.lines.append(outcome[gi])
    for x in remaining:
        d.lines.append(f"  EXTRA in generated: {x[5]} {x[0]:g}x{x[1]:g}x{x[2]:g} {x[3]}")
        d.extra += 1
    return d
