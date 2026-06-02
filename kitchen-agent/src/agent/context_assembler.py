"""
src/agent/context_assembler.py
================================
ContextAssembler — makes context window construction explicit and testable.

Before this module, context was assembled implicitly inside the provider's
``process_chat_turn`` method.  This made it impossible to test token budgets,
observe where tokens are being spent, or debug context window issues.

The ContextAssembler has a single responsibility: build the context window.
It knows about budget, ordering, and trimming.  It does NOT know about
LLM providers or tools.

Design decisions
----------------
* **ContextSlot enum**: Every segment of the context window has a named slot.
  This prevents any one segment from starving others and makes token usage
  observable.
* **ContextBudget**: Single place to tune context window allocations.
* **AssembledContext**: Immutable result — what gets handed to the provider.
* **Optional dependencies**: NoteManager and FileManager are optional
  (they arrive in Phase 5).  When absent, those slots are simply empty.

Phase 3 scope
-------------
Currently used for:
  - System prompt resolution from PromptManager
  - History trimming when over token budget
  - Context slot observability

Future (Phase 5):
  - Note attachment via NoteManager
  - File attachment via FileManager
  - SearchCoordinator integration
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Context slot enum
# ---------------------------------------------------------------------------

class ContextSlot(Enum):
    """
    Explicit budget allocation per context segment.
    Prevents any one segment from starving others.
    """

    SYSTEM_PROMPT = auto()
    CONVERSATION_HISTORY = auto()
    ATTACHED_NOTES = auto()
    ATTACHED_FILES = auto()
    SEARCH_RESULTS = auto()
    TOOL_RESULTS = auto()


# ---------------------------------------------------------------------------
# Context budget
# ---------------------------------------------------------------------------

@dataclass
class ContextBudget:
    """
    Token budget per slot.
    Single place to tune context window usage.
    """

    total: int = 128_000
    allocations: dict[ContextSlot, float] = field(default_factory=lambda: {
        ContextSlot.SYSTEM_PROMPT:        0.05,
        ContextSlot.CONVERSATION_HISTORY: 0.50,
        ContextSlot.ATTACHED_NOTES:       0.15,
        ContextSlot.ATTACHED_FILES:       0.15,
        ContextSlot.SEARCH_RESULTS:       0.10,
        ContextSlot.TOOL_RESULTS:         0.05,
    })

    def tokens_for(self, slot: ContextSlot) -> int:
        return int(self.total * self.allocations[slot])


# ---------------------------------------------------------------------------
# Assembled context result
# ---------------------------------------------------------------------------

@dataclass
class AssembledContext:
    """What gets handed to the LLM provider. Immutable after assembly."""

    system_prompt: str
    messages: list[dict]
    total_tokens_estimated: int
    slots_used: dict[ContextSlot, int]  # for observability
    images: list[dict] = field(default_factory=list)  # inline images for the LLM
    context_files: list[str] = field(default_factory=list)  # file paths to inject


# ---------------------------------------------------------------------------
# Protocols — what the assembler needs from its dependencies
# ---------------------------------------------------------------------------

class TokenCounterProtocol(Protocol):
    def count(self, text: str) -> int: ...
    def count_message(self, message: dict) -> int: ...
    def trim_to(self, text: str, max_tokens: int) -> str: ...


class PromptManagerProtocol(Protocol):
    def get_system_instruction(self, mode: str = "default") -> str: ...


# ---------------------------------------------------------------------------
# ContextAssembler
# ---------------------------------------------------------------------------

class ContextAssembler:
    """
    Single responsibility: build the context window.

    Knows about budget. Knows about ordering. Knows about trimming.
    Does NOT know about LLM providers or tools.
    """

    def __init__(
        self,
        token_budget: ContextBudget,
        token_counter: TokenCounterProtocol,
        prompt_manager: PromptManagerProtocol,
    ) -> None:
        self._budget = token_budget
        self._tokens = token_counter
        self._prompts = prompt_manager

    def assemble(
        self,
        session: dict,
        mode: str = "default",
        user_message: str = "",
        note_ids: list[str] | None = None,
        file_ids: list[str] | None = None,
    ) -> AssembledContext:
        """
        Build the full context window for one chat turn.

        Args:
            session:      Session-like dict with a ``messages`` key.
            mode:         Prompt mode (resolved via PromptManager).
            user_message: The user's new message text.
            note_ids:     Optional note IDs to attach (Phase 5).
            file_ids:     Optional file IDs to attach (Phase 5).

        Returns:
            An AssembledContext with system_prompt, messages,
            total_tokens_estimated, and slots_used for observability.
        """
        slots_used: dict[ContextSlot, int] = {}

        system_prompt = self._build_system(mode, slots_used)
        history = self._trim_history(session, slots_used)
        enrichments = self._attach_content(
            note_ids=note_ids, file_ids=file_ids, slots_used=slots_used,
        )

        messages = history + enrichments
        if user_message:
            messages.append({"role": "user", "content": user_message})

        return AssembledContext(
            system_prompt=system_prompt,
            messages=messages,
            total_tokens_estimated=sum(slots_used.values()),
            slots_used=slots_used,
        )

    # ── System prompt ────────────────────────────────────────────────

    def _build_system(
        self,
        mode: str,
        slots_used: dict[ContextSlot, int],
    ) -> str:
        prompt = self._prompts.get_system_instruction(mode)
        budget = self._budget.tokens_for(ContextSlot.SYSTEM_PROMPT)
        tokens = self._tokens.count(prompt)

        if tokens > budget:
            prompt = self._tokens.trim_to(prompt, budget)
            tokens = budget

        slots_used[ContextSlot.SYSTEM_PROMPT] = tokens
        return prompt

    # ── History trimming ─────────────────────────────────────────────

    def _trim_history(
        self,
        session: dict,
        slots_used: dict[ContextSlot, int],
    ) -> list[dict]:
        budget = self._budget.tokens_for(ContextSlot.CONVERSATION_HISTORY)
        messages = session.get("messages", [])
        kept: list[dict] = []
        used = 0

        # Walk history newest-first, keep what fits
        for msg in reversed(messages):
            tokens = self._tokens.count_message(msg)
            if used + tokens > budget:
                break
            kept.insert(0, msg)
            used += tokens

        slots_used[ContextSlot.CONVERSATION_HISTORY] = used
        return kept

    # ── Content attachment (stubs for Phase 5) ───────────────────────

    def _attach_content(
        self,
        note_ids: list[str] | None,
        file_ids: list[str] | None,
        slots_used: dict[ContextSlot, int],
    ) -> list[dict]:
        """
        Attach notes and files as context messages.
        Each gets its own budget slot — neither can starve the other.

        Currently stubs — will be wired in Phase 5 when
        NoteManager and FileManager exist.
        """
        enrichments: list[dict] = []

        if note_ids:
            slots_used[ContextSlot.ATTACHED_NOTES] = 0  # Phase 5
        if file_ids:
            slots_used[ContextSlot.ATTACHED_FILES] = 0  # Phase 5

        return enrichments
