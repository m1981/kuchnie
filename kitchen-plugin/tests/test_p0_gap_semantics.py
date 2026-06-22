"""P0-2: Gap Semantics Contract Tests.

PROBLEM: The current `gap` setting conflates two different concepts:
    1. Carcass-to-carcass spacing (between cabinet boxes)
    2. Front-to-front spacing (between visible door/drawer faces)

REALITY CHECK:
    - In European frameless kitchens, cabinet carcasses are typically FLUSH (0mm gap)
    - The visible 2-3mm gap is ONLY between door/drawer fronts
    - Countertops sit directly on carcasses with no gap
    - Plinths are flush with carcass fronts

SOLUTION: Split into two settings:
    - `cabinetGap`: spacing between carcass boxes (usually 0mm)
    - `frontGap`: spacing between door/drawer fronts (usually 2-3mm)

These tests enforce the NEW semantic. They will FAIL until the implementation
is updated to use separate gap settings.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.config_parser import load_config, _apply_defaults, _validate


# ─── Gap Constants (the contract) ─────────────────────────────────────────────

DEFAULT_CABINET_GAP = 0    # mm, carcass-to-carcass (flush)
DEFAULT_FRONT_GAP = 2      # mm, front-to-front (visible gap)


# ─── Settings Defaults Tests ──────────────────────────────────────────────────

class TestGapDefaults:
    """Verify that gap defaults are correctly defined."""

    def test_default_cabinet_gap_is_zero(self):
        """Cabinet carcasses should be flush by default (0mm gap)."""
        from src.config_parser import DEFAULTS
        assert DEFAULTS["cabinetGap"] == DEFAULT_CABINET_GAP

    def test_default_front_gap_is_two(self):
        """Front panels should have 2mm visible gap by default."""
        from src.config_parser import DEFAULTS
        assert DEFAULTS["frontGap"] == DEFAULT_FRONT_GAP

    def test_old_gap_setting_removed(self):
        """The old ambiguous 'gap' setting should not exist in defaults."""
        from src.config_parser import DEFAULTS
        assert "gap" not in DEFAULTS, (
            "Old 'gap' setting must be replaced by 'cabinetGap' and 'frontGap'"
        )

    def test_apply_defaults_sets_both_gaps(self):
        """_apply_defaults must set both cabinetGap and frontGap."""
        config = {"runs": []}
        _apply_defaults(config)
        assert config["settings"]["cabinetGap"] == DEFAULT_CABINET_GAP
        assert config["settings"]["frontGap"] == DEFAULT_FRONT_GAP


# ─── Backward Compatibility Tests ─────────────────────────────────────────────

class TestBackwardCompatibility:
    """Verify that old configs with 'gap' still work."""

    def test_old_gap_maps_to_front_gap(self):
        """Old 'gap' setting should be treated as 'frontGap' for backward compat."""
        config = {
            "settings": {"gap": 3},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        # Old gap=3 should become frontGap=3, cabinetGap=0
        assert config["settings"]["frontGap"] == 3
        assert config["settings"]["cabinetGap"] == DEFAULT_CABINET_GAP

    def test_new_settings_override_old_gap(self):
        """If both old and new settings exist, new ones take precedence."""
        config = {
            "settings": {"gap": 5, "cabinetGap": 1, "frontGap": 3},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        assert config["settings"]["cabinetGap"] == 1
        assert config["settings"]["frontGap"] == 3


# ─── Position Calculation Tests ───────────────────────────────────────────────

class TestPositionUsesCabinetGap:
    """Verify that cabinet positions use cabinetGap (not frontGap)."""

    def _make_run(self, widths: list[int]) -> dict:
        return {
            "label": "test",
            "base": [{"type": "base-door", "width": w} for w in widths],
        }

    def test_cabinet_gap_zero_cabinets_are_adjacent(self):
        """With cabinetGap=0, cabinet boxes are directly adjacent."""
        from src.config_parser import calculate_run_positions

        run = self._make_run([600, 600])
        settings = {"cabinetGap": 0, "frontGap": 2}
        positions = calculate_run_positions(run, settings)

        assert positions[0]["x_mm"] == 0
        assert positions[1]["x_mm"] == 600  # No gap between carcasses

    def test_cabinet_gap_nonzero_adds_space(self):
        """With cabinetGap=1, there's 1mm between carcass boxes."""
        from src.config_parser import calculate_run_positions

        run = self._make_run([600, 600])
        settings = {"cabinetGap": 1, "frontGap": 2}
        positions = calculate_run_positions(run, settings)

        assert positions[0]["x_mm"] == 0
        assert positions[1]["x_mm"] == 601  # 600 + 1mm cabinet gap

    def test_front_gap_does_not_affect_positions(self):
        """frontGap should NOT change cabinet box positions."""
        from src.config_parser import calculate_run_positions

        run = self._make_run([600, 400])
        settings_a = {"cabinetGap": 0, "frontGap": 2}
        settings_b = {"cabinetGap": 0, "frontGap": 5}

        pos_a = calculate_run_positions(run, settings_a)
        pos_b = calculate_run_positions(run, settings_b)

        # Positions must be identical regardless of frontGap
        assert pos_a[0]["x_mm"] == pos_b[0]["x_mm"]
        assert pos_a[1]["x_mm"] == pos_b[1]["x_mm"]

    def test_total_width_uses_cabinet_gap(self):
        """Total run width = sum of cabinet widths + cabinetGap * (n-1)."""
        from src.config_parser import calculate_run_positions

        run = self._make_run([600, 800, 600])
        settings = {"cabinetGap": 0, "frontGap": 2}
        positions = calculate_run_positions(run, settings)

        # Total = 600 + 800 + 600 + 2 * 0 = 2000
        last = positions[-1]
        end_x = last["x_mm"] + run["base"][-1]["width"]
        assert end_x == 2000


