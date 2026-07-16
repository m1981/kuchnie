"""Buildability verdict — the ordered gate runner (wk-89a668a2, UC-2 step 5).

Pins the orchestration contract: one structured verdict, ordered gates
delegating to the scattered checks (tr-00421995), advisory findings that
never flip the verdict, and parked gates reported SKIPPED — not silently
absent. Rule content itself is pinned where it lives
(test_validate_gates.py, test_legrabox.py, test_cabinet_instance.py …).
"""
from kuchnie_core.buildability import (
    ADVISORY,
    BLOCKING,
    GateStatus,
    evaluate_buildability,
)
from kuchnie_core.model import CabinetInstance, Kitchen, Row

PARKED = {"G2", "G3", "G4", "G5", "G7"}


def cab(id="C1", type="dolna_drzwiowa", width=600, height=720, plinth=100):
    return CabinetInstance(
        id=id, type=type, description="t",
        width_mm=width, height_mm=height, depth_mm=560,
        body_material="P18", back_material="HDF3", front_material="F18",
        plinth_height_mm=plinth,
    )


def kitchen_with(cabinets, wall=3000):
    return Kitchen(rows=[Row(id="r1", label="A", wall_width_mm=wall,
                             wall_height_mm=2600, cabinets=cabinets)])


def gate(verdict, gate_id):
    return next(g for g in verdict.gates if g.gate_id == gate_id)


# ── clean kitchen: buildable, every executed gate passes ─────────

def test_clean_kitchen_is_buildable():
    v = evaluate_buildability(kitchen_with([
        cab("K1", width=600), cab("K2", width=800),
        cab("G1", type="gorna_drzwiowa", height=720, plinth=0)]))
    assert v.buildable
    assert v.findings == []
    executed = [g for g in v.gates if g.status is not GateStatus.SKIPPED]
    assert executed and all(g.status is GateStatus.PASSED for g in executed)


# ── blocking gates flip the verdict ──────────────────────────────

def test_broken_worktop_line_blocks():
    v = evaluate_buildability(kitchen_with([
        cab("K1", height=720), cab("K2", height=730)]))
    assert not v.buildable
    g1 = gate(v, "G1")
    assert g1.status is GateStatus.FAILED
    f = g1.findings[0]
    assert f.severity == BLOCKING and f.ref == "A" and "G1" in f.message


def test_undecomposable_type_blocks_at_m4():
    k = kitchen_with([cab("K1")])
    k.rows[0].cabinets[0].type = "dolna_karuzela"  # no decomposer registered
    v = evaluate_buildability(k)
    m4 = gate(v, "M4")
    assert m4.status is GateStatus.FAILED
    assert m4.findings[0].ref == "K1"
    assert not v.buildable


def test_mutated_cabinet_caught_by_m1():
    k = kitchen_with([cab("K1")])
    k.rows[0].cabinets[0].width_mm = 20  # post-init mutation skips __post_init__
    v = evaluate_buildability(k)
    m1 = gate(v, "M1")
    assert m1.status is GateStatus.FAILED and m1.findings[0].ref == "K1"
    assert not v.buildable


def test_invalid_legrabox_nl_blocks_at_m3():
    c = cab("L1", type="dolna_legrabox")
    c.drawers = [{"id": "s1", "height_code": "C", "nl": 999}]
    v = evaluate_buildability(kitchen_with([c]))
    m3 = gate(v, "M3")
    assert m3.status is GateStatus.FAILED
    assert m3.findings[0].ref == "L1/s1"
    assert not v.buildable


# ── advisory findings never flip the verdict ─────────────────────

def test_advisory_width_reported_but_kitchen_buildable():
    v = evaluate_buildability(kitchen_with([cab("K1", width=611)]))
    assert v.buildable
    advisories = [f for f in v.findings if f.severity == ADVISORY]
    assert len(advisories) == 1
    assert advisories[0].gate_id == "WSTD" and advisories[0].ref == "K1"
    assert gate(v, "WSTD").status is GateStatus.PASSED


# ── parked / unavailable gates are SKIPPED, not absent ───────────

def test_parked_gates_reported_skipped_with_reason():
    v = evaluate_buildability(kitchen_with([cab("K1")]))
    skipped = {g.gate_id: g for g in v.skipped}
    assert PARKED <= set(skipped)
    assert all(g.skip_reason for g in skipped.values())


def test_manifest_gate_skipped_without_manifest():
    v = evaluate_buildability(kitchen_with([cab("K1")]))
    m5 = gate(v, "M5")
    assert m5.status is GateStatus.SKIPPED and "manifest" in m5.skip_reason


def test_manifest_gate_runs_and_blocks_with_manifest():
    manifest = {
        "objects": [{
            "name": "K1_carcass",
            "expected_dimensions_mm": {"width": 600},
            "local_dimensions_mm": [590, 560, 720],
            "vertex_count": 8, "face_count": 6,
        }],
        "settings": {}, "layout": {},
    }
    v = evaluate_buildability(kitchen_with([cab("K1")]), manifest=manifest)
    m5 = gate(v, "M5")
    assert m5.status is GateStatus.FAILED
    assert m5.findings[0].ref == "K1_carcass"
    assert not v.buildable


# ── verdict shape ────────────────────────────────────────────────

def test_findings_ordered_blocking_first():
    v = evaluate_buildability(kitchen_with([
        cab("K1", width=611, height=720), cab("K2", height=730)]))
    severities = [f.severity for f in v.findings]
    assert BLOCKING in severities and ADVISORY in severities
    assert severities.index(ADVISORY) > max(
        i for i, s in enumerate(severities) if s == BLOCKING)


def test_gate_order_is_stable():
    v = evaluate_buildability(kitchen_with([cab("K1")]))
    assert [g.gate_id for g in v.gates] == [
        "M1", "M2", "M3", "M4", "M5",
        "FIT", "WSTD", "G1", "G2", "G3", "G4", "G5", "G6", "G7",
    ]


def test_to_dict_round_trips_the_essentials():
    v = evaluate_buildability(kitchen_with([cab("K1", height=730),
                                            cab("K2", height=720)]))
    d = v.to_dict()
    assert d["buildable"] is False
    assert len(d["gates"]) == len(v.gates)
    assert d["gates"][0]["gate"] == "M1"
    assert d["findings"][0]["severity"] == BLOCKING
    skipped = [g for g in d["gates"] if g["status"] == "skipped"]
    assert skipped and all(g["skip_reason"] for g in skipped)
