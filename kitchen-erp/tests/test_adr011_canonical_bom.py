"""ADR-011 contract: the recipe-based BOMGenerator is the ONLY cost path.

The old direct-computation path (Cabinet.calculate_cost, the use_new_bom
runtime toggle, the *_new method suffixes) is deleted, not deprecated.
These tests pin the deletion so it cannot quietly grow back.
"""
from kitchen_erp.core.models import Cabinet


def test_cabinet_has_no_legacy_cost_method():
    """Cabinet.calculate_cost was the old path; ADR-011 deletes it."""
    assert not hasattr(Cabinet, "calculate_cost")


def test_state_has_single_canonical_cost_path():
    """KitchenState routes cost traces through BOMGenerator only:
    no toggle, no _new suffixes, canonical method names present."""
    from kitchen_erp.ui.state import KitchenState

    assert "use_new_bom" not in KitchenState.__fields__
    assert not hasattr(KitchenState, "set_use_new_bom")
    assert not hasattr(KitchenState, "open_selected_cabinet_cost_trace_new")
    assert not hasattr(KitchenState, "open_project_cost_trace_new")

    assert hasattr(KitchenState, "open_selected_cabinet_cost_trace")
    assert hasattr(KitchenState, "open_project_cost_trace")
