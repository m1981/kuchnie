"""dolna_narozna_slepa — blind base corner cabinet (wk-31467921).

Hand-computed reference, cabinet 1050 × 720 × 560, plinth 100, blind zone
560 (perpendicular run depth), filler 50, one door:

  side_h   = 720 − 100                     = 620
  sides    2× 560 × 620 × 18
  bottom   1014 × 560 × 18                 (1050 − 2×18)
  trawersy 2× 1014 × 100 × 18
  back     1028 × 598 × 3                  (1050−36+16−2 × 620−36+16−2)
  blind    560 × 614 × 18                  (door height 620 − 6)
  filler   50 × 614 × 18
  door     (440 − 6) / 1 = 434 × 614 × 18  (visible 1050−560−50 = 440)
  cokół    1046 × 97 × 18
"""

import pytest

from kuchnie_core.decomposer import decompose
from kuchnie_core.model import (
    CabinetInstance,
    CornerBlindConfig,
    GrainAxis,
    PanelRole,
)


def make_corner(**overrides) -> CabinetInstance:
    kwargs = dict(
        id="DNL105",
        type="dolna_narozna_slepa",
        description="blind corner test",
        width_mm=1050,
        height_mm=720,
        depth_mm=560,
        body_material="PLYTA_BIALA_18",
        back_material="HDF_BIALA_3",
        front_material="K5307_18",
        plinth_height_mm=100,
        fronts=[{"id": "F1", "typ": "drzwiowy", "ilosc_zawiasow": 2}],
        config=CornerBlindConfig(corner_side="left", second_width_mm=560),
    )
    kwargs.update(overrides)
    return CabinetInstance(**kwargs)


def _panel(result, role):
    return [p for p in result.panels if p.role is role]


def test_registered_in_type_registry():
    from kuchnie_core.catalog import TYPE_REGISTRY
    assert "dolna_narozna_slepa" in TYPE_REGISTRY


def test_panel_roster():
    result = decompose(make_corner())
    roles = sorted(p.role.value for p in result.panels)
    assert roles == sorted([
        "left_side", "right_side", "bottom", "top", "top", "back",
        "front_blind", "filler", "front_door", "plinth",
    ])


def test_carcass_dimensions_hand_computed():
    result = decompose(make_corner())
    for side in _panel(result, PanelRole.LEFT_SIDE) + _panel(result, PanelRole.RIGHT_SIDE):
        assert (side.width_mm, side.height_mm) == (560, 620)
    bottom = _panel(result, PanelRole.BOTTOM)[0]
    assert (bottom.width_mm, bottom.height_mm) == (1014, 560)
    for trawers in _panel(result, PanelRole.TOP):
        assert (trawers.width_mm, trawers.height_mm) == (1014, 100)
    back = _panel(result, PanelRole.BACK)[0]
    assert (back.width_mm, back.height_mm) == (1028, 598)
    assert back.height_mm < 620  # reduced back: never taller than the sides
    plinth = _panel(result, PanelRole.PLINTH)[0]
    assert (plinth.width_mm, plinth.height_mm) == (1046, 97)


def test_front_split_hand_computed():
    result = decompose(make_corner())
    blind = _panel(result, PanelRole.FRONT_BLIND)[0]
    filler = _panel(result, PanelRole.FILLER)[0]
    door = _panel(result, PanelRole.FRONT_DOOR)[0]
    assert (blind.width_mm, blind.height_mm) == (560, 614)
    assert (filler.width_mm, filler.height_mm) == (50, 614)
    assert (door.width_mm, door.height_mm) == (434, 614)
    # blind + filler + door + door gaps fill the cabinet width exactly
    assert blind.width_mm + filler.width_mm + door.width_mm + 6 == 1050


def test_front_parts_are_front_material_with_vertical_grain():
    result = decompose(make_corner())
    for role in (PanelRole.FRONT_BLIND, PanelRole.FILLER, PanelRole.FRONT_DOOR):
        p = _panel(result, role)[0]
        assert p.material == "K5307_18"
        assert p.grain == GrainAxis.HEIGHT


def test_blind_front_banded_on_filler_side_only():
    # corner_side="left" → blind zone at the left end → its RIGHT edge shows
    result = decompose(make_corner())
    blind = _panel(result, PanelRole.FRONT_BLIND)[0]
    assert set(blind.banded_edges) == {"right"}

    mirrored = decompose(make_corner(
        config=CornerBlindConfig(corner_side="right", second_width_mm=560)))
    blind = _panel(mirrored, PanelRole.FRONT_BLIND)[0]
    assert set(blind.banded_edges) == {"left"}


def test_hinges_on_door_only_no_handle_on_blind():
    result = decompose(make_corner())
    hinges = [a for a in result.accessories if a.type == "hinge"]
    assert len(hinges) == 1
    assert hinges[0].quantity == 2


def test_machining_confirmats_and_grooves():
    result = decompose(make_corner())
    sides = _panel(result, PanelRole.LEFT_SIDE) + _panel(result, PanelRole.RIGHT_SIDE)
    for side in sides:
        confirmats = [op for op in side.machining_ops if op.drill_type == "confirmat"]
        grooves = [op for op in side.machining_ops if op.type == "groove"]
        assert len(confirmats) == 5  # 3 into bottom + 2 into trawersy
        assert len(grooves) == 1
    bottom = _panel(result, PanelRole.BOTTOM)[0]
    assert any(op.type == "groove" for op in bottom.machining_ops)
    rear = [p for p in _panel(result, PanelRole.TOP) if not p.banded_edges][0]
    assert any(op.type == "groove" for op in rear.machining_ops)


def test_opening_too_narrow_raises():
    with pytest.raises(ValueError, match="too narrow"):
        decompose(make_corner(width_mm=800))  # 800-560-50 = 190 < 250


def test_defaults_without_config():
    """Hand-built instance with config=None: blind zone falls back to depth."""
    result = decompose(make_corner(config=None))
    blind = [p for p in result.panels if p.role is PanelRole.FRONT_BLIND][0]
    assert blind.width_mm == 560
    filler = [p for p in result.panels if p.role is PanelRole.FILLER][0]
    assert filler.width_mm == 50
