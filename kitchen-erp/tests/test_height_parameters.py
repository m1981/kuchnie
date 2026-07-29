# tests/test_height_parameters.py
"""wk-5b929a7c: Height parameter set -- per-project working heights on
ProjectDefaults, the elbow derivation, and G1 across legs
(kitchen-erp/docs/specs/height-parameter-set.md).

Expectations are hand-computed from the spec's Data-model table and API
contract, never derived by running the code under test (house style, see
test_survey_pack.py). SC-hps-* docstring citations reference the spec's
success criteria; run-time proof rides wk-5b929a7c's acceptance command.
"""
import pytest
from sqlmodel import select

from kitchen_erp.core.heights import (
    DEFAULT_ELBOW_OFFSET_MM,
    derive_worktop_height,
    worktop_height_warning,
)
from kitchen_erp.core.models import (
    HardwareSet,
    Material,
    Project,
    ProjectDefaults,
)
from kuchnie_core import CabinetInstance, HeightSet, Kitchen, Row
from kuchnie_core.kitchen import row_findings, validate_rows

# The spec's numbers, hand-copied -- NOT imported expectations.
# Elbow formula: worktop = elbow - 100..150; default offset = midpoint 125.
# Default band: 720 carcass + 100..150 plinth + 38 top => 850..910.


# ── Fixture builders ────────────────────────────────────────────

def _defaults(**heights) -> ProjectDefaults:
    """A minimally-valid ProjectDefaults (FK graph per test_quote_freshness
    idiom) carrying the given height fields."""
    return ProjectDefaults(
        corpus_mat=Material(name="Egger W980", price_per_unit=10.0, unit="m2"),
        front_mat=Material(name="Front MDF", price_per_unit=20.0, unit="m2"),
        back_mat=Material(name="HDF", price_per_unit=5.0, unit="m2"),
        edge_band_mat=Material(name="ABS", price_per_unit=1.0, unit="lm"),
        hinge_sys=HardwareSet(name="Hinge", price_per_set=2.0),
        drawer_sys=HardwareSet(name="Drawer", price_per_set=30.0),
        **heights,
    )


def _base_cab(cab_id: str, plinth_mm: int) -> CabinetInstance:
    """A standard-width (600) base carcass: 720 high, plinth as given, so
    its worktop line is plinth + 720 + 38 top."""
    return CabinetInstance(
        id=cab_id, type="dolna", description="base 600",
        width_mm=600, height_mm=720, depth_mm=510,
        body_material="W980", back_material="HDF", front_material="W980",
        plinth_height_mm=plinth_mm,
    )


def _two_leg_kitchen(plinth_a_mm: int, plinth_b_mm: int) -> Kitchen:
    """An L-kitchen as two legs (rows): each leg internally consistent
    (one height, one plinth -- no intra-row G1/G6 noise), legs differ only
    by plinth so only the across-legs comparison can tell them apart."""
    leg_a = Row(id="A", label="Leg A", wall_width_mm=2400, wall_height_mm=2600,
                cabinets=[_base_cab("A1", plinth_a_mm),
                          _base_cab("A2", plinth_a_mm)])
    leg_b = Row(id="B", label="Leg B", wall_width_mm=2400, wall_height_mm=2600,
                cabinets=[_base_cab("B1", plinth_b_mm),
                          _base_cab("B2", plinth_b_mm)])
    return Kitchen(project_name="two-leg-L", rows=[leg_a, leg_b])


# Leg A on the decided line: 130 plinth + 720 carcass + 38 top = 888.
DECIDED_LINE_MM = 888.0
# Leg B diverging: 100 plinth + 720 carcass + 38 top = 858.
DIVERGING_LINE_MM = 858.0


# ── Derivation formula ──────────────────────────────────────────

class TestDeriveWorktopHeight:
    def test_elbow_990_across_the_offset_band(self):
        """SC-hps-002 -- worktop = elbow - offset: elbow 990 maps to
        840..890 across the 100..150 offset band."""
        assert derive_worktop_height(990, offset_mm=100) == 890
        assert derive_worktop_height(990, offset_mm=150) == 840
        assert derive_worktop_height(990, offset_mm=110) == 880

    def test_default_offset_is_the_band_midpoint(self):
        """SC-hps-002 -- omitted offset uses the 125 midpoint: 990 -> 865."""
        assert DEFAULT_ELBOW_OFFSET_MM == 125
        assert derive_worktop_height(990) == 865

    @pytest.mark.parametrize("offset", [99, 151, 0, -10, 200])
    def test_out_of_band_offset_refused_not_clamped(self, offset):
        """SC-hps-003 -- offset outside 100..150 raises ValueError (named
        error, not clamping; API contract table)."""
        with pytest.raises(ValueError):
            derive_worktop_height(990, offset_mm=offset)

    def test_band_edges_are_valid_offsets(self):
        """SC-hps-003 -- 100 and 150 are inside the band (refusal is
        strictly outside, not at the edges)."""
        assert derive_worktop_height(1000, offset_mm=100) == 900
        assert derive_worktop_height(1000, offset_mm=150) == 850


# ── Out-of-band warning rule ────────────────────────────────────

