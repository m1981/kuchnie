# tests/test_variants.py
"""wk-593a317b increment 1: the variant model on the Project spine.

Design record: docs/specs/purchasing-variants.md -- "Variants are
parameters, not copies" + the variant lifecycle state machine
(Draft -> Frozen -> Sent -> Offer-received -> ACCEPTED -> Ordered,
forward-only, ACCEPT locks).

Expectations are hand-computed from VARIANT_STATE_SEQUENCE and the
model's own validation contract, never derived by running the code
under test (house style, see test_domain_adapter.py).
"""
import pytest
from sqlmodel import select

from kitchen_erp.core.models import (
    CORNER_MECHANISMS,
    DEFAULT_VARIANT_STATE,
    HINGE_CLASSES,
    Cabinet,
    HardwareSet,
    Material,
    Project,
    ProjectDefaults,
    VARIANT_STATE_SEQUENCE,
    Variant,
    VariantLockedError,
    VariantStateError,
)
from kitchen_erp.core.variant_derivation import (
    BomLine,
    derive_variant,
    resolve_parameters,
)


def make_variant(**kw) -> Variant:
    base = dict(name="wariant A", project=Project(customer_name="Kowalski"))
    base.update(kw)
    return Variant(**base)


class TestVariantDefaults:
    def test_new_variant_starts_in_draft_with_no_overrides(self):
        v = make_variant()
        # purchasing-variants.md lifecycle starts at Draft
        assert v.state == "draft"
        assert v.state == DEFAULT_VARIANT_STATE
        assert not v.is_locked
        # a fresh variant IS the baseline: every axis inherits
        assert v.overrides() == {}

    def test_state_vocabulary_is_the_spec_lifecycle(self):
        # purchasing-variants.md § "The variant lifecycle", in order
        assert VARIANT_STATE_SEQUENCE == [
            "draft", "frozen", "sent", "offer_received", "accepted", "ordered",
        ]

    def test_variant_attaches_to_the_project_spine(self):
        project = Project(customer_name="Kowalski")
        v = Variant(name="wariant A", project=project)
        assert project.variants == [v]
        assert v.project is project


class TestVariantLifecycle:
    def test_full_forward_chain(self):
        """Every hop of the spec lifecycle is a legal forward move."""
        v = make_variant()
        for state in VARIANT_STATE_SEQUENCE[1:]:
            v.advance_state(state)
            assert v.state == state
        assert v.state == "ordered"

    def test_backward_move_rejected(self):
        v = make_variant()
        v.advance_state("sent")
        with pytest.raises(VariantStateError):
            v.advance_state("frozen")
        # rejected move leaves state untouched
        assert v.state == "sent"

    def test_no_op_move_rejected(self):
        v = make_variant()
        v.advance_state("frozen")
        with pytest.raises(VariantStateError):
            v.advance_state("frozen")

    def test_unknown_state_rejected(self):
        v = make_variant()
        with pytest.raises(VariantStateError):
            v.advance_state("negotiating")
        assert v.state == "draft"

    def test_lock_engages_at_accepted_and_stays(self):
        v = make_variant()
        v.advance_state("frozen")
        assert not v.is_locked
        v.advance_state("accepted")
        assert v.is_locked
        v.advance_state("ordered")
        assert v.is_locked


