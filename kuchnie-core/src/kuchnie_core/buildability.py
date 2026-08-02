"""Buildability verdict — ordered gate runner over the scattered checks.

UC-2 step 5 (wk-89a668a2): the system validates the kitchen and issues a
SINGLE structured verdict before any production artifact is emitted.
Until now the checks were scattered (tr-00421995) across five modules —
validator.py, legrabox.py, kitchen.py, model.py, construction.py — with
no module running them as ordered gates.

This module ORCHESTRATES. Apart from the row rules it now hosts (see the
design-legality family below), every gate delegates to the existing check
where it lives today:

  Mechanical family (scrap prevention):
    M1  cabinet dimensional sanity      → model.CabinetInstance.validate
    M2  construction width fit          → construction.ConstructionMethod
                                          .validate_cabinet_width
    M3  drawer system availability      → legrabox.validate_height_nl /
                                          validate_capacity
    M4  decomposable to panels          → decomposer.decompose raise-sites
    M5  geometry manifest checks        → validator.validate_manifest
                                          (SKIPPED when no manifest given)

  Design-legality family (playbook Phase-8 gate,
  docs/l-kitchen-design-playbook.md §6) — the today-feasible slice
  (wk-bae72832) is encoded by ``row_findings`` below, the one rule set
  this module owns outright; kitchen.validate_rows renders it as strings:
    FIT  cabinets fit their rows
    WSTD standard-width composition     (advisory — never flips verdict)
    G1   one worktop line per run
    G6   plinth line unbroken

  Parked design gates (G2/G3/G4/G5/G7) need model support the Kitchen
  does not carry yet; they are reported as explicitly SKIPPED with the
  missing-support reason — never silently absent.

Findings order by scrap severity (UC-2 ext 5a): blocking before advisory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .findings import ADVISORY, BLOCKING, Finding, GateStatus
from .model import Kitchen
from .standards import KitchenStandards


@dataclass
class GateResult:
    """One gate's run record — present for EVERY gate, skipped included."""
    gate_id: str
    name: str
    status: GateStatus
    findings: list[Finding] = field(default_factory=list)
    skip_reason: str = ""

    def to_dict(self) -> dict:
        d = {
            "gate": self.gate_id,
            "name": self.name,
            "status": self.status.value,
            "findings": [f.to_dict() for f in self.findings],
        }
        if self.skip_reason:
            d["skip_reason"] = self.skip_reason
        return d


@dataclass
class BuildabilityVerdict:
    """The single verdict UC-2 step 5 asks for."""
    buildable: bool
    gates: list[GateResult] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        """All findings across gates, blocking first (UC-2 ext 5a)."""
        flat = [f for g in self.gates for f in g.findings]
        return sorted(flat, key=lambda f: f.severity != BLOCKING)

    @property
    def skipped(self) -> list[GateResult]:
        return [g for g in self.gates if g.status is GateStatus.SKIPPED]

    def to_dict(self) -> dict:
        return {
            "buildable": self.buildable,
            "gates": [g.to_dict() for g in self.gates],
            "findings": [f.to_dict() for f in self.findings],
        }


# ── Parked design gates ─────────────────────────────────────────
# Playbook gates that need model support Kitchen/Row do not carry yet
# (wk-89a668a2). Reported SKIPPED so the verdict is honest about what
# it did NOT check.

_PARKED_GATES: list[tuple[str, str, str]] = [
    ("G2", "corner fillers present on both runs",
     "model carries no L-run adjacency (which rows meet at a corner)"),
    ("G3", "door/drawer collision walk-through",
     "model carries no door-swing or room-door positions"),
    ("G4", "appliance cutouts match model sheets",
     "model carries no appliance positions or model-sheet data"),
    ("G5", "work triangle + landings legality",
     "model carries no appliance positions"),
    ("G7", "worktop joint clear of cutouts; gas/hood distances",
     "model carries no worktop cutout positions"),
]


def _skipped(gate_id: str, name: str, reason: str) -> GateResult:
    return GateResult(gate_id, name, GateStatus.SKIPPED, [], reason)


def _ran(gate_id: str, name: str, findings: list[Finding]) -> GateResult:
    blocked = any(f.severity == BLOCKING for f in findings)
    status = GateStatus.FAILED if blocked else GateStatus.PASSED
    return GateResult(gate_id, name, status, findings)


