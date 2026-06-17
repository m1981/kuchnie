#!/usr/bin/env python3
"""End-to-end example: define a kitchen → generate CSV files.

Run:  python example_generate.py
"""

from __future__ import annotations

from pathlib import Path

from kitchen_cad.models import (
    CorpusSpec,
    DrawerSpec,
    HandleSpec,
    HingeSpec,
)
from kitchen_cad.panel_calculator import calculate_panels
from kitchen_cad.drill_engine import apply_all_drilling
from kitchen_cad.csv_generator import generate_cutting_csv, generate_edging_csv

OUTPUT = Path(__file__).parent / "output" / "demo_kitchen"


# ── Define a simple L-shaped kitchen (3 base cabinets + 2 wall cabinets) ──

kitchen = [
    # ── Base cabinets (dolne) ──
    CorpusSpec(
        id="K01",
        name="Szafka dolna pod zlew 800",
        corpus_type="base_door",
        width=800, height=720, depth=510,
        material_corpus="D3821_SW",   # Dąb Sztokholm (Swiss Krono)
        material_front="U164_EM",     # Antracyt Velvet
        shelves=[],
        doors=[2],
        hinges=HingeSpec(count=2),
        handles=HandleSpec(spacing=256),
    ),
    CorpusSpec(
        id="K02",
        name="Szafka dolna szufladowa 600",
        corpus_type="base_drawer",
        width=600, height=720, depth=510,
        material_corpus="D3821_SW",
        material_front="U164_EM",
        drawers=[
            DrawerSpec(internal_height=150),
            DrawerSpec(internal_height=270),
        ],
        handles=HandleSpec(spacing=160),
    ),
    CorpusSpec(
        id="K03",
        name="Szafka dolna narożna 900",
        corpus_type="base_door",
        width=900, height=720, depth=510,
        material_corpus="D3821_SW",
        material_front="U164_EM",
        shelves=[352],
        doors=[2],
        hinges=HingeSpec(count=3),  # 3 hinges for wide door
        handles=HandleSpec(spacing=320),
    ),

    # ── Wall cabinets (górne) ──
    CorpusSpec(
        id="G01",
        name="Szafka wisząca nad zlewem 800",
        corpus_type="wall_door",
        width=800, height=720, depth=300,
        material_corpus="D3821_SW",
        material_front="U164_EM",
        shelves=[352],
        doors=[2],
        hinges=HingeSpec(count=2),
    ),
    CorpusSpec(
        id="G02",
        name="Szafka wisząca 600",
        corpus_type="wall_door",
        width=600, height=720, depth=300,
        material_corpus="D3821_SW",
        material_front="U164_EM",
        shelves=[352],
        doors=[2],
        hinges=HingeSpec(count=2),
    ),
]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    all_panels = []

    for spec in kitchen:
        # Step 1: calculate panels
        panels = calculate_panels(spec)
        # Step 2: apply drilling (System 32 + hinges + handles)
        panels = apply_all_drilling(panels, spec)
        all_panels.extend(panels)

    # Step 3: generate CSV files
    cutting_path = generate_cutting_csv(all_panels, OUTPUT / "ciecie.csv")
    edging_path = generate_edging_csv(all_panels, OUTPUT / "oklejanie.csv")

    # ── Print summary ──
    print(f"✅ Wygenerowano {len(all_panels)} formatek z {len(kitchen)} korpusów")
    print(f"   📄 Cięcie:     {cutting_path}")
    print(f"   📄 Oklejanie:  {edging_path}")
    print()

    # Print drill point summary
    total_drills = sum(len(p.drill_points) for p in all_panels)
    print(f"   🔩 Łącznie otworów: {total_drills}")
    for p in all_panels:
        if p.drill_points:
            print(f"      {p.id:15s}  {len(p.drill_points):3d} otworów  "
                  f"({p.width:g}×{p.height:g}×{p.thickness:g}  {p.material})")

    print()
    print("─── Cutting CSV preview ───")
    with open(cutting_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            print(f"  {line.rstrip()}")
            if i >= 8:
                print("  ...")
                break

    print()
    print("─── Edging CSV preview ───")
    with open(edging_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            print(f"  {line.rstrip()}")
            if i >= 10:
                print("  ...")
                break


if __name__ == "__main__":
    main()