class TestVariantOverrides:
    def test_draft_variant_accepts_typed_overrides(self):
        v = make_variant()
        decor = Material(id=9, name="Dab Sonoma", price_per_unit=45.0, unit="m2")
        v.set_overrides(
            front_decor=decor,
            drawer_system="legrabox",
            corner_mechanism="magic_corner",
            hinge_class="soft_close",
            worktop="postforming_38",
        )
        assert v.overrides() == {
            "front_decor": "Dab Sonoma",
            "drawer_system": "legrabox",
            "corner_mechanism": "magic_corner",
            "hinge_class": "soft_close",
            "worktop": "postforming_38",
        }

    def test_none_clears_an_axis_and_unpassed_axes_stay(self):
        v = make_variant()
        v.set_overrides(drawer_system="merivobox", hinge_class="soft_close")
        v.set_overrides(drawer_system=None)  # back to baseline on ONE axis
        assert v.overrides() == {"hinge_class": "soft_close"}

    def test_unknown_drawer_system_refused(self):
        v = make_variant()
        with pytest.raises(ValueError, match="drawer system"):
            v.set_overrides(drawer_system="hafele_matrix")
        assert v.overrides() == {}

    def test_unknown_corner_mechanism_and_hinge_class_refused(self):
        v = make_variant()
        with pytest.raises(ValueError, match="corner mechanism"):
            v.set_overrides(corner_mechanism="lazy_susan_9000")
        with pytest.raises(ValueError, match="hinge class"):
            v.set_overrides(hinge_class="titanium")
        # vocabularies stay what the spec's substitution registry names
        assert "magic_corner" in CORNER_MECHANISMS
        assert "soft_close" in HINGE_CLASSES

    def test_accept_lock_mutation_raises(self):
        """The ACCEPT lock (UC-4 step 5): mutating a locked variant must
        raise. The change-order mechanism itself is a later increment."""
        v = make_variant()
        v.set_overrides(drawer_system="legrabox")
        v.advance_state("accepted")
        with pytest.raises(VariantLockedError):
            v.set_overrides(drawer_system="tandembox_antaro")
        # the lock leaves the accepted parameters untouched
        assert v.overrides() == {"drawer_system": "legrabox"}

    def test_ordered_variant_is_still_locked(self):
        v = make_variant()
        v.advance_state("ordered")
        with pytest.raises(VariantLockedError):
            v.set_overrides(hinge_class="soft_close")

    def test_sent_variant_is_never_mutated(self):
        """purchasing-variants.md: rejected offers loop back to a sibling
        draft, never mutate a Sent variant. Not the ACCEPT lock -- a
        plain state error."""
        v = make_variant()
        v.advance_state("sent")
        with pytest.raises(VariantStateError) as exc_info:
            v.set_overrides(drawer_system="merivobox")
        assert not isinstance(exc_info.value, VariantLockedError)


class TestVariantPersistence:
    def test_variant_round_trips_through_the_db(self, session):
        project = Project(customer_name="Kowalski")
        decor = Material(name="Dab Sonoma", price_per_unit=45.0, unit="m2")
        v = Variant(name="wariant B", project=project, baseline_ref="layout-v3")
        session.add_all([project, decor])
        session.commit()
        v.set_overrides(front_decor=decor, drawer_system="legrabox")
        v.advance_state("frozen")
        session.add(v)
        session.commit()
        session.refresh(v)

        assert v.project_id == project.id
        assert v.state == "frozen"
        assert v.baseline_ref == "layout-v3"
        assert v.front_decor.name == "Dab Sonoma"
        assert v.drawer_system == "legrabox"

    def test_deleting_a_project_cascades_to_its_variants(self, session):
        project = Project(customer_name="Kowalski")
        Variant(name="wariant A", project=project)
        session.add(project)
        session.commit()
        session.delete(project)
        session.commit()
        assert session.exec(select(Variant)).all() == []


# ---------------------------------------------------------------------------
# Re-derivation (the pre-written acceptance claim of purchasing-variants.md):
# "kitchen-erp Variants hold parameter overrides on a project and re-derive
# rozrys, CNC and BOM from one decomposition per variant; a drawer-system
# substitution changes the emitted drilling ops, pinned by test"
#
# Hand-computed expectations (never re-derived from the code under test):
#   D60 drawer cabinet 600W x 720H x 510D, 3 drawers, 18mm sides/bottom:
#     carcass internal width KB = 600 - 2*18            = 564
#     TANDEMBOX antaro:  LW = 564 - 2*12.5 = 539; back panel = 501 x 89 (M)
#     LEGRABOX:          LW = 564 - 2*13   = 538; back panel = 500 x 63 (M)
#   Runner screw axis (stack, drawers bottom-up, zone height 608/3):
#     y = 18 + 37 = 55, then 55 + 608/3, then 55 + 2*608/3; x = 46 from
#     the front edge; 5mm dia, 12mm blind -- per side panel, both sides.
# ---------------------------------------------------------------------------

DRAWER_ZONE_H = 608 / 3  # (720 - 100 plinth - 4*3mm gaps) / 3 drawers


@pytest.fixture
def project():
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
    Cabinet(name="D45", type="BASE", module_kind="BASE_CABINET",
            width_mm=450.0, height_mm=720.0, depth_mm=510.0,
            door_count=1, drawer_count=0, order_index=1, project=proj)
    return proj


