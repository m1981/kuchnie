"""Configurator API — 6-step kitchen material wizard.

Endpoints:
  POST   /configurator/sessions              Create session
  GET    /configurator/sessions/{t}/options   Options for current step
  PATCH  /configurator/sessions/{t}/select    Make choice, advance step
  GET    /configurator/sessions/{t}/bom       Bill of materials
  GET    /configurator/templates              Curated starting points
  POST   /configurator/sessions/{t}/from_template  Init from template
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from catalog.api.deps import get_db
from catalog.models.domain import (
    BOMOut,
    ConfiguratorOption,
    ConfiguratorStepOut,
    FromTemplateRequest,
    SelectRequest,
    SessionOut,
    TemplateOut,
)
from catalog.repositories.configurator import (
    EDGE_STEPS,
    STEPS,
    VARIANT_STEPS,
    ConfiguratorRepository,
)

router = APIRouter(prefix="/configurator", tags=["configurator"])


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(db: sqlite3.Connection = Depends(get_db)) -> SessionOut:
    repo = ConfiguratorRepository(db)
    result = repo.create_session()
    return SessionOut(**result)


@router.get("/sessions/{token}", response_model=SessionOut)
def get_session(
    token: str,
    db: sqlite3.Connection = Depends(get_db),
) -> SessionOut:
    """Get session state. Used for shareable links."""
    repo = ConfiguratorRepository(db)
    session = repo.get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut(
        session_token=session["session_token"],
        current_step=session["current_step"],
    )


@router.get(
    "/sessions/{token}/options",
    response_model=ConfiguratorStepOut,
)
def get_options(
    token: str,
    color_family: str | None = None,
    style: str | None = None,
    db: sqlite3.Connection = Depends(get_db),
) -> ConfiguratorStepOut:
    repo = ConfiguratorRepository(db)
    session = repo.get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    step = session["current_step"]

    if step == "front":
        raw = repo.front_options(color_family=color_family, style=style)
    elif step == "carcass":
        raw = repo.carcass_options(session["front_variant_id"])
    elif step == "worktop":
        raw = repo.worktop_options()
    elif step == "edge":
        raw = repo.edge_options(session["front_variant_id"])
    elif step == "side_panel":
        raw = repo.side_panel_options()
    elif step == "plinth":
        raw = repo.plinth_options()
    else:
        raw = []

    options = [ConfiguratorOption(**o) for o in raw]
    return ConfiguratorStepOut(current_step=step, options=options)


@router.patch(
    "/sessions/{token}/select",
    response_model=SessionOut,
)
def select(
    token: str,
    req: SelectRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> SessionOut:
    repo = ConfiguratorRepository(db)
    session = repo.get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    current = session["current_step"]

    # Validate step matches current
    if req.step != current:
        raise HTTPException(
            status_code=400,
            detail=f"Expected step '{current}', got '{req.step}'",
        )

    # Validate we have a selection
    if req.step in VARIANT_STEPS:
        if not req.variant_id:
            raise HTTPException(status_code=400, detail="variant_id required")
        # Verify variant exists
        vrow = db.execute(
            "SELECT id FROM variants WHERE business_id = ?",
            (req.variant_id,),
        ).fetchone()
        if not vrow:
            raise HTTPException(status_code=400, detail="Variant not found")
        column = {
            "front": "front_variant_id",
            "carcass": "carcass_variant_id",
            "worktop": "worktop_variant_id",
            "side_panel": "side_panel_variant_id",
            "plinth": "plinth_variant_id",
        }[req.step]
        next_step = _next_step_or_done(current)
        repo.update_step(token, next_step, column, req.variant_id)
    elif req.step in EDGE_STEPS:
        if not req.edge_id:
            raise HTTPException(status_code=400, detail="edge_id required")
        # Verify edge exists
        erow = db.execute(
            "SELECT id FROM edges WHERE id = ?",
            (req.edge_id,),
        ).fetchone()
        if not erow:
            raise HTTPException(status_code=400, detail="Edge not found")
        next_step = _next_step_or_done(current)
        repo.update_step(token, next_step, "edge_id", req.edge_id)
    else:
        raise HTTPException(status_code=400, detail=f"Cannot select for step '{req.step}'")

    session = repo.get_session(token)
    return SessionOut(
        session_token=session["session_token"],
        current_step=session["current_step"],
    )


@router.get("/sessions/{token}/bom", response_model=BOMOut)
def get_bom(
    token: str,
    db: sqlite3.Connection = Depends(get_db),
) -> BOMOut:
    repo = ConfiguratorRepository(db)
    session = repo.get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = repo.build_bom(session)
    return BOMOut(**result)


@router.get("/compare")
def compare_variants(
    ids: str,
    db: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    """Compare multiple variants side-by-side.

    Usage: GET /configurator/compare?ids=K003-CH-18-FP,K190-CH-18-PE
    """
    variant_ids = [v.strip() for v in ids.split(",") if v.strip()]
    if len(variant_ids) < 2 or len(variant_ids) > 5:
        raise HTTPException(
            status_code=400,
            detail="Provide 2-5 variant IDs, comma-separated",
        )
    repo = ConfiguratorRepository(db)
    return repo.compare_variants(variant_ids)


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(
    db: sqlite3.Connection = Depends(get_db),
) -> list[TemplateOut]:
    # MVP: curated_kitchens table may not exist yet
    try:
        rows = db.execute(
            "SELECT slug, name, description, hero_image, front_variant_id, featured "
            "FROM curated_kitchens ORDER BY featured DESC, name"
        ).fetchall()
        return [TemplateOut(**dict(r)) for r in rows]
    except sqlite3.OperationalError:
        return []


@router.post(
    "/sessions/{token}/from_template",
    response_model=SessionOut,
)
def from_template(
    token: str,
    req: FromTemplateRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> SessionOut:
    repo = ConfiguratorRepository(db)
    session = repo.get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Try curated_kitchens table
    try:
        tmpl = db.execute(
            "SELECT * FROM curated_kitchens WHERE slug = ?",
            (req.template_slug,),
        ).fetchone()
    except sqlite3.OperationalError:
        tmpl = None

    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    # Set all selections from template
    for step, col in [
        ("front", "front_variant_id"),
        ("carcass", "carcass_variant_id"),
        ("worktop", "worktop_variant_id"),
        ("side_panel", "side_panel_variant_id"),
        ("plinth", "plinth_variant_id"),
    ]:
        val = tmpl.get(col)
        if val:
            repo.update_step(token, "done", col, val)

    edge = tmpl.get("edge_id")
    if edge:
        repo.update_step(token, "done", "edge_id", edge)

    session = repo.get_session(token)
    return SessionOut(
        session_token=session["session_token"],
        current_step=session["current_step"],
    )


# ── Helpers ──────────────────────────────────────────────────────


def _next_step_or_done(current: str) -> str:
    idx = STEPS.index(current)
    if idx < len(STEPS) - 1:
        return STEPS[idx + 1]
    return "done"
