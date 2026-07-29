# kitchen_erp/core/heights.py
"""Height parameter derivation and warning rule (wk-5b929a7c; spec:
kitchen-erp/docs/specs/height-parameter-set.md).

The playbook fixes working heights once per project (Phase 1): the worktop
line is derived from the user's measured elbow height (survey pack,
`survey_user_profile`) as elbow minus a 100..150 mm offset. The decided
lines persist on ProjectDefaults (models.py); this module owns only the
derivation formula and the out-of-band warning -- carcass construction
math stays with kuchnie_core.construction.ConstructionMethod (ADR-002),
and the G1-across-legs consumer lives in kuchnie_core.kitchen.

Pure functions, no persistence: the project record UI and the setup flow
call these against ProjectDefaults values.
"""

# Elbow-formula offset band (playbook Phase 1): worktop = elbow - 100..150.
ELBOW_OFFSET_MIN_MM: float = 100.0
ELBOW_OFFSET_MAX_MM: float = 150.0
# Default offset = band midpoint.
DEFAULT_ELBOW_OFFSET_MM: float = 125.0

# Default worktop band when no elbow is recorded:
# 720 carcass + 100..150 plinth + 38 top => 850..910.
WORKTOP_BAND_MIN_MM: float = 850.0
WORKTOP_BAND_MAX_MM: float = 910.0


def derive_worktop_height(
    elbow_mm: float, offset_mm: float = DEFAULT_ELBOW_OFFSET_MM
) -> float:
    """Worktop line from the measured elbow: elbow - offset, offset in
    100..150 mm (playbook Phase 1 elbow formula).

    An offset outside the band raises ValueError -- named error, not
    clamping: the operator chose a number the playbook does not back, so
    the derivation refuses rather than silently correcting it.
    """
    if not ELBOW_OFFSET_MIN_MM <= offset_mm <= ELBOW_OFFSET_MAX_MM:
        raise ValueError(
            f"elbow offset {offset_mm}mm outside the playbook band "
            f"{ELBOW_OFFSET_MIN_MM:g}..{ELBOW_OFFSET_MAX_MM:g}mm "
            f"(worktop = elbow - offset; not clamped by design)"
        )
    return elbow_mm - offset_mm


def worktop_height_warning(
    worktop_height_mm: float | None, elbow_height_mm: float | None
) -> str | None:
    """The spec's warning rule: a decided worktop line outside the
    850..910 default band WITHOUT a recorded elbow derivation renders a
    warning in the project record. Returns the warning string, or None.

    The operator can still decide it -- bodies differ -- so this never
    raises; with an elbow recorded the out-of-band value is a conscious
    derivation and no warning applies. Consumed later by the project
    record UI (no UI work in wk-5b929a7c).
    """
    if worktop_height_mm is None or elbow_height_mm is not None:
        return None
    if WORKTOP_BAND_MIN_MM <= worktop_height_mm <= WORKTOP_BAND_MAX_MM:
        return None
    return (
        f"worktop_height_mm {worktop_height_mm:g}mm is outside the default "
        f"band {WORKTOP_BAND_MIN_MM:g}..{WORKTOP_BAND_MAX_MM:g}mm "
        f"(720 carcass + 100..150 plinth + 38 top) and no elbow_height_mm "
        f"is recorded -- derive from the survey pack elbow or confirm the "
        f"decision"
    )
