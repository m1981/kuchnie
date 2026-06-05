"""
api/sessions.py
───────────────
Session lifecycle endpoints.

Routes:
  GET    /api/sessions                    → list sessions
  GET    /api/sessions/tree               → session tree
  GET    /api/sessions/{id}               → get one session
  DELETE /api/sessions/{id}               → delete session
  PATCH  /api/sessions/{id}/archive       → archive session
  DELETE /api/sessions/{id}/archive       → unarchive session
  POST   /api/sessions/{id}/fork          → fork session
  GET    /api/sessions/{id}/export        → export as markdown
  GET    /api/sessions/{id}/export/llm    → export as LLM JSON
  PATCH  /api/sessions/{id}/messages/{tid}         → edit message
  DELETE /api/sessions/{id}/messages/{tid}         → delete message
  POST   /api/sessions/{id}/messages/truncate      → truncate turns
  GET    /api/sessions/{id}/system-prompt          → get system prompt
  PATCH  /api/sessions/{id}/system-prompt          → update system prompt
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from src.dependencies import (
    get_export_service,
    get_message_editor,
    get_session_repo,
)
from src.export_service import ExportService
from src.message_editor import EditError, MessageEditService
from src.repositories import SessionRepository
from src.schemas import (
    ForkRequest,
    ForkResponse,
    LlmExportConfig,
    LlmExportMetadata,
    LlmExportResponse,
    LlmExportTurn,
    MessageDeleteResponse,
    MessageEditRequest,
    MessageEditResponse,
    SessionNode,
    SessionSummary,
    SystemPromptResponse,
    SystemPromptUpdateRequest,
    SystemPromptUpdateResponse,
    TruncateRequest,
    TruncateResponse,
)

router = APIRouter()


# ── Session listing ────────────────────────────────────────────────

@router.get("/api/sessions", response_model=list[SessionSummary])
def get_sessions(
    include_archived: bool = Query(False),
    session_repo: SessionRepository = Depends(get_session_repo),
) -> list[SessionSummary]:
    """Returns a flat list of all sessions ordered by most-recently updated."""
    return [
        SessionSummary(**row)
        for row in session_repo.list_sessions(include_archived=include_archived)
    ]


@router.get("/api/sessions/tree", response_model=list[SessionNode])
def get_session_tree(
    include_archived: bool = Query(True),
    session_repo: SessionRepository = Depends(get_session_repo),
) -> list[SessionNode]:
    """Returns all sessions as a forest of trees."""

    def _build(node: dict) -> SessionNode:
        return SessionNode(
            **{k: v for k, v in node.items() if k != "children"},
            children=[_build(c) for c in node.get("children", [])],
        )

    return [
        _build(root)
        for root in session_repo.get_session_tree(include_archived=include_archived)
    ]


@router.get("/api/sessions/{session_id}")
def get_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> dict:
    _, ui_json, _ = session_repo.load_session(session_id)
    ui_messages = json.loads(ui_json) if ui_json and ui_json != "[]" else []
    return {"ui_messages": ui_messages}


@router.get("/api/sessions/{session_id}/state")
def get_session_state(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> dict:
    """Lightweight state check for test verification.
    Returns message count, turn_ids, and roles without full message content."""
    _, ui_json, _ = session_repo.load_session(session_id)
    ui_messages = json.loads(ui_json) if ui_json and ui_json != "[]" else []
    return {
        "session_id": session_id,
        "message_count": len(ui_messages),
        "turn_ids": [m.get("turn_id") for m in ui_messages],
        "roles": [m["role"] for m in ui_messages],
    }


# ── Session lifecycle ──────────────────────────────────────────────

@router.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> None:
    """Permanently deletes a session and all its notes."""
    try:
        session_repo.delete_session(session_id)
    except ValueError as exc:
        detail = str(exc)
        status = 409 if "child" in detail.lower() else 404
        raise HTTPException(status_code=status, detail=detail) from exc


@router.patch("/api/sessions/{session_id}/archive", status_code=200)
def archive_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> dict:
    archived = session_repo.archive_session(session_id)
    if not archived:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or already archived: {session_id}",
        )
    return {"archived": True, "session_id": session_id}


@router.delete("/api/sessions/{session_id}/archive", status_code=200)
def unarchive_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> dict:
    """Reverses an archive."""
    unarchived = session_repo.unarchive_session(session_id)
    if not unarchived:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or not archived: {session_id}",
        )
    return {"archived": False, "session_id": session_id}


@router.post("/api/sessions/{session_id}/fork", response_model=ForkResponse)
def fork_session(
    session_id: str,
    request: ForkRequest,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> ForkResponse:
    try:
        new_id = session_repo.fork_session(session_id, request.turn_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ForkResponse(new_session_id=new_id)


# ── Export ─────────────────────────────────────────────────────────

@router.get(
    "/api/sessions/{session_id}/export",
    response_class=PlainTextResponse,
)
def export_session(
    session_id: str,
    export_service: ExportService = Depends(get_export_service),
) -> PlainTextResponse:
    """Exports the session as a human-readable Markdown document."""
    try:
        markdown = export_service.export_markdown(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(content=markdown, media_type="text/markdown")


@router.get(
    "/api/sessions/{session_id}/export/llm",
    response_model=LlmExportResponse,
)
def export_session_llm(
    session_id: str,
    export_service: ExportService = Depends(get_export_service),
) -> LlmExportResponse:
    """Exports the complete LLM call context as structured JSON."""
    try:
        data = export_service.export_llm_json(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return LlmExportResponse(
        metadata=LlmExportMetadata(**data["metadata"]),
        config=LlmExportConfig(**data["config"]),
        turns=[LlmExportTurn(**turn) for turn in data["turns"]],
    )


# ── Message editing ────────────────────────────────────────────────

@router.patch(
    "/api/sessions/{session_id}/messages/{turn_id}",
    response_model=MessageEditResponse,
)
def edit_message(
    session_id: str,
    turn_id: str,
    request: MessageEditRequest,
    editor: MessageEditService = Depends(get_message_editor),
) -> MessageEditResponse:
    """Edit the content of a single chat message identified by turn_id."""
    try:
        editor.edit_message(
            session_id=session_id,
            turn_id=turn_id,
            new_content=request.new_content,
        )
    except EditError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return MessageEditResponse(updated=True, turn_id=turn_id)


@router.delete(
    "/api/sessions/{session_id}/messages/{turn_id}",
    response_model=MessageDeleteResponse,
)
def delete_message(
    session_id: str,
    turn_id: str,
    delete_pair: bool = Query(False, description="Also delete the next paired message"),
    editor: MessageEditService = Depends(get_message_editor),
) -> MessageDeleteResponse:
    """Delete a single chat message (optionally with its paired response)."""
    try:
        editor.delete_message(
            session_id=session_id,
            turn_id=turn_id,
            delete_pair=delete_pair,
        )
    except EditError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return MessageDeleteResponse(deleted=True, turn_id=turn_id, delete_pair=delete_pair)


@router.post(
    "/api/sessions/{session_id}/messages/truncate",
    response_model=TruncateResponse,
)
def truncate_messages(
    session_id: str,
    request: TruncateRequest,
    editor: MessageEditService = Depends(get_message_editor),
) -> TruncateResponse:
    """Remove the last N turn-pairs from the conversation tail."""
    try:
        editor.truncate_turns(session_id=session_id, n=request.n)
    except EditError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return TruncateResponse(truncated=True, turns_removed=request.n)


# ── System prompt ──────────────────────────────────────────────────

@router.get(
    "/api/sessions/{session_id}/system-prompt",
    response_model=SystemPromptResponse,
)
def get_system_prompt(
    session_id: str,
    editor: MessageEditService = Depends(get_message_editor),
) -> SystemPromptResponse:
    """Retrieve the session-scoped system prompt (or null if unset)."""
    system_prompt = editor.get_system_prompt(session_id)
    return SystemPromptResponse(session_id=session_id, system_prompt=system_prompt)


@router.patch(
    "/api/sessions/{session_id}/system-prompt",
    response_model=SystemPromptUpdateResponse,
)
def update_system_prompt(
    session_id: str,
    request: SystemPromptUpdateRequest,
    editor: MessageEditService = Depends(get_message_editor),
) -> SystemPromptUpdateResponse:
    """Set or clear the session-scoped system prompt override."""
    editor.update_system_prompt(
        session_id=session_id,
        system_prompt=request.system_prompt,
    )
    return SystemPromptUpdateResponse(updated=True)