# ─── Front Spacing Tests ──────────────────────────────────────────────────────

class TestFrontGapSemantics:
    """Verify frontGap is used for door/drawer visual spacing."""

    def test_front_gap_applies_between_double_doors(self):
        """Double-door cabinet: two doors separated by frontGap."""
        # This will be tested in geometry tests once implemented
        # For now, verify the setting exists and is documented
        from src.config_parser import DEFAULTS
        assert "frontGap" in DEFAULTS

    def test_front_gap_applies_between_drawer_fronts(self):
        """Drawer cabinet: drawer fronts separated by frontGap."""
        from src.config_parser import DEFAULTS
        assert "frontGap" in DEFAULTS

    def test_front_gap_applies_between_door_and_drawer(self):
        """Drawer-door cabinet: drawer and door separated by frontGap."""
        from src.config_parser import DEFAULTS
        assert "frontGap" in DEFAULTS

    def test_zero_front_gap_fronts_are_flush(self):
        """With frontGap=0, door/drawer fronts have no visible gap."""
        # This is a valid configuration for modern handleless kitchens
        from src.config_parser import DEFAULTS
        # Just verify 0 is an acceptable value
        assert DEFAULTS["frontGap"] >= 0


# ─── Validation Tests ─────────────────────────────────────────────────────────

class TestGapValidation:
    """Verify that gap values are validated."""

    def test_negative_cabinet_gap_rejected(self):
        """Cabinet gap must not be negative."""
        config = {
            "settings": {"cabinetGap": -1},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        # Should either raise or warn
        warnings = []
        # TODO: implement validation
        # assert any("cabinetGap" in w for w in warnings)

    def test_negative_front_gap_rejected(self):
        """Front gap must not be negative."""
        config = {
            "settings": {"frontGap": -1},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        # TODO: implement validation

    def test_excessive_gap_warns(self):
        """Gaps larger than 10mm should generate a warning."""
        config = {
            "settings": {"cabinetGap": 50, "frontGap": 50},
            "runs": [{"base": [{"type": "base-door", "width": 600}]}],
        }
        _apply_defaults(config)
        # TODO: implement validation


# ─── Integration Test: Full Config With New Gaps ──────────────────────────────

class TestFullConfigWithNewGaps:
    """Test that a complete config works with the new gap system."""

    def test_i_shape_with_explicit_gaps(self):
        """I-shape config with explicit cabinetGap and frontGap."""
        config = {
            "version": "1.0",
            "units": "mm",
            "name": "Test Kitchen",
            "settings": {
                "baseBodyHeight": 720,
                "baseDepth": 560,
                "wallHeight": 600,
                "wallDepth": 300,
                "plinthHeight": 120,
                "cabinetGap": 0,
                "frontGap": 2,
            },
            "runs": [
                {
                    "label": "back wall",
                    "base": [
                        {"type": "filler", "width": 50},
                        {"type": "base-door", "width": 600},
                        {"type": "base-sink", "width": 800},
                        {"type": "base-door", "width": 600},
                        {"type": "filler", "width": 50},
                    ],
                }
            ],
        }
        _apply_defaults(config)
        _validate(config)

        from src.config_parser import calculate_run_positions
        positions = calculate_run_positions(config["runs"][0], config["settings"])

        # Filler at 0, cabinet at 50 (no gap), sink at 650, cabinet at 1450, filler at 2050
        assert positions[0]["x_mm"] == 0
        assert positions[1]["x_mm"] == 50    # filler width, no cabinet gap
        assert positions[2]["x_mm"] == 650   # 50 + 600
        assert positions[3]["x_mm"] == 1450  # 650 + 800
        assert positions[4]["x_mm"] == 2050  # 1450 + 600