# ── Row-derived gates (FIT / WSTD / G1 / G6) ────────────────────
# row_findings owns these rules and emits Finding objects with gate ids
# attached (wk-acc8e094) — we bucket, never parse strings.


@dataclass(frozen=True)
class HeightSet:
    """Decided per-project height lines (playbook Phase 1), supplied by
    the consumer that stores them (kitchen-erp ProjectDefaults,
    wk-5b929a7c) — kuchnie-core defines its own carrier so the dependency
    stays one-way (ERP imports core, never the reverse).

    worktop_height_mm: the decided worktop line, floor to worktop top.
    worktop_thickness_mm: top thickness used to read a leg's actual line
        off its base carcasses (plinth + carcass + top); playbook default
        38 — the model's WorktopSegment carries per-row geometry, this is
        the project-line convention.
    """
    worktop_height_mm: float | None = None
    worktop_thickness_mm: float = 38.0


def row_findings(
    kitchen: Kitchen, heights: HeightSet | None = None
) -> list[Finding]:
    """The design-legality slice of the buildability gate, structured
    (wk-acc8e094): each rule emits a Finding with its gate id, severity
    and offending ref — the runner buckets these directly, no string
    parsing. ``kitchen.validate_rows`` renders the same findings as
    strings.

    Rules (today-feasible playbook Phase-8 slice, wk-89a668a2):

    * FIT  — cabinets fit their rows (blocking).
    * G1   — one worktop line per run: base cabinets (plinth > 0) in a
      row must share total height_mm (blocking). With a ``heights``
      set supplied (wk-5b929a7c), G1 ADDITIONALLY compares each row's
      (leg's) worktop line — plinth + carcass + top thickness — against
      the decided ``worktop_height_mm`` and reports a diverging leg
      (finding, not exception; ``heights=None`` keeps exactly today's
      behaviour).
    * G6   — plinth line unbroken: base cabinets in a row must share
      plinth_height_mm (blocking).
    * WSTD — run composition uses standard widths (KitchenStandards;
      corner cabinets exempt — they follow their own 1000–1300 rule;
      wall irregularity is absorbed by one filler at the wall end).
      Advisory — it flags, it does not fail.

    G2/G3/G4/G5/G7 of the gate need model support the Row does not carry
    yet (L-adjacency, appliance positions, cutout positions) and stay
    with wk-89a668a2.
    """
    findings: list[Finding] = []
    std = KitchenStandards()
    for row in kitchen.rows:
        used = row.used_width_mm()
        if used > row.wall_width_mm:
            findings.append(Finding(
                "FIT", BLOCKING,
                f"Row '{row.label}': cabinets use {used}mm "
                f"but wall is only {row.wall_width_mm}mm",
                row.label,
            ))
        remaining = row.remaining_mm()
        if remaining < 0:
            findings.append(Finding(
                "FIT", BLOCKING,
                f"Row '{row.label}': {-remaining}mm overflows the wall",
                row.label,
            ))

        base = [c for c in row.cabinets if c.plinth_height_mm > 0]
        carcass_heights = {c.height_mm for c in base}
        if len(carcass_heights) > 1:
            findings.append(Finding(
                "G1", BLOCKING,
                f"Row '{row.label}': G1 — worktop line broken, base cabinet "
                f"heights differ {sorted(carcass_heights)}mm (playbook "
                f"Phase 1: one height line per run)",
                row.label,
            ))
        if (heights is not None
                and heights.worktop_height_mm is not None and base):
            decided = heights.worktop_height_mm
            top = heights.worktop_thickness_mm
            lines = sorted({
                c.plinth_height_mm + c.height_mm + top for c in base
            })
            # 1e-3mm tolerance: absorbs float noise while staying far
            # below carpentry precision (wk-5b929a7c red-team finding —
            # sub-micron divergences rendered self-identical messages).
            diverging = [line for line in lines
                         if abs(line - decided) > 1e-3]
            if diverging:
                findings.append(Finding(
                    "G1", BLOCKING,
                    f"Row '{row.label}': G1 — worktop line off the decided "
                    f"project line: plinth + carcass + {top:g}mm top gives "
                    f"{', '.join(f'{line:g}' for line in diverging)}mm, "
                    f"decided worktop_height_mm is {decided:g}mm (playbook "
                    f"Phase 1: one project-wide line across legs; "
                    f"720 carcass + 100..150 plinth + 38 top ⇒ 850..910)",
                    row.label,
                ))
        plinths = {c.plinth_height_mm for c in base}
        if len(plinths) > 1:
            findings.append(Finding(
                "G6", BLOCKING,
                f"Row '{row.label}': G6 — plinth line broken, plinth heights "
                f"differ {sorted(plinths)}mm",
                row.label,
            ))
        for c in row.cabinets:
            if "narozna" in c.type:
                continue
            if not std.is_standard_width(c.width_mm):
                findings.append(Finding(
                    "WSTD", ADVISORY,
                    f"advisory: Row '{row.label}': cabinet {c.id} width "
                    f"{c.width_mm}mm is non-standard (playbook Phase 4: "
                    f"standard widths only; absorb wall irregularity with "
                    f"one filler at the wall end)",
                    c.id,
                ))
    return findings


