"""GET /catalog/producers"""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from catalog.api.deps import get_db
from catalog.models.domain import ProducerOut

router = APIRouter(prefix="/producers", tags=["producers"])


@router.get("", response_model=list[ProducerOut])
def list_producers(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> list[dict]:
    rows = db.execute("SELECT * FROM producers ORDER BY name").fetchall()
    return [dict(r) for r in rows]
