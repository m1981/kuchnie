# kitchen_erp/core/survey.py
"""Survey pack completeness (wk-3fd0fac4; spec: kitchen-erp/docs/specs/survey-pack.md).

The playbook's Phase-0 rule -- missing input = redesign later
(docs/l-kitchen-design-playbook.md) -- becomes checkable spine data: a
fixed enumeration of named ArtifactRef kinds plus a checklist query.
Project.transition_stage consumes survey_pack_missing on forward moves
crossing into 3_layout_design or beyond (the direct 2->3 edge and skips
like 1->3, wk-fc3aba75); everything else about staging stays in
models.py, untouched by this module.

Non-goals mirror the spec: no geometry capture (hb5 owns room geometry),
no parsing of appliance model sheets (archived verbatim), no per-appliance
sheet coverage (gate G4's later concern).
"""
from kitchen_erp.core.models import Project

# The five Phase-0 capture kinds (survey-pack.md, "Data model"), listed in
# the playbook's Phase-0 item order. Additive vocabulary on the existing
# ArtifactRef.kind column -- no schema migration. Completeness = at least
# one ArtifactRef of each kind; `survey_appliance_sheet` may repeat (one
# sheet per appliance) and counts as covered from the first sheet.
REQUIRED_SURVEY_KINDS: list[str] = [
    "survey_dims",             # wall dimensions + diagonals (sketch/PDF/photo)
    "survey_media",            # media points: water, drain, gas, sockets, duct
    "survey_appliance_sheet",  # manufacturer model sheet(s), one per appliance
    "survey_user_profile",     # user height, elbow height, handedness
    "survey_budget",           # budget bracket agreed with the client
]


def survey_pack_missing(project: Project) -> list[str]:
    """Required survey kinds this project still lacks, sorted.

    Empty list = the pack is complete. Feeds the project-record checklist
    render (so the surveyor sees the gap during the visit) and the
    design-entry transition guard in Project.transition_stage. A kind-set membership
    check only -- artifact content is never inspected here (a
    checklist-complete pack with a misread tape measure still passes;
    accepted residual in the spec).
    """
    present = {ref.kind for ref in project.artifact_refs}
    return sorted(kind for kind in REQUIRED_SURVEY_KINDS if kind not in present)
