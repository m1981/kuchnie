"""FastAPI application — catalog API.

Usage:
    uvicorn catalog.api.main:app --reload --port 8000
    open http://localhost:8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from catalog.api import deps
from catalog.api.routers import admin, availability, decors, producers, worktops
from catalog.db.engine import get_connection, init_schema

_DB_PATH = Path(__file__).parent.parent / "db" / "catalog.db"
_PUBLIC_DIR = Path(__file__).parent.parent / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup, close on shutdown."""
    db = get_connection(str(_DB_PATH))
    init_schema(db)
    deps.set_db(db)
    yield
    db.close()


app = FastAPI(
    title="Kuchnie Catalog API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(producers.router, prefix="/catalog")
app.include_router(decors.router, prefix="/catalog")
app.include_router(worktops.router, prefix="/catalog")
app.include_router(availability.router, prefix="/catalog")
app.include_router(admin.router, prefix="/catalog")

# Serve frontend static files (index.html, images, catalog.json fallback)
if _PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_PUBLIC_DIR), html=True), name="static")
