# tests/test_drawer_substitution.py
"""Citing tests for kitchen-erp/docs/specs/drawer-substitution.md
(SC-drsub-001..006) -- UC-1 ext 1a, the drawer-system axis of the
budget walk. `tl2 mirror --manifest
kitchen-erp/docs/specs/drawer-substitution.sc.txt --root kitchen-erp`
guards the citation in both directions; the SC id sits in the FIRST
line of each test's docstring.

House style (test_domain_adapter.py): expectations are hand-computed
from the Blum planning data and the owner-ruled widelka parameters,
never derived by running the code under test.

Imports are FUNCTION-LOCAL throughout, deliberately: `tl2 vacuity`
overlays this one file onto a pre-change base tree, and a module-level
import of a module absent at that base would die at collection
(INCONCLUSIVE) instead of failing at assertion level (PROVEN). Bases
used per test:
  SC-001/002: ca3721f (pre kuchnie-27b -- ERP drilled ONE legrabox
              screw and spelled height code "M" for every system)
  SC-004:     4b39f44~1 (before the derivation increment existed)
  SC-003/005/006: the commit preceding the one that lands this file
              (variant_pricing.py absent -> red).

Hand-computed geometry, D60 drawer cabinet 600W x 720H x 510D, 3
drawers, 18mm sides/bottom (same arithmetic as test_variants.py):
  KB = 600 - 2*18 = 564
  TANDEMBOX antaro: LW = 564 - 2*12.5 = 539; back panel 501 x 89  (M)
  MERIVOBOX:        LW = 564 - 2*12.5 = 539; back panel 501 x 63  (M)
  LEGRABOX:         LW = 564 - 2*13   = 538; back panel 500 x 148 (C)
  Runner screw axis y: 55, 55 + 608/3, 55 + 2*608/3 (plinth 100,
  4 x 3mm gaps); x offsets from the front edge: generic chart = the
  first mark only (46); LEGRABOX NL500 = 46/78/110/398.
"""
import pytest

DRAWER_ZONE_H = 608 / 3
EXPECTED_Y = [55.0, round(55 + DRAWER_ZONE_H, 2), round(55 + 2 * DRAWER_ZONE_H, 2)]
LEGRABOX_NL500_SCREWS = [46, 78, 110, 398]

# The catalog-verified drawer-system registry (blum_drawers._SYSTEMS,
# spelled by hand -- the spec's "three selectable systems").
REGISTRY = ["tandembox_antaro", "merivobox", "legrabox"]

# Per-system pins for the same D60 stack (hand-computed above).
SYSTEM_PINS = {
    "tandembox_antaro": {
        "screws_per_runner_x": [46],
        "back_panel": (501, 89),
        "note": "TandemboxAntaro runner screw (NL=500)",
    },
    "merivobox": {
        "screws_per_runner_x": [46],
        "back_panel": (501, 63),
        "note": "Merivobox runner screw (NL=500)",
    },
    "legrabox": {
        "screws_per_runner_x": LEGRABOX_NL500_SCREWS,
        "back_panel": (500, 148),
        "note": "LEGRABOX C runner screw (NL=500)",
    },
}


def make_project():
    """D60-only project (DRAWER_BASE, 3 drawers) with full defaults."""
    from kitchen_erp.core.models import (
        Cabinet, HardwareSet, Material, Project, ProjectDefaults,
    )
    defaults = ProjectDefaults(
        corpus_mat=Material(id=1, name="Egger W980", price_per_unit=10.0, unit="m2"),
        front_mat=Material(id=2, name="Front MDF", price_per_unit=20.0, unit="m2"),
        back_mat=Material(id=3, name="HDF", price_per_unit=5.0, unit="m2"),
        edge_band_mat=Material(id=4, name="ABS", price_per_unit=1.0, unit="lm"),
        hinge_sys=HardwareSet(id=1, name="Hinge", price_per_set=2.0),
        drawer_sys=HardwareSet(id=2, name="Drawer", price_per_set=30.0),
    )
    proj = Project(customer_name="Kowalski", defaults=defaults)
    Cabinet(name="D60", type="BASE", module_kind="DRAWER_BASE",
            width_mm=600.0, height_mm=720.0, depth_mm=510.0,
            door_count=0, drawer_count=3, order_index=0, project=proj)
    return proj


def runner_ops(artifacts):
    """(panel_id, x, y, note) for every runner drilling op."""
    return [(pid, op.x_mm, round(op.y_mm, 2), op.note)
            for pid, op in artifacts.cnc_ops if op.drill_type == "runner_screw"]


def box_backs(artifacts):
    """(width, height) of every drawer-box back panel, sorted."""
    return sorted((p.width_mm, p.height_mm)
                  for r in artifacts.results for p in r.panels
                  if p.id.endswith("_back") and "_drawer_" in p.id)


