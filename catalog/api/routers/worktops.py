"""GET /catalog/worktops"""

from __future__ import annotations

import sqlite3
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from catalog.api.deps import get_db
from catalog.models.domain import WorktopOut
from catalog.repositories.worktop_repo import WorktopRepository

router = APIRouter(prefix="/worktops", tags=["worktops"])


@router.get("", response_model=list[WorktopOut])
def list_worktops(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    construction: Optional[str] = Query(None),
    producer: Optional[str] = Query(None),
) -> list[WorktopOut]:
    repo = WorktopRepository(db)
    return repo.list_filtered(construction=construction, producer=producer)
