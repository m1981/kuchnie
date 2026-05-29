"""
src/schemas.py
==============
Pydantic models for API requests and responses.
"""

from typing import Any
from pydantic import BaseModel


class ChatImagePart(BaseModel):
    mime_type: str  # e.g. "image/jpeg"
    data: str       # base64-encoded bytes


class ChatRequest(BaseModel):
    session_id: str
    message: str
    system_prompt: str | None = None
    images: list[ChatImagePart] | None = None
    context_files: list[str] | None = None


class ToolLog(BaseModel):
    name: str
    args: dict[str, Any]
    result: dict[str, Any]


class ChatResponse(BaseModel):
    text: str
    tools_used: list[ToolLog]


class ForkRequest(BaseModel):
    turn_index: int


class ForkResponse(BaseModel):
    new_session_id: str


class SessionSummary(BaseModel):
    """Flat representation of a session as returned by GET /api/sessions."""
    id: str
    title: str | None
    updated_at: str | None
    parent_id: str | None = None
    fork_turn_index: int | None = None
    root_id: str | None = None
    archived_at: str | None = None


class SessionNode(BaseModel):
    """One node in the session tree returned by GET /api/sessions/tree."""
    id: str
    title: str | None
    updated_at: str | None
    parent_id: str | None = None
    fork_turn_index: int | None = None
    root_id: str | None = None
    archived_at: str | None = None
    children: list["SessionNode"] = []


# Required so Pydantic can resolve the self-referential type.
SessionNode.model_rebuild()


class FileReadResponse(BaseModel):
    filepath: str
    content: str


class FileWriteRequest(BaseModel):
    content: str


class FileAppendRequest(BaseModel):
    filepath: str
    content: str


class FileListItem(BaseModel):
    path: str
    name: str


# ---------------------------------------------------------------------------
# F03 — Snapshot / Revert schemas
# ---------------------------------------------------------------------------

class RevertResponse(BaseModel):
    """
    Response returned by POST /api/files/revert/{revert_id}.

    success : Always True on a 200 response (errors become HTTP 4xx).
    message : Human-readable description, e.g. "Reverted changes to notes.md".
    """
    success: bool
    message: str


class NoteCreateRequest(BaseModel):
    selected_text: str
    source_role: str  # "user" | "assistant"
    note: str = ""


class NoteResponse(BaseModel):
    id: str
    session_id: str
    selected_text: str
    note: str
    source_role: str
    created_at: str


# ---------------------------------------------------------------------------
# LLM-context debug export schemas
# ---------------------------------------------------------------------------

class LlmExportMetadata(BaseModel):
    """Metadata block for the LLM debug export."""
    session_id: str
    title: str
    turn_count: int
    export_timestamp: str  # ISO 8601 UTC


class LlmExportPart(BaseModel):
    """
    One Part inside a turn.

    ``type`` is one of: ``"text"``, ``"function_call"``,
    ``"function_response"``, ``"unknown_part"``.
    The remaining keys depend on the type (open-ended to handle future types).
    """
    type: str
    model_config = {"extra": "allow"}


class LlmExportTurn(BaseModel):
    """One Content turn as the LLM sees it."""
    role: str
    parts: list[dict[str, Any]]  # keep as raw dicts — structure varies by type


class LlmExportResponse(BaseModel):
    """
    Response returned by GET /api/sessions/{id}/export/llm.

    metadata : Session info and export timestamp.
    turns    : Ordered list of every Content turn in the LLM context window.
    """
    metadata: LlmExportMetadata
    turns: list[LlmExportTurn]