def runner_ops(artifacts):
    """(panel_id, x, y, dia, depth, note) for every runner drilling op."""
    return [(pid, op.x_mm, round(op.y_mm, 2), op.diameter_mm, op.depth_mm, op.note)
            for pid, op in artifacts.cnc_ops if op.drill_type == "runner_screw"]


def carcass_geometry(artifacts):
    """(panel_id, thickness, w, h) for every non-drawer-box panel --
    material deliberately excluded: geometry only."""
    return [(p.id, p.thickness_mm, round(p.width_mm, 1), round(p.height_mm, 1))
            for r in artifacts.results for p in r.panels
            if "_drawer_" not in p.id]


class TestResolveParameters:
    def test_baseline_variant_resolves_to_project_defaults(self, project):
        params = resolve_parameters(Variant(name="base", project=project),
                                    project.defaults)
        assert params.front_decor == "Front MDF"
        assert params.drawer_system == "tandembox_antaro"  # adapter's historic tier
        assert params.corner_mechanism == "plain_shelves"
        assert params.hinge_class == "standard"
        assert params.worktop is None

    def test_overrides_fold_over_the_baseline(self, project):
        v = Variant(name="premium", project=project)
        v.set_overrides(drawer_system="legrabox", hinge_class="soft_close")
        params = resolve_parameters(v, project.defaults)
        assert params.drawer_system == "legrabox"
        assert params.hinge_class == "soft_close"
        assert params.front_decor == "Front MDF"  # untouched axis inherits


class TestDrawerSystemSubstitution:
    """Killer feature 2: a substitution is geometry, not a price line."""

    def test_drawer_tier_changes_the_emitted_drilling_ops(self, project):
        """THE acceptance pin: two variants differing ONLY in drawer-system
        tier produce different drilling ops from the same baseline."""
        base = Variant(name="tandembox", project=project)
        prem = Variant(name="legrabox", project=project)
        prem.set_overrides(drawer_system="legrabox")

        ops_base = runner_ops(derive_variant(base))
        ops_prem = runner_ops(derive_variant(prem))

        # 3 drawers x 2 side panels, positions hand-computed above
        expected_y = [55.0, round(55 + DRAWER_ZONE_H, 2), round(55 + 2 * DRAWER_ZONE_H, 2)]
        assert ops_base == [
            (f"erp-D60_{side}", 46, y, 5, 12, "TandemboxAntaro runner screw (NL=500)")
            for side in ("left", "right") for y in expected_y
        ]
        assert ops_prem == [
            (f"erp-D60_{side}", 46, y, 5, 12, "Legrabox runner screw (NL=500)")
            for side in ("left", "right") for y in expected_y
        ]
        assert ops_base != ops_prem

    def test_drawer_tier_changes_the_box_parts(self, project):
        """The cascade rule reaches board: LEGRABOX and TANDEMBOX cut
        different drawer-box backs (LW and back heights differ)."""
        base = Variant(name="tandembox", project=project)
        prem = Variant(name="legrabox", project=project)
        prem.set_overrides(drawer_system="legrabox")

        def box_backs(artifacts):
            return sorted((p.id, p.width_mm, p.height_mm)
                          for r in artifacts.results for p in r.panels
                          if p.id.endswith("_back") and "_drawer_" in p.id)

        assert box_backs(derive_variant(base)) == [
            (f"erp-D60_drawer_S{i}_back", 501, 89) for i in (1, 2, 3)
        ]
        assert box_backs(derive_variant(prem)) == [
            (f"erp-D60_drawer_S{i}_back", 500, 63) for i in (1, 2, 3)
        ]

    def test_drawer_tier_changes_runner_bom_lines_not_carcass(self, project):
        base_art = derive_variant(Variant(name="tandembox", project=project))
        prem = Variant(name="legrabox", project=project)
        prem.set_overrides(drawer_system="legrabox")
        prem_art = derive_variant(prem)

        assert BomLine("Prowadnica tandembox_antaro (S1)", 1, "szt") in base_art.bom_lines
        assert BomLine("Prowadnica legrabox (S1)", 1, "szt") in prem_art.bom_lines
        # same baseline: the carcass itself is identical geometry
        assert carcass_geometry(base_art) == carcass_geometry(prem_art)