def _row_gate_buckets(
    kitchen: Kitchen,
    heights: HeightSet | None = None,
) -> dict[str, list[Finding]]:
    buckets: dict[str, list[Finding]] = {
        "FIT": [], "WSTD": [], "G1": [], "G6": [],
    }
    for finding in row_findings(kitchen, heights=heights):
        if finding.gate_id not in buckets:
            raise ValueError(
                f"row_findings emitted unknown gate id {finding.gate_id!r} — "
                f"add it to _row_gate_buckets AND a gates.append in "
                f"evaluate_buildability, or the finding would be dropped"
            )
        buckets[finding.gate_id].append(finding)
    return buckets


# ── Mechanical gates (M1–M5) ────────────────────────────────────

def _gate_cabinet_sanity(kitchen: Kitchen) -> list[Finding]:
    """M1 — model.CabinetInstance.validate per cabinet.

    __post_init__ already rejects invalid construction; this catches
    instances mutated or deserialized after that point.
    """
    findings = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            for err in cab.validate():
                findings.append(Finding("M1", BLOCKING, err, cab.id))
    return findings


def _gate_construction_fit(kitchen: Kitchen) -> list[Finding]:
    """M2 — construction.ConstructionMethod.validate_cabinet_width."""
    from .catalog import method_from_cab

    findings = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            method = method_from_cab(cab)
            for err in method.validate_cabinet_width(cab.width_mm):
                findings.append(Finding("M2", BLOCKING, err, cab.id))
    return findings


def _gate_drawer_systems(kitchen: Kitchen) -> list[Finding]:
    """M3 — legrabox.validate_height_nl / validate_capacity per drawer.

    Defaults mirror catalog.decompose_dolna_legrabox so the gate judges
    the same configuration the decomposer will use.
    """
    from .legrabox import validate_capacity, validate_height_nl

    findings = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            if cab.type != "dolna_legrabox":
                continue
            for drawer in cab.drawers:
                ref = f"{cab.id}/{drawer.get('id', '?')}"
                height_code = drawer.get("height_code", "C")
                nl = drawer.get("nl", 500)
                capacity = drawer.get("capacity_kg", 40)
                for err in validate_height_nl(height_code, nl):
                    findings.append(Finding("M3", BLOCKING, err, ref))
                for err in validate_capacity(nl, capacity):
                    findings.append(Finding("M3", BLOCKING, err, ref))
    return findings


def _gate_decomposable(kitchen: Kitchen) -> list[Finding]:
    """M4 — every cabinet must decompose to panels.

    Wraps the raise-sites behind decomposer.decompose (unknown type,
    corner-blind opening too narrow, drawer-box geometry) — UC-2 minimal
    guarantee: nothing is emitted for types that cannot be decomposed.
    """
    from .decomposer import decompose

    findings = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            try:
                decompose(cab)
            except (ValueError, KeyError) as exc:
                findings.append(Finding("M4", BLOCKING, str(exc), cab.id))
    return findings


