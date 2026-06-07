"""
api/chat.py
───────────
Chat turn execution and token estimation endpoints.

Routes:
  POST /api/chat                → execute one turn
  POST /api/tokens/estimate     → estimate tokens before sending
  GET  /api/sessions/{id}/tokens → count tokens in existing session
"""
from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException

from src.chat_service import ChatService, ChatTurnRequest
from src.config import settings
from src.dependencies import (
    get_chat_service,
    get_prompt_manager,
    get_session_repo,
)
from src.prompt_manager import PromptManager
from src.repositories import SessionRepository
from src.schemas import (
    ChatRequest,
    ChatResponse,
    SessionTokensResponse,
    TokenEstimateRequest,
    TokenEstimateResponse,
)
from src.logger import bind_request_context, clear_request_context, log_timing
from src.token_counter import build_pending_context_estimate, count_session_tokens
from src.tools.file_ops import read_file

log = structlog.get_logger(__name__)

router = APIRouter()


# ── Chat turn ──────────────────────────────────────────────────────

@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    pm: PromptManager = Depends(get_prompt_manager),
) -> ChatResponse:
    """
    Processes a chat message through the Gemini agent and persists state.

    F05 — System instruction resolution
    ------------------------------------
    Priority (highest → lowest):
      1. ``request.system_prompt`` — explicit raw override (legacy / power-user)
      2. ``request.mode_id``       — resolved via PromptManager (new default)
    """
    # Bind request context for all subsequent log calls
    bind_request_context(
        session_id=request.session_id[:8],
        mode=request.mode_id,
        req_provider=request.provider,
        req_model=request.model,
    )

    log.info(
        "chat_request_received",
        message_preview=request.message[:80],
        has_images=bool(request.images),
        has_context_files=bool(request.context_files),
    )

    try:
        # Resolve the system instruction with the F05 priority rules
        if request.system_prompt is not None:
            system_instruction: str | None = request.system_prompt
        else:
            resolved = pm.get_system_instruction(request.mode_id)
            system_instruction = resolved if resolved else None

        # Resolve effective use_tools flag
        mode_obj = pm.get_mode(request.mode_id)
        mode_tools_default = mode_obj.tools_enabled_default if mode_obj else True
        use_tools: bool = request.tools_enabled and mode_tools_default

        # Resolve context file paths
        resolved_context_files = _resolve_context_file_paths(request.context_files)

        loop = asyncio.get_event_loop()

        chat_request = ChatTurnRequest(
            session_id=request.session_id,
            user_message=request.message,
            system_prompt=system_instruction,
            images=[img.model_dump() for img in request.images] if request.images else [],
            context_files=resolved_context_files,
            mode=request.mode_id or "default",
            use_tools=use_tools,
            provider=request.provider,
            model=request.model,
        )

        with log_timing(log, "chat_request_complete") as timing:
            result = await loop.run_in_executor(
                None,
                partial(service.handle_turn, chat_request),
            )

        log.info(
            "chat_response_sent",
            provider=result.provider_name,
            model=result.model_name,
            response_length=len(result.assistant_message),
            tool_calls=len(result.tool_calls_made),
            tools_used=result.tool_calls_made[:5],  # first 5 tool names
        )

        return ChatResponse(
            text=result.assistant_message,
            tools_used=result.tool_calls_made,
            user_turn_id=result.user_turn_id,
            assistant_turn_id=result.assistant_turn_id,
            provider=result.provider_name,
            model=result.model_name,
        )
    except Exception as exc:
        log.exception("chat_request_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        clear_request_context()


# ── Token estimation ───────────────────────────────────────────────

@router.post("/api/tokens/estimate", response_model=TokenEstimateResponse)
def estimate_pending_tokens(
    request: TokenEstimateRequest,
) -> TokenEstimateResponse:
    """Estimate token cost of a pending turn before sending."""
    resolved_files = _resolve_context_file_paths(request.context_files)

    context_file_contents: list[str] = []
    for path in (resolved_files or []):
        result = read_file(path)
        context_file_contents.append(result.get("content", ""))

    estimate = build_pending_context_estimate(
        user_message=request.user_message,
        images=(
            [img.model_dump() for img in request.images]
            if request.images
            else None
        ),
        context_file_contents=context_file_contents,
        system_prompt=request.system_prompt,
        history_token_count=request.history_token_count,
    )

    return TokenEstimateResponse(
        text_tokens=estimate.text_tokens,
        image_tokens=estimate.image_tokens,
        context_file_tokens=estimate.context_file_tokens,
        system_prompt_tokens=estimate.system_prompt_tokens,
        history_tokens=estimate.history_tokens,
        total_tokens=estimate.total_tokens,
        fallback_used=estimate.fallback_used,
    )


@router.get(
    "/api/sessions/{session_id}/tokens",
    response_model=SessionTokensResponse,
)
def get_session_token_count(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
) -> SessionTokensResponse:
    """Count tokens in an existing session."""
    api_json, _ui_json, system_prompt = session_repo.load_session(session_id)
    estimate = count_session_tokens(api_json, system_prompt=system_prompt)

    return SessionTokensResponse(
        session_id=session_id,
        text_tokens=estimate.text_tokens,
        image_tokens=estimate.image_tokens,
        context_file_tokens=estimate.context_file_tokens,
        system_prompt_tokens=estimate.system_prompt_tokens,
        history_tokens=estimate.history_tokens,
        total_tokens=estimate.total_tokens,
        fallback_used=estimate.fallback_used,
    )


# ── Private helpers ────────────────────────────────────────────────

def _resolve_context_file_paths(
    context_files: list[str] | None,
) -> list[str] | None:
    """
    Resolve context file paths sent by the frontend to full filesystem paths.

    Args:
        context_files: Raw list from the HTTP request, or ``None``.

    Returns:
        Resolved list of absolute path strings, or ``None`` when the input is
        empty / ``None``.
    """
    if not context_files:
        return None

    data_dir_resolved = settings.data_dir.resolve()
    resolved_paths: list[str] = []

    for fp in context_files:
        candidate = Path(fp)

        if candidate.is_absolute():
            try:
                candidate.resolve().relative_to(data_dir_resolved)
            except ValueError:
                log.warning(
                    "context_file_path_traversal_dropped",
                    path=fp,
                    data_dir=str(data_dir_resolved),
                )
                continue
            resolved_paths.append(fp)
        else:
            prefixed = (settings.data_dir / fp).resolve()
            if not str(prefixed).startswith(str(data_dir_resolved)):
                log.warning(
                    "context_file_path_traversal_dropped",
                    path=fp,
                    resolved=str(prefixed),
                )
                continue
            resolved_paths.append(str(prefixed))

    return resolved_paths or None
