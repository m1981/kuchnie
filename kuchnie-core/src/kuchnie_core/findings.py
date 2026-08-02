"""Finding vocabulary — the shared language of the gate layer.

`Finding`, `GateStatus` and the two severities are spoken by BOTH the
gate layer (`buildability.py`, which runs the rules) and the aggregation
layer (`kitchen.py`, which renders them) — the property of neither
(kuchnie-5un). They live here, in a leaf module that imports nothing
from `kuchnie_core`, so either side may import them at module level
without the two ends of the package reaching for each other.

Nothing in this module knows what a kitchen is; that is the point.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Finding severities. Advisory findings flag; they never fail a gate
# or flip the verdict.
BLOCKING = "blocking"
ADVISORY = "advisory"


class GateStatus(str, Enum):
    """Outcome of one gate run."""
    PASSED = "passed"    # ran; no blocking findings (advisories allowed)
    FAILED = "failed"    # ran; at least one blocking finding
    SKIPPED = "skipped"  # could not run; skip_reason says why


@dataclass
class Finding:
    """One issue raised by one gate."""
    gate_id: str
    severity: str        # BLOCKING | ADVISORY
    message: str
    ref: str = ""        # offending cabinet/drawer/row/panel id ("" = kitchen-wide)

    def to_dict(self) -> dict:
        return {
            "gate": self.gate_id,
            "severity": self.severity,
            "message": self.message,
            "ref": self.ref,
        }
