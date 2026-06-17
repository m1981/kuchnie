"""Phase 2 tests: Mirror / Odbicie lustrzane (TC-10.x).

Mirror = creating a symmetric copy of a panel (e.g. left door → right door).
Drill points and edge banding are reflected.

These tests define expected behavior for mirror functionality.
Features marked with xfail are not yet implemented.

Covers:
- TC-10.1: X mirror (vertical reflection — left ↔ right)
- TC-10.2: Y mirror (horizontal reflection — top ↔ bottom)
"""

from __future__ import annotations

import pytest

from kitchen_cad.models import (
    DrillFace,
    DrillPoint,
    DrillType,
    EdgeBand,
    EdgeSide,
    Panel,
    PanelRole,
)


# ---------------------------------------------------------------------------
# Mirror helpers (expected API — TDD)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="Mirror function not yet implemented", strict=False)
def test_mirror_x_exists():
    """TC-10.1: mirror_x function should exist."""
    from kitchen_cad.mirror import mirror_x  # noqa: F401
    assert callable(mirror_x)


@pytest.mark.xfail(reason="Mirror function not yet implemented", strict=False)
def test_mirror_y_exists():
    """TC-10.2: mirror_y function should exist."""
    from kitchen_cad.mirror import mirror_y  # noqa: F401
    assert callable(mirror_y)


# ---------------------------------------------------------------------------
# TC-10.1: X mirror (vertical — left ↔ right)
# ---------------------------------------------------------------------------


class TestMirrorX:
    """TC-10.1: Vertical mirror (left-right swap)."""

    def _make_left_door(self) -> Panel:
        """Create a left-hinged door with drill points."""
        return Panel(
            id="F1-L",
            role=PanelRole.FRONT_DOOR,
            width=594.0,
            height=714.0,
            thickness=18.0,
            material="U164_EM",
            edges=[
                EdgeBand(side=EdgeSide.TOP),
                EdgeBand(side=EdgeSide.BOTTOM),
                EdgeBand(side=EdgeSide.LEFT),
                EdgeBand(side=EdgeSide.RIGHT),
            ],
            drill_points=[
                # Hinge cup at x=5 (left edge)
                DrillPoint(
                    x=5.0, y=100.0,
                    diameter=35.0, depth=13.0,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.HINGE_CUP,
                    label="cup_left",
                ),
                # Handle at center
                DrillPoint(
                    x=297.0, y=357.0,
                    diameter=5.0, depth=0,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.HANDLE,
                    label="handle",
                ),
            ],
        )

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_mirror_x_creates_right_door(self):
        """TC-10.1.1: Mirror X converts left door to right door."""
        from kitchen_cad.mirror import mirror_x

        left = self._make_left_door()
        right = mirror_x(left)

        assert right.id != left.id  # New ID
        assert right.width == left.width
        assert right.height == left.height
        assert right.role == left.role

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_mirror_x_reflects_drill_x_coordinates(self):
        """TC-10.1.2: X mirror reflects drill point X coordinates."""
        from kitchen_cad.mirror import mirror_x

        left = self._make_left_door()
        right = mirror_x(left)

        # Cup at x=5 should become x = width - 5 = 589
        cup_left = [dp for dp in left.drill_points if dp.drill_type == DrillType.HINGE_CUP][0]
        cup_right = [dp for dp in right.drill_points if dp.drill_type == DrillType.HINGE_CUP][0]

        assert cup_right.x == pytest.approx(left.width - cup_left.x, abs=0.1)
        # Y should remain unchanged
        assert cup_right.y == pytest.approx(cup_left.y, abs=0.1)

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_mirror_x_handle_position(self):
        """TC-10.1.3: Handle at center stays at center after X mirror."""
        from kitchen_cad.mirror import mirror_x

        left = self._make_left_door()
        right = mirror_x(left)

        handle_left = [dp for dp in left.drill_points if dp.drill_type == DrillType.HANDLE][0]
        handle_right = [dp for dp in right.drill_points if dp.drill_type == DrillType.HANDLE][0]

        # Handle at center should stay at center
        assert handle_right.x == pytest.approx(handle_left.x, abs=0.1)
        assert handle_right.y == pytest.approx(handle_left.y, abs=0.1)

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_mirror_x_preserves_edges(self):
        """TC-10.1.4: Edge banding preserved after X mirror."""
        from kitchen_cad.mirror import mirror_x

        left = self._make_left_door()
        right = mirror_x(left)

        left_edges = {e.side for e in left.edges}
        right_edges = {e.side for e in right.edges}

        # All 4 edges should be preserved
        assert left_edges == right_edges

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_mirror_x_preserves_dimensions(self):
        """TC-10.1.5: Dimensions unchanged after mirror."""
        from kitchen_cad.mirror import mirror_x

        original = self._make_left_door()
        mirrored = mirror_x(original)

        assert mirrored.width == original.width
        assert mirrored.height == original.height
        assert mirrored.thickness == original.thickness


