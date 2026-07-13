"""Machining-ops oracle: golden/ops.csv parsing + diff vs a decomposition.

This exists because the panel oracle alone let G8 (runner rows drilled for
the M drawer at the bottom) reach a human eyeball before it was caught —
coordinates are where scrap-risk lives, so coordinates get their own diff.

golden/ops.csv (semicolon, header row; blank cells where not applicable):

    Element;Typ;X;Y;Srednica;Glebokosc;Szerokosc;Dlugosc;DrillType
    Bok lewy;drill;46;55;5;12;;;runner_screw
    Bok lewy;groove;12;;;8;4;720;

Matching semantics:

* ops are matched per ELEMENT GROUP when the golden element name has a
  generated counterpart (names normalized: lowercase, Polish diacritics
  folded) — so "Bok lewy" ops meet "Bok lewy"'s ops;
* golden elements with no generated name-match fall back to one global
  pool, so naming drift degrades attribution, not detection;
* within a group, an op matches on (Typ, DrillType, Srednica, Glebokosc,
  Szerokosc, Dlugosc) exactly and (X, Y) within `tol_mm` (default 0.5);
* a generated panel with quantity N contributes its ops N times.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

_DIACRITICS = str.maketrans("ąćęłńóśźż", "acelnoszz")


def _norm(name: str) -> str:
    return name.strip().lower().translate(_DIACRITICS)


@dataclass(frozen=True)
class GoldenOp:
    element: str
    typ: str                 # "drill" | "groove" | "dado" | "rabbet"
    x: float | None = None
    y: float | None = None
    srednica: float | None = None
    glebokosc: float | None = None
    szerokosc: float | None = None
    dlugosc: float | None = None
    drill_type: str = ""


def _f(v: str | None) -> float | None:
    v = (v or "").strip()
    return float(v) if v else None


def read_golden_ops(path: str | Path) -> list[GoldenOp]:
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f, delimiter=";"):
            out.append(GoldenOp(
                element=rec["Element"].strip(),
                typ=rec["Typ"].strip(),
                x=_f(rec.get("X")),
                y=_f(rec.get("Y")),
                srednica=_f(rec.get("Srednica")),
                glebokosc=_f(rec.get("Glebokosc")),
                szerokosc=_f(rec.get("Szerokosc")),
                dlugosc=_f(rec.get("Dlugosc")),
                drill_type=(rec.get("DrillType") or "").strip(),
            ))
    return out


# One concrete op instance: (norm_element, display, typ, drill_type,
#                            srednica, glebokosc, szerokosc, dlugosc, x, y)
_Op = tuple


def _ops_from_decomposition(result) -> list[_Op]:
    out: list[_Op] = []
    for p in result.panels:
        for _ in range(p.quantity):
            for op in p.machining_ops:
                out.append((
                    _norm(p.name), p.name, op.type, op.drill_type or "",
                    float(op.diameter_mm or 0), float(op.depth_mm or 0),
                    float(op.width_mm or 0), float(op.length_mm or 0),
                    float(op.x_mm or 0), float(op.y_mm or 0),
                ))
    return out


def _ops_from_golden(ops: list[GoldenOp]) -> list[_Op]:
    return [(
        _norm(g.element), g.element, g.typ, g.drill_type,
        float(g.srednica or 0), float(g.glebokosc or 0),
        float(g.szerokosc or 0), float(g.dlugosc or 0),
        float(g.x or 0), float(g.y or 0),
    ) for g in ops]


def _sig(op: _Op) -> tuple:
    """Everything that must match exactly (all but element + coords)."""
    return op[2:8]


def _op_str(op: _Op) -> str:
    kind = f"{op[2]}{f'/{op[3]}' if op[3] else ''}"
    dims = f"D{op[4]:g} gl.{op[5]:g}" if op[2] == "drill" else \
        f"szer.{op[6]:g} gl.{op[5]:g} dl.{op[7]:g}"
    return f"{op[1]}: {kind} {dims} @({op[8]:g},{op[9]:g})"


@dataclass
class OpsDiffResult:
    lines: list[str]
    matched: int = 0
    missing: int = 0
    extra: int = 0

    @property
    def clean(self) -> bool:
        return self.missing == self.extra == 0

    def text(self) -> str:
        summary = (f"ops summary: {self.matched} match, "
                   f"{self.missing} missing, {self.extra} extra")
        return "\n".join([*self.lines, "", summary]) + "\n"


def _match_pool(gold: list[_Op], gen: list[_Op], tol: float,
                d: OpsDiffResult) -> tuple[list[_Op], list[_Op]]:
    """Match ops within one pool; returns (unmatched_gold, unmatched_gen)."""
    remaining = list(gen)
    left = []
    for g in gold:
        hit = next(
            (x for x in remaining if _sig(x) == _sig(g)
             and abs(x[8] - g[8]) <= tol and abs(x[9] - g[9]) <= tol),
            None,
        )
        if hit:
            remaining.remove(hit)
            d.matched += 1
        else:
            left.append(g)
    return left, remaining


def diff_ops(golden: list[GoldenOp], result, tol_mm: float = 0.5) -> OpsDiffResult:
    gold = _ops_from_golden(golden)
    gen = _ops_from_decomposition(result)
    d = OpsDiffResult(lines=["golden vs generated — machining ops", ""])

    gen_elements = {op[0] for op in gen}
    pool_gold: list[_Op] = []
    pool_gen: list[_Op] = [x for x in gen if not any(
        g[0] == x[0] for g in gold)]

    # per-element groups where names align
    for elem in sorted({g[0] for g in gold}):
        g_group = [g for g in gold if g[0] == elem]
        if elem in gen_elements:
            x_group = [x for x in gen if x[0] == elem]
            left_g, left_x = _match_pool(g_group, x_group, tol_mm, d)
            pool_gold += left_g
            pool_gen += left_x
        else:
            pool_gold += g_group  # attribution lost, detection kept

    # global fallback pool (naming drift, e.g. "Front M" vs "Front F1")
    left_g, left_x = _match_pool(pool_gold, pool_gen, tol_mm, d)
    for g in left_g:
        d.lines.append(f"  MISSING op: {_op_str(g)}")
        d.missing += 1
    for x in left_x:
        d.lines.append(f"  EXTRA op:   {_op_str(x)}")
        d.extra += 1
    if d.clean:
        d.lines.append(f"  all {d.matched} ops matched (coord tol ±{tol_mm}mm)")
    return d
