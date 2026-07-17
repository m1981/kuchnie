# tests/test_offers.py
"""Pins the offer-loop acceptance of docs/specs/purchasing-variants.md
(wk-593a317b increment 2): "Offers record against variants with optional
line itemization, archive the source verbatim as an ArtifactRef, and an
ACCEPT locks the variant so later edits require an explicit change-order;
pinned by test"."""
from datetime import datetime
from pathlib import Path

import pytest
from sqlmodel import select

from kitchen_erp.core.models import (
    ArtifactRef,
    Material,
    Offer,
    OfferLine,
    Project,
    Variant,
    VariantLockedError,
    VariantStateError,
)
from kitchen_erp.core.offers import OfferRecordingError, accept_variant, record_offer


@pytest.fixture
def sent_variant(session):
    project = Project(customer_name="Kowalski")
    variant = Variant(name="wariant A", project=project)
    session.add(project)
    session.commit()
    variant.advance_state("frozen")
    variant.advance_state("sent")
    session.add(variant)
    session.commit()
    session.refresh(variant)
    return variant


def offer_pdf(tmp_path: Path, content: bytes = b"%PDF-1.4 oferta 4200 netto") -> Path:
    path = tmp_path / "oferta-uslugi.pdf"
    path.write_bytes(content)
    return path


def test_bare_total_offer_records_archives_and_advances_state(session, tmp_path, sent_variant):
    source = offer_pdf(tmp_path)
    offer = record_offer(
        session, sent_variant, supplier="Uslugi CNC Wroclaw", currency="pln",
        total_net=4200.0, source=source, archive_dir=tmp_path / "archive",
    )
    # bare total is a complete, valid offer
    assert offer.total_net == 4200.0 and offer.lines == []
    assert offer.currency == "PLN"
    assert isinstance(offer.received_at, datetime)
    # verbatim archive, byte-identical, referenced from the offer
    assert Path(offer.source_ref).read_bytes() == source.read_bytes()
    # ...and registered as a project ArtifactRef
    refs = session.exec(select(ArtifactRef)).all()
    assert [(r.kind, r.path, r.project_id) for r in refs] == [
        ("offer_source", offer.source_ref, sent_variant.project_id)
    ]
    # lifecycle: sent -> offer_received
    assert sent_variant.state == "offer_received"


def test_itemized_offer_stores_lines_as_given(session, tmp_path, sent_variant):
    offer = record_offer(
        session, sent_variant, supplier="Uslugi CNC", currency="PLN",
        total_net=4200.0, source=offer_pdf(tmp_path), archive_dir=tmp_path / "a",
        lines=[
            {"kind": "board", "description": "U112 18mm", "qty": 3.2, "unit": "m2", "amount": 1200.0},
            {"kind": "cut", "description": "ciecie", "amount": 800.0},          # no qty/unit — fine
            {"kind": "other", "description": "dojazd", "amount": 150.0},
        ],
    )
    stored = session.exec(select(OfferLine)).all()
    assert len(stored) == 3
    assert stored[1].qty is None and stored[1].unit is None
    # lines are NOT reconciled against the total (1200+800+150 != 4200) — by design
    assert offer.total_net == 4200.0


def test_offer_against_draft_or_frozen_is_refused(session, tmp_path):
    project = Project(customer_name="K")
    draft = Variant(name="draft", project=project)
    session.add(project)
    session.commit()
    with pytest.raises(VariantStateError, match="SENT"):
        record_offer(session, draft, supplier="X", currency="PLN",
                     total_net=100.0, source=offer_pdf(tmp_path),
                     archive_dir=tmp_path / "a")
    assert session.exec(select(Offer)).all() == []


@pytest.mark.parametrize(
    ("kwargs", "fragment"),
    [
        ({"total_net": 0.0}, "must be > 0"),
        ({"currency": "ZLOTE"}, "3-letter"),
        ({"supplier": "  "}, "supplier"),
        ({"lines": [{"kind": "rabat", "amount": 5.0}]}, "kind"),
        ({"lines": [{"kind": "cut", "amount": "800"}]}, "amount"),
    ],
)
def test_malformed_offer_refused_whole(session, tmp_path, sent_variant, kwargs, fragment):
    base = dict(supplier="X", currency="PLN", total_net=100.0,
                source=offer_pdf(tmp_path), archive_dir=tmp_path / "a")
    with pytest.raises(OfferRecordingError, match=fragment):
        record_offer(session, sent_variant, **{**base, **kwargs})
    assert session.exec(select(Offer)).all() == []
    assert sent_variant.state == "sent"  # refused offers advance nothing
    # refusal is atomic: no ArtifactRef row and no archive copy may leak
    # (validation must run BEFORE archive_source — pinned against reorder)
    assert session.exec(select(ArtifactRef)).all() == []
    assert not (tmp_path / "a").exists()


def test_competing_offer_while_offer_received_is_allowed(session, tmp_path, sent_variant):
    for dealer in ("Dealer A", "Dealer B"):
        record_offer(session, sent_variant, supplier=dealer, currency="PLN",
                     total_net=4000.0, source=offer_pdf(tmp_path),
                     archive_dir=tmp_path / "a")
    assert len(sent_variant.offers) == 2
    assert sent_variant.state == "offer_received"


def test_accept_locks_the_variant_against_edits(session, tmp_path, sent_variant):
    record_offer(session, sent_variant, supplier="X", currency="PLN",
                 total_net=4200.0, source=offer_pdf(tmp_path),
                 archive_dir=tmp_path / "a")
    accept_variant(session, sent_variant)
    assert sent_variant.state == "accepted" and sent_variant.is_locked
    # the ACCEPT lock: later edits require an explicit change-order
    decor = Material(name="Dab Sonoma", price_per_unit=30.0, unit="m2")
    with pytest.raises(VariantLockedError, match="change-order"):
        sent_variant.set_overrides(front_decor=decor)


def test_accept_without_recorded_offer_is_refused(session, sent_variant):
    with pytest.raises(VariantStateError, match="recorded offer"):
        accept_variant(session, sent_variant)  # still 'sent', no offer
    assert sent_variant.state == "sent"


def test_rejected_offer_never_mutates_the_sent_variant(session, tmp_path, sent_variant):
    """The lifecycle rule: rejection = loop back to a sibling draft.
    There is no reject verb on the offer — pin that the recorded offer
    row and the variant survive untouched when the client walks away."""
    offer = record_offer(session, sent_variant, supplier="X", currency="PLN",
                         total_net=9999.0, source=offer_pdf(tmp_path),
                         archive_dir=tmp_path / "a")
    sibling = Variant(name="wariant B (tanszy)", project=sent_variant.project)
    session.add(sibling)
    session.commit()
    assert sent_variant.state == "offer_received"   # unchanged by rejection
    assert offer.total_net == 9999.0                # archived answer stands
    assert sibling.state == "draft"                 # iteration continues here