class TestWorktopHeightWarning:
    def test_out_of_band_without_elbow_warns(self):
        """SC-hps-004 -- decided line outside 850..910 with no recorded
        elbow renders a warning naming the band."""
        warning = worktop_height_warning(940, None)
        assert warning is not None
        assert "940" in warning
        assert "850" in warning and "910" in warning
        assert worktop_height_warning(840, None) is not None

    def test_in_band_or_derived_or_undecided_stays_silent(self):
        """SC-hps-004 -- no warning inside the band, none when an elbow
        derivation is recorded (bodies differ -- conscious decision), none
        while the line is undecided."""
        assert worktop_height_warning(880, None) is None
        assert worktop_height_warning(850, None) is None   # band edge
        assert worktop_height_warning(910, None) is None   # band edge
        assert worktop_height_warning(940, 1065) is None   # elbow recorded
        assert worktop_height_warning(None, None) is None
        assert worktop_height_warning(None, 990) is None


# ── ProjectDefaults persistence ─────────────────────────────────

class TestProjectDefaultsHeightFields:
    def test_round_trip_of_all_four_fields(self, session):
        """SC-hps-001 -- elbow_height_mm, worktop_height_mm, wall_line_mm,
        tall_line_mm persist and load back on ProjectDefaults."""
        defaults = _defaults(
            elbow_height_mm=990.0,
            worktop_height_mm=865.0,
            wall_line_mm=1420.0,
            tall_line_mm=2180.0,
        )
        session.add(Project(customer_name="Kowalski", defaults=defaults))
        session.commit()

        stored = session.exec(select(ProjectDefaults)).one()
        assert stored.elbow_height_mm == 990.0
        assert stored.worktop_height_mm == 865.0
        assert stored.wall_line_mm == 1420.0
        assert stored.tall_line_mm == 2180.0

    def test_fields_default_to_none_additive_migration(self, session):
        """SC-hps-001 -- all four columns are nullable and default None:
        an existing project row loads with no height set (band-default
        behaviour, today's G1 semantics)."""
        session.add(Project(customer_name="Nowak", defaults=_defaults()))
        session.commit()

        stored = session.exec(select(ProjectDefaults)).one()
        assert stored.elbow_height_mm is None
        assert stored.worktop_height_mm is None
        assert stored.wall_line_mm is None
        assert stored.tall_line_mm is None


# ── G1 across legs (kuchnie-core consumer) ──────────────────────

class TestG1AcrossLegs:
    def test_diverging_leg_named_in_a_g1_finding(self):
        """SC-hps-005 -- one leg on the decided 888 line, the other at 858:
        G1 names the diverging leg and states the plinth + carcass + top
        arithmetic (finding, not exception)."""
        kitchen = _two_leg_kitchen(plinth_a_mm=130, plinth_b_mm=100)
        heights = HeightSet(worktop_height_mm=DECIDED_LINE_MM)

        g1 = [f for f in row_findings(kitchen, heights) if f.gate_id == "G1"]
        assert len(g1) == 1
        finding = g1[0]
        assert finding.ref == "Leg B"
        assert "Leg B" in finding.message
        assert "858" in finding.message
        assert "888" in finding.message
        # the message states the arithmetic, not just the verdict
        assert "plinth + carcass" in finding.message

        # validate_rows threads heights through to the same rendering
        assert any("Leg B" in m and "858" in m
                   for m in validate_rows(kitchen, heights))

    def test_both_legs_on_the_decided_line_stay_silent(self):
        """SC-hps-006 -- both legs at 130 + 720 + 38 = 888 against the
        decided 888 line: no findings at all."""
        kitchen = _two_leg_kitchen(plinth_a_mm=130, plinth_b_mm=130)
        heights = HeightSet(worktop_height_mm=DECIDED_LINE_MM)
        assert row_findings(kitchen, heights) == []
        assert validate_rows(kitchen, heights) == []

    def test_heights_omitted_keeps_todays_behaviour(self):
        """SC-hps-007 -- without a height set (or with an undecided line)
        the diverging fixture raises no findings: each leg is internally
        consistent and today's G1 is intra-row only. Additive, not
        breaking."""
        kitchen = _two_leg_kitchen(plinth_a_mm=130, plinth_b_mm=100)
        assert row_findings(kitchen) == []
        assert validate_rows(kitchen) == []
        # a HeightSet with no decided worktop line is equally inert
        assert row_findings(kitchen, HeightSet()) == []

    def test_buildability_verdict_consumes_the_height_set(self):
        """SC-hps-005 -- the API contract's trigger is the buildability
        verdict run: evaluate_buildability(kitchen, heights=...) threads
        the set into the G1 gate (blocking finding on the diverging leg)
        while the no-kwarg call keeps today's intra-row-only semantics."""
        from kuchnie_core.buildability import GateStatus, evaluate_buildability

        kitchen = _two_leg_kitchen(plinth_a_mm=130, plinth_b_mm=100)
        heights = HeightSet(worktop_height_mm=DECIDED_LINE_MM)

        verdict = evaluate_buildability(kitchen, heights=heights)
        g1 = next(g for g in verdict.gates if g.gate_id == "G1")
        assert g1.status is GateStatus.FAILED
        assert any("Leg B" in f.message for f in g1.findings)
        assert not verdict.buildable

        legacy = evaluate_buildability(kitchen)
        legacy_g1 = next(g for g in legacy.gates if g.gate_id == "G1")
        assert legacy_g1.status is GateStatus.PASSED
