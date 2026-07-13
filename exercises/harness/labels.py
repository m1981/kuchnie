"""Single source for domain-value -> Polish-label mappings.

Both the writers (emit) and the golden diff (compare) consume THIS mapping;
duplicating the GrainAxis string values as literals elsewhere is how a core
rename silently degrades the oracle (harness r2 finding 4).
"""
from __future__ import annotations

from kuchnie_core.model import GrainAxis

#: Panel.grain value -> rozrys Uslojenie label.
GRAIN_LABEL: dict[str | None, str] = {
    GrainAxis.HEIGHT: "pion",
    GrainAxis.WIDTH: "poziom",
    None: "brak",
}


def grain_label(grain: str | None) -> str:
    """Label for a Panel.grain value; unknown values pass through verbatim
    so a new GrainAxis member surfaces in output instead of masquerading
    as 'brak'."""
    return GRAIN_LABEL.get(grain, grain)  # type: ignore[return-value]
