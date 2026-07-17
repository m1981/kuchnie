"""ADR-015 contract: kuchnie_core.calculate_bom is the ONE geometry→quantity
fold. kitchen-erp's quantity buckets and the variant purchasing lines are
views over its BOMItem role/measure fields — they must never re-walk panels
or redo area/length arithmetic, or the folds can drift apart again
(premise tr-847d40f8: offer calibration learning against differing numbers).
"""
import inspect

from kuchnie_core.bom import calculate_bom

from kitchen_erp.core import domain_adapter, variant_derivation
from kitchen_erp.core.domain_adapter import (
    quantities_from_decomposition,
    role_bucket,
    to_kuchnie_core,
)
from kitchen_erp.core.models import Cabinet, HardwareSet, Material, ProjectDefaults

from kuchnie_core.decomposer import decompose


def _defaults():
    return ProjectDefaults(
        corpus_mat=Material(id=1, name="Egger W980", price_per_unit=10.0, unit="m2"),
        front_mat=Material(id=2, name="Front MDF", price_per_unit=20.0, unit="m2"),
        back_mat=Material(id=3, name="HDF", price_per_unit=5.0, unit="m2"),
        edge_band_mat=Material(id=4, name="ABS", price_per_unit=1.0, unit="lm"),
        hinge_sys=HardwareSet(id=1, name="Hinge", price_per_set=2.0),
        drawer_sys=HardwareSet(id=2, name="Drawer", price_per_set=30.0),
    )


def test_erp_views_carry_no_panel_arithmetic():
    """The view functions reference calculate_bom and never touch raw panel
    geometry (width_mm/height_mm/banded_edges) — the drift-prevention pin."""
    for fn in (quantities_from_decomposition, variant_derivation._bom_lines):
        src = inspect.getsource(fn)
        assert "calculate_bom" in src, fn.__qualname__
        for forbidden in ("width_mm", "height_mm", "banded_edges", "1e6", "/ 1000"):
            assert forbidden not in src, f"{fn.__qualname__} re-folds geometry: {forbidden}"


def test_buckets_equal_item_measures():
    """DomainQuantities is exactly the role-bucketed sum of BOMItem.measure."""
    defaults = _defaults()
    cabinet = Cabinet(name="D60", type="BASE", module_kind="DRAWER_BASE",
                      width_mm=600.0, height_mm=820.0, depth_mm=560.0,
                      door_count=0, drawer_count=3)
    result = decompose(to_kuchnie_core(cabinet, defaults))
    q = quantities_from_decomposition(result)

    sums = {"panel": {}, "edge_band": {}}
    for item in calculate_bom(result).items:
        if item.category in sums:
            bucket = role_bucket(item.role)
            sums[item.category][bucket] = sums[item.category].get(bucket, 0.0) + item.measure

    assert q.corpus_m2 == sums["panel"].get("corpus", 0.0)
    assert q.front_m2 == sums["panel"].get("front", 0.0)
    assert q.back_m2 == sums["panel"].get("back", 0.0)
    assert q.drawer_box_m2 == sums["panel"].get("box", 0.0)
    assert q.corpus_edge_lm == sums["edge_band"].get("corpus", 0.0)
    assert q.front_edge_lm == sums["edge_band"].get("front", 0.0)
    # positive control: this cabinet actually has board and edging
    assert q.corpus_m2 > 0 and q.front_m2 > 0 and q.front_edge_lm > 0


def test_domain_adapter_module_folds_once():
    """No second panel walk anywhere in the adapter module body."""
    src = inspect.getsource(domain_adapter)
    assert src.count("for panel in") == 0
