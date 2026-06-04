"""
api/providers.py
────────────────
Provider information and app metadata endpoints.

Routes:
  GET /api/providers          → list available providers
  GET /api/providers/active   → active provider and model
  GET /api/app-info           → app metadata
"""
from __future__ import annotations

from fastapi import APIRouter

from src.config import settings
from src.schemas import ActiveProvider, AppInfo, ModelInfo, ProviderInfo

router = APIRouter()


# ── Provider catalogue (static) ────────────────────────────────────

_PROVIDER_CATALOGUE: list[ProviderInfo] = [
    ProviderInfo(
        id="gemini",
        label="Google Gemini",
        default_model="gemini-3.1-pro-preview",
        models=[
            ModelInfo(id="gemini-3.1-pro-preview", label="Gemini 3.1 Pro", context_k=1000),
            ModelInfo(id="gemini-3.5-flash", label="Gemini 3.5 Flash", context_k=1000),
        ],
    ),
    ProviderInfo(
        id="anthropic",
        label="Anthropic Claude",
        default_model="claude-sonnet-4-6",
        models=[
            ModelInfo(id="claude-opus-4-8", label="Claude Opus 4.8", context_k=200),
            ModelInfo(id="claude-sonnet-4-6", label="Claude Sonnet 4.6", context_k=200),
        ],
    ),
    ProviderInfo(
        id="mimo",
        label="Xiaomi MiMo",
        default_model="mimo-v2.5-pro",
        models=[
            ModelInfo(id="mimo-v2.5-pro", label="MiMo V2.5 Pro", context_k=1000),
            ModelInfo(id="mimo-v2.5", label="MiMo V2.5", context_k=1000),
        ],
    ),
]

_PROVIDER_MAP: dict[str, ProviderInfo] = {p.id: p for p in _PROVIDER_CATALOGUE}


@router.get("/api/providers", response_model=list[ProviderInfo])
def list_providers() -> list[ProviderInfo]:
    """Returns the full provider + model catalogue."""
    return _PROVIDER_CATALOGUE


@router.get("/api/providers/active", response_model=ActiveProvider)
def get_active_provider() -> ActiveProvider:
    """Returns the server-configured default provider and model."""
    provider = settings.llm_provider
    if provider == "gemini":
        model: str = settings.gemini_model
    elif provider == "anthropic":
        model = settings.anthropic_model
    elif provider == "mimo":
        model = settings.mimo_model
    else:
        model = _default_model_for(provider)
    return ActiveProvider(provider=provider, model=model)


@router.get("/api/app-info", response_model=AppInfo)
def get_app_info() -> AppInfo:
    """Returns domain branding metadata."""
    return AppInfo(title=settings.app_title, description=settings.app_description)


def _default_model_for(provider_id: str) -> str:
    entry = _PROVIDER_MAP.get(provider_id)
    if entry:
        return entry.default_model
    if provider_id == "gemini":
        return settings.gemini_model
    if provider_id == "anthropic":
        return settings.anthropic_model
    return ""
