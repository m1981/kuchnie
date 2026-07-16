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
    Material,
    Project,
    VARIANT_STATE_SEQUENCE,
    Variant,
    VariantLockedError,
    VariantStateError,
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
