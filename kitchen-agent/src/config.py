"""
src/config.py
=============
Central application settings powered by pydantic-settings.

All knobs live here.  Values can be overridden via environment variables
(names match the field names, upper-cased) or a .env file in the project root.

Usage:
    from src.config import settings

    settings.data_dir          # Path("data")
    settings.gemini_model      # "gemini-3.1-pro-preview"
    settings.allowed_origins   # ["http://localhost:5173"]
"""

from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Paths ────────────────────────────────────────────────────────────────
    data_dir: Path = Path("data")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "chats.db"

    @property
    def prompt_log_path(self) -> Path:
        return self.data_dir / "prompt_log.md"

    # ── Gemini ───────────────────────────────────────────────────────────────
    gemini_model: str = "gemini-3.1-pro-preview"
    gemini_temperature: float = 0.2

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list in env:  ALLOWED_ORIGINS=http://localhost:5173,https://example.com
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]


# Singleton — import this everywhere instead of instantiating Settings() again.
settings = Settings()
