# tests/test_calculations.py
import pytest
from kitchen_erp.models import Material, HardwareSet, ProjectDefaults, Cabinet
from kitchen_erp.schemas import CabinetCostResult


def test_cabinet_cost_calculation():
    # 1. ARRANGE: Setup our test data
    corpus_mat = Material(id=1, name="Corpus", price_per_unit=10.0, unit="m2")
    front_mat = Material(id=2, name="Front", price_per_unit=20.0, unit="m2")
    back_mat = Material(id=3, name="Back", price_per_unit=5.0, unit="m2")
    edge_mat = Material(id=4, name="Edge", price_per_unit=1.0, unit="lm")

    hinge_sys = HardwareSet(id=1, name="Hinge", price_per_set=2.0)
    drawer_sys = HardwareSet(id=2, name="Drawer", price_per_set=30.0)

    defaults = ProjectDefaults(
        corpus_mat=corpus_mat,
        front_mat=front_mat,
        back_mat=back_mat,
        edge_band_mat=edge_mat,
        hinge_sys=hinge_sys,
        drawer_sys=drawer_sys
    )

    # Cabinet: 1000W x 1000H x 500D. 1 Door.
    cabinet = Cabinet(
        name="Test Base",
        type="BASE",
        width_mm=1000.0,
        height_mm=1000.0,
        depth_mm=500.0,
        door_count=1,
        drawer_count=0
    )

    waste_factor = 1.20  # 20% waste

    # 2. ACT: Perform the calculation
    result = cabinet.calculate_cost(defaults, waste_factor)

    # 3. ASSERT: Verify the math
    # Corpus Area: 2*(1000*500) + 2*(1000*500) = 2,000,000 mm2 = 2.0 m2
    # Corpus Cost: 2.0 * $10 * 1.2 = $24.0
    # Back Area: 1000*1000 = 1.0 m2 -> Cost: 1.0 * $5 * 1.2 = $6.0
    # Front Area: 1000*1000 = 1.0 m2 -> Cost: 1.0 * $20 * 1.2 = $24.0
    # Edge Length: (1000*2 + 1000*2)*2 = 8000 mm = 8.0 lm -> Cost: 8.0 * $1 = $8.0
    # Total Material = 24 + 6 + 24 + 8 = 62.0

    # Hardware: 1 door, 1000mm height -> 3 hinges (rule: >900mm = 3). 3 * $2 = $6.0

    assert isinstance(result, CabinetCostResult)
    assert result.material_cost == 62.0
    assert result.hardware_cost == 6.0
    assert result.total_cost == 68.0
    assert [line.label.split(":")[0] for line in result.trace_lines] == [
        "Corpus board",
        "Back panel",
        "Fronts",
        "Edge banding",
        "Hinges",
        "Drawers",
    ]
    assert sum(line.subtotal for line in result.trace_lines if line.category == "Material") == result.material_cost
    assert sum(line.subtotal for line in result.trace_lines if line.category == "Hardware") == result.hardware_cost
