"""ADR-012 §2 — ``MachiningOp.face`` + ``MachiningOp.drill_type``.

Motivation: downstream CAM code needs to distinguish operations by face
of the panel (which face of the board goes into the CNC nest first) and
by drill type (5mm shelf pin vs 35mm hinge cup vs runner screw). Both
fields are added with safe defaults so every existing ``MachiningOp(...)``
constructor keeps working unchanged.

Locked-in contract:

  * ``face`` defaults to ``"inside"`` \u2014 the most common case (holes drilled
    from the inside face of a carcass panel).
  * ``drill_type`` defaults to ``""`` \u2014 explicitly unclassified. Downstream
    code that filters by drill_type must handle the empty case.
  * Both fields are open strings, not enums. ADR-012 \u00a72 rationale:
    keeps model lean, lets kitchen-cam extend the vocabulary without a
    core dependency inversion.
  * LEGRABOX runner-mount ops (currently the only ops kuchnie_core
    produces) implicitly get ``face="inside"`` via the default \u2014 that
    matches how the screws are actually driven and is locked here.
"""

from __future__ import annotations

from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import load_cabinet
from kuchnie_core.model import MachiningOp


# ── Field defaults ──────────────────────────────────────────────

class TestMachiningOpDefaults:
    """New fields default to safe, existing-code-preserving values."""

    def test_face_defaults_to_inside(self):
        op = MachiningOp(type="drill")
        assert op.face == "inside"

    def test_drill_type_defaults_to_empty(self):
        op = MachiningOp(type="drill")
        assert op.drill_type == ""

    def test_existing_kwargs_still_work(self):
        # Guard: adding fields must not break the pre-ADR-012 constructor.
        op = MachiningOp(
            type="drill", x_mm=32, y_mm=46, diameter_mm=5, note="test",
        )
        assert op.type == "drill"
        assert op.x_mm == 32
        assert op.y_mm == 46
        assert op.face == "inside"
        assert op.drill_type == ""


# ── Explicit assignment ─────────────────────────────────────────

class TestMachiningOpExplicit:
    """Fields accept the vocabulary enumerated in ADR-012 §2 (open strings)."""

    def test_can_set_face(self):
        for face in ("inside", "outside", "front", "back"):
            op = MachiningOp(type="drill", face=face)
            assert op.face == face

    def test_can_set_drill_type(self):
        for dt in (
            "system32", "hinge_cup", "hinge_screw", "hinge_dowel",
            "dowel_connector", "minifix", "handle", "shelf_pin",
        ):
            op = MachiningOp(type="drill", drill_type=dt)
            assert op.drill_type == dt

    def test_drill_type_is_open_vocabulary(self):
        # ADR-012 §2: "drill_type remains a string (not enum) to keep the
        # model lean and let kitchen-cam extend the vocabulary without
        # a core dependency inversion." So novel values must be accepted.
        op = MachiningOp(type="drill", drill_type="future_cam_extension")
        assert op.drill_type == "future_cam_extension"


# ── LEGRABOX runner-mount ops \u2014 real decomposer output ─────────

class TestLegraboxRunnerOpDefaults:
    """LEGRABOX runner-mount screws are drilled from the inside face and
    classified ``drill_type="runner_screw"`` so downstream CAM can route
    them without string-matching on ``note`` (ADR-012 \u00a72).
    """

    def test_runner_ops_are_classified_and_inside_face(self):
        from pathlib import Path
        fixtures = Path(__file__).resolve().parent.parent / "fixtures"
        cab = load_cabinet(fixtures / "K02_legrabox.yaml")
        result = decompose(cab)

        side_panels = [p for p in result.panels if p.id.endswith("_left") or p.id.endswith("_right")]
        assert side_panels, "K02 LEGRABOX must produce side panels with runner ops"

        all_ops = [op for p in side_panels for op in p.machining_ops]
        assert all_ops, "LEGRABOX side panels must carry runner-mount drill ops"

        for op in all_ops:
            assert op.face == "inside", (
                f"LEGRABOX runner ops drilled from inside face; got face={op.face!r}"
            )
            assert op.drill_type == "runner_screw", (
                f"runner ops must be routable by drill_type; got {op.drill_type!r}"
            )
