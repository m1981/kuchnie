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
    """
    Request body for POST /api/chat.

    F05 changes
    -----------
    ``mode_id`` replaces the old ``system_prompt`` as the primary way to
    select a persona.  The backend resolves ``mode_id`` → full system
    instruction via ``PromptManager`` before calling the agent.

    Backward compatibility
    ----------------------
    ``system_prompt`` is kept as an **optional override**.  When provided it
    takes precedence over ``mode_id`` so the old Svelte frontend (which sends
    the full prompt string directly) continues to work without changes.

    Priority (highest → lowest):
      1. ``system_prompt``  (explicit raw override — legacy / power-user path)
      2. ``mode_id``        (resolved via PromptManager — new default path)
    """
    session_id: str
    message: str
    # F05 — new primary field; defaults to "general"
    mode_id: str = "general"
    # Legacy override — if set, bypasses mode_id resolution entirely
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
# F04 — LLM-context debug export schemas (extended from F03)
# ---------------------------------------------------------------------------

class LlmExportMetadata(BaseModel):
    """Metadata block for the LLM debug export."""
    session_id: str
    title: str
    turn_count: int
    export_timestamp: str  # ISO 8601 UTC


class LlmExportConfig(BaseModel):
    """
    Reconstructed GenerateContentConfig envelope — what the Gemini API
    received alongside the conversation turns.

    model              : Gemini model name (e.g. "gemini-3.1-pro-preview").
    temperature        : Sampling temperature used for this session.
    system_instruction : Persisted system prompt, or null if none was active.
    tools              : Full tool/function_declarations schema as sent to the API.
    """
    model: str
    temperature: float
    system_instruction: str | None
    tools: list[dict[str, Any]]  # open structure — mirrors SDK wire format


class LlmExportTurn(BaseModel):
    """One Content turn as the LLM sees it."""
    role: str
    parts: list[dict[str, Any]]  # keep as raw dicts — structure varies by type


class LlmExportResponse(BaseModel):
    """
    Response returned by GET /api/sessions/{id}/export/llm.

    Key order (canonical, matches debug reading order):
      metadata → config → turns

    metadata : Session info and export timestamp.
    config   : Reconstructed GenerateContentConfig envelope (F04).
    turns    : Ordered list of every Content turn in the LLM context window.
    """
    metadata: LlmExportMetadata
    config: LlmExportConfig
    turns: list[LlmExportTurn]


# ---------------------------------------------------------------------------
# F05 — Backend Prompt Management schemas
# ---------------------------------------------------------------------------

class PromptModeResponse(BaseModel):
    """
    Metadata for one prompt mode, returned by GET /api/prompts/modes.

    Intentionally does NOT include ``content`` so the frontend never
    receives the full system prompt text in the list response.
    """
    id: str
    label: str
    eyebrow: str


class PromptModeDetail(BaseModel):
    """
    Full detail for one prompt mode, returned by GET /api/prompts/modes/{mode_id}.

    Includes ``content`` — the complete resolved system instruction
    (base_agent_rules + mode body) — so the frontend can display it
    in an expandable panel when the user explicitly asks to inspect it.

    Returns 404 when the mode_id is not found.
    """
    id: str
    label: str
    eyebrow: str
    content: str


# ---------------------------------------------------------------------------
# Message Editor schemas — in-session message editing/deletion
# ---------------------------------------------------------------------------

class MessageEditRequest(BaseModel):
    """
    Request body for PATCH /api/sessions/{id}/messages/{index}.

    new_content : Replacement text for the targeted message.
                  Must be non-empty after stripping whitespace.
    """
    new_content: str


class MessageEditResponse(BaseModel):
    """
    Response returned by PATCH /api/sessions/{id}/messages/{index}.

    updated   : Always True on a 200 response.
    ui_index  : The zero-based position that was edited (echoed back).
    """
    updated: bool
    ui_index: int


class MessageDeleteResponse(BaseModel):
    """
    Response returned by DELETE /api/sessions/{id}/messages/{index}.

    deleted     : Always True on a 200 response.
    ui_index    : The zero-based position that was deleted.
    delete_pair : Whether the paired next message was also removed.
    """
    deleted: bool
    ui_index: int
    delete_pair: bool


class TruncateRequest(BaseModel):
    """
    Request body for POST /api/sessions/{id}/messages/truncate.

    n : Number of complete turn-pairs (user + assistant) to remove from the tail.
        Must be >= 1.
    """
    n: int


class TruncateResponse(BaseModel):
    """
    Response returned by POST /api/sessions/{id}/messages/truncate.

    truncated     : Always True on a 200 response.
    turns_removed : The value of ``n`` that was applied.
    """
    truncated: bool
    turns_removed: int


class SystemPromptUpdateRequest(BaseModel):
    """
    Request body for PATCH /api/sessions/{id}/system-prompt.

    system_prompt : The new session-scoped system-prompt override.
                    Empty string is valid (clears the override).
    """
    system_prompt: str


class SystemPromptResponse(BaseModel):
    """
    Response returned by GET /api/sessions/{id}/system-prompt.

    session_id    : The session UUID.
    system_prompt : Current value stored in the DB (None if never set).
    """
    session_id: str
    system_prompt: str | None


class SystemPromptUpdateResponse(BaseModel):
    """
    Response returned by PATCH /api/sessions/{id}/system-prompt.

    updated : Always True on a 200 response.
    """
    updated: bool
