"""Hardware oracle: golden/hardware.csv parsing + diff vs accessories.

Measures G13 (BOM hardware completeness) mechanically each run instead of
by eyeball. Matching is by accessory TYPE with summed quantities — names
drift ("LEGRABOX kpl. C" vs "Prowadnica legrabox (S2)"), types don't.

golden/hardware.csv (semicolon, header row):

    Typ;Pozycja;Ilosc
    runner;LEGRABOX kpl. NL500 40kg;3
    confirmat;Konfirmat 7x50;10
    leg;Nozka regulowana 100;4

`Pozycja` is reporting text; `Typ` must use the accessory-type vocabulary
(runner, hinge, handle, shelf_pin, ...). Types the pipeline does not emit
yet (confirmat-as-hardware, legs, clips) show up as MISSING — that IS the
G13 measurement, not a harness bug.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GoldenHardware:
    typ: str
    pozycja: str
    ilosc: int


def read_golden_hardware(path: str | Path) -> list[GoldenHardware]:
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f, delimiter=";"):
            out.append(GoldenHardware(
                typ=rec["Typ"].strip(),
                pozycja=rec["Pozycja"].strip(),
                ilosc=int(rec["Ilosc"]),
            ))
    return out


@dataclass
class HardwareDiffResult:
    lines: list[str]
    matched: int = 0
    missing: int = 0   # golden types absent or under-counted
    extra: int = 0     # generated types absent from golden or over-counted

    @property
    def clean(self) -> bool:
        return self.missing == self.extra == 0

    def text(self) -> str:
        summary = (f"hardware summary: {self.matched} type(s) match, "
                   f"{self.missing} missing, {self.extra} extra")
        return "\n".join([*self.lines, "", summary]) + "\n"


def diff_hardware(golden: list[GoldenHardware], result) -> HardwareDiffResult:
    want: dict[str, int] = {}
    label: dict[str, str] = {}
    for g in golden:
        want[g.typ] = want.get(g.typ, 0) + g.ilosc
        label.setdefault(g.typ, g.pozycja)
    got: dict[str, int] = {}
    for acc in result.accessories:
        got[acc.type] = got.get(acc.type, 0) + acc.quantity

    d = HardwareDiffResult(lines=["golden vs generated — hardware (by type)", ""])
    for typ in sorted(set(want) | set(got)):
        w, h = want.get(typ, 0), got.get(typ, 0)
        name = label.get(typ, typ)
        if w == h:
            d.lines.append(f"  MATCH    {typ:<12} {h} ({name})")
            d.matched += 1
        elif h < w:
            d.lines.append(f"  MISSING  {typ:<12} golden {w} vs generated {h} ({name})")
            d.missing += 1
        else:
            d.lines.append(f"  EXTRA    {typ:<12} golden {w} vs generated {h} ({name})")
            d.extra += 1
    return d