def _gate_manifest(manifest: dict) -> list[Finding]:
    """M5 — validator.validate_manifest over the geometry manifest."""
    from .validator import validate_manifest

    findings = []
    result = validate_manifest(manifest)
    for issue in result.issues:
        severity = BLOCKING if issue.severity == "error" else ADVISORY
        findings.append(Finding(
            "M5", severity,
            f"{issue.check}: {issue.message}",
            issue.object_name,
        ))
    return findings


# ── The runner ──────────────────────────────────────────────────

def evaluate_buildability(
    kitchen: Kitchen,
    manifest: dict | None = None,
    heights: HeightSet | None = None,
) -> BuildabilityVerdict:
    """Run every buildability gate in order and issue ONE verdict.

    Args:
        kitchen:  the Kitchen to judge.
        manifest: optional geometry manifest (validator.py's input);
                  without it gate M5 is SKIPPED, not silently dropped.
        heights:  optional HeightSet with the decided project
                  height lines (wk-5b929a7c) — G1 then also compares
                  legs against worktop_height_mm; omitted keeps today's
                  intra-row-only G1.

    Returns:
        BuildabilityVerdict — buildable iff no gate FAILED. Advisory
        findings and SKIPPED gates never flip the verdict.
    """
    gates: list[GateResult] = [
        _ran("M1", "cabinet dimensional sanity",
             _gate_cabinet_sanity(kitchen)),
        _ran("M2", "construction width fit",
             _gate_construction_fit(kitchen)),
        _ran("M3", "drawer system availability",
             _gate_drawer_systems(kitchen)),
        _ran("M4", "decomposable to panels",
             _gate_decomposable(kitchen)),
    ]

    if manifest is None:
        gates.append(_skipped(
            "M5", "geometry manifest checks",
            "no geometry manifest supplied (extraction output required)"))
    else:
        gates.append(_ran("M5", "geometry manifest checks",
                          _gate_manifest(manifest)))

    buckets = _row_gate_buckets(kitchen, heights=heights)
    gates.append(_ran("FIT", "cabinets fit their rows", buckets["FIT"]))
    gates.append(_ran("WSTD", "standard-width composition (advisory)",
                      buckets["WSTD"]))
    gates.append(_ran("G1", "one worktop line per run", buckets["G1"]))

    parked = dict.fromkeys(("G2", "G3", "G4", "G5"))
    for gate_id, name, reason in _PARKED_GATES:
        if gate_id in parked:
            gates.append(_skipped(gate_id, name, reason))

    gates.append(_ran("G6", "plinth line unbroken", buckets["G6"]))

    g7 = next(p for p in _PARKED_GATES if p[0] == "G7")
    gates.append(_skipped(*g7))

    buildable = not any(g.status is GateStatus.FAILED for g in gates)
    return BuildabilityVerdict(buildable=buildable, gates=gates)


# ── Emission gating (UC-2 ext 5a, wk-cb6a17c8) ──────────────────

class BuildabilityError(ValueError):
    """Raised by emission doorways when the verdict is FAILED.

    Carries the full verdict so callers can list findings by scrap
    severity instead of re-running the gates.
    """

    def __init__(self, verdict: BuildabilityVerdict):
        self.verdict = verdict
        blocking = [f for f in verdict.findings if f.severity == BLOCKING]
        lines = "; ".join(
            f"[{f.gate_id}] {f.message}" for f in blocking[:5])
        more = f" (+{len(blocking) - 5} more)" if len(blocking) > 5 else ""
        super().__init__(
            f"kitchen is not buildable — {len(blocking)} blocking "
            f"finding(s): {lines}{more}"
        )


def require_buildable(
    kitchen: Kitchen,
    manifest: dict | None = None,
    verdict: BuildabilityVerdict | None = None,
) -> BuildabilityVerdict:
    """The emission doorway: no production artifact may be written for a
    kitchen whose verdict FAILED (UC-2 ext 5a — no override flag by
    design). Pass a precomputed ``verdict`` to avoid re-running gates;
    otherwise one is evaluated here.

    Returns the (passing) verdict so emitters can attach it to output.
    Raises BuildabilityError when the verdict is FAILED.
    """
    if verdict is None:
        verdict = evaluate_buildability(kitchen, manifest)
    if not verdict.buildable:
        raise BuildabilityError(verdict)
    return verdict
