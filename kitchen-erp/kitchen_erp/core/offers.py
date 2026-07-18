# kitchen_erp/core/offers.py
"""The offer/ACCEPT loop — wk-593a317b increment 2 (spec:
docs/specs/purchasing-variants.md § "Offer recording" and § "The variant
lifecycle").

The physics: every cutting-service round-trip costs 1-3 days, so only the
finalist variant is Sent; the answer is recorded here. Two rules carry it:

- **No granularity lock-in.** A bare total is a complete, valid offer.
  Itemized lines are stored verbatim-as-understood (kind/description/
  qty/unit/amount) and are never reconciled against the total — no
  service's paperwork style can block the flow.
- **Provenance first.** The paperwork itself (PDF/scan/mail export) is
  archived verbatim before anything is parsed, registered as a project
  ArtifactRef (kind='offer_source'), and the Offer row points at that
  archive copy. Same capture idiom as price ingestion (archive_source).

State: recording an offer advances a SENT variant to OFFER_RECEIVED;
competing offers may keep arriving while OFFER_RECEIVED. ACCEPT advances
to ACCEPTED and engages the lock (Variant.set_overrides then raises
VariantLockedError — later edits are explicit change-orders). A rejected
offer changes nothing here: you loop back to a sibling draft variant.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlmodel import Session

from .models import (
    OFFER_LINE_KINDS,
    ArtifactRef,
    Offer,
    OfferLine,
    Variant,
    VariantStateError,
)
from .price_import import archive_source

# States an offer may be recorded in: the first record advances sent ->
# offer_received; later records are competing dealer answers.
_RECORDABLE_STATES = {"sent", "offer_received"}


class OfferRecordingError(ValueError):
    """A malformed offer: bad amount, unknown line kind. The offer is
    refused whole — nothing is coerced or partially stored."""


def record_offer(
    session: Session,
    variant: Variant,
    *,
    supplier: str,
    currency: str,
    total_net: float,
    source: Path,
    archive_dir: Path,
    received_at: datetime | None = None,
    lines: list[dict] | None = None,
) -> Offer:
    """Record a received offer against a sent variant.

    `lines` is OPTIONAL (bare total is valid): each dict may carry
    kind/description/qty/unit/amount; kind must be in OFFER_LINE_KINDS
    and amount must be a positive number — qty/unit stay as given.
    Returns the persisted Offer. Raises VariantStateError outside
    sent/offer_received, OfferRecordingError for malformed input."""
    if variant.state not in _RECORDABLE_STATES:
        raise VariantStateError(
            f"variant {variant.name!r} is {variant.state}: offers record "
            "against a SENT variant (rejected offers loop back to a "
            "sibling draft, they never mutate this one)"
        )
    if not supplier.strip():
        raise OfferRecordingError("supplier must be named")
    currency = currency.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise OfferRecordingError(f"currency {currency!r} is not a 3-letter code")
    if not total_net > 0:
        raise OfferRecordingError(f"total_net {total_net} must be > 0")
    offer_lines: list[OfferLine] = []
    for i, raw in enumerate(lines or []):
        kind = raw.get("kind", "other")
        if kind not in OFFER_LINE_KINDS:
            raise OfferRecordingError(
                f"line {i}: kind {kind!r} not in {OFFER_LINE_KINDS}"
            )
        amount = raw.get("amount")
        if not isinstance(amount, (int, float)) or not amount > 0:
            raise OfferRecordingError(f"line {i}: amount {amount!r} must be > 0")
        offer_lines.append(OfferLine(
            kind=kind,
            description=str(raw.get("description", "")),
            qty=raw.get("qty"),
            unit=raw.get("unit"),
            amount=float(amount),
        ))

    archived = archive_source(Path(source), Path(archive_dir))
    session.add(ArtifactRef(
        project_id=variant.project_id, kind="offer_source", path=str(archived)
    ))
    offer = Offer(
        variant=variant,
        supplier=supplier.strip(),
        currency=currency,
        total_net=total_net,
        source_ref=str(archived),
        lines=offer_lines,
        **({"received_at": received_at} if received_at else {}),
    )
    session.add(offer)
    if variant.state == "sent":
        variant.advance_state("offer_received")
        session.add(variant)
    session.commit()
    session.refresh(offer)
    return offer


def accept_variant(session: Session, variant: Variant) -> None:
    """The ACCEPT of UC-4 step 5: client said yes at the comparison board.

    Requires at least one recorded offer (you accept an answer, not a
    hope) and the OFFER_RECEIVED state. Advances to ACCEPTED, engaging
    the lock — from here Variant.set_overrides raises VariantLockedError
    and any edit is an explicit change-order with visible redo cost."""
    if variant.state != "offer_received":
        raise VariantStateError(
            f"variant {variant.name!r} is {variant.state}: ACCEPT requires "
            "a recorded offer (state offer_received)"
        )
    if not variant.offers:
        raise VariantStateError(
            f"variant {variant.name!r} has no recorded offer to accept"
        )
    variant.advance_state("accepted")
    session.add(variant)
    session.commit()
