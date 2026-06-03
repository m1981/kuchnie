"""
main.py
───────
Application entry point.

Responsibilities (only these):
  - Create the FastAPI app instance
  - Register middleware
  - Register routers
  - Startup/shutdown lifecycle hooks

Nothing else lives here.
  Routes    → src/api/
  DI wiring → src/dependencies.py
  Config    → src/config.py
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.logger import setup_logging
from src.api import chat, sessions, files, notes, prompts, providers


# ── Logging ────────────────────────────────────────────────────────

setup_logging()


# ── Lifespan ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: warm the singleton cache so first request is not slow.
    Shutdown: nothing to clean up (SQLite closes on GC).
    """
    from src.dependencies import (
        get_settings,
        get_db_connection,
        get_tool_registry,
        get_prompt_manager,
    )

    get_settings()       # validates env vars at startup, not first request
    get_db_connection()  # opens DB and runs migrations at startup
    get_tool_registry()  # registers all tools at startup
    get_prompt_manager() # loads prompt files at startup

    yield
    # nothing to teardown


# ── App ────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    lifespan=lifespan,
)


# ── Middleware ─────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ────────────────────────────────────────────────────────

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(files.router)
app.include_router(notes.router)
app.include_router(prompts.router)
app.include_router(providers.router)
