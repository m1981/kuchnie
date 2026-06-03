"""
src/main.py
===========
FastAPI application — HTTP layer only.

Responsibilities
----------------
* App init, middleware, CORS
* Router registration
* Logging setup

All route handlers live in src/api/*.py routers.
All dependency wiring lives in src/dependencies.py.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.logger import setup_logging

# Initialize structured logging
setup_logging(is_local_dev=True)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

from src.api.chat import router as chat_router
from src.api.files import router as files_router
from src.api.notes import router as notes_router
from src.api.prompts import router as prompts_router
from src.api.providers import router as providers_router
from src.api.sessions import router as sessions_router

app.include_router(chat_router)
app.include_router(files_router)
app.include_router(notes_router)
app.include_router(prompts_router)
app.include_router(providers_router)
app.include_router(sessions_router)

# ── Backward-compatible re-exports for tests ───────────────────────
# These names were in main.py before the router refactor.
# Tests import them from src.main — keep them accessible here.
# New code should import from src.dependencies instead.
from src.dependencies import (  # noqa: F401
    get_session_repo,
    get_note_repo,
    get_chat_service,
    get_export_service,
    get_prompt_manager,
    get_message_editor,
    get_turn_orchestrator,
)
from src.chat_service import ChatService, ChatTurnRequest  # noqa: F401
from src.api.files import _resolve_data_path  # noqa: F401
from src.api.chat import _resolve_context_file_paths  # noqa: F401
from src.tools.file_ops import append_to_file, read_file, revert_backup  # noqa: F401
from src.tools.repo_map import get_repo_map  # noqa: F401
from src.token_counter import count_session_tokens, build_pending_context_estimate  # noqa: F401
