# tests/test_survey_pack.py
"""wk-3fd0fac4: Survey pack -- named ArtifactRef kinds, completeness
checklist, and the 2_pomiar -> 3_layout_design gate
(kitchen-erp/docs/specs/survey-pack.md).

Expectations are hand-computed from the spec's Data-model table and the
model's own validation contract, never derived by running the code under
test (house style, see test_project_spine.py). SC-svpk-* docstring
citations reference the spec's success criteria; run-time proof rides
wk-3fd0fac4's acceptance command.
"""
import pytest
from sqlmodel import select

from kitchen_erp.core.models import Project, StageTransitionError
from kitchen_erp.core.survey import REQUIRED_SURVEY_KINDS, survey_pack_missing

# The five Phase-0 kinds, hand-copied from the spec's Data-model table --
# NOT imported expectations.
SPEC_KINDS = [
    "survey_dims",
    "survey_media",
    "survey_appliance_sheet",
    "survey_user_profile",
    "survey_budget",
]


def _project_at_pomiar() -> Project:
    project = Project(customer_name="Kowalski")
    project.transition_stage("2_pomiar")
    return project


def _attach_full_pack(project: Project) -> None:
    for kind in SPEC_KINDS:
        project.add_artifact(kind, f"/survey/kowalski/{kind}.pdf")


class TestRequiredSurveyKinds:
    def test_constant_matches_the_specs_five_kinds(self):
        """SC-svpk-001"""
        assert REQUIRED_SURVEY_KINDS == SPEC_KINDS
        # a set-level check too, so ordering churn cannot mask a swap
        assert set(REQUIRED_SURVEY_KINDS) == set(SPEC_KINDS)
        assert len(REQUIRED_SURVEY_KINDS) == 5


class TestSurveyPackMissing:
    def test_empty_pack_reports_all_five_kinds_sorted(self):
        """SC-svpk-002"""
        project = _project_at_pomiar()
        assert survey_pack_missing(project) == sorted(SPEC_KINDS)

    def test_partial_pack_names_exactly_the_absent_kinds(self):
        """SC-svpk-003"""
        project = _project_at_pomiar()
        project.add_artifact("survey_dims", "/survey/dims.pdf")
        project.add_artifact("survey_budget", "/survey/budget.txt")
        assert survey_pack_missing(project) == [
            "survey_appliance_sheet",
            "survey_media",
            "survey_user_profile",
        ]

    def test_non_survey_artifacts_do_not_count_toward_the_pack(self):
        """SC-svpk-002 -- a folder of unrelated attachments is not a pack."""
        project = _project_at_pomiar()
        project.add_artifact("rozrys_csv", "/exports/rozrys.csv")
        project.add_artifact("offer_pdf", "/offers/offer.pdf")
        assert survey_pack_missing(project) == sorted(SPEC_KINDS)

    def test_repeated_appliance_sheet_counts_from_the_first(self):
        """SC-svpk-004 -- one sheet per appliance may repeat; the kind is
        covered from the first sheet (per-appliance coverage is G4's
        later concern, not this pack's)."""
        project = _project_at_pomiar()
        project.add_artifact("survey_appliance_sheet", "/survey/oven.pdf")
        project.add_artifact("survey_appliance_sheet", "/survey/hood.pdf")
        project.add_artifact("survey_appliance_sheet", "/survey/dishwasher.pdf")
        missing = survey_pack_missing(project)
        assert "survey_appliance_sheet" not in missing
        assert missing == [
            "survey_budget",
            "survey_dims",
            "survey_media",
            "survey_user_profile",
        ]

    def test_complete_pack_reports_nothing_missing(self):
        """SC-svpk-005"""
        project = _project_at_pomiar()
        _attach_full_pack(project)
        assert survey_pack_missing(project) == []