def covering_price_book(artifacts, unit_price=100.0):
    """Price-book INPUT (not an expectation): every line of one
    derivation priced flat, plus the runner lines of the two systems
    the derivation did not run with, so an axis walk finds every
    candidate fully priced."""
    book = {line.name: unit_price for line in artifacts.bom_lines}
    for system in REGISTRY:
        for i in (1, 2, 3):
            book[f"Prowadnica {system} (S{i})"] = unit_price
    return book


def test_axis_switch_rederives_everything_no_predecessor_artifact_survives():
    """SC-drsub-001: switching the drawer-system axis re-derives rozrys,
    CNC ops and BOM from the single decomposition; no artifact of the
    previous system survives into the substituted variant."""
    from kitchen_erp.core.models import Variant
    from kitchen_erp.core.variant_derivation import BomLine, derive_variant

    project = make_project()
    v = Variant(name="walk", project=project)
    base_art = derive_variant(v)                    # baseline: tandembox_antaro
    v.set_overrides(drawer_system="legrabox")
    sub_art = derive_variant(v)                     # the substitution

    # Nothing of the previous system survives: no tandembox note in any
    # CNC op, no tandembox runner line in the BOM, no tandembox box back
    # (501 x 89) among the substituted box parts.
    assert all("Tandembox" not in note for *_, note in runner_ops(sub_art))
    assert all("tandembox" not in line.name for line in sub_art.bom_lines)
    assert box_backs(sub_art) == [(500, 148)] * 3   # LEGRABOX C, not (501, 89)

    # All three artifact families flipped together (one decomposition
    # feeds them all, ADR-015): CNC carries the LEGRABOX chart, BOM
    # carries the legrabox runner lines, rozrys carries the LEGRABOX box
    # cut (500-wide backs aggregated).
    assert all(note == "LEGRABOX C runner screw (NL=500)"
               for *_, note in runner_ops(sub_art))
    for i in (1, 2, 3):
        assert BomLine(f"Prowadnica legrabox (S{i})", 1, "szt") in sub_art.bom_lines
    assert any(row.width_mm == 500 for row in sub_art.rozrys_rows)

    # And the baseline itself was tandembox, so the flip is the axis
    # switch, not a fixture accident.
    assert box_backs(base_art) == [(501, 89)] * 3


def test_substitution_reaches_every_selectable_system():
    """SC-drsub-002: substitution reaches EVERY selectable system: for
    the same cabinet each of tandembox_antaro, merivobox and legrabox
    yields its own machining pattern and its own screws-per-runner
    count (the kuchnie-c7l regression class, pinned)."""
    from kuchnie_core import DrawerSystemFactory
    from kitchen_erp.core.models import Variant
    from kitchen_erp.core.variant_derivation import derive_variant

    # "Every selectable system" is the factory registry, and it is
    # exactly the spec's three.
    assert DrawerSystemFactory.list_ids() == REGISTRY

    project = make_project()
    patterns = {}
    for system in REGISTRY:
        v = Variant(name=f"axis-{system}", project=project)
        v.set_overrides(drawer_system=system)
        art = derive_variant(v)
        pins = SYSTEM_PINS[system]

        # Full per-system drilling pattern: each of the 3 runners drills
        # this system's OWN x offsets at the stack heights, on both side
        # panels -- the 2026-08-02 regression drilled the default
        # system's pattern for two of three (kuchnie-c7l class).
        expected = [(f"erp-D60_{side}", x, y, pins["note"])
                    for side in ("left", "right") for y in EXPECTED_Y
                    for x in pins["screws_per_runner_x"]]
        assert runner_ops(art) == expected

        # Box parts are the system's own too (LW and back height).
        assert box_backs(art) == [pins["back_panel"]] * 3
        patterns[system] = (tuple(runner_ops(art)), tuple(box_backs(art)))

    # The three patterns are mutually distinct -- a substitution that
    # silently reused another system's artifacts could not pass this.
    assert len(set(patterns.values())) == 3


def test_substituted_variant_priced_both_tiers_and_walk_terminates():
    """SC-drsub-003: a substituted variant is priced in both tiers, and
    the budget walk terminates: either a variant with price <= the
    client's budget, or an explicit "no fit on this axis" -- never a
    silent dead end."""
    from kitchen_erp.core.models import Variant
    from kitchen_erp.core.variant_derivation import derive_variant
    from kitchen_erp.core.variant_pricing import walk_drawer_axis

    project = make_project()
    v = Variant(name="walk", project=project)
    book = covering_price_book(derive_variant(v))

    # Generous budget: the walk lands on a fitting candidate, priced in
    # both widelka tiers (od < do by the owner margins 0.95/1.15 + VAT,
    # ruled 2026-08-02 -- the board never shows a point estimate).
    result = walk_drawer_axis(v, budget_brutto=1_000_000.0, price_book=book)
    assert result.fit is not None and not result.fit.rejected
    assert not result.no_fit_on_axis
    assert result.fit.price.od_brutto <= 1_000_000.0
    assert 0 < result.fit.price.od_brutto < result.fit.price.do_brutto
    assert result.fit.price.incomplete is False

    # Impossible budget: the walk still terminates, names every candidate
    # it tried (all three registry systems), and says "no fit on this
    # axis" explicitly -- a silent dead end would show as fit=None with
    # nothing else to read.
    result = walk_drawer_axis(v, budget_brutto=1.0, price_book=book)
    assert result.no_fit_on_axis is True and result.fit is None
    assert sorted(c.system for c in result.candidates) == sorted(REGISTRY)
    assert all(c.price is not None or c.rejected for c in result.candidates)

    # The walk proposes; the board applies: the variant's own axis is
    # left where it was.
    assert v.drawer_system is None


