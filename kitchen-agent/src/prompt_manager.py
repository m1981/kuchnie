"""
src/prompt_manager.py
=====================
F05 — Backend Prompt Management.

Responsibilities
----------------
* Read prompt Markdown files from ``prompts/`` on startup (or on demand).
* Cache them in memory so there is ZERO disk I/O during the hot chat path.
* Expose metadata (id / label / eyebrow) to the frontend via the REST API
  without leaking the full prompt text.
* Resolve a ``mode_id`` → complete ``system_instruction`` string for the LLM.
* Support hot-reload (``reload_prompts()``) so prompt files can be edited
  and picked up immediately without restarting the server.

Design decisions
----------------
* **Singleton at module level** — ``prompt_manager`` is imported directly by
  ``main.py`` for the FastAPI DI factory.  Tests override it via
  ``app.dependency_overrides``.
* **Graceful degradation** — missing files / directory never raise; they
  produce empty strings so the agent can still run.
* **base_agent_rules.md** is prepended to every mode's content so agentic
  rules are always present regardless of the selected mode.
"""

from pathlib import Path

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class PromptMode(BaseModel):
    """In-memory representation of one prompt mode."""
    id: str
    label: str
    eyebrow: str
    content: str  # full combined prompt (base rules + mode body) — never sent to frontend


# ---------------------------------------------------------------------------
# Mode registry
# ---------------------------------------------------------------------------

# Ordered list that defines which modes exist and what their labels are.
# File discovery is driven by this registry: add a new entry + matching .md file
# to introduce a new mode.
_MODE_REGISTRY: list[dict[str, str]] = [
    {
        "id":     "general",
        "label":  "General",
        "eyebrow":"Workspace help",
        "file":   "general.md",
    },
    {
        "id":     "design",
        "label":  "Design",
        "eyebrow":"Ergonomics and layout",
        "file":   "design.md",
    },
    {
        "id":     "assembly",
        "label":  "Assembly",
        "eyebrow":"Build and fitting",
        "file":   "assembly.md",
    },
]


# ---------------------------------------------------------------------------
# PromptManager
# ---------------------------------------------------------------------------

class PromptManager:
    """
    Reads Markdown prompt files once on construction (or on ``reload_prompts``)
    and serves them from an in-memory cache for the rest of the process lifetime.

    Parameters
    ----------
    prompts_dir:
        Directory that contains ``base_agent_rules.md`` and one ``.md`` file
        per mode listed in ``_MODE_REGISTRY``.
        Defaults to ``"prompts"`` (relative to the working directory).
    """

    def __init__(self, prompts_dir: str = "prompts") -> None:
        self._prompts_dir: Path = Path(prompts_dir)
        self._cache: dict[str, PromptMode] = {}
        self._base_rules: str = ""
        self.reload_prompts()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload_prompts(self) -> None:
        """
        (Re-)read all Markdown files and refresh the in-memory cache.

        Safe to call at runtime — replaces the cache atomically so concurrent
        readers always see a consistent snapshot.  Any file that does not exist
        is treated as an empty string (graceful degradation).
        """
        new_cache: dict[str, PromptMode] = {}

        # 1. Load base rules (applied to ALL modes)
        base_rules = self._read_file("base_agent_rules.md")
        self._base_rules = base_rules

        if not self._prompts_dir.exists():
            logger.warning("prompts_dir_missing", path=str(self._prompts_dir))
            self._cache = new_cache
            return

        # 2. Load each mode and combine with base rules
        for entry in _MODE_REGISTRY:
            mode_body = self._read_file(entry["file"])
            separator = "\n\n" if base_rules and mode_body else ""
            full_prompt = f"{base_rules}{separator}{mode_body}".strip()

            new_cache[entry["id"]] = PromptMode(
                id=entry["id"],
                label=entry["label"],
                eyebrow=entry["eyebrow"],
                content=full_prompt,
            )
            logger.debug(
                "prompt_loaded",
                mode_id=entry["id"],
                chars=len(full_prompt),
            )

        # Atomic swap — no reader ever sees a half-built cache
        self._cache = new_cache
        logger.info("prompts_reloaded", mode_count=len(self._cache))

    def get_all_modes(self) -> list[dict[str, str]]:
        """
        Returns metadata for every cached mode.

        **Never includes ``content``** — only ``id``, ``label``, and
        ``eyebrow`` are returned so the frontend knows which buttons to render
        without receiving the full prompt text.
        """
        return [
            {"id": mode.id, "label": mode.label, "eyebrow": mode.eyebrow}
            for mode in self._cache.values()
        ]

    def get_system_instruction(self, mode_id: str) -> str:
        """
        Returns the full system instruction string for the given ``mode_id``.

        Falls back to ``_base_rules`` when the mode is unknown so the LLM
        always has at least the base agentic rules, even for unknown modes.
        """
        mode = self._cache.get(mode_id)
        if mode is not None:
            return mode.content
        logger.warning("unknown_mode_id_fallback", mode_id=mode_id)
        return self._base_rules

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_file(self, filename: str) -> str:
        """Read a file relative to ``prompts_dir``; return '' if absent."""
        filepath = self._prompts_dir / filename
        if not filepath.exists():
            logger.debug("prompt_file_missing", path=str(filepath))
            return ""
        return filepath.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

# Instantiated once when the module is first imported.
# main.py uses this via the get_prompt_manager() DI factory.
# Tests override it via app.dependency_overrides[get_prompt_manager].
prompt_manager = PromptManager()
