"""GET /catalog/decors, /catalog/decors/{id}, /catalog/decors/{id}/variants, /catalog/decors/{id}/pairings"""

from __future__ import annotations

import sqlite3
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from catalog.api.deps import get_db
from catalog.models.domain import (
    DecorSummary,
    DecorWithVariants,
    PaginatedResponse,
    PairingOut,
    VariantOut,
)
from catalog.repositories.decor_repo import DecorRepository
from catalog.repositories.pairing_repo import PairingRepository

router = APIRouter(prefix="/decors", tags=["decors"])


@router.get("", response_model=PaginatedResponse)
def list_decors(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    producer: Optional[str] = Query(None),
    color_family: Optional[str] = Query(None),
    material_type: Optional[str] = Query(None),
    structure: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse:
    repo = DecorRepository(db)
    items, total = repo.list_filtered(
        producer=producer,
        color_family=color_family,
        material_type=material_type,
        structure=structure,
        role=role,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{decor_id}", response_model=DecorWithVariants)
def get_decor(
    decor_id: str,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> DecorWithVariants:
    repo = DecorRepository(db)
    result = repo.get_by_id(decor_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Decor '{decor_id}' not found")
    return result


@router.get("/{decor_id}/variants", response_model=list[VariantOut])
def get_decor_variants(
    decor_id: str,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    material_type: Optional[str] = Query(None),
) -> list[VariantOut]:
    repo = DecorRepository(db)
    return repo.get_variants(decor_id, material_type=material_type)


@router.get("/{decor_id}/pairings", response_model=list[PairingOut])
def get_decor_pairings(
    decor_id: str,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    pairing_type: Optional[str] = Query(None),
) -> list[PairingOut]:
    repo = PairingRepository(db)
    return repo.get_for_decor(decor_id, pairing_type=pairing_type)