class TestDecorSubstitution:
    def test_decor_override_changes_edging_and_bom_not_geometry(self, project):
        """Decor swap cascade: edging lines + BOM front lines re-derive,
        carcass geometry stays byte-identical."""
        decor = Material(id=9, name="Dab Sonoma", price_per_unit=45.0, unit="m2")
        base = Variant(name="baseline", project=project)
        swapped = Variant(name="sonoma", project=project)
        swapped.set_overrides(front_decor=decor)

        base_art = derive_variant(base)
        swap_art = derive_variant(swapped)

        # geometry: identical panel ids/thicknesses/dims, cabinet by cabinet
        assert carcass_geometry(base_art) == carcass_geometry(swap_art)

        # edging: front edges re-band to the new decor (G11's class of check
        # -- edging follows decor, never a generic line)
        def front_edge_materials(artifacts):
            return {row.material for row in artifacts.edging_rows
                    if "front" in row.panel_id.lower() or row.panel_name.startswith("Front")}
        assert front_edge_materials(base_art) == {"ABS_Front MDF"}
        assert front_edge_materials(swap_art) == {"ABS_Dab Sonoma"}

        # BOM: the front board bucket re-prices under the new decor name,
        # same quantity (geometry unchanged)
        def front_line(artifacts, name):
            return next(l for l in artifacts.bom_lines
                        if l.name == name and l.unit == "m2")
        base_front = front_line(base_art, "Front MDF")
        swap_front = front_line(swap_art, "Dab Sonoma")
        assert base_front.qty == swap_front.qty
        assert all(l.name != "Front MDF" for l in swap_art.bom_lines)

    def test_cabinet_level_front_override_survives_the_variant_axis(self, project):
        """Cabinet.override_front_mat is a deliberate per-cabinet exception
        (test_domain_adapter contract) -- the variant decor does not
        steamroll it."""
        special = Material(id=8, name="Lacquered", price_per_unit=50.0, unit="m2")
        project.cabinets[1].override_front_mat = special
        decor = Material(id=9, name="Dab Sonoma", price_per_unit=45.0, unit="m2")
        v = Variant(name="sonoma", project=project)
        v.set_overrides(front_decor=decor)

        art = derive_variant(v)
        door_fronts = {p.material for r in art.results for p in r.panels
                       if r.cabinet_id == "erp-D45" and p.id.startswith("erp-D45_front")}
        drawer_fronts = {p.material for r in art.results for p in r.panels
                         if r.cabinet_id == "erp-D60" and "_front_" in p.id}
        assert door_fronts == {"Lacquered"}
        assert drawer_fronts == {"Dab Sonoma"}

    def test_override_front_board_prices_under_its_own_decor(self, project):
        """ADR-015 payoff: board lines group by actual panel material, so a
        per-cabinet front override's m² lands on its own purchasing line
        instead of inflating the variant decor's order quantity."""
        special = Material(id=8, name="Lacquered", price_per_unit=50.0, unit="m2")
        project.cabinets[1].override_front_mat = special
        decor = Material(id=9, name="Dab Sonoma", price_per_unit=45.0, unit="m2")
        v = Variant(name="sonoma", project=project)
        v.set_overrides(front_decor=decor)

        art = derive_variant(v)
        board = {l.name: l.qty for l in art.bom_lines if l.unit == "m2"}
        assert "Lacquered" in board and "Dab Sonoma" in board
        # the two front positions are disjoint quantities, both non-zero
        assert board["Lacquered"] > 0 and board["Dab Sonoma"] > 0


class TestNoStaleArtifacts:
    def test_every_derivation_is_fresh_no_caching_across_override_changes(self, project):
        """A Variant stores parameters, never artifacts: change an override
        in draft and the next derivation reflects it immediately."""
        v = Variant(name="wip", project=project)
        before = runner_ops(derive_variant(v))
        v.set_overrides(drawer_system="merivobox")
        after = runner_ops(derive_variant(v))
        assert all("TandemboxAntaro" in note for *_, note in before)
        assert all("Merivobox" in note for *_, note in after)

    def test_derivation_without_project_defaults_fails_loudly(self):
        v = Variant(name="orphan", project=Project(customer_name="Kowalski"))
        with pytest.raises(ValueError, match="defaults"):
            derive_variant(v)