# ---------------------------------------------------------------------------
# TC-10.2: Y mirror (horizontal — top ↔ bottom)
# ---------------------------------------------------------------------------


class TestMirrorY:
    """TC-10.2: Horizontal mirror (top-bottom swap)."""

    def _make_front_with_handle(self) -> Panel:
        """Create a door with handle near top."""
        return Panel(
            id="F1",
            role=PanelRole.FRONT_DOOR,
            width=594.0,
            height=714.0,
            thickness=18.0,
            material="U164_EM",
            drill_points=[
                # Handle near top
                DrillPoint(
                    x=297.0, y=614.0,
                    diameter=5.0, depth=0,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.HANDLE,
                    label="handle_top",
                ),
            ],
        )

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_mirror_y_reflects_drill_y_coordinates(self):
        """TC-10.2.1: Y mirror reflects drill point Y coordinates."""
        from kitchen_cad.mirror import mirror_y

        original = self._make_front_with_handle()
        mirrored = mirror_y(original)

        handle_orig = [dp for dp in original.drill_points if dp.drill_type == DrillType.HANDLE][0]
        handle_mirr = [dp for dp in mirrored.drill_points if dp.drill_type == DrillType.HANDLE][0]

        # Handle at y=614 should become y = height - 614 = 100
        assert handle_mirr.y == pytest.approx(original.height - handle_orig.y, abs=0.1)
        # X should remain unchanged
        assert handle_mirr.x == pytest.approx(handle_orig.x, abs=0.1)

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_mirror_y_preserves_dimensions(self):
        """TC-10.2.2: Dimensions unchanged after Y mirror."""
        from kitchen_cad.mirror import mirror_y

        original = self._make_front_with_handle()
        mirrored = mirror_y(original)

        assert mirrored.width == original.width
        assert mirrored.height == original.height


# ---------------------------------------------------------------------------
# Mirror utility calculations (pure math — testable now)
# ---------------------------------------------------------------------------


class TestMirrorMath:
    """Mirror coordinate calculations — pure math, no model dependency."""

    def test_reflect_x(self):
        """X reflection: x' = width - x."""
        width = 594.0
        x = 5.0
        reflected = width - x
        assert reflected == pytest.approx(589.0)

    def test_reflect_y(self):
        """Y reflection: y' = height - y."""
        height = 714.0
        y = 614.0
        reflected = height - y
        assert reflected == pytest.approx(100.0)

    def test_reflect_center_x(self):
        """Center X stays at center after reflection."""
        width = 594.0
        center = width / 2
        reflected = width - center
        assert reflected == pytest.approx(center, abs=0.01)

    def test_reflect_center_y(self):
        """Center Y stays at center after reflection."""
        height = 714.0
        center = height / 2
        reflected = height - center
        assert reflected == pytest.approx(center, abs=0.01)

    @pytest.mark.parametrize(
        "original, width, expected",
        [
            (5.0, 594.0, 589.0),
            (100.0, 594.0, 494.0),
            (297.0, 594.0, 297.0),  # center
            (0.0, 594.0, 594.0),    # edge
            (594.0, 594.0, 0.0),    # opposite edge
        ],
    )
    def test_reflect_x_parametrized(self, original: float, width: float, expected: float):
        """Parametrized X reflection tests."""
        assert width - original == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# Mirror with side panels
# ---------------------------------------------------------------------------


class TestSidePanelMirror:
    """Mirror for side panels (LEFT ↔ RIGHT)."""

    def _make_left_side(self) -> Panel:
        return Panel(
            id="K01-BOK-L",
            role=PanelRole.LEFT_SIDE,
            width=510.0,
            height=720.0,
            thickness=18.0,
            material="D3821_SW",
            edges=[
                EdgeBand(side=EdgeSide.TOP),
                EdgeBand(side=EdgeSide.LEFT),
            ],
            drill_points=[
                DrillPoint(
                    x=37.0, y=100.0,
                    diameter=5.0, depth=13.0,
                    face=DrillFace.INSIDE,
                    drill_type=DrillType.SYSTEM_32,
                    label="s32_100",
                ),
            ],
        )

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_left_side_mirrors_to_right(self):
        """TC-10.1.6: Left side panel mirrors to right side."""
        from kitchen_cad.mirror import mirror_x

        left = self._make_left_side()
        right = mirror_x(left)

        assert right.role == PanelRole.RIGHT_SIDE
        assert right.width == left.width
        assert right.height == left.height

    @pytest.mark.xfail(reason="Mirror not yet implemented", strict=False)
    def test_side_panel_system32_preserved(self):
        """TC-10.1.7: System 32 holes preserved after mirror."""
        from kitchen_cad.mirror import mirror_x

        left = self._make_left_side()
        right = mirror_x(left)

        left_s32 = [dp for dp in left.drill_points if dp.drill_type == DrillType.SYSTEM_32]
        right_s32 = [dp for dp in right.drill_points if dp.drill_type == DrillType.SYSTEM_32]

        assert len(right_s32) == len(left_s32)