class TestSurveyGateTwoToThree:
    def test_incomplete_pack_refused_with_missing_kinds_named(self):
        """SC-svpk-006"""
        project = _project_at_pomiar()
        with pytest.raises(StageTransitionError) as exc_info:
            project.transition_stage("3_layout_design")
        message = str(exc_info.value)
        for kind in SPEC_KINDS:
            assert kind in message
        # refused transition leaves the stage untouched
        assert project.stage == "2_pomiar"

    def test_partial_pack_refusal_names_exactly_the_absent_kinds(self):
        """SC-svpk-003, SC-svpk-006"""
        project = _project_at_pomiar()
        project.add_artifact("survey_dims", "/survey/dims.pdf")
        project.add_artifact("survey_media", "/survey/media.pdf")
        project.add_artifact("survey_user_profile", "/survey/profile.txt")
        with pytest.raises(StageTransitionError) as exc_info:
            project.transition_stage("3_layout_design")
        message = str(exc_info.value)
        assert "survey_appliance_sheet" in message
        assert "survey_budget" in message
        # attached kinds are not reported as missing
        assert "survey_dims" not in message
        assert "survey_media" not in message
        assert "survey_user_profile" not in message
        assert project.stage == "2_pomiar"

    def test_complete_pack_passes_the_gate(self):
        """SC-svpk-007"""
        project = _project_at_pomiar()
        _attach_full_pack(project)
        project.transition_stage("3_layout_design")
        assert project.stage == "3_layout_design"


class TestOtherTransitionsUntouched:
    def test_earlier_and_later_edges_ignore_the_pack(self):
        """SC-svpk-007 -- the guard is scoped to the 2->3 edge; every
        other forward move works with an empty pack."""
        project = Project(customer_name="Kowalski")
        project.transition_stage("2_pomiar")  # 1->2: not gated
        assert project.stage == "2_pomiar"

        # 3->onward edges are not gated either
        _attach_full_pack(project)
        project.transition_stage("3_layout_design")
        project.transition_stage("5_purchasing")
        project.transition_stage("11_handover_archive")
        assert project.stage == "11_handover_archive"

    def test_existing_refusals_unchanged_by_the_gate(self):
        """SC-svpk-007 -- unknown-stage and backward refusals behave as
        before the survey gate existed (test_project_spine.py contract)."""
        project = _project_at_pomiar()
        with pytest.raises(StageTransitionError):
            project.transition_stage("99_not_a_stage")
        with pytest.raises(StageTransitionError):
            project.transition_stage("1_first_visit")  # backward
        with pytest.raises(StageTransitionError):
            project.transition_stage("2_pomiar")  # no-op
        assert project.stage == "2_pomiar"

    def test_project_already_past_stage_2_is_not_retroactively_blocked(self):
        """SC-svpk-007 -- migration policy: a project at stage >= 3 moves
        on regardless of pack state (no backfill obligation)."""
        project = Project(customer_name="Kowalski")
        project.stage = "3_layout_design"  # legacy row, set directly
        project.transition_stage("4_decomposition")
        assert project.stage == "4_decomposition"


class TestSurveyPackPersisted:
    def test_gate_and_checklist_over_a_persisted_project(self, session):
        """SC-svpk-005, SC-svpk-006 -- the checklist is a kind-set query
        over persisted ArtifactRef rows, not just in-memory objects."""
        project = _project_at_pomiar()
        project.add_artifact("survey_dims", "/survey/dims.pdf")
        session.add(project)
        session.commit()

        stored = session.exec(select(Project)).one()
        with pytest.raises(StageTransitionError) as exc_info:
            stored.transition_stage("3_layout_design")
        assert "survey_budget" in str(exc_info.value)

        for kind in ("survey_media", "survey_appliance_sheet",
                     "survey_user_profile", "survey_budget"):
            stored.add_artifact(kind, f"/survey/{kind}.pdf")
        session.add(stored)
        session.commit()

        assert survey_pack_missing(stored) == []
        stored.transition_stage("3_layout_design")
        assert stored.stage == "3_layout_design"
