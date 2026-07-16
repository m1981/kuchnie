"""Buildability verdict — ordered gate runner over the scattered checks.

UC-2 step 5 (wk-89a668a2): the system validates the kitchen and issues a
SINGLE structured verdict before any production artifact is emitted.
Until now the checks were scattered (tr-00421995) across five modules —
validator.py, legrabox.py, kitchen.py, model.py, construction.py — with
no module running them as ordered gates.

This module ORCHESTRATES; it owns no rules. Every gate delegates to the
existing check where it lives today:

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
  docs/l-kitchen-design-playbook.md §6) — delegated to
  kitchen.validate_rows, which encodes the today-feasible slice
  (wk-bae72832):
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

import re
from dataclasses import dataclass, field
from enum import Enum

from .model import Kitchen

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
# kitchen.validate_rows owns these rules; it returns flat strings with
# stable markers ("advisory:" prefix, "G1 —", "G6 —"). We classify,
# not re-check.

_ROW_RE = re.compile(r"Row '([^']+)'")
_CAB_RE = re.compile(r"cabinet (\S+) width")


def _row_ref(message: str) -> str:
    cab = _CAB_RE.search(message)
    if cab:
        return cab.group(1)
    row = _ROW_RE.search(message)
    return row.group(1) if row else ""


def _row_gate_buckets(kitchen: Kitchen) -> dict[str, list[Finding]]:
    from .kitchen import validate_rows

    buckets: dict[str, list[Finding]] = {
        "FIT": [], "WSTD": [], "G1": [], "G6": [],
    }
    for message in validate_rows(kitchen):
        if message.startswith("advisory:"):
            buckets["WSTD"].append(
                Finding("WSTD", ADVISORY, message, _row_ref(message)))
        elif "G1 —" in message:
            buckets["G1"].append(
                Finding("G1", BLOCKING, message, _row_ref(message)))
        elif "G6 —" in message:
            buckets["G6"].append(
                Finding("G6", BLOCKING, message, _row_ref(message)))
        else:
            buckets["FIT"].append(
                Finding("FIT", BLOCKING, message, _row_ref(message)))
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
    from .catalog import _method_from_cab

    findings = []
    for row in kitchen.rows:
        for cab in row.cabinets:
            method = _method_from_cab(cab)
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
) -> BuildabilityVerdict:
    """Run every buildability gate in order and issue ONE verdict.

    Args:
        kitchen:  the Kitchen to judge.
        manifest: optional geometry manifest (validator.py's input);
                  without it gate M5 is SKIPPED, not silently dropped.

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

    buckets = _row_gate_buckets(kitchen)
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
