"""L-layout model — Meyer-contract tests against the validator manifest contract.

Spec: kuchnie-core/docs/specs/l-layout-model.md (wk-29bb6401, ADR-034).
One assertion block per row of the spec's Operation-contracts table, plus
seeded-violation cases for invariants 1-3, the degenerate-TURNS pin
(wk-075803aa) and the flat-Kitchen back-compat check (invariant 4).

Success criteria mirrored in kuchnie-core/docs/specs/l-layout-model.sc.txt.

Hand-computed L geometry used throughout (kitchen-plan mm, validator
[x, y] pairs):

    Leg A ("run_a"): direction east, wall 3000 mm
        start (0, 0) -> end (3000, 0)            # 0 + 3000 east = 3000
    Corner: blind cabinet "NAR1" at the junction
        leg A: consumed 1050 (blind carcass) + filler 50
        leg B: consumed  560 (blind body depth across leg B) + filler 50
    Leg B ("run_b"): direction south, turn "right" (east+right -> south
        per the validator's TURNS table), wall 2400 mm
        start (3000, 0) -> end (3000, -2400)     # 0 - 2400 south = -2400

    usable A = 3000 - (1050 + 50) = 1900
    usable B = 2400 - ( 560 + 50) = 1790
"""

import pytest

from kuchnie_core import (
    CornerLink,
    Kitchen,
    Row,
    Run,
    direction_after_turn,
    kitchen_from_dict,
    kitchen_to_dict,
    row_findings,
    validate_rows,
)
from kuchnie_core.loader import load_kitchen
from kuchnie_core.model import TURNS
from kuchnie_core.validator import check_run_continuity, validate_manifest

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# ── Hand-computed L kitchen builder ─────────────────────────────

def _l_kitchen() -> tuple[Kitchen, CornerLink]:
    """The reference L from the module docstring, built by hand."""
    leg_a = Run(
        id="run_a", label="Leg A", wall_width_mm=3000, wall_height_mm=2600,
        start_position_mm=[0.0, 0.0], end_position_mm=[3000.0, 0.0],
        direction="east", corner_participation="leg_a",
    )
    leg_b = Run(
        id="run_b", label="Leg B", wall_width_mm=2400, wall_height_mm=2600,
        start_position_mm=[3000.0, 0.0], end_position_mm=[3000.0, -2400.0],
        direction="south", turn="right", corner_participation="leg_b",
    )
    kitchen = Kitchen(project_name="L-ref", rows=[leg_a, leg_b],
                      legs=["run_a", "run_b"])
    corner = CornerLink.for_kitchen(
        kitchen,
        run_a_id="run_a", run_b_id="run_b", corner_cabinet_id="NAR1",
        strategy="blind",
        filler_a_mm=50.0, filler_b_mm=50.0,
        consumed_a_mm=1050.0, consumed_b_mm=560.0,
    )
    kitchen.corner = corner
    return kitchen, corner


# ── Run: additive layout fields (invariant 4 at dataclass level) ─

def test_run_layout_fields_are_additive_and_optional():
    """[SC-llay-001] Run extends Row with optional layout fields.

    A Row built the pre-spec way carries None defaults for the layout
    fields and behaves as before; Run is the same class (ubiquitous-
    language alias), so flat JSON stays byte-compatible.
    """
    row = Row(id="r1", label="legacy", wall_width_mm=2000, wall_height_mm=2600)
    assert row.start_position_mm is None
    assert row.end_position_mm is None
    assert row.direction is None
    assert row.turn is None
    assert row.corner_participation is None
    # legacy behaviour intact
    assert row.used_width_mm() == 0
    assert row.remaining_mm() == 2000
    # Run IS the existing Row, now aware of where it starts
    assert Run is Row
    run = Run(id="r2", label="aware", wall_width_mm=3000, wall_height_mm=2600,
              start_position_mm=[0.0, 0.0], end_position_mm=[3000.0, 0.0],
              direction="east")
    assert run.direction == "east"


# ── Kitchen.geometry_manifest(): contract row 1 (invariants 2, 3) ─

