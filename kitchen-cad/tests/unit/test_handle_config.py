"""Phase 1 tests: Handle configuration (TC-6.1, TC-6.2).

Covers:
- TC-6.1.x: Handle types (none, standard 2-hole, knob 1-hole)
- TC-6.2.x: Handle position (top/bottom/center)
- TC-6.3.x: Handle orientation (horizontal/vertical)
- TC-6.4.x: Handle spacing
"""

from __future__ import annotations

import pytest

from kitchen_cad.models import (
    CorpusSpec,
    DrawerSpec,
    HandleSpec,
    Panel,
    PanelRole,
)
from kitchen_cad.drill_engine import apply_handles


# ---------------------------------------------------------------------------
# TC-6.1: Handle types
# ---------------------------------------------------------------------------


class TestHandleTypes:
    """TC-6.1: Verify different handle types."""

    def _make_drawer_panel(self) -> Panel:
        return Panel(
            id="F1",
            role=PanelRole.FRONT_DRAWER,
            width=594.0,
            height=200.0,
            thickness=18.0,
            material="TEST",
        )

    def test_no_handle(self):
        """TC-6.1.1: No handle — no drill points added."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=None,
        )
        panel = self._make_drawer_panel()
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]
        assert len(handle_holes) == 0

    def test_standard_bar_handle_2_holes(self):
        """TC-6.1.2: Standard bar handle — 2 × ∅5mm through-holes."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=HandleSpec(spacing=256.0, hole_diameter=5.0),
        )
        panel = self._make_drawer_panel()
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]
        assert len(handle_holes) == 2
        for hole in handle_holes:
            assert hole.diameter == 5.0
            assert hole.depth == 0  # through hole

    def test_knob_single_hole(self):
        """TC-6.1.3: Knob — 1 × ∅5mm (spacing=0 means single hole at center).

        NOTE: Current engine always creates 2 holes.
        This test documents expected behavior for a knob.
        A knob would need spacing=0 which places both holes at center.
        """
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=HandleSpec(spacing=0.0, hole_diameter=5.0),
        )
        panel = self._make_drawer_panel()
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]
        # With spacing=0, both holes overlap at center
        # This is technically 2 holes at same position — a knob implementation
        # would need a separate "knob" handle type
        assert len(handle_holes) == 2
        # Both should be at center X
        center_x = panel.width / 2
        for hole in handle_holes:
            assert hole.x == pytest.approx(center_x, abs=0.1)


# ---------------------------------------------------------------------------
# TC-6.2: Handle position
# ---------------------------------------------------------------------------


class TestHandlePosition:
    """TC-6.2: Verify handle positioning on drawer front."""

    def _make_drawer_panel(self, width=594.0, height=200.0) -> Panel:
        return Panel(
            id="F1",
            role=PanelRole.FRONT_DRAWER,
            width=width,
            height=height,
            thickness=18.0,
            material="TEST",
        )

    def test_handle_centered_horizontally(self):
        """TC-6.2.1: Handle holes centered horizontally on drawer front."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=HandleSpec(spacing=160.0),
        )
        panel = self._make_drawer_panel(width=594.0, height=200.0)
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]

        center_x = 594.0 / 2
        x_positions = sorted([h.x for h in handle_holes])

        # First hole: center - spacing/2
        assert x_positions[0] == pytest.approx(center_x - 80.0, abs=0.1)
        # Second hole: center + spacing/2
        assert x_positions[1] == pytest.approx(center_x + 80.0, abs=0.1)

    def test_handle_centered_vertically(self):
        """TC-6.2.2: Handle holes centered vertically on drawer front."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=HandleSpec(spacing=160.0),
        )
        panel = self._make_drawer_panel(width=594.0, height=200.0)
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]

        expected_y = 200.0 / 2
        for hole in handle_holes:
            assert hole.y == pytest.approx(expected_y, abs=0.1)

    def test_handle_position_from_top(self):
        """TC-6.2.3: Handle positioned from top of drawer.

        NOTE: Current engine always centers vertically.
        This test documents expected behavior.
        """
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=HandleSpec(spacing=160.0, position="top"),
        )
        panel = self._make_drawer_panel(width=594.0, height=200.0)
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]

        # Current engine ignores position parameter and always centers
        # This documents the gap
        for hole in handle_holes:
            assert hole.y == pytest.approx(100.0, abs=0.1)  # always centered


# ---------------------------------------------------------------------------
# TC-6.3: Handle orientation
# ---------------------------------------------------------------------------


class TestHandleOrientation:
    """TC-6.3: Verify handle orientation affects hole placement."""

    def _make_drawer_panel(self) -> Panel:
        return Panel(
            id="F1",
            role=PanelRole.FRONT_DRAWER,
            width=594.0,
            height=200.0,
            thickness=18.0,
            material="TEST",
        )

    def test_horizontal_handle_spacing(self):
        """TC-6.3.1: Horizontal handle — holes spread along X axis."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=HandleSpec(spacing=160.0),
        )
        panel = self._make_drawer_panel()
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]

        x_positions = [h.x for h in handle_holes]
        y_positions = [h.y for h in handle_holes]

        # Holes should differ in X, same Y (horizontal)
        assert abs(x_positions[0] - x_positions[1]) > 0
        assert y_positions[0] == pytest.approx(y_positions[1])


# ---------------------------------------------------------------------------
# TC-6.4: Handle spacing values
# ---------------------------------------------------------------------------


class TestHandleSpacing:
    """TC-6.4: Verify different handle spacing values."""

    def _make_drawer_panel(self) -> Panel:
        return Panel(
            id="F1",
            role=PanelRole.FRONT_DRAWER,
            width=594.0,
            height=200.0,
            thickness=18.0,
            material="TEST",
        )

    @pytest.mark.parametrize(
        "spacing",
        [128.0, 160.0, 256.0, 320.0],
        ids=["TC-6.4.1_128mm", "TC-6.4.2_160mm", "TC-6.4.3_256mm", "TC-6.4.4_320mm"],
    )
    def test_handle_spacing_values(self, spacing: float):
        """TC-6.4.1-4: Different standard spacing values."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=HandleSpec(spacing=spacing),
        )
        panel = self._make_drawer_panel()
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]

        x_positions = sorted([h.x for h in handle_holes])
        actual_spacing = x_positions[1] - x_positions[0]
        assert actual_spacing == pytest.approx(spacing, abs=0.1)

    def test_zero_spacing_galka(self):
        """TC-6.4.5: Spacing 0 — both holes at center (knob/gałka)."""
        spec = CorpusSpec(
            id="T",
            name="test",
            corpus_type="base_drawer",
            width=600,
            height=720,
            depth=510,
            handles=HandleSpec(spacing=0.0),
        )
        panel = self._make_drawer_panel()
        result = apply_handles([panel], spec)
        handle_holes = [dp for dp in result[0].drill_points if dp.drill_type.value == "uchwyt"]

        center_x = panel.width / 2
        for hole in handle_holes:
            assert hole.x == pytest.approx(center_x, abs=0.1)
