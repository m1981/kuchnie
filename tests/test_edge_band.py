"""Edge band material string format tests.

Proves:
  1. Format is "{edge_type}_{board_material}"
  2. Documented as local identifier (not catalog DB code)
"""

from kuchnie_core.catalog import _normalize_edge_material


def test_normalize_format():
    result = _normalize_edge_material("ABS", "swiss_krono.U119_VL")
    assert result == "ABS_swiss_krono.U119_VL"


def test_normalize_with_different_type():
    result = _normalize_edge_material("PVC", "egger.H1145_ST10")
    assert result == "PVC_egger.H1145_ST10"