def test_geometry_manifest_passes_validate_manifest_for_l():
    """[SC-llay-002] Contract: Runs carry positions + directions ->
    the returned dict passes validate_manifest with issue count 0
    (spec Operation-contracts row 1; invariants 2 and 3).

    Continuity by hand: leg A ends (3000, 0), leg B starts (3000, 0)
    -> dx = dy = 0 <= 1.0 mm tolerance. Direction by hand: east +
    turn "right" -> "south" per the validator's TURNS table.
    """
    kitchen, _ = _l_kitchen()
    manifest = kitchen.geometry_manifest()
    result = validate_manifest(manifest)
    assert len(result.issues) == 0
    assert result.is_valid

    # The manifest speaks the validator's language: run entries carry
    # the keys check_run_continuity reads, in legs order.
    runs = manifest["layout"]["runs"]
    assert [r["index"] for r in runs] == [0, 1]
    assert runs[0]["label"] == "Leg A"
    assert runs[0]["start_position_mm"] == [0.0, 0.0]
    assert runs[0]["end_position_mm"] == [3000.0, 0.0]
    assert runs[0]["direction"] == "east"
    assert runs[0]["turn"] is None
    assert runs[1]["start_position_mm"] == [3000.0, 0.0]
    assert runs[1]["end_position_mm"] == [3000.0, -2400.0]
    assert runs[1]["direction"] == "south"
    assert runs[1]["turn"] == "right"
    assert manifest["layout"]["type"] == "l_shape"
    assert manifest["layout"]["run_count"] == 2

    # Precondition side: a run without positions is refused by name.
    bare = Kitchen(rows=[Row(id="r1", label="", wall_width_mm=1000,
                             wall_height_mm=2600)])
    with pytest.raises(ValueError, match="r1"):
        bare.geometry_manifest()


# ── Run.usable_width_mm(): contract row 2 (invariant 1) ─────────

def test_usable_width_subtracts_corner_consumption_on_both_legs():
    """[SC-llay-003] Contract: corner link resolved -> wall width minus
    this leg's corner consumption + filler (spec Operation-contracts
    row 2; invariant 1: the corner consumes width from BOTH legs).

    Hand-computed: A = 3000 - (1050 + 50) = 1900;
                   B = 2400 - ( 560 + 50) = 1790.
    Seeded violation: leg B read WITHOUT the corner reports the plain
    wall width 2400 -- the invariant-1 violation shape the spec names
    (usable width equal to wall width despite the corner blind at its
    start), detectable as 2400 != 1790.
    """
    kitchen, corner = _l_kitchen()
    leg_a = kitchen.run_by_id("run_a")
    leg_b = kitchen.run_by_id("run_b")
    assert leg_a.usable_width_mm(corner) == 1900.0
    assert leg_b.usable_width_mm(corner) == 1790.0
    # invariant-1 violation: consumption ignored
    assert leg_b.usable_width_mm() == 2400.0
    assert leg_b.usable_width_mm() != leg_b.usable_width_mm(corner)
    # a run outside the corner is untouched by it
    stray = Run(id="run_c", label="", wall_width_mm=1200, wall_height_mm=2600)
    assert stray.usable_width_mm(corner) == 1200.0


# ── CornerLink construction: contract row 3 (invariants 1, 5) ───

def test_corner_link_records_per_leg_widths_and_refuses_unknown_run():
    """[SC-llay-004] Contract: both Run ids exist in the Kitchen ->
    consumed widths recorded per leg (spec Operation-contracts row 3;
    invariants 1 and 5). A corner naming an absent Run id is refused.
    """
    kitchen, corner = _l_kitchen()
    assert corner.strategy == "blind"
    assert corner.corner_cabinet_id == "NAR1"
    assert corner.consumed_mm("run_a") == 1050.0
    assert corner.consumed_mm("run_b") == 560.0
    assert corner.filler_mm("run_a") == 50.0
    assert corner.filler_mm("run_b") == 50.0
    with pytest.raises(ValueError, match="ghost"):
        CornerLink.for_kitchen(
            kitchen, run_a_id="run_a", run_b_id="ghost",
            corner_cabinet_id="NAR1",
        )
    with pytest.raises(ValueError, match="run_x"):
        corner.consumed_mm("run_x")
    # red-team hardening (wk-29bb6401): a corner joins two DISTINCT legs,
    # and leg widths are physical -- negatives refused at construction.
    with pytest.raises(ValueError, match="distinct"):
        CornerLink.for_kitchen(
            kitchen, run_a_id="run_a", run_b_id="run_a",
            corner_cabinet_id="NAR1",
        )
    with pytest.raises(ValueError, match="consumed_a_mm"):
        CornerLink.for_kitchen(
            kitchen, run_a_id="run_a", run_b_id="run_b",
            corner_cabinet_id="NAR1", consumed_a_mm=-500.0,
        )


# ── Seeded violation: invariant 2 (run continuity) ──────────────

def test_600mm_gap_fires_run_continuity_error():
    """[SC-llay-005] Invariant 2 seeded violation: leg B starting
    600 mm off leg A's end makes check_run_continuity fire.

    Hand-computed: leg A ends (3000, 0); leg B start moved to
    (3000, 600) -> dy = 600 > 1.0 mm tolerance -> "run_continuity".
    """
    kitchen, _ = _l_kitchen()
    leg_b = kitchen.run_by_id("run_b")
    leg_b.start_position_mm = [3000.0, 600.0]
    leg_b.end_position_mm = [3000.0, -1800.0]  # keep wall length 2400
    result = validate_manifest(kitchen.geometry_manifest())
    checks = [i.check for i in result.issues]
    assert "run_continuity" in checks
    assert not result.is_valid


