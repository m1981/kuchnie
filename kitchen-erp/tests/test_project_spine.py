# tests/test_project_spine.py
"""wk-02a62298: Project/Order spine -- stage, lifecycle dates, artifact
references threading L1 stages 1-11 (docs/specs/process-coverage.md).

Expectations are hand-computed from STAGE_SEQUENCE / the model's own
validation contract, never derived by running the code under test (see
test_domain_adapter.py for the house style).
"""
import pytest
from kitchen_erp.core.models import (
    Project,
    ArtifactRef,
    STAGE_SEQUENCE,
    DEFAULT_STAGE,
    StageTransitionError,
)


class TestDefaultStage:
    def test_new_project_defaults_to_first_stage(self):
        project = Project(customer_name="Kowalski")
        # STAGE_SEQUENCE[0] is "1_first_visit" per process-coverage.md row 1
        assert project.stage == "1_first_visit"
        assert project.stage == DEFAULT_STAGE

    def test_new_project_has_no_lifecycle_dates_except_created(self):
        project = Project(customer_name="Kowalski")
        assert project.created_at is not None
        assert project.quoted_at is None
        assert project.ordered_at is None
        assert project.production_at is None
        assert project.installed_at is None


class TestStageTransitions:
    def test_legal_transition_chain(self):
        """Walk the full spine forward one hop at a time -- every step in
        STAGE_SEQUENCE is a legal forward move."""
        project = Project(customer_name="Kowalski")
        assert project.stage == "1_first_visit"

        project.transition_stage("2_pomiar")
        assert project.stage == "2_pomiar"

        # The 2->3 edge additionally requires a complete survey pack
        # (docs/specs/survey-pack.md; gated behavior owned by
        # test_survey_pack.py) -- attach the five required kinds so this
        # test keeps exercising the plain forward-walk contract.
        for kind in ("survey_dims", "survey_media", "survey_appliance_sheet",
                     "survey_user_profile", "survey_budget"):
            project.add_artifact(kind, f"/survey/{kind}.pdf")
        project.transition_stage("3_layout_design")
        assert project.stage == "3_layout_design"

        project.transition_stage("5_purchasing")  # skipping forward (4) is fine
        assert project.stage == "5_purchasing"

        project.transition_stage("11_handover_archive")
        assert project.stage == "11_handover_archive"
        assert project.stage == STAGE_SEQUENCE[-1]

    def test_backward_transition_rejected(self):
        project = Project(customer_name="Kowalski")
        # Jumping forward past 3_layout_design requires a complete survey
        # pack (docs/specs/survey-pack.md, wk-fc3aba75; gated behavior owned
        # by test_survey_pack.py) -- attach the five required kinds so this
        # test keeps exercising the backward-refusal contract.
        for kind in ("survey_dims", "survey_media", "survey_appliance_sheet",
                     "survey_user_profile", "survey_budget"):
            project.add_artifact(kind, f"/survey/{kind}.pdf")
        project.transition_stage("5_purchasing")
        with pytest.raises(StageTransitionError):
            project.transition_stage("2_pomiar")
        # rejected transition leaves state untouched
        assert project.stage == "5_purchasing"

    def test_noop_transition_rejected(self):
        project = Project(customer_name="Kowalski")
        project.transition_stage("2_pomiar")
        with pytest.raises(StageTransitionError):
            project.transition_stage("2_pomiar")
        assert project.stage == "2_pomiar"

    def test_unknown_stage_rejected(self):
        project = Project(customer_name="Kowalski")
        with pytest.raises(StageTransitionError):
            project.transition_stage("99_not_a_stage")
        assert project.stage == "1_first_visit"

    def test_stage_10_delivery_installation_is_not_a_stage(self):
        """Stage 10 (Delivery & installation) is 'out, permanent' per
        docs/specs/process-coverage.md -- it must never be a valid stage id."""
        assert "10_delivery_installation" not in STAGE_SEQUENCE
        assert not any(s.startswith("10_") for s in STAGE_SEQUENCE)
        project = Project(customer_name="Kowalski")
        with pytest.raises(StageTransitionError):
            project.transition_stage("10_delivery_installation")


class TestArtifactRefRoundTrip:
    def test_add_artifact_round_trip(self):
        project = Project(customer_name="Kowalski")
        ref = project.add_artifact("rozrys_csv", "/exports/kowalski/rozrys.csv")

        assert isinstance(ref, ArtifactRef)
        assert ref.kind == "rozrys_csv"
        assert ref.path == "/exports/kowalski/rozrys.csv"
        # relationship back-populates in-memory without a DB session
        assert ref in project.artifact_refs
        assert ref.project is project

    def test_multiple_artifacts_accumulate(self):
        project = Project(customer_name="Kowalski")
        project.add_artifact("rozrys_csv", "/exports/rozrys.csv")
        project.add_artifact("bom", "/exports/bom.pdf")
        project.add_artifact("cnc_program", "/exports/cnc/prog.nc")

        assert len(project.artifact_refs) == 3
        assert {ref.kind for ref in project.artifact_refs} == {
            "rozrys_csv", "bom", "cnc_program",
        }