def test_invalid_stack_after_substitution_is_rejected_not_redimensioned():
    """SC-drsub-004: a drawer stack that violates NL/height fit after
    substitution is REJECTED by per-cabinet validate() (UC-1 ext 3a) --
    rejection, not silent re-dimensioning."""
    from kuchnie_core.decomposer import decompose
    from kuchnie_core.model import CabinetInstance
    from kitchen_erp.core.variant_derivation import _attach_drawer_boxes

    def d60_with(height_code):
        # "wysokosc" pins the zone height so the stack itself is
        # geometrically fine under the ORIGINAL system; only the
        # substituted system lacks the height code.
        return CabinetInstance(
            id="sc4", type="dolna_szufladowa", description="SC-004",
            width_mm=600, height_mm=720, depth_mm=510,
            body_material="Egger W980", back_material="HDF",
            front_material="Front MDF",
            drawers=[{"id": "S1", "typ": "tandembox_antaro",
                      "wysokosc": 606, "height_code": height_code}],
        )

    # "D" is a TANDEMBOX-only code: valid before, invalid after a
    # substitution to MERIVOBOX (codes N/M/E).
    inst = d60_with("D")
    result = decompose(inst)
    n_before = len(result.panels)
    with pytest.raises(ValueError, match="[Uu]nknown height code"):
        _attach_drawer_boxes(result, inst, "merivobox")
    # Rejection, not re-dimensioning: no drawer-box panel of some
    # fallback height was quietly emitted.
    assert len(result.panels) == n_before

    # And the mirror direction: "E" is MERIVOBOX-only, TANDEMBOX
    # (codes N/M/D) must reject it the same way.
    inst = d60_with("E")
    result = decompose(inst)
    n_before = len(result.panels)
    with pytest.raises(ValueError, match="[Uu]nknown height code"):
        _attach_drawer_boxes(result, inst, "tandembox_antaro")
    assert len(result.panels) == n_before


def test_unpriced_substitution_line_is_flagged_never_omitted():
    """SC-drsub-005: an unpriced line produced by substitution surfaces
    flagged on the board; it is never silently omitted from the total
    (the UC-1 ext 2a pattern)."""
    from kitchen_erp.core.models import Variant
    from kitchen_erp.core.variant_derivation import derive_variant
    from kitchen_erp.core.variant_pricing import price_variant

    project = make_project()
    v = Variant(name="mv", project=project)
    v.set_overrides(drawer_system="merivobox")
    art = derive_variant(v)

    full_book = covering_price_book(art)
    # The substitution produced merivobox runner lines the price book
    # does not know -- exactly the board's unpriced-line moment.
    missing_book = {k: p for k, p in full_book.items()
                    if not k.startswith("Prowadnica merivobox")}

    priced = price_variant(art, missing_book)
    runner_lines = [l for l in priced.lines
                    if l.name.startswith("Prowadnica merivobox")]

    # The lines SURFACE, flagged -- not dropped from the result.
    assert len(runner_lines) == 3
    assert all(l.priced is False and l.unit_price is None for l in runner_lines)
    assert priced.incomplete is True

    # And the omission from the total is loud, not silent: against the
    # fully-covered book the difference is exactly the three runner
    # lines at 100.0 each (hand-computed: 3 x 1szt x 100.0).
    assert price_variant(art, full_book).incomplete is False
    assert price_variant(art, full_book).total_net - priced.total_net == 300.0


def test_substitution_proposals_come_only_from_the_registry():
    """SC-drsub-006: substitution proposals come only from
    catalog-verified registry entries; a free-typed replacement is not
    offered."""
    from kuchnie_core import DrawerSystemFactory
    from kitchen_erp.core.models import Variant
    from kitchen_erp.core.variant_derivation import derive_variant
    from kitchen_erp.core.variant_pricing import walk_drawer_axis

    project = make_project()
    v = Variant(name="reg", project=project)

    # A free-typed replacement is refused at the only mutation doorway.
    with pytest.raises(ValueError, match="drawer system"):
        v.set_overrides(drawer_system="hafele_matrix")
    assert v.overrides() == {}

    # The walk's proposals are the registry, whole and nothing else.
    book = covering_price_book(derive_variant(v))
    result = walk_drawer_axis(v, budget_brutto=1_000_000.0, price_book=book)
    proposed = [c.system for c in result.candidates]
    assert sorted(proposed) == sorted(DrawerSystemFactory.list_ids())
    assert all(system in REGISTRY for system in proposed)