# ── Seeded violation: invariant 3 (direction after turn) ────────

def test_wrong_direction_after_turn_fires_direction_error():
    """[SC-llay-006] Invariant 3 seeded violation: east + turn "left"
    declared as "north" contradicts the validator's TURNS table (east
    + left -> "south" there) -> the "direction" check fires.
    """
    kitchen, _ = _l_kitchen()
    leg_b = kitchen.run_by_id("run_b")
    leg_b.turn = "left"
    leg_b.direction = "north"
    # keep positions chained so the failure isolates the direction check:
    # north from (3000, 0) for 2400 -> (3000, 2400)
    leg_b.end_position_mm = [3000.0, 2400.0]
    issues = check_run_continuity(kitchen.geometry_manifest()["layout"])
    assert [i.check for i in issues] == ["direction"]
    assert "should give 'south'" in issues[0].message


# ── Degenerate TURNS pin (conform, do not fix) ──────────────────

def test_turns_mapping_pins_current_degenerate_validator_behaviour():
    """[SC-llay-007] Pin of the CURRENT degenerate TURNS mapping.

    The validator's table maps left and right from a given direction to
    the SAME next direction (e.g. east+left AND east+right -> south).
    That is geometrically wrong for one of the two, but spec invariant 3
    requires following the validator's mapping as-is; the fix is the
    follow-up wk-075803aa (bd kuchnie-wcj). When that lands, this pin
    is the test to rewrite.
    """
    # the model's duplicated table matches the validator's, pair by pair
    for frm in ("east", "north", "west", "south"):
        assert TURNS[(frm, "left")] == TURNS[(frm, "right")]  # degenerate
    assert direction_after_turn("east", "left") == "south"
    assert direction_after_turn("east", "right") == "south"
    assert direction_after_turn("north", "left") == "west"
    assert direction_after_turn("south", "right") == "east"
    with pytest.raises(ValueError):
        direction_after_turn("up", "left")

    # and the validator agrees: east+left declared "south" passes clean
    kitchen, _ = _l_kitchen()
    leg_b = kitchen.run_by_id("run_b")
    leg_b.turn = "left"
    assert leg_b.direction == "south"
    issues = check_run_continuity(kitchen.geometry_manifest()["layout"])
    assert issues == []


# ── Flat-Kitchen back-compat: contract row 4 (invariant 4) ──────

def test_legacy_flat_kitchen_loads_validates_and_serializes_as_today():
    """[SC-llay-008] Contract: JSON/YAML without positions -> model
    identical to today's; validators skip position checks (spec
    Operation-contracts row 4; invariant 4).

    Loads the pre-spec fixture kitchen_01.yaml: layout fields default
    to None, row_findings/validate_rows behave as before, and
    kitchen_to_dict omits the new keys so the serialized shape is
    byte-compatible with older consumers. Round-trips keep legs/corner
    at their empty defaults.
    """
    kitchen = load_kitchen(FIXTURES / "kitchen_01.yaml")
    for row in kitchen.rows:
        assert row.start_position_mm is None
        assert row.direction is None
    assert kitchen.legs == []
    assert kitchen.corner is None

    # validators run exactly as today (position checks skipped)
    assert validate_rows(kitchen) == [f.message for f in row_findings(kitchen)]

    # serialized dict carries the legacy key set -- new keys omitted
    data = kitchen_to_dict(kitchen)
    assert set(data.keys()) == {
        "version", "project_name", "created", "rows", "worktops",
    }
    for row_dict in data["rows"]:
        assert set(row_dict.keys()) == {
            "id", "label", "wall_width_mm", "wall_height_mm", "cabinets",
        }

    # and the round-trip restores the same flat model
    restored = kitchen_from_dict(data)
    assert restored.legs == []
    assert restored.corner is None
    assert [r.id for r in restored.rows] == [r.id for r in kitchen.rows]


def test_positioned_kitchen_roundtrips_through_dict():
    """[SC-llay-002] Serialization side of the manifest contract: a
    positioned L round-trips through kitchen_to_dict/kitchen_from_dict
    with legs, corner and per-run layout fields intact, and the restored
    Kitchen emits a manifest that still validates clean.
    """
    kitchen, corner = _l_kitchen()
    restored = kitchen_from_dict(kitchen_to_dict(kitchen))
    assert restored.legs == ["run_a", "run_b"]
    assert restored.corner == corner
    assert restored.run_by_id("run_b").turn == "right"
    assert restored.run_by_id("run_b").start_position_mm == [3000.0, 0.0]
    result = validate_manifest(restored.geometry_manifest())
    assert len(result.issues) == 0
