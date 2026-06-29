"""GET /catalog/availability"""

from __future__ import annotations

import sqlite3
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from catalog.api.deps import get_db
from catalog.models.domain import AvailabilityOut
from catalog.repositories.availability_repo import AvailabilityRepository

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("", response_model=list[AvailabilityOut])
def list_availability(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    channel: Optional[str] = Query(None),
    producer: Optional[str] = Query(None),
) -> list[AvailabilityOut]:
    repo = AvailabilityRepository(db)
    return repo.list_filtered(channel=channel, producer=producer)
