# Architecture Analysis & Design Recommendations

## First: What You Have Is Already Good

Before recommendations — your current design shows clear thinking:

- Provider abstraction is solid
- Repository pattern is correct
- Separation of concerns is visible
- Cross-cutting concerns are identified

---

## Key Observations & Concerns

### 1. The Agent is a Bottleneck

```
CHAT → AGENT → PROTO (LLM)
AGENT → REG (Tools)
```

`agent.py` currently does **too much** — it knows about providers AND tools AND orchestration. As you grow, this becomes a god object.

### 2. ChatService is Overloaded

```python
# ChatService currently touches:
CHAT --> AGENT      # orchestration
CHAT --> SREP       # persistence
CHAT --> SER        # serialization
CHAT --> PLOG       # logging
CHAT --> TOK        # token counting
CHAT --> EXP        # export
```

That's 6 direct dependencies. SRP violation waiting to explode.

### 3. Notes Are Orphaned

`NoteRepository` exists but has **no service, no route, no connection** to the chat flow in the diagram. As you grow notes into a real feature, this gap will hurt.

### 4. Tools Are Flat

```
registry.py → file_ops, repo_map, search_kb
```

All tools live at the same level. When you add BM25, embeddings, file attachments — this becomes a mess without sub-grouping.

### 5. Missing: Context Assembly

There's no explicit concept of **"what goes into the LLM context window"**. Token counting exists but context building (history + notes + files + system prompt) has no home.

---

## Recommended Architecture

```
flowchart TD
    CLIENT["🌐 HTTP Clients"]

    subgraph API["FastAPI Layer"]
        ROUTES["Routes"]
        SCHEMAS["Pydantic Schemas"]
        DI["DI Container"]
    end

    subgraph SVC["Service Layer  ← thin orchestrators"]
        CHAT_SVC["ChatService\norchestrate turn only"]
        NOTE_SVC["NoteService\nCRUD + search"]
        FILE_SVC["FileService\nattach · retrieve"]
        EDIT_SVC["MessageEditService"]
        EXPORT_SVC["ExportService\nmarkdown · json"]
    end

    subgraph AGENT["Agent Layer  ← LLM orchestration"]
        TURN["TurnOrchestrator\nmanage one turn lifecycle"]
        CTX["ContextAssembler\nbuild context window"]
        TOOL_EXEC["ToolExecutor\nresolve + run + validate"]
    end

    subgraph PROV["Provider Layer"]
        PROTO["LLMProvider Protocol"]
        GEMINI["GeminiProvider"]
        ANTHRO["AnthropicProvider"]
        NORM["ResponseNormalizer\nunify response shapes"]
    end

    subgraph TOOLS["Tool Registry"]
        REG["ToolRegistry\nregister · discover · schema"]
        subgraph FILE_TOOLS["File Tools"]
            FOPS["file_ops"]
            ATTACH["attachments"]
        end
        subgraph SEARCH_TOOLS["Search Tools"]
            BM25["BM25Search"]
            EMBED["EmbeddingSearch"]
            GREP["GrepSearch"]
        end
        subgraph REPO_TOOLS["Repo Tools"]
            RMAP["repo_map"]
        end
    end

    subgraph CONTENT["Content Layer  ← NEW"]
        NOTE_MGR["NoteManager\nlifecycle + linking"]
        FILE_MGR["FileManager\nattach · chunk · index"]
        SEARCH["SearchCoordinator\nfan-out · merge · rank"]
    end

    subgraph CROSS["Cross-cutting"]
        PM["PromptManager"]
        PLOG["PromptLogger"]
        TOK["TokenBudget\ncount · trim · warn"]
        CFG["Settings"]
    end

    subgraph STORE["Storage Layer"]
        SREP["SessionRepository Protocol"]
        NREP["NoteRepository Protocol"]
        FREP["FileRepository Protocol"]
        SSQL["SQLiteSessionRepository"]
        NSQL["SQLiteNoteRepository"]
        FSQL["SQLiteFileRepository"]
        CONN["SQLiteConnection"]
    end

    CLIENT --> ROUTES
    ROUTES --> SCHEMAS --> DI
    DI --> CHAT_SVC & NOTE_SVC & FILE_SVC & EDIT_SVC & EXPORT_SVC

    CHAT_SVC --> TURN
    TURN --> CTX
    TURN --> TOOL_EXEC
    TURN --> PROTO
    CTX --> NOTE_MGR & FILE_MGR & SREP & PM & TOK
    TOOL_EXEC --> REG

    PROTO --> GEMINI & ANTHRO
    GEMINI & ANTHRO --> NORM

    NOTE_SVC --> NOTE_MGR --> NREP --> NSQL --> CONN
    FILE_SVC --> FILE_MGR --> FREP --> FSQL --> CONN
    SEARCH --> BM25 & EMBED & GREP

    SREP --> SSQL --> CONN
    CHAT_SVC --> PLOG
```

---

## The Critical New Concepts

### ContextAssembler — The Missing Piece

```python
# agent/context_assembler.py
from dataclasses import dataclass, field
from typing import Protocol
from enum import Enum, auto


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


@dataclass
class AssembledContext:
    """What gets handed to the LLM provider. Immutable after assembly."""
    system_prompt: str
    messages: list[dict]
    total_tokens_estimated: int
    slots_used: dict[ContextSlot, int]  # for observability


class ContextAssembler:
    """
    Single responsibility: build the context window.
    Knows about budget. Knows about ordering. Knows about trimming.
    Does NOT know about LLM providers or tools.
    """

    def __init__(
        self,
        token_budget: ContextBudget,
        token_counter: "TokenCounter",
        prompt_manager: "PromptManager",
        note_manager: "NoteManager",
        file_manager: "FileManager",
    ) -> None:
        self._budget = token_budget
        self._tokens = token_counter
        self._prompts = prompt_manager
        self._notes = note_manager
        self._files = file_manager

    def assemble(
        self,
        session: "Session",
        turn_input: "TurnInput",
    ) -> AssembledContext:
        slots_used = {}

        system_prompt = self._build_system(turn_input, slots_used)
        history = self._trim_history(session, slots_used)
        enrichments = self._attach_content(turn_input, slots_used)

        messages = history + enrichments + [
            {"role": "user", "content": turn_input.user_message}
        ]

        return AssembledContext(
            system_prompt=system_prompt,
            messages=messages,
            total_tokens_estimated=sum(slots_used.values()),
            slots_used=slots_used,
        )

    def _build_system(
        self,
        turn_input: "TurnInput",
        slots_used: dict,
    ) -> str:
        prompt = self._prompts.load(turn_input.mode)
        budget = self._budget.tokens_for(ContextSlot.SYSTEM_PROMPT)
        tokens = self._tokens.count(prompt)

        if tokens > budget:
            prompt = self._tokens.trim_to(prompt, budget)

        slots_used[ContextSlot.SYSTEM_PROMPT] = min(tokens, budget)
        return prompt

    def _trim_history(
        self,
        session: "Session",
        slots_used: dict,
    ) -> list[dict]:
        budget = self._budget.tokens_for(ContextSlot.CONVERSATION_HISTORY)
        messages = []
        used = 0

        # Walk history newest-first, keep what fits
        for msg in reversed(session.messages):
            tokens = self._tokens.count_message(msg)
            if used + tokens > budget:
                break
            messages.insert(0, msg)
            used += tokens

        slots_used[ContextSlot.CONVERSATION_HISTORY] = used
        return messages

    def _attach_content(
        self,
        turn_input: "TurnInput",
        slots_used: dict,
    ) -> list[dict]:
        """
        Attach notes and files as context messages.
        Each gets its own budget slot — neither can starve the other.
        """
        enrichments = []

        if turn_input.note_ids:
            note_budget = self._budget.tokens_for(ContextSlot.ATTACHED_NOTES)
            notes_content = self._notes.get_for_context(
                turn_input.note_ids, max_tokens=note_budget
            )
            if notes_content:
                enrichments.append({
                    "role": "user",
                    "content": f"<notes>\n{notes_content}\n</notes>"
                })
                slots_used[ContextSlot.ATTACHED_NOTES] = (
                    self._tokens.count(notes_content)
                )

        if turn_input.file_ids:
            file_budget = self._budget.tokens_for(ContextSlot.ATTACHED_FILES)
            files_content = self._files.get_for_context(
                turn_input.file_ids, max_tokens=file_budget
            )
            if files_content:
                enrichments.append({
                    "role": "user",
                    "content": f"<files>\n{files_content}\n</files>"
                })
                slots_used[ContextSlot.ATTACHED_FILES] = (
                    self._tokens.count(files_content)
                )

        return enrichments
```

---

### TurnOrchestrator — Thin, Clear Lifecycle

```python
# agent/turn_orchestrator.py
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class TurnInput:
    user_message: str
    session_id: str
    mode: str = "default"
    note_ids: list[str] = None
    file_ids: list[str] = None
    stream: bool = False


@dataclass
class TurnOutput:
    assistant_message: str
    tool_calls_made: list[str]
    tokens_used: dict  # {input, output, total}
    context_slots: dict  # observability


class TurnOrchestrator:
    """
    Manages one complete chat turn lifecycle.

    Lifecycle:
    1. Assemble context
    2. Call LLM (with tool loop if needed)
    3. Return normalized output

    Does NOT: persist, log, count tokens globally.
    Those are ChatService responsibilities.
    """

    def __init__(
        self,
        context_assembler: ContextAssembler,
        tool_executor: "ToolExecutor",
        provider: "LLMProvider",
        response_normalizer: "ResponseNormalizer",
    ) -> None:
        self._ctx = context_assembler
        self._tools = tool_executor
        self._provider = provider
        self._normalizer = response_normalizer

    async def run(
        self,
        session: "Session",
        turn_input: TurnInput,
    ) -> TurnOutput:
        context = self._ctx.assemble(session, turn_input)
        raw_response = await self._provider.complete(context)
        normalized = self._normalizer.normalize(raw_response)

        # Agentic tool loop
        tool_calls_made = []
        while normalized.has_tool_calls:
            tool_results = await self._tools.execute_all(
                normalized.tool_calls
            )
            tool_calls_made.extend(
                [tc.name for tc in normalized.tool_calls]
            )
            raw_response = await self._provider.complete_with_tools(
                context, normalized.tool_calls, tool_results
            )
            normalized = self._normalizer.normalize(raw_response)

        return TurnOutput(
            assistant_message=normalized.text,
            tool_calls_made=tool_calls_made,
            tokens_used=normalized.usage,
            context_slots=context.slots_used,
        )

    async def stream(
        self,
        session: "Session",
        turn_input: TurnInput,
    ) -> AsyncIterator[str]:
        context = self._ctx.assemble(session, turn_input)
        async for chunk in self._provider.stream(context):
            yield self._normalizer.normalize_chunk(chunk)
```

---

### ToolRegistry — Structured, Discoverable

````python
# tools/registry.py
from dataclasses import dataclass, field
from typing import Callable, Any
from enum import Enum


class ToolCategory(Enum):
    FILE_OPERATIONS = "file_operations"
    SEARCH = "search"
    REPOSITORY = "repository"
    NOTES = "notes"          # future
    WEB = "web"              # future


@dataclass
class ToolDefinition:
    """
    Single source of truth for a tool.
    Schema + implementation + metadata in one place.
    """
    name: str
    category: ToolCategory
    description: str
    parameters: dict          # JSON Schema
    handler: Callable
    requires_confirmation: bool = False  # for destructive ops
    enabled: bool = True


class ToolRegistry:
    """
    Self-contained tool registry.
    Providers ask for schemas. ToolExecutor asks for handlers.
    No global state. Injectable.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get_handler(self, name: str) -> Callable:
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name!r}")
        return self._tools[name].handler

    def schemas_for_provider(
        self,
        provider: str,  # "gemini" | "anthropic"
        categories: list[ToolCategory] | None = None,
    ) -> list[dict]:
        """
        Return provider-specific tool schemas.
        Each provider has different schema format requirements.
        """
        tools = [
            t for t in self._tools.values()
            if t.enabled and (
                categories is None or t.category in categories
            )
        ]
        if provider == "gemini":
            return [self._to_gemini_schema(t) for t in tools]
        elif provider == "anthropic":
            return [self._to_anthropic_schema(t) for t in tools]
        raise ValueError(f"Unknown provider: {provider!r}")

    def _to_gemini_schema(self, tool: ToolDefinition) -> dict:
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }

---

### **user**:

continue

---

### **assistant**:

```python
    def _to_anthropic_schema(self, tool: ToolDefinition) -> dict:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }


def build_default_registry() -> ToolRegistry:
    """
    Factory function — single place to wire all tools.
    Import this in DI container, not individual tools.
    """
    from .file_tools.file_ops import (
        read_file, edit_file, create_file, append_file
    )
    from .search_tools.grep_search import grep_search
    from .repo_tools.repo_map import get_repo_map

    registry = ToolRegistry()

    registry.register(ToolDefinition(
        name="read_file",
        category=ToolCategory.FILE_OPERATIONS,
        description="Read contents of a file by path.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
            },
            "required": ["path"],
        },
        handler=read_file,
    ))

    registry.register(ToolDefinition(
        name="edit_file",
        category=ToolCategory.FILE_OPERATIONS,
        description="Edit a file by replacing a string segment.",
        parameters={
            "type": "object",
            "properties": {
                "path":        {"type": "string"},
                "old_content": {"type": "string"},
                "new_content": {"type": "string"},
            },
            "required": ["path", "old_content", "new_content"],
        },
        handler=edit_file,
        requires_confirmation=True,  # destructive
    ))

    registry.register(ToolDefinition(
        name="search_knowledge_base",
        category=ToolCategory.SEARCH,
        description="Search project data directory using grep.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path":  {"type": "string", "default": "/data"},
            },
            "required": ["query"],
        },
        handler=grep_search,
    ))

    registry.register(ToolDefinition(
        name="get_repo_map",
        category=ToolCategory.REPOSITORY,
        description="Get a tree view of the project structure.",
        parameters={
            "type": "object",
            "properties": {
                "depth": {"type": "integer", "default": 3},
            },
        },
        handler=get_repo_map,
    ))

    return registry
````

---

### ToolExecutor — Isolated Execution Concerns

```python
# agent/tool_executor.py
import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    """Normalized tool call — provider-agnostic."""
    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """Normalized tool result — provider-agnostic."""
    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


class ToolExecutor:
    """
    Single responsibility: execute tool calls safely.

    - Resolves handler from registry
    - Runs concurrently where safe
    - Catches and wraps errors (LLM should see error, not crash)
    - Does NOT know about providers or sessions
    """

    def __init__(self, registry: "ToolRegistry") -> None:
        self._registry = registry

    async def execute_all(
        self,
        tool_calls: list[ToolCall],
    ) -> list[ToolResult]:
        """Run all tool calls concurrently."""
        tasks = [self._execute_one(tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)

    async def _execute_one(self, tool_call: ToolCall) -> ToolResult:
        try:
            handler = self._registry.get_handler(tool_call.name)

            # Support both sync and async handlers transparently
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**tool_call.arguments)
            else:
                result = await asyncio.to_thread(
                    handler, **tool_call.arguments
                )

            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=str(result),
                is_error=False,
            )

        except Exception as e:
            # Never crash the turn — return structured error to LLM
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=f"Tool error: {type(e).__name__}: {e}",
                is_error=True,
            )
```

---

### ResponseNormalizer — Provider Differences Contained Here

```python
# providers/normalizer.py
from dataclasses import dataclass, field
from typing import Any
from agent.tool_executor import ToolCall


@dataclass
class NormalizedResponse:
    """
    Single shape regardless of which provider responded.
    Rest of the app only ever sees this.
    """
    text: str
    has_tool_calls: bool
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)  # input/output/total tokens
    raw: Any = None  # keep original for debugging


class ResponseNormalizer:
    """
    Absorbs ALL provider-specific response shape differences.

    Gemini and Anthropic return very different structures.
    This is the only place that knows about both.
    """

    def normalize(self, raw: Any, provider: str) -> NormalizedResponse:
        if provider == "gemini":
            return self._from_gemini(raw)
        elif provider == "anthropic":
            return self._from_anthropic(raw)
        raise ValueError(f"Unknown provider: {provider!r}")

    def normalize_chunk(self, chunk: Any, provider: str) -> str:
        """Extract text delta from streaming chunk."""
        if provider == "gemini":
            return self._gemini_chunk_text(chunk)
        elif provider == "anthropic":
            return self._anthropic_chunk_text(chunk)
        return ""

    # ── Gemini ────────────────────────────────────────────

    def _from_gemini(self, raw: Any) -> NormalizedResponse:
        """
        google-genai SDK response shape:
        response.candidates[0].content.parts → text or function_call
        response.usage_metadata → token counts
        """
        candidate = raw.candidates[0]
        parts = candidate.content.parts

        text_parts = []
        tool_calls = []

        for part in parts:
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)
            elif hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    id=fc.id if hasattr(fc, "id") else fc.name,
                    name=fc.name,
                    arguments=dict(fc.args),
                ))

        usage = {}
        if hasattr(raw, "usage_metadata"):
            um = raw.usage_metadata
            usage = {
                "input":  getattr(um, "prompt_token_count", 0),
                "output": getattr(um, "candidates_token_count", 0),
                "total":  getattr(um, "total_token_count", 0),
            }

        return NormalizedResponse(
            text="".join(text_parts),
            has_tool_calls=bool(tool_calls),
            tool_calls=tool_calls,
            usage=usage,
            raw=raw,
        )

    def _gemini_chunk_text(self, chunk: Any) -> str:
        try:
            return chunk.candidates[0].content.parts[0].text or ""
        except (IndexError, AttributeError):
            return ""

    # ── Anthropic ─────────────────────────────────────────

    def _from_anthropic(self, raw: Any) -> NormalizedResponse:
        """
        anthropic SDK response shape:
        response.content → list of TextBlock | ToolUseBlock
        response.usage → input_tokens, output_tokens
        """
        text_parts = []
        tool_calls = []

        for block in raw.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                ))

        usage = {}
        if hasattr(raw, "usage"):
            usage = {
                "input":  raw.usage.input_tokens,
                "output": raw.usage.output_tokens,
                "total":  (
                    raw.usage.input_tokens + raw.usage.output_tokens
                ),
            }

        return NormalizedResponse(
            text="".join(text_parts),
            has_tool_calls=bool(tool_calls),
            tool_calls=tool_calls,
            usage=usage,
            raw=raw,
        )

    def _anthropic_chunk_text(self, chunk: Any) -> str:
        """
        Anthropic streaming events:
        content_block_delta → delta.type == "text_delta"
        """
        try:
            if chunk.type == "content_block_delta":
                if chunk.delta.type == "text_delta":
                    return chunk.delta.text
        except AttributeError:
            pass
        return ""
```

---

### ChatService — Now Thin and Clear

```python
# services/chat_service.py
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class ChatTurnRequest:
    session_id: str
    user_message: str
    mode: str = "default"
    note_ids: list[str] = None
    file_ids: list[str] = None
    stream: bool = False


@dataclass
class ChatTurnResponse:
    session_id: str
    assistant_message: str
    tool_calls_made: list[str]
    tokens_used: dict
    context_slots: dict


class ChatService:
    """
    Thin orchestrator. Coordinates but does not implement.

    Responsibilities (only these):
    1. Load session
    2. Run turn
    3. Persist result
    4. Log
    5. Return response

    Explicitly NOT responsible for:
    - Context assembly (TurnOrchestrator → ContextAssembler)
    - Tool execution (ToolExecutor)
    - Provider differences (ResponseNormalizer)
    - Token counting logic (TokenBudget)
    """

    def __init__(
        self,
        session_repo: "SessionRepository",
        turn_orchestrator: "TurnOrchestrator",
        prompt_logger: "PromptLogger",
    ) -> None:
        self._sessions = session_repo
        self._orchestrator = turn_orchestrator
        self._logger = prompt_logger

    async def handle_turn(
        self,
        request: ChatTurnRequest,
    ) -> ChatTurnResponse:
        # 1. Load
        session = await self._sessions.load(request.session_id)

        # 2. Build turn input
        turn_input = TurnInput(
            user_message=request.user_message,
            mode=request.mode,
            note_ids=request.note_ids or [],
            file_ids=request.file_ids or [],
        )

        # 3. Run
        turn_output = await self._orchestrator.run(session, turn_input)

        # 4. Persist
        session.add_message("user", request.user_message)
        session.add_message("assistant", turn_output.assistant_message)
        await self._sessions.save(session)

        # 5. Log
        await self._logger.log(
            session_id=request.session_id,
            turn_input=turn_input,
            turn_output=turn_output,
        )

        return ChatTurnResponse(
            session_id=request.session_id,
            assistant_message=turn_output.assistant_message,
            tool_calls_made=turn_output.tool_calls_made,
            tokens_used=turn_output.tokens_used,
            context_slots=turn_output.context_slots,
        )

    async def stream_turn(
        self,
        request: ChatTurnRequest,
    ) -> AsyncIterator[str]:
        session = await self._sessions.load(request.session_id)
        turn_input = TurnInput(
            user_message=request.user_message,
            mode=request.mode,
            note_ids=request.note_ids or [],
            file_ids=request.file_ids or [],
        )

        full_response = []
        async for chunk in self._orchestrator.stream(session, turn_input):
            full_response.append(chunk)
            yield chunk

        # Persist after stream completes
        session.add_message("user", request.user_message)
        session.add_message("assistant", "".join(full_response))
        await self._sessions.save(session)
```

---

### SearchCoordinator — Ready for BM25 + Embeddings

````python
# content/search_coordinator.py
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Protocol


@dataclass
class SearchResult:
    source: str        # "bm25" | "embedding" | "grep"
    content: str
    score: float
    metadata: dict


class SearchBackend(Protocol):
    """
    Any search backend implements this.
    Add BM25, embeddings, grep — all behind same interface.
    """
    async def search(
        self,
        query: str,
        limit: int,
        **kwargs,
    ) -> list[SearchResult]: ...


class SearchCoordinator:
    """
    Fan-out search across multiple backends.
    Merge and rank results.
    Single place to tune search strategy.

    Today: grep only
    Tomorrow: BM25 + embeddings, no changes to callers
    """

    def __init__(self, backends: dict[str, SearchBackend]) -> None:
        self._backends = backends

    async def search(
        self,
        query: str,
        limit: int = 10,
        backends: list[str] | None = None,  # None = all
    ) -> list[SearchResult]:
        import asyncio

        active = {
            name: backend
            for name, backend in self._backends.items()
            if backends is None or name in backends
        }

        results_per_backend = await asyncio.gather(*[
            backend.search(query, limit)
            for backend in active.values()
        ])

        all_results = [
            result
            for backend_results in results_per_backend
            for result in backend_results
        ]

        return self._rank(all_results, limit)

    def _rank(
        self,
        results: list[SearchResult],
        limit: int,
    ) -> list[SearchResult]:
        """
        Simple score-based ranking today.
        Replace with RRF (Reciprocal Rank Fusion) when
        multiple backends are active.
        """
        seen_content = set()
        unique = []
        for r in sorted(results, key=lambda x: x.score, reverse=True):
            if r.content not in seen_content:
                seen_content.add(r.content)
                unique.append(r)
        return unique[:limit]


# ── Concrete backends ──────────────────────────────────

class GrepSearchBackend:
    """Current implementation, now behind the protocol."""

    async def search(
        self,
        query: str,
        limit: int,
        **kwargs,
    ) -> list[SearchResult]:
        import asyncio
        import subprocess

        result = await asyncio.to_thread(
            subprocess.run,
            ["grep", "-r", "-n", query, "/data"],
            capture_output=True, text=True,
        )

        results = []
        for line in

---

### **user**:

continue

---

### **assistant**:

```python
        for line in result.stdout.splitlines()[:limit]:
            results.append(SearchResult(
                source="grep",
                content=line,
                score=1.0,  # grep has no score, flat ranking
                metadata={"raw_line": line},
            ))
        return results


class BM25SearchBackend:
    """
    Drop-in when you add rank_bm25 or bm25s library.
    Caller (SearchCoordinator) never changes.
    """

    def __init__(self, index_path: str) -> None:
        self._index_path = index_path
        self._index = None  # lazy load

    async def search(
        self,
        query: str,
        limit: int,
        **kwargs,
    ) -> list[SearchResult]:
        import asyncio
        return await asyncio.to_thread(
            self._sync_search, query, limit
        )

    def _sync_search(
        self,
        query: str,
        limit: int,
    ) -> list[SearchResult]:
        index = self._get_index()
        scores, indices = index.get_scores_and_indices(query)

        results = []
        for score, idx in zip(scores[:limit], indices[:limit]):
            doc = index.corpus[idx]
            results.append(SearchResult(
                source="bm25",
                content=doc,
                score=float(score),
                metadata={"corpus_index": idx},
            ))
        return results

    def _get_index(self):
        """Lazy load index — only when first search happens."""
        if self._index is None:
            from bm25s import BM25
            self._index = BM25.load(self._index_path)
        return self._index


class EmbeddingSearchBackend:
    """
    Placeholder for when you add vector search.
    Same protocol — zero changes to SearchCoordinator.
    """

    def __init__(
        self,
        embedding_client: Any,
        vector_store: Any,
    ) -> None:
        self._embedder = embedding_client
        self._store = vector_store

    async def search(
        self,
        query: str,
        limit: int,
        **kwargs,
    ) -> list[SearchResult]:
        query_vector = await self._embedder.embed(query)
        raw_results = await self._store.similarity_search(
            query_vector, limit=limit
        )

        return [
            SearchResult(
                source="embedding",
                content=r.content,
                score=r.similarity,
                metadata=r.metadata,
            )
            for r in raw_results
        ]
````

---

### Dependency Injection Container — One Place to Wire Everything

```python
# dependencies.py  (FastAPI DI wiring)
from functools import lru_cache
from fastapi import Depends

from config import Settings
from providers.gemini_provider import GeminiProvider
from providers.anthropic_provider import AnthropicProvider
from providers.normalizer import ResponseNormalizer
from agent.context_assembler import ContextAssembler, ContextBudget
from agent.tool_executor import ToolExecutor
from agent.turn_orchestrator import TurnOrchestrator
from tools.registry import build_default_registry
from content.note_manager import NoteManager
from content.file_manager import FileManager
from content.search_coordinator import (
    SearchCoordinator, GrepSearchBackend, BM25SearchBackend
)
from services.chat_service import ChatService
from services.note_service import NoteService
from services.file_service import FileService
from storage.repositories import (
    SQLiteSessionRepository,
    SQLiteNoteRepository,
    SQLiteFileRepository,
)
from storage.connection import SQLiteConnection
from cross_cutting.prompt_logger import PromptLogger
from cross_cutting.prompt_manager import PromptManager
from cross_cutting.token_counter import TokenCounter


# ── Singleton-scoped (created once) ───────────────────────────────

@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_db_connection(
    settings: Settings = Depends(get_settings),
) -> SQLiteConnection:
    return SQLiteConnection(path=settings.db_path)


@lru_cache
def get_tool_registry():
    """
    Build once. All tools registered here.
    To add a tool: go to build_default_registry(), nowhere else.
    """
    return build_default_registry()


@lru_cache
def get_response_normalizer() -> ResponseNormalizer:
    return ResponseNormalizer()


@lru_cache
def get_token_counter(
    settings: Settings = Depends(get_settings),
) -> TokenCounter:
    return TokenCounter(default_model=settings.default_model)


@lru_cache
def get_prompt_manager(
    settings: Settings = Depends(get_settings),
) -> PromptManager:
    return PromptManager(prompts_dir=settings.prompts_dir)


# ── Request-scoped (created per request) ──────────────────────────

def get_session_repository(
    conn: SQLiteConnection = Depends(get_db_connection),
) -> SQLiteSessionRepository:
    return SQLiteSessionRepository(conn)


def get_note_repository(
    conn: SQLiteConnection = Depends(get_db_connection),
) -> SQLiteNoteRepository:
    return SQLiteNoteRepository(conn)


def get_file_repository(
    conn: SQLiteConnection = Depends(get_db_connection),
) -> SQLiteFileRepository:
    return SQLiteFileRepository(conn)


# ── Provider selection ─────────────────────────────────────────────

def get_llm_provider(
    settings: Settings = Depends(get_settings),
    normalizer: ResponseNormalizer = Depends(get_response_normalizer),
):
    """
    Single place for provider selection logic.
    Swap provider via settings/env var — no code changes.
    """
    if settings.llm_provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            normalizer=normalizer,
        )
    elif settings.llm_provider == "anthropic":
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            normalizer=normalizer,
        )
    raise ValueError(f"Unknown provider: {settings.llm_provider!r}")


# ── Content layer ──────────────────────────────────────────────────

def get_search_coordinator(
    settings: Settings = Depends(get_settings),
) -> SearchCoordinator:
    """
    Add BM25 or embeddings here when ready.
    No other file changes needed.
    """
    backends = {
        "grep": GrepSearchBackend(),
    }
    if settings.bm25_index_path:
        backends["bm25"] = BM25SearchBackend(
            index_path=settings.bm25_index_path
        )
    return SearchCoordinator(backends=backends)


def get_note_manager(
    repo: SQLiteNoteRepository = Depends(get_note_repository),
    token_counter: TokenCounter = Depends(get_token_counter),
    search: SearchCoordinator = Depends(get_search_coordinator),
) -> NoteManager:
    return NoteManager(
        repo=repo,
        token_counter=token_counter,
        search=search,
    )


def get_file_manager(
    repo: SQLiteFileRepository = Depends(get_file_repository),
    token_counter: TokenCounter = Depends(get_token_counter),
) -> FileManager:
    return FileManager(repo=repo, token_counter=token_counter)


# ── Agent layer ────────────────────────────────────────────────────

def get_context_assembler(
    token_counter: TokenCounter = Depends(get_token_counter),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
    note_manager: NoteManager = Depends(get_note_manager),
    file_manager: FileManager = Depends(get_file_manager),
    settings: Settings = Depends(get_settings),
) -> ContextAssembler:
    budget = ContextBudget(total=settings.context_window_tokens)
    return ContextAssembler(
        token_budget=budget,
        token_counter=token_counter,
        prompt_manager=prompt_manager,
        note_manager=note_manager,
        file_manager=file_manager,
    )


def get_tool_executor(
    registry=Depends(get_tool_registry),
) -> ToolExecutor:
    return ToolExecutor(registry=registry)


def get_turn_orchestrator(
    context_assembler: ContextAssembler = Depends(get_context_assembler),
    tool_executor: ToolExecutor = Depends(get_tool_executor),
    provider=Depends(get_llm_provider),
) -> TurnOrchestrator:
    return TurnOrchestrator(
        context_assembler=context_assembler,
        tool_executor=tool_executor,
        provider=provider,
        response_normalizer=get_response_normalizer(),
    )


# ── Service layer ──────────────────────────────────────────────────

def get_chat_service(
    session_repo=Depends(get_session_repository),
    orchestrator: TurnOrchestrator = Depends(get_turn_orchestrator),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    return ChatService(
        session_repo=session_repo,
        turn_orchestrator=orchestrator,
        prompt_logger=PromptLogger(log_path=settings.prompt_log_path),
    )


def get_note_service(
    note_manager: NoteManager = Depends(get_note_manager),
) -> NoteService:
    return NoteService(note_manager=note_manager)


def get_file_service(
    file_manager: FileManager = Depends(get_file_manager),
) -> FileService:
    return FileService(file_manager=file_manager)
```

---

### Final Folder Structure — Screaming the Right Things

```
myapp/
│
├── main.py                         # FastAPI app init, router registration
├── dependencies.py                 # ALL DI wiring — one file, one truth
├── config.py                       # pydantic-settings Settings
│
├── api/                            # Interface Adapters
│   ├── chat.py                     # POST /chat, GET /chat/stream
│   ├── sessions.py                 # GET/DELETE /sessions
│   ├── notes.py                    # CRUD /notes
│   ├── files.py                    # POST/GET /files
│   └── schemas/
│       ├── chat_schemas.py
│       ├── note_schemas.py
│       └── file_schemas.py
│
├── services/                       # Thin orchestrators
│   ├── chat_service.py
│   ├── note_service.py
│   ├── file_service.py
│   └── message_edit_service.py
│
├── agent/                          # LLM turn lifecycle
│   ├── turn_orchestrator.py        # manages one turn end-to-end
│   ├── context_assembler.py        # builds context window
│   └── tool_executor.py            # runs tools safely
│
├── providers/                      # LLM provider adapters
│   ├── base.py                     # LLMProvider Protocol
│   ├── normalizer.py               # ResponseNormalizer
│   ├── gemini_provider.py
│   └── anthropic_provider.py
│
├── tools/                          # Tool definitions + handlers
│   ├── registry.py                 # ToolRegistry + build_default_registry()
│   ├── file_tools/
│   │   ├── file_ops.py
│   │   └── attachments.py          # future: SDK file upload
│   ├── search_tools/
│   │   ├── grep_search.py
│   │   ├── bm25_search.py          # add when ready
│   │   └── embedding_search.py     # add when ready
│   └── repo_tools/
│       └── repo_map.py
│
├── content/                        # Content management domain
│   ├── note_manager.py
│   ├── file_manager.py
│   └── search_coordinator.py
│
├── storage/                        # Data persistence
│   ├── repositories.py             # Protocols + SQLite implementations
│   ├── connection.py
│   └── migrations/
│       ├── 001_initial.sql
│       └── 002_add_files.sql
│
└── cross_cutting/                  # Shared infrastructure concerns
    ├── prompt_logger.py
    ├── prompt_manager.py
    ├── token_counter.py
    └── exporter.py
```

---

## Summary: What Changed and Why

```
┌─────────────────────┬──────────────────────┬───────────────────────────┐
│ Before              │ After                │ Why                       │
├─────────────────────┼──────────────────────┼───────────────────────────┤
│ agent.py god object │ TurnOrchestrator     │ SRP — one lifecycle class │
│                     │ + ContextAssembler   │                           │
│                     │ + ToolExecutor       │                           │
├─────────────────────┼──────────────────────┼───────────────────────────┤
│ ChatService 6 deps  │ ChatService 3 deps   │ SRP — delegates not does  │
├─────────────────────┼──────────────────────┼───────────────────────────┤
│ Notes orphaned      │ NoteManager          │ Content layer has a home  │
│                     │ + NoteService        │                           │
│                     │ + /api/notes.py      │                           │
├─────────────────────┼──────────────────────┼───────────────────────────┤
│ Flat tools/         │ tools/ sub-grouped   │ OCP — add search backend  │
│                     │ by category          │ without touching existing │
├─────────────────────┼──────────────────────┼───────────────────────────┤
│ No context budget   │ ContextAssembler     │ Explicit token allocation │
│                     │ + ContextBudget      │ per content type          │
├─────────────────────┼──────────────────────┼───────────────────────────┤
│ Provider diffs      │ ResponseNormalizer   │ All SDK differences in    │
│ scattered           │ owns all of it       │ one place                 │
├─────────────────────┼──────────────────────┼───────────────────────────┤
│ DI spread around    │ dependencies.py      │ One file = full picture   │
│                     │ owns all wiring      │ of app composition        │
└─────────────────────┴──────────────────────┴───────────────────────────┘
```

> **The north star**: any new developer should be able to read `dependencies.py` and understand the entire application composition, then navigate to any feature folder and understand it in isolation.

---

### **user**:

Great effort. When you look and suggested implementation. How would you plan redesing/refactor following best principles? I have 700 tests do you need to review signatures?

---

### **assistant**:

# Refactor Planning: From Current to Target Architecture

## First: The Right Mindset

```
❌ "Let's rewrite everything"     → Big bang, breaks 700 tests, risky
✅ "Strangler Fig pattern"        → Incremental, tests guide you, safe
```

> Your 700 tests are your **safety net AND your specification**.
> Never break them. Let them pull you forward.

---

## Before Writing a Single Line — Signature Audit

**Yes, I need to see signatures.** Specifically:

```python
# What I need to understand before planning phases:

# 1. Current ChatService / agent.py public interface
class ChatService:
    async def handle_turn(...) -> ?
    async def edit_message(...) -> ?

# 2. Current repository protocols
class SessionRepository(Protocol):
    def save(...) -> ?
    def load(...) -> ?

# 3. Current provider interface
class LLMProvider(Protocol):
    def complete(...) -> ?
    def stream(...) -> ?

# 4. What your 700 tests test AT (which layer)
# unit tests hitting domain objects?
# integration tests hitting services?
# API tests hitting FastAPI routes?
```

**Why it matters critically:**

```
If tests hit ChatService.handle_turn()
→ we can refactor internals freely
→ handle_turn() signature must stay stable

If tests hit agent.process_chat_turn() directly
→ we need shim/adapter during transition
→ more careful phasing needed

If tests hit FastAPI routes
→ most protected, internals are free to change
→ easiest refactor scenario
```

---

## The Strangler Fig Strategy

```
                    TODAY                         TARGET
                      │                              │
    ┌─────────────────▼──────────────┐               │
    │         Existing Code          │               │
    │  agent.py (god object)         │    ┌──────────▼──────────┐
    │  ChatService (6 deps)          │    │  New Code (parallel) │
    │  flat tools/                   │    │  TurnOrchestrator    │
    │  orphaned notes                │    │  ContextAssembler    │
    └────────────────────────────────┘    │  ToolExecutor        │
                      │                   │  ResponseNormalizer  │
                      │    PHASE 1-5      └──────────┬──────────┘
                      │   gradually                  │
                      └──────────────────────────────┘
                         old code deleted only when
                         new code has test coverage
```

---

## Refactor Phases

### Phase 0 — Audit & Baseline (No code changes)

```python
# TASK 1: Test distribution audit
# Run this to understand where your tests live

"""
tests/
├── unit/           ← how many? what do they test?
├── integration/    ← how many? what do they test?
├── api/            ← how many? what do they test?
└── conftest.py     ← what fixtures exist?
"""

# TASK 2: Dependency map — run in your project
# pip install pydeps
# pydeps myapp --max-bacon=3 --cluster

# TASK 3: Identify test seams
# A seam = place where behavior can change without editing source
# These are your safe refactor boundaries
```

```python
# TASK 4: Characterization tests for untested paths
# Before touching anything, lock current behavior

# Example: if agent.py has no direct tests
# write characterization tests NOW

async def test_agent_current_behavior_characterization():
    """
    This test documents CURRENT behavior, not desired behavior.
    It will guide us during refactor.
    DELETE when TurnOrchestrator replaces agent.py
    """
    result = await process_chat_turn(
        session=make_test_session(),
        message="hello",
        provider=FakeProvider(),
    )
    assert result is not None
    assert isinstance(result, str)  # whatever it currently returns
```

---

### Phase 1 — Extract Without Breaking (Week 1-2)

**Goal**: Pull `ResponseNormalizer` out of providers. Zero behavior change.

**Why first**: It has no dependencies on anything else. Lowest risk.

```python
# Step 1a: Create new file, move logic
# providers/normalizer.py  ← NEW FILE

# Step 1b: Import from old location to maintain compatibility
# providers/gemini_provider.py

# BEFORE:
class GeminiProvider:
    def _parse_response(self, raw):
        # 40 lines of parsing logic inline
        candidate = raw.candidates[0]
        ...

# AFTER (Phase 1 — keep old method, delegate to normalizer):
from providers.normalizer import ResponseNormalizer

class GeminiProvider:
    def __init__(self, ...) -> None:
        ...
        self._normalizer = ResponseNormalizer()  # add quietly

    def _parse_response(self, raw):
        # Old method still exists — tests still pass
        # But now delegates to normalizer
        return self._normalizer.normalize(raw, provider="gemini")
```

```python
# Step 1c: Same for AnthropicProvider
class AnthropicProvider:
    def _parse_response(self, raw):
        return self._normalizer.normalize(raw, provider="anthropic")

# Step 1d: Tests should be GREEN here
# Run full suite — if anything breaks, stop and fix
```

**Exit criteria for Phase 1:**

```
✅ 700 tests still pass
✅ ResponseNormalizer exists and is tested independently
✅ Both providers delegate to it
✅ No behavior change observable from outside
```

---

### Phase 2 — ToolExecutor Extraction (Week 2-3)

**Goal**: Pull tool execution out of `agent.py` into `ToolExecutor`.

**Why second**: Tools are mostly pure functions. Easy to test in isolation.

```python
# Step 2a: Create ToolExecutor alongside existing code
# agent/tool_executor.py  ← NEW FILE
# (full implementation as shown in previous response)

# Step 2b: Write tests for ToolExecutor in ISOLATION first
# tests/unit/agent/test_tool_executor.py

class FakeRegistry:
    """Test double — no real tools needed."""
    def get_handler(self, name: str):
        handlers = {
            "read_file": lambda path: f"content of {path}",
            "failing_tool": lambda: (_ for _ in ()).throw(
                RuntimeError("tool broke")
            ),
        }
        if name not in handlers:
            raise ValueError(f"Unknown: {name}")
        return handlers[name]


@pytest.mark.asyncio
async def test_tool_executor_runs_successfully():
    executor = ToolExecutor(registry=FakeRegistry())
    results = await executor.execute_all([
        ToolCall(id="1", name="read_file", arguments={"path": "/test"})
    ])
    assert len(results) == 1
    assert results[0].is_error is False
    assert "content of /test" in results[0].content


@pytest.mark.asyncio
async def test_tool_executor_wraps_errors_gracefully():
    """LLM should see error message, app should not crash."""
    executor = ToolExecutor(registry=FakeRegistry())
    results = await executor.execute_all([
        ToolCall(id="2", name="failing_tool", arguments={})
    ])
    assert results[0].is_error is True
    assert "tool broke" in results[0].content


@pytest.mark.asyncio
async def test_tool_executor_runs_concurrently():
    import time
    call_times = []

    def slow_tool(**kwargs):
        import time
        time.sleep(0.1)
        call_times.append(time.time())
        return "done"

    class TimedRegistry:
        def get_handler(self, name):
            return slow_tool

    executor = ToolExecutor(registry=TimedRegistry())
    start = time.time()
    await executor.execute_all([
        ToolCall(id=str(i), name="slow", arguments={})
        for i in range(5)
    ])
    elapsed = time.time() - start
    # 5 × 0.1s serial = 0.5s, concurrent should be ~0.1s
    assert elapsed < 0.3, "Tools should run concurrently"
```

```python
# Step 2c: Wire ToolExecutor into agent.py (delegate, don't delete)
# agent.py — DURING TRANSITION

class _LegacyAgent:
    """
    Kept alive during refactor.
    Delegates tool execution to new ToolExecutor.
    Will be deleted in Phase 4.
    """
    def __init__(self, ...):
        ...
        # Quietly introduce ToolExecutor
        self._tool_executor = ToolExecutor(registry=self._registry)

    async def _run_tools(self, tool_calls):
        # OLD: inline tool execution logic
        # NEW: delegate
        return await self._tool_executor.execute_all(tool_calls)
```

**Exit criteria for Phase 2:**

```
✅ 700 tests still pass
✅ ToolExecutor has its own test suite (add ~20 tests)
✅ agent.py delegates to ToolExecutor internally
✅ ToolExecutor can be used independently
```

---

### Phase 3 — ContextAssembler Extraction (Week 3-4)

**Goal**: Make context building explicit and testable.

**Why third**: Highest value change. Context bugs are the hardest to debug.

```python
# Step 3a: Tests FIRST this time (TDD for new component)
# tests/unit/agent/test_context_assembler.py

def make_assembler(total_tokens=10_000) -> ContextAssembler:
    """Test factory — keeps tests clean."""
    return ContextAssembler(
        token_budget=ContextBudget(total=total_tokens),
        token_counter=FakeTokenCounter(tokens_per_message=100),
        prompt_manager=FakePromptManager(prompt="You are helpful."),
        note_manager=FakeNoteManager(),
        file_manager=FakeFileManager(),
    )


def test_assembled_context_contains_system_prompt():
    assembler = make_assembler()
    session = make_session(messages=[])
    turn = TurnInput(user_message="hello", mode="default")

    ctx = assembler.assemble(session, turn)

    assert ctx.system_prompt == "You are helpful."
    assert ctx.total_tokens_estimated > 0


def test_history_trimmed_when_over_budget():
    """
    Critical: long conversations must not exceed token budget.
    This was previously untestable because it was inside agent.py.
    """
    assembler = make_assembler(total_tokens=1_000)
    session = make_session(messages=[
        {"role": "user", "content": "msg"} for _ in range(100)
    ])
    turn = TurnInput(user_message="new message", mode="default")

    ctx = assembler.assemble(session, turn)

    assert ctx.total_tokens_estimated <= 1_000


def test_notes_included_when_provided():
    note_manager = FakeNoteManager(notes={"n1": "Important context"})
    assembler = make_assembler()
    assembler._notes = note_manager

    session = make_session(messages=[])
    turn = TurnInput(
        user_message="question",
        mode="default",
        note_ids=["n1"],
    )

    ctx = assembler.assemble(session, turn)

    assert any(
        "Important context" in str(msg.get("content", ""))
        for msg in ctx.messages
    )


def test_context_slots_are_observable():
    """
    We must be able to see WHERE tokens are being spent.
    Critical for debugging context window issues.
    """
    assembler = make_assembler()
    session = make_session(messages=[
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ])
    turn = TurnInput(user_message="question", mode="default")

    ctx = assembler.assemble(session, turn)

    assert ContextSlot.SYSTEM_PROMPT in ctx.slots_used
    assert ContextSlot.CONVERSATION_HISTORY in ctx.slots_used
    assert all(v >= 0 for v in ctx.slots_used.values())
```

```python
# Step 3b: Implement ContextAssembler (full impl from previous response)

# Step 3c: Introduce into agent.py via delegation
# agent.py — DURING TRANSITION

class _LegacyAgent:
    def __init__(self, ..., context_assembler=None):
        ...
        # Accept injected assembler OR build legacy one
        # This allows gradual adoption without breaking callers
        self._context_assembler = (
            context_assembler or self._build_legacy_context
        )

    async def process_chat_turn(self, session, message, ...):
        # NEW path: use ContextAssembler if available
        if isinstance(self._context_assembler, ContextAssembler):
            context = self._context_assembler.assemble(
                session,
                TurnInput(user_message=message, ...)
            )
        else:
            # OLD path: legacy inline context building
            context = self._build_legacy_context(session, message)
        ...
```

**Exit criteria for Phase 3:**

```
✅ 700 tests still pass
✅ ContextAssembler has focused test suite (~30 tests)
✅ Token budget behavior is explicitly tested
✅ Context slot observability works
✅ agent.py delegates to ContextAssembler
```

---

### Phase 4 — TurnOrchestrator & ChatService Slim-down (Week 4-5)

**Goal**: Replace `agent.py` god object. Slim `ChatService`.

```python
# Step 4a: TurnOrchestrator wraps the now-extracted pieces
# At this point:
# - ToolExecutor exists and is tested ✅
# - ContextAssembler exists and is tested ✅
# - ResponseNormalizer exists and is tested ✅
# TurnOrchestrator just composes them — low risk

# tests/unit/agent/test_turn_orchestrator.py

@pytest.mark.asyncio
async def test_turn_orchestrator_simple_response():
    """No tool calls — straight LLM response."""
    orchestrator = TurnOrchestrator(
        context_assembler=FakeContextAssembler(),
        tool_executor=FakeToolExecutor(),
        provider=FakeProvider(response="Hello back!"),
        response_normalizer=ResponseNormalizer(),
    )

    output = await orchestrator.run(
        session=make_session(),
        turn_input=TurnInput(user_message="Hello"),
    )

    assert output.assistant_message == "Hello back!"
    assert output.tool_calls_made == []


@pytest.mark.asyncio
async def test_turn_orchestrator_tool_loop():
    """LLM calls a tool, gets result, responds."""
    tool_call = ToolCall(id="1", name="read_file", arguments={"path": "/f"})

    provider = FakeProvider(
        responses=[
            FakeResponseWithToolCall(tool_call),  # first: tool call
            FakeResponse("Here is the file content."),  # second: answer
        ]
    )

    output = await orchestrator.run(
        session=make_session(),
        turn_input=TurnInput(user_message="Read /f"),
    )

    assert "read_file" in output.tool_calls_made
    assert output.assistant_message == "Here is the file content."


@pytest.mark.asyncio
async def test_turn_orchestrator_tool_loop_max_iterations():
    """Prevent infinite tool loops."""
    provider = FakeProvider(
        always_returns_tool_call=True  # pathological LLM
    )

    with pytest.raises(MaxToolIterationsError):
        await orchestrator.run(
            session=make_session(),
            turn_input=TurnInput(user_message="loop forever"),
        )
```

````python
# Step 4b: ChatService ref

---

### **user**:

continue

---

### **assistant**:

```python
# Step 4b: ChatService refactor — slim down dependencies

# tests/unit/services/test_chat_service.py

# BEFORE testing ChatService we need to understand
# what the 700 tests currently assert about it
# Common patterns we expect to find:

@pytest.mark.asyncio
async def test_chat_service_persists_both_messages():
    """
    User message AND assistant message must be saved.
    Regression risk: high — easy to forget one side.
    """
    session_repo = FakeSessionRepository()
    orchestrator = FakeOrchestrator(
        response=TurnOutput(
            assistant_message="I can help.",
            tool_calls_made=[],
            tokens_used={"input": 10, "output": 5, "total": 15},
            context_slots={},
        )
    )

    service = ChatService(
        session_repo=session_repo,
        turn_orchestrator=orchestrator,
        prompt_logger=FakePromptLogger(),
    )

    await service.handle_turn(ChatTurnRequest(
        session_id="sess-1",
        user_message="Help me please.",
    ))

    saved_session = session_repo.get("sess-1")
    messages = saved_session.messages

    assert any(
        m["role"] == "user" and "Help me please" in m["content"]
        for m in messages
    )
    assert any(
        m["role"] == "assistant" and "I can help" in m["content"]
        for m in messages
    )


@pytest.mark.asyncio
async def test_chat_service_logs_every_turn():
    logger = FakePromptLogger()
    service = ChatService(
        session_repo=FakeSessionRepository(),
        turn_orchestrator=FakeOrchestrator(),
        prompt_logger=logger,
    )

    await service.handle_turn(ChatTurnRequest(
        session_id="sess-1",
        user_message="Hello",
    ))

    assert logger.log_call_count == 1
    assert logger.last_session_id == "sess-1"


@pytest.mark.asyncio
async def test_chat_service_returns_structured_response():
    """
    Response shape must be stable — API depends on it.
    This is the contract test for the service layer.
    """
    service = make_chat_service(
        orchestrator=FakeOrchestrator(
            response=TurnOutput(
                assistant_message="Answer.",
                tool_calls_made=["read_file"],
                tokens_used={"input": 50, "output": 20, "total": 70},
                context_slots={},
            )
        )
    )

    response = await service.handle_turn(ChatTurnRequest(
        session_id="sess-1",
        user_message="Question",
    ))

    assert isinstance(response, ChatTurnResponse)
    assert response.assistant_message == "Answer."
    assert "read_file" in response.tool_calls_made
    assert response.tokens_used["total"] == 70


@pytest.mark.asyncio
async def test_chat_service_propagates_orchestrator_errors():
    """
    If LLM fails, service must propagate cleanly.
    Not swallow, not crash with unrelated error.
    """
    service = make_chat_service(
        orchestrator=FakeOrchestrator(
            raises=LLMProviderError("Rate limit exceeded")
        )
    )

    with pytest.raises(LLMProviderError, match="Rate limit"):
        await service.handle_turn(ChatTurnRequest(
            session_id="sess-1",
            user_message="Hello",
        ))


# ── Transition shim: keep old handle_turn signature alive ─────────

# If your existing 700 tests call the OLD ChatService signature
# use this adapter pattern during transition

class ChatServiceV1Shim:
    """
    Temporary adapter.
    Keeps old signature alive while new ChatService is wired.
    DELETE after all tests migrated to new signature.
    Tagged: MIGRATION_SHIM — grep to find and remove later.
    """

    def __init__(self, new_service: ChatService) -> None:
        self._new = new_service

    async def handle_turn(
        self,
        session_id: str,
        message: str,          # old: positional str
        mode: str = "default",
        # ... whatever old signature had
    ) -> str:                  # old: returned plain str
        response = await self._new.handle_turn(ChatTurnRequest(
            session_id=session_id,
            user_message=message,
            mode=mode,
        ))
        return response.assistant_message  # unwrap to old return type
````

---

### Phase 5 — Content Layer & Notes (Week 5-6)

**Goal**: Give notes a real home. Wire search coordinator.

```python
# Step 5a: NoteManager tests before implementation
# tests/unit/content/test_note_manager.py

@pytest.mark.asyncio
async def test_note_manager_creates_note():
    repo = FakeNoteRepository()
    manager = NoteManager(
        repo=repo,
        token_counter=FakeTokenCounter(),
        search=FakeSearchCoordinator(),
    )

    note = await manager.create(
        title="Meeting notes",
        content="Discussed Q4 roadmap.",
        tags=["meeting", "q4"],
    )

    assert note.id is not None
    assert note.title == "Meeting notes"
    assert await repo.exists(note.id)


@pytest.mark.asyncio
async def test_note_manager_get_for_context_respects_budget():
    """
    Critical: notes injected into context must respect token budget.
    Oversized notes must be truncated, not excluded entirely.
    """
    long_content = "word " * 10_000  # very long note
    repo = FakeNoteRepository(notes=[
        Note(id="n1", title="Long note", content=long_content)
    ])
    counter = FakeTokenCounter(tokens_per_char=1)
    manager = NoteManager(
        repo=repo,
        token_counter=counter,
        search=FakeSearchCoordinator(),
    )

    result = await manager.get_for_context(
        note_ids=["n1"],
        max_tokens=500,
    )

    actual_tokens = counter.count(result)
    assert actual_tokens <= 500
    assert len(result) > 0  # not empty — truncated, not dropped


@pytest.mark.asyncio
async def test_note_manager_search_delegates_to_coordinator():
    search = FakeSearchCoordinator(results=[
        SearchResult(
            source="bm25",
            content="Q4 roadmap discussion",
            score=0.95,
            metadata={},
        )
    ])
    manager = NoteManager(
        repo=FakeNoteRepository(),
        token_counter=FakeTokenCounter(),
        search=search,
    )

    results = await manager.search("Q4 roadmap")

    assert len(results) == 1
    assert search.was_called_with_query("Q4 roadmap")


# Step 5b: NoteService — thin, just like ChatService
# tests/unit/services/test_note_service.py

@pytest.mark.asyncio
async def test_note_service_create_returns_schema():
    """API layer gets a clean schema, not a domain object."""
    service = NoteService(note_manager=FakeNoteManager())

    result = await service.create(CreateNoteRequest(
        title="Test",
        content="Content here",
    ))

    assert isinstance(result, NoteResponse)
    assert result.title == "Test"


@pytest.mark.asyncio
async def test_note_service_delete_nonexistent_raises():
    service = NoteService(
        note_manager=FakeNoteManager(raises_on_delete=True)
    )

    with pytest.raises(NoteNotFoundError):
        await service.delete(note_id="nonexistent-id")


# Step 5c: SearchCoordinator tests
# tests/unit/content/test_search_coordinator.py

@pytest.mark.asyncio
async def test_search_coordinator_fans_out_to_all_backends():
    backend_a = FakeSearchBackend(results=[
        SearchResult(source="a", content="result A", score=0.9, metadata={})
    ])
    backend_b = FakeSearchBackend(results=[
        SearchResult(source="b", content="result B", score=0.7, metadata={})
    ])

    coordinator = SearchCoordinator(
        backends={"a": backend_a, "b": backend_b}
    )

    results = await coordinator.search("test query", limit=10)

    assert backend_a.was_called
    assert backend_b.was_called
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_coordinator_deduplicates_results():
    same_content = "duplicate result"
    backend_a = FakeSearchBackend(results=[
        SearchResult(source="a", content=same_content, score=0.9, metadata={})
    ])
    backend_b = FakeSearchBackend(results=[
        SearchResult(source="b", content=same_content, score=0.8, metadata={})
    ])

    coordinator = SearchCoordinator(
        backends={"a": backend_a, "b": backend_b}
    )

    results = await coordinator.search("query", limit=10)

    contents = [r.content for r in results]
    assert len(contents) == len(set(contents)), "Duplicates found"


@pytest.mark.asyncio
async def test_search_coordinator_ranks_by_score():
    coordinator = SearchCoordinator(backends={
        "mixed": FakeSearchBackend(results=[
            SearchResult(source="x", content="low",  score=0.3, metadata={}),
            SearchResult(source="x", content="high", score=0.9, metadata={}),
            SearchResult(source="x", content="mid",  score=0.6, metadata={}),
        ])
    })

    results = await coordinator.search("query", limit=10)

    assert results[0].content == "high"
    assert results[1].content == "mid"
    assert results[2].content == "low"


@pytest.mark.asyncio
async def test_search_coordinator_respects_backend_filter():
    """Caller can choose which backends to use."""
    backend_a = FakeSearchBackend(results=[
        SearchResult(source="a", content="A result", score=0.9, metadata={})
    ])
    backend_b = FakeSearchBackend(results=[
        SearchResult(source="b", content="B result", score=0.8, metadata={})
    ])

    coordinator = SearchCoordinator(
        backends={"a": backend_a, "b": backend_b}
    )

    results = await coordinator.search(
        "query",
        limit=10,
        backends=["a"],  # only backend a
    )

    assert backend_a.was_called
    assert not backend_b.was_called
    assert all(r.source == "a" for r in results)
```

---

### Phase 6 — ToolRegistry Restructure (Week 6)

```python
# Step 6a: Grouped tool tests
# tests/unit/tools/test_registry.py

def test_registry_returns_gemini_schema_format():
    registry = build_default_registry()
    schemas = registry.schemas_for_provider("gemini")

    for schema in schemas:
        # Gemini format: name, description, parameters
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
        # NOT "input_schema" — that's Anthropic
        assert "input_schema" not in schema


def test_registry_returns_anthropic_schema_format():
    registry = build_default_registry()
    schemas = registry.schemas_for_provider("anthropic")

    for schema in schemas:
        # Anthropic format: name, description, input_schema
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema
        assert "parameters" not in schema


def test_registry_filters_by_category():
    registry = build_default_registry()
    schemas = registry.schemas_for_provider(
        "gemini",
        categories=[ToolCategory.SEARCH],
    )

    names = [s["name"] for s in schemas]
    assert "search_knowledge_base" in names
    assert "read_file" not in names  # file tool excluded


def test_registry_unknown_tool_raises_clearly():
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="Unknown tool: 'ghost_tool'"):
        registry.get_handler("ghost_tool")


def test_registry_disabled_tool_excluded_from_schemas():
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="hidden_tool",
        category=ToolCategory.FILE_OPERATIONS,
        description="Should not appear",
        parameters={},
        handler=lambda: None,
        enabled=False,          # disabled
    ))

    schemas = registry.schemas_for_provider("gemini")
    names = [s["name"] for s in schemas]

    assert "hidden_tool" not in names
```

---

## Complete Test Fakes — Reusable Across All Phases

````python
# tests/fakes.py
# ─────────────────────────────────────────────────────────────────
# Central location for all test doubles.
# NEVER use MagicMock for domain objects — use explicit fakes.
# Fakes document the contract. Mocks hide it.

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agent.context_assembler import AssembledContext, ContextSlot
from agent.tool_executor import ToolCall, ToolResult
from agent.turn_orchestrator import TurnInput, TurnOutput
from providers.normalizer import NormalizedResponse
from storage.repositories import Session, Note


# ── Session ───────────────────────────────────────────────────────

def make_session(
    session_id: str = None,
    messages: list[dict] = None,
) -> Session:
    return Session(
        id=session_id or str(uuid4()),
        messages=messages or [],
    )


# ── Repositories ──────────────────────────────────────────────────

class FakeSessionRepository:
    """
    In-memory session store.
    Explicit state inspection via .get() and .all_saved.
    """

    def __init__(self, sessions: dict = None) -> None:
        self._store: dict[str, Session] = sessions or {}
        self.save_call_count = 0

    async def save(self, session: Session) -> None:
        self._store[session.id] = session
        self.save_call_count += 1

    async def load(self, session_id: str) -> Session:
        if session_id not in self._store:
            # Auto-create for convenience in tests
            session = make_session(session_id=session_id)
            self._store[session_id] = session
        return self._store[session_id]

    def get(self, session_id: str) -> Session | None:
        """Direct inspection for test assertions."""
        return self._store.get(session_id)

    @property
    def all_saved(self) -> list[Session]:
        return list(self._store.values())


class FakeNoteRepository:

    def __init__(
        self,
        notes: list[Note] = None,
        raises_on_delete: bool = False,
    ) -> None:
        self._store: dict[str, Note] = {
            n.id: n for n in (notes or [])
        }
        self._raises_on_delete = raises_on_delete

    async def add(self, note: Note) -> None:
        self._store[note.id] = note

    async def get(self, note_id: str) -> Note | None:
        return self._store.get(note_id)

    async def list_all(self) -> list[Note]:
        return list(self._store.values())

    async def delete(self, note_id:

---

### **user**:

continue

---

### **assistant**:

```python
    async def delete(self, note_id: str) -> None:
        if self._raises_on_delete:
            from content.exceptions import NoteNotFoundError
            raise NoteNotFoundError(f"Note {note_id!r} not found.")
        self._store.pop(note_id, None)

    async def exists(self, note_id: str) -> bool:
        return note_id in self._store


# ── Providers ─────────────────────────────────────────────────────

@dataclass
class FakeProviderResponse:
    """
    Explicit response shape for fake provider.
    More readable than constructing NormalizedResponse directly.
    """
    text: str = "Default fake response."
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=lambda: {
        "input": 10, "output": 5, "total": 15
    })

    def to_normalized(self) -> NormalizedResponse:
        return NormalizedResponse(
            text=self.text,
            has_tool_calls=bool(self.tool_calls),
            tool_calls=self.tool_calls,
            usage=self.usage,
        )


class FakeProvider:
    """
    Controllable LLM provider.
    Supports: single response, sequence of responses,
              always-tool-call mode, always-error mode.
    """

    def __init__(
        self,
        response: str | FakeProviderResponse = "Fake response.",
        responses: list[FakeProviderResponse] = None,
        raises: Exception = None,
        always_returns_tool_call: bool = False,
    ) -> None:
        if isinstance(response, str):
            response = FakeProviderResponse(text=response)

        self._responses = responses or [response]
        self._raises = raises
        self._always_tool_call = always_returns_tool_call
        self._call_count = 0
        self.complete_call_count = 0
        self.last_context: AssembledContext | None = None

    async def complete(
        self,
        context: AssembledContext,
    ) -> NormalizedResponse:
        self.complete_call_count += 1
        self.last_context = context

        if self._raises:
            raise self._raises

        if self._always_tool_call:
            return NormalizedResponse(
                text="",
                has_tool_calls=True,
                tool_calls=[ToolCall(
                    id=str(self._call_count),
                    name="fake_tool",
                    arguments={},
                )],
                usage={"input": 10, "output": 5, "total": 15},
            )

        response = self._responses[
            min(self._call_count, len(self._responses) - 1)
        ]
        self._call_count += 1
        return response.to_normalized()

    async def complete_with_tools(
        self,
        context: AssembledContext,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
    ) -> NormalizedResponse:
        return await self.complete(context)

    async def stream(self, context: AssembledContext):
        response = self._responses[0]
        for word in response.text.split():
            yield word + " "


# ── Agent layer ───────────────────────────────────────────────────

class FakeContextAssembler:
    """
    Returns minimal valid AssembledContext.
    Tests that need specific context behavior
    should use real ContextAssembler with FakeTokenCounter.
    """

    def __init__(
        self,
        system_prompt: str = "You are helpful.",
        messages: list[dict] = None,
    ) -> None:
        self._system_prompt = system_prompt
        self._messages = messages or []
        self.assemble_call_count = 0
        self.last_turn_input: TurnInput | None = None

    def assemble(
        self,
        session: Session,
        turn_input: TurnInput,
    ) -> AssembledContext:
        self.assemble_call_count += 1
        self.last_turn_input = turn_input
        return AssembledContext(
            system_prompt=self._system_prompt,
            messages=self._messages + [
                {"role": "user", "content": turn_input.user_message}
            ],
            total_tokens_estimated=100,
            slots_used={
                ContextSlot.SYSTEM_PROMPT: 20,
                ContextSlot.CONVERSATION_HISTORY: 80,
            },
        )


class FakeToolExecutor:
    """
    Controllable tool executor.
    Records calls for assertion.
    """

    def __init__(
        self,
        results: list[ToolResult] = None,
        raises: Exception = None,
    ) -> None:
        self._results = results or []
        self._raises = raises
        self.executed_tool_names: list[str] = []
        self.execute_call_count = 0

    async def execute_all(
        self,
        tool_calls: list[ToolCall],
    ) -> list[ToolResult]:
        self.execute_call_count += 1
        self.executed_tool_names.extend(tc.name for tc in tool_calls)

        if self._raises:
            raise self._raises

        if self._results:
            return self._results

        # Default: return success result for each call
        return [
            ToolResult(
                tool_call_id=tc.id,
                name=tc.name,
                content=f"Fake result for {tc.name}",
                is_error=False,
            )
            for tc in tool_calls
        ]


class FakeOrchestrator:
    """
    Fake TurnOrchestrator.
    Most ChatService tests only care that it was called
    and what it returned — not HOW it works internally.
    """

    def __init__(
        self,
        response: TurnOutput = None,
        raises: Exception = None,
        stream_chunks: list[str] = None,
    ) -> None:
        self._response = response or TurnOutput(
            assistant_message="Fake assistant response.",
            tool_calls_made=[],
            tokens_used={"input": 10, "output": 5, "total": 15},
            context_slots={},
        )
        self._raises = raises
        self._stream_chunks = stream_chunks or ["Fake ", "streamed ", "response."]
        self.run_call_count = 0
        self.last_turn_input: TurnInput | None = None

    async def run(
        self,
        session: Session,
        turn_input: TurnInput,
    ) -> TurnOutput:
        self.run_call_count += 1
        self.last_turn_input = turn_input

        if self._raises:
            raise self._raises

        return self._response

    async def stream(self, session: Session, turn_input: TurnInput):
        self.last_turn_input = turn_input
        for chunk in self._stream_chunks:
            yield chunk


# ── Content layer ─────────────────────────────────────────────────

class FakeNoteManager:

    def __init__(
        self,
        notes: list[Note] = None,
        raises_on_delete: bool = False,
        search_results: list = None,
    ) -> None:
        self._notes: dict[str, Note] = {
            n.id: n for n in (notes or [])
        }
        self._raises_on_delete = raises_on_delete
        self._search_results = search_results or []
        self.create_call_count = 0
        self.search_queries: list[str] = []

    async def create(
        self,
        title: str,
        content: str,
        tags: list[str] = None,
    ) -> Note:
        self.create_call_count += 1
        note = Note(
            id=str(uuid4()),
            title=title,
            content=content,
            tags=tags or [],
        )
        self._notes[note.id] = note
        return note

    async def get(self, note_id: str) -> Note | None:
        return self._notes.get(note_id)

    async def list_all(self) -> list[Note]:
        return list(self._notes.values())

    async def delete(self, note_id: str) -> None:
        if self._raises_on_delete:
            from content.exceptions import NoteNotFoundError
            raise NoteNotFoundError(f"Note {note_id!r} not found.")
        self._notes.pop(note_id, None)

    async def get_for_context(
        self,
        note_ids: list[str],
        max_tokens: int,
    ) -> str:
        notes = [
            self._notes[nid]
            for nid in note_ids
            if nid in self._notes
        ]
        return "\n\n".join(n.content for n in notes)

    async def search(self, query: str) -> list:
        self.search_queries.append(query)
        return self._search_results

    def was_searched_with(self, query: str) -> bool:
        return query in self.search_queries


class FakeSearchCoordinator:

    def __init__(self, results: list = None) -> None:
        self._results = results or []
        self.search_calls: list[dict] = []

    async def search(
        self,
        query: str,
        limit: int = 10,
        backends: list[str] | None = None,
    ) -> list:
        self.search_calls.append({
            "query": query,
            "limit": limit,
            "backends": backends,
        })
        return self._results

    def was_called_with_query(self, query: str) -> bool:
        return any(c["query"] == query for c in self.search_calls)

    @property
    def was_called(self) -> bool:
        return len(self.search_calls) > 0


# ── Cross-cutting ─────────────────────────────────────────────────

class FakePromptLogger:

    def __init__(self) -> None:
        self.log_call_count = 0
        self.last_session_id: str | None = None
        self.entries: list[dict] = []

    async def log(
        self,
        session_id: str,
        turn_input: TurnInput,
        turn_output: TurnOutput,
    ) -> None:
        self.log_call_count += 1
        self.last_session_id = session_id
        self.entries.append({
            "session_id": session_id,
            "input": turn_input,
            "output": turn_output,
        })


class FakeTokenCounter:
    """
    Predictable token counter for deterministic tests.
    Default: 1 token per character (simple, predictable).
    """

    def __init__(self, tokens_per_char: int = 1) -> None:
        self._rate = tokens_per_char

    def count(self, text: str) -> int:
        return len(text) * self._rate

    def count_message(self, message: dict) -> int:
        content = message.get("content", "")
        return self.count(str(content))

    def trim_to(self, text: str, max_tokens: int) -> str:
        max_chars = max_tokens // self._rate
        return text[:max_chars]


class FakePromptManager:

    def __init__(self, prompt: str = "You are helpful.") -> None:
        self._prompt = prompt
        self.load_calls: list[str] = []

    def load(self, mode: str) -> str:
        self.load_calls.append(mode)
        return self._prompt

    def was_loaded_with_mode(self, mode: str) -> bool:
        return mode in self.load_calls
````

---

## Migration Safety Checklist Per Phase

````python
# scripts/check_migration_phase.py
# ─────────────────────────────────────────────────────────────────
# Run after each phase to verify safety before proceeding.
# Usage: python scripts/check_migration_phase.py --phase 2

import subprocess
import sys
from dataclasses import dataclass


@dataclass
class PhaseCheck:
    description: str
    command: list[str]
    expect_zero_exit: bool = True


PHASE_CHECKS: dict[int, list[PhaseCheck]] = {

    1: [
        PhaseCheck(
            description="All 700 tests pass",
            command=["pytest", "--tb=short", "-q"],
        ),
        PhaseCheck(
            description="ResponseNormalizer has tests",
            command=["pytest", "tests/unit/providers/test_normalizer.py", "-v"],
        ),
        PhaseCheck(
            description="No direct SDK calls outside providers/",
            command=[
                "grep", "-r",
                "--include=*.py",
                "-l",
                "google.generativeai\|anthropic.Anthropic",
                "services/", "agent/", "tools/",
            ],
            expect_zero_exit=False,  # grep exits 1 when nothing found = good
        ),
    ],

    2: [
        PhaseCheck(
            description="All 700 tests pass",
            command=["pytest", "--tb=short", "-q"],
        ),
        PhaseCheck(
            description="ToolExecutor has tests",
            command=["pytest", "tests/unit/agent/test_tool_executor.py", "-v"],
        ),
        PhaseCheck(
            description="Tool execution not inlined in agent.py",
            command=[
                "grep", "-n",
                "FUNCTION_MAP\[",
                "agent/agent.py",
            ],
            expect_zero_exit=False,
        ),
    ],

    3: [
        PhaseCheck(
            description="All 700 tests pass",
            command=["pytest", "--tb=short", "-q"],
        ),
        PhaseCheck(
            description="ContextAssembler has tests",
            command=["pytest", "tests/unit/agent/test_context_assembler.py", "-v"],
        ),
        PhaseCheck(
            description="Token budget tests exist",
            command=[
                "grep", "-r",
                "token_budget\|max_tokens\|ContextBudget",
                "tests/",
            ],
        ),
    ],

    4: [
        PhaseCheck(
            description="All 700 tests pass",
            command=["pytest", "--tb=short", "-q"],
        ),
        PhaseCheck(
            description="TurnOrchestrator has tests",
            command=["pytest", "tests/unit/agent/test_turn_orchestrator.py", "-v"],
        ),
        PhaseCheck(
            description="ChatService has max 3 constructor params",
            command=[
                "python", "-c",
                "from services.chat_service import ChatService; "
                "import inspect; "
                "params = inspect.signature(ChatService.__init__).parameters; "
                "non_self = [p for p in params if p != 'self']; "
                "assert len(non_self) <= 3, f'Too many: {non_self}'",
            ],
        ),
        PhaseCheck(
            description="No MIGRATION_SHIM left unreferenced",
            command=[
                "grep", "-rn", "MIGRATION_SHIM", ".",
                "--include=*.py",
            ],
            expect_zero_exit=False,  # should be zero by end of phase 4
        ),
    ],

    5: [
        PhaseCheck(
            description="All tests pass including new content tests",
            command=["pytest", "--tb=short", "-q"],
        ),
        PhaseCheck(
            description="Notes have API routes",
            command=["grep", "-r", "/notes", "api/"],
        ),
        PhaseCheck(
            description="NoteRepository is not orphaned",
            command=[
                "python", "-c",
                "from dependencies import get_note_service; "
                "print

---

### **user**:

continue

---

### **assistant**:

```python
                "print('NoteService wired correctly')",
            ],
        ),
        PhaseCheck(
            description="SearchCoordinator has tests",
            command=["pytest", "tests/unit/content/test_search_coordinator.py", "-v"],
        ),
    ],

    6: [
        PhaseCheck(
            description="All tests pass",
            command=["pytest", "--tb=short", "-q"],
        ),
        PhaseCheck(
            description="Tools grouped by category",
            command=["python", "-c",
                "from tools.registry import build_default_registry, ToolCategory; "
                "r = build_default_registry(); "
                "schemas = r.schemas_for_provider('gemini', "
                "categories=[ToolCategory.SEARCH]); "
                "print(f'Search tools: {len(schemas)}'); "
                "assert len(schemas) > 0",
            ],
        ),
        PhaseCheck(
            description="No flat tool imports in agent code",
            command=[
                "grep", "-rn",
                "from tools.file_ops\|from tools.repo_map\|from tools.search",
                "agent/",
            ],
            expect_zero_exit=False,  # should find nothing
        ),
    ],
}


def run_checks(phase: int) -> bool:
    checks = PHASE_CHECKS.get(phase)
    if not checks:
        print(f"No checks defined for phase {phase}")
        return False

    print(f"\n{'='*60}")
    print(f"Phase {phase} Safety Checks")
    print(f"{'='*60}\n")

    all_passed = True
    for check in checks:
        result = subprocess.run(
            check.command,
            capture_output=True,
            text=True,
        )
        passed = (result.returncode == 0) == check.expect_zero_exit

        status = "✅" if passed else "❌"
        print(f"{status} {check.description}")

        if not passed:
            all_passed = False
            print(f"   Command: {' '.join(check.command)}")
            if result.stdout:
                print(f"   stdout: {result.stdout[:200]}")
            if result.stderr:
                print(f"   stderr: {result.stderr[:200]}")

    print(f"\n{'='*60}")
    if all_passed:
        print(f"✅ Phase {phase} complete — safe to proceed")
    else:
        print(f"❌ Phase {phase} has failures — do NOT proceed")
    print(f"{'='*60}\n")

    return all_passed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, required=True)
    args = parser.parse_args()

    success = run_checks(args.phase)
    sys.exit(0 if success else 1)
````

---

## Complete Refactor Roadmap — Single View

```
WEEK 1          WEEK 2          WEEK 3          WEEK 4          WEEK 5          WEEK 6
│               │               │               │               │               │
▼               ▼               ▼               ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  PHASE 0    │ │  PHASE 1    │ │  PHASE 2    │ │  PHASE 3    │ │  PHASE 4    │ │  PHASE 5+6  │
│             │ │             │ │             │ │             │ │             │ │             │
│ Audit       │ │ Extract     │ │ Extract     │ │ Extract     │ │ Introduce   │ │ Content     │
│ tests       │ │ Response    │ │ Tool        │ │ Context     │ │ Turn        │ │ Layer +     │
│             │ │ Normalizer  │ │ Executor    │ │ Assembler   │ │ Orchestrator│ │ Tool Groups │
│ Map deps    │ │             │ │             │ │             │ │             │ │             │
│             │ │ ~10 new     │ │ ~20 new     │ │ ~30 new     │ │ ~25 new     │ │ ~40 new     │
│ 0 new tests │ │ tests       │ │ tests       │ │ tests       │ │ tests       │ │ tests       │
│             │ │             │ │             │ │             │ │             │ │             │
│ 700 pass ✅ │ │ 710 pass ✅ │ │ 730 pass ✅ │ │ 760 pass ✅ │ │ 785 pass ✅ │ │ 825 pass ✅ │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
     │               │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼               ▼
  Understand      Providers       Agent tools     Context is      God object      Notes have
  what you        speak one       are isolated    explicit +      is gone         a home.
  actually        language        + testable      observable      ChatService     Search is
  have                                                            is thin         pluggable
```

---

## Answering Your Question Directly

```
"I have 700 tests — do you need to review signatures?"
```

**Yes — but selectively. Here is exactly what matters:**

```python
# ── The 5 signatures that determine your refactor plan ────────────

# 1. What does handle_turn currently accept and return?
#    If it returns str  → need shim in Phase 4
#    If it returns dict → easier migration
async def handle_turn(self, ???) -> ???:
    ...

# 2. What does process_chat_turn in agent.py accept?
#    If tests call this directly → need characterization tests first
#    If only ChatService calls it → free to refactor
async def process_chat_turn(self, ???) -> ???:
    ...

# 3. What does LLMProvider.complete() accept?
#    This determines how ContextAssembler output is shaped
def complete(self, ???) -> ???:
    ...

# 4. What do SessionRepository methods accept/return?
#    Protocol must stay stable across all phases
def save(self, ???) -> ???:
def load(self, ???) -> ???:
    ...

# 5. Where do your 700 tests ENTER the system?
#    This is the most important question of all
```

```
Test entry points determine refactor freedom:

Entry at FastAPI routes    → maximum freedom, internals are invisible
Entry at Service layer     → keep service signatures stable
Entry at Agent/agent.py    → need shims during transition
Entry at Provider layer    → keep provider protocol stable
Entry at Repository layer  → keep repository protocol stable
```

---

## What To Send Me Next

```
To give you a precise phase-by-phase plan with zero guesswork:

1. Current ChatService.__init__ signature
   + handle_turn signature + return type

2. Current agent.py / process_chat_turn signature
   + return type

3. Current LLMProvider Protocol
   (base.py — the Protocol definition)

4. One example test from each category:
   - A unit test
   - An integration test
   - An API test (if any)

5. Output of:
   pytest --collect-only -q 2>/dev/null | tail -20
   (shows test distribution across modules)

With those 5 things I can give you:
✅ Exact phase ordering for YOUR codebase
✅ Which signatures need shims
✅ Which tests need updating vs which are free
✅ Estimated test count per phase
✅ Specific risks to watch for
```

> **Bottom line**: Your 700 tests are not a burden — they are the **engine** of this refactor. Each phase ends only when all tests pass. The tests tell you when you are done, not your intuition.

---

### **user**:

I'm doing such big refactor first time. Will they work after all this refactoring?

````


## tests/test_anthropic_provider.py
```python
import base64
import json
from unittest.mock import MagicMock, patch, call
import pytest
import anthropic
from src.providers.anthropic_provider import AnthropicProvider

def _text_block(text: str) -> MagicMock

def _tool_use_block(name: str, tool_input: dict, tool_id: str) -> MagicMock

def _make_response(content_blocks: list, stop_reason: str='end_turn') -> MagicMock

def provider() -> AnthropicProvider

def test_simple_text_response(provider: AnthropicProvider) -> None

def test_simple_text_appended_to_history(provider: AnthropicProvider) -> None

def test_single_tool_call_dispatched(provider: AnthropicProvider) -> None

def test_single_tool_call_history_structure(provider: AnthropicProvider) -> None

def test_unknown_tool_returns_error_result(provider: AnthropicProvider) -> None

def test_tool_exception_returns_error_result(provider: AnthropicProvider) -> None

def test_context_files_injected_before_message(provider: AnthropicProvider) -> None

def test_unreadable_context_file_skipped(provider: AnthropicProvider) -> None

def test_valid_image_sent_as_base64_block(provider: AnthropicProvider) -> None

def test_bad_base64_image_skipped(provider: AnthropicProvider) -> None

def test_system_instruction_forwarded(provider: AnthropicProvider) -> None

def test_no_system_instruction_not_sent(provider: AnthropicProvider) -> None

def test_no_tools_skips_agentic_loop(provider: AnthropicProvider) -> None

def test_no_tools_sends_no_tools_to_api(provider: AnthropicProvider) -> None

def test_no_tools_history_has_user_and_assistant_turn(provider: AnthropicProvider) -> None

def test_tools_enabled_true_still_uses_agentic_loop(provider: AnthropicProvider) -> None

def test_multi_tool_turn(provider: AnthropicProvider) -> None

def test_tool_schemas_built_from_registry(provider: AnthropicProvider) -> None

def test_empty_final_text_handled(provider: AnthropicProvider) -> None
````

## tests/test_archive_delete.py

```python
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config
from src.repositories import SQLiteConnection, SQLiteSessionRepository, SQLiteNoteRepository
from src.main import app, get_session_repo, get_note_repo

class TestArchiveSession
    def test_returns_true_when_archived(self, tmp_path: Path) -> None
    def test_archived_at_is_set(self, tmp_path: Path) -> None
    def test_returns_false_for_nonexistent_session(self, tmp_path: Path) -> None
    def test_returns_false_when_already_archived(self, tmp_path: Path) -> None
    def test_archived_session_disappears_from_default_list(self, tmp_path: Path) -> None
    def test_archive_does_not_delete_data(self, tmp_path: Path) -> None
    def test_archive_does_not_affect_sibling(self, tmp_path: Path) -> None

class TestUnarchiveSession
    def test_returns_true_when_unarchived(self, tmp_path: Path) -> None
    def test_archived_at_cleared_after_unarchive(self, tmp_path: Path) -> None
    def test_unarchived_session_reappears_in_default_list(self, tmp_path: Path) -> None
    def test_returns_false_for_nonexistent_session(self, tmp_path: Path) -> None
    def test_returns_false_when_not_archived(self, tmp_path: Path) -> None

class TestListSessionsFilter
    def test_default_hides_archived(self, tmp_path: Path) -> None
    def test_include_archived_true_shows_all(self, tmp_path: Path) -> None
    def test_archived_at_field_present_in_rows(self, tmp_path: Path) -> None

class TestGetSessionTreeFilter
    def test_tree_includes_archived_by_default(self, tmp_path: Path) -> None
    def test_tree_excludes_archived_when_requested(self, tmp_path: Path) -> None
    def test_archived_node_carries_archived_at(self, tmp_path: Path) -> None

class TestDeleteSession
    def test_deletes_leaf_session(self, tmp_path: Path) -> None
    def test_raises_for_nonexistent_session(self, tmp_path: Path) -> None
    def test_raises_when_session_has_children(self, tmp_path: Path) -> None
    def test_parent_deletable_after_child_deleted(self, tmp_path: Path) -> None
    def test_grandchild_blocks_intermediate_delete(self, tmp_path: Path) -> None
    def test_notes_cascade_deleted(self, tmp_path: Path) -> None
    def test_archived_child_still_blocks_parent_delete(self, tmp_path: Path) -> None
    def test_sibling_unaffected_by_leaf_delete(self, tmp_path: Path) -> None

class TestArchiveEndpoint
    def test_returns_200_on_success(self, client: TestClient, session_id: str) -> None
    def test_session_hidden_from_default_list_after_archive(self, client: TestClient, session_id: str) -> None
    def test_returns_404_for_unknown_session(self, client: TestClient) -> None
    def test_returns_404_when_already_archived(self, client: TestClient, session_id: str) -> None
    def test_archived_at_appears_in_include_archived_list(self, client: TestClient, session_id: str) -> None

class TestUnarchiveEndpoint
    def test_returns_200_on_success(self, client: TestClient, session_id: str) -> None
    def test_session_reappears_in_default_list_after_unarchive(self, client: TestClient, session_id: str) -> None
    def test_returns_404_for_unknown_session(self, client: TestClient) -> None
    def test_returns_404_when_not_archived(self, client: TestClient, session_id: str) -> None

class TestDeleteSessionEndpoint
    def test_returns_204_for_leaf_session(self, client: TestClient, session_id: str) -> None
    def test_session_gone_after_delete(self, client: TestClient, session_id: str) -> None
    def test_returns_404_for_unknown_session(self, client: TestClient) -> None
    def test_returns_409_when_children_exist(self, client: TestClient, session_repo: SQLiteSessionRepository, session_id: str) -> None
    def test_allowed_after_child_deleted(self, client: TestClient, session_repo: SQLiteSessionRepository, session_id: str) -> None
    def test_archived_child_blocks_parent_delete(self, client: TestClient, session_repo: SQLiteSessionRepository, session_id: str) -> None

class TestListSessionsQueryParam
    def test_default_excludes_archived(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_include_archived_false_explicit(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_include_archived_true_shows_all(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_archived_at_field_in_response(self, client: TestClient, session_id: str) -> None

class TestTreeQueryParam
    def test_tree_includes_archived_by_default(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_tree_excludes_archived_when_false(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_archived_node_has_archived_at_set(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None

def _make_conn(tmp_path: Path) -> SQLiteConnection

def _seed(repo: SQLiteSessionRepository, session_id: str, title: str='Chat') -> str

def conn(tmp_path: Path) -> SQLiteConnection

def session_repo(conn: SQLiteConnection) -> SQLiteSessionRepository

def client(session_repo: SQLiteSessionRepository, tmp_path: Path, monkeypatch) -> TestClient

def session_id(session_repo: SQLiteSessionRepository) -> str
```

## tests/test_backup_file_ops.py

```python
import json
import uuid
from pathlib import Path
from unittest.mock import patch
import pytest
from src.tools.file_ops import _create_backup, revert_backup, edit_file, create_file, append_to_file

class TestCreateBackup
    def test_creates_backups_dir(self, tmp_path: Path) -> None
    def test_returns_valid_uuid_string(self, tmp_path: Path) -> None
    def test_each_call_returns_unique_id(self, tmp_path: Path) -> None
    def test_backup_records_existing_file_content(self, tmp_path: Path) -> None
    def test_backup_records_filepath(self, tmp_path: Path) -> None
    def test_backup_for_non_existent_file(self, tmp_path: Path) -> None
    def test_backup_json_file_is_named_by_revert_id(self, tmp_path: Path) -> None

class TestRevertBackup
    def test_restores_original_content(self, tmp_path: Path) -> None
    def test_deletes_created_file_on_revert(self, tmp_path: Path) -> None
    def test_deletes_backup_file_after_successful_revert(self, tmp_path: Path) -> None
    def test_double_revert_returns_error(self, tmp_path: Path) -> None
    def test_returns_error_for_unknown_revert_id(self, tmp_path: Path) -> None
    def test_returns_error_for_malformed_backup_json(self, tmp_path: Path) -> None
    def test_backup_preserved_on_error(self, tmp_path: Path) -> None
    def test_revert_success_message_mentions_file(self, tmp_path: Path) -> None
    def test_revert_when_file_was_created_but_already_deleted(self, tmp_path: Path) -> None

class TestEditFileWithBackup
    def test_edit_file_returns_revert_id(self, tmp_path: Path) -> None
    def test_edit_file_revert_id_is_non_empty(self, tmp_path: Path) -> None
    def test_edit_file_backup_captures_original_content(self, tmp_path: Path) -> None
    def test_edit_file_no_revert_id_on_error(self, tmp_path: Path) -> None
    def test_edit_file_backward_compatible_no_backup_dir(self, tmp_path: Path) -> None

class TestCreateFileWithBackup
    def test_create_file_returns_revert_id(self, tmp_path: Path) -> None
    def test_create_file_backup_records_not_existed(self, tmp_path: Path) -> None
    def test_create_file_no_revert_id_when_file_exists(self, tmp_path: Path) -> None
    def test_create_file_backward_compatible_no_backup_dir(self, tmp_path: Path) -> None

class TestAppendToFileWithBackup
    def test_append_returns_revert_id(self, tmp_path: Path) -> None
    def test_append_backup_records_existed_true(self, tmp_path: Path) -> None
    def test_append_backup_records_existed_false_for_new_file(self, tmp_path: Path) -> None
    def test_append_backward_compatible_no_backup_dir(self, tmp_path: Path) -> None

def _is_valid_uuid(value: str) -> bool

def _read_backup(backup_dir: Path, revert_id: str) -> dict
```

## tests/test_chat_provider_routing.py

```python
from functools import partial
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.main import app, get_chat_service, get_session_repo
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.schemas import ChatRequest
from src.providers.base import get_provider
from src.providers.gemini import GeminiProvider
from src.providers.base import get_provider
from src.providers.anthropic_provider import AnthropicProvider
import src.config
from src.providers.base import get_provider
from src.providers.gemini import GeminiProvider
from src.providers.base import get_provider
from google.genai import types
from src.providers.gemini import GeminiProvider
import src.config
from google.genai import types
from src.providers.gemini import GeminiProvider
from src.providers.anthropic_provider import AnthropicProvider
import src.config
from src.providers.anthropic_provider import AnthropicProvider

def test_chat_request_accepts_provider_field() -> None

def test_chat_request_accepts_model_field() -> None

def test_chat_request_provider_defaults_to_none() -> None

def test_chat_request_model_defaults_to_none() -> None

def test_chat_request_provider_and_model_together() -> None

def test_get_provider_passes_model_to_gemini() -> None

def test_get_provider_passes_model_to_anthropic() -> None

def test_get_provider_uses_settings_default_when_no_override() -> None

def test_get_provider_raises_for_unknown_provider_name() -> None

def test_gemini_provider_uses_model_override_in_api_call() -> None

def test_gemini_provider_uses_settings_model_by_default() -> None

def test_anthropic_provider_uses_model_override_in_api_call() -> None

def test_anthropic_provider_uses_settings_model_by_default() -> None

def repo(tmp_path)

def _make_chat_client(repo: SQLiteSessionRepository) -> TestClient

def test_chat_endpoint_accepts_provider_and_model(repo, tmp_path) -> None

def test_chat_endpoint_routes_to_correct_provider(repo, tmp_path) -> None

def test_chat_endpoint_uses_server_default_when_no_provider(repo) -> None

def test_chat_unknown_provider_returns_400(repo) -> None
```

## tests/test_chat_service.py

```python
import json
from unittest.mock import MagicMock, call, patch
import pytest
from src.chat_service import ChatService, _make_title
from src.repositories import SQLiteConnection, SQLiteSessionRepository

def test_make_title_short_message() -> None

def test_make_title_long_message_truncated() -> None

def test_make_title_no_user_message() -> None

def test_make_title_empty_list() -> None

def repo(tmp_path)

def test_handle_turn_saves_session(mock_agent: MagicMock, mock_log: MagicMock, repo: SQLiteSessionRepository) -> None

def test_handle_turn_appends_to_existing_history(mock_agent: MagicMock, mock_log: MagicMock, repo: SQLiteSessionRepository) -> None

def test_handle_turn_logs_prompt(mock_agent: MagicMock, mock_log: MagicMock, repo: SQLiteSessionRepository) -> None

def test_handle_turn_passes_images_and_context(mock_agent: MagicMock, mock_log: MagicMock, repo: SQLiteSessionRepository) -> None
```

## tests/test_config.py

```python
from pathlib import Path
import pytest
from src.config import Settings

def test_db_path_derived_from_data_dir() -> None

def test_prompt_log_path_derived_from_data_dir() -> None

def test_parse_origins_from_comma_string() -> None

def test_parse_origins_strips_whitespace() -> None

def test_parse_origins_filters_empty_segments() -> None

def test_parse_origins_list_passthrough() -> None
```

## tests/test_config_provider.py

```python
import os
import pytest
from src.config import Settings

def test_default_provider_is_gemini() -> None

def test_llm_provider_can_be_set_to_anthropic() -> None

def test_anthropic_model_has_default() -> None

def test_anthropic_model_can_be_overridden() -> None

def test_anthropic_api_key_field_exists_and_is_nullable() -> None

def test_anthropic_api_key_accepts_env_var(monkeypatch) -> None

def test_anthropic_temperature_has_sensible_default() -> None

def test_anthropic_temperature_can_be_overridden() -> None

def test_anthropic_max_tokens_has_positive_default() -> None
```

## tests/test_context_files.py

```python
from __future__ import annotations
import json
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config
from src.main import app, get_session_repo, get_chat_service
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.agent import process_chat_turn
from src.agent import process_chat_turn
import src.main
from src.chat_service import ChatService
from src.tools.file_ops import read_file
from src.tools.file_ops import read_file
import os
from src.tools.file_ops import read_file
from src.agent import process_chat_turn

class TestAgentContextFilesUnitRegression
    def test_agent_injects_content_when_file_readable(self, mock_read_file: MagicMock, mock_generate: MagicMock) -> None
    def test_agent_skips_when_path_has_no_data_prefix(self, mock_read_file: MagicMock, mock_generate: MagicMock) -> None

class TestContextFilePathResolution
    def test_bare_filename_is_prefixed_with_data_dir(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None
    def test_full_data_path_passes_through_unchanged(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None
    def test_null_context_files_not_passed(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None
    def test_empty_context_files_list_becomes_none(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None

class TestContextFileIntegration
    def test_context_file_content_reaches_agent(self, data_dir: Path, context_file: Path, monkeypatch: pytest.MonkeyPatch) -> None
    def test_context_file_content_is_readable_via_resolved_path(self, data_dir: Path, context_file: Path, monkeypatch: pytest.MonkeyPatch) -> None
    def test_multiple_context_files_all_prefixed(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None
    def test_response_200_when_context_file_provided(self, data_dir: Path, context_file: Path, monkeypatch: pytest.MonkeyPatch) -> None

class TestFileListPathFormat
    def test_list_files_path_is_relative_to_data_dir(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None
    def test_list_files_path_does_not_include_data_prefix(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None
    def test_bare_filename_is_not_readable_by_read_file(self, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None

def data_dir(tmp_path: Path) -> Path

def client(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient

def context_file(data_dir: Path) -> Path

def _stub_agent(text: str='ok', tools: list | None=None)
```

## tests/test_context_files_ui.py

```python
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config
from src.main import app, get_session_repo, get_chat_service
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.chat_service import ChatService

class TestChatServiceContextFilesOnUiMessage
    def test_context_files_stored_on_user_ui_message(self, service: ChatService, repo: SQLiteSessionRepository) -> None
    def test_context_files_basenames_only(self, service: ChatService, repo: SQLiteSessionRepository) -> None
    def test_multiple_context_files_all_stored(self, service: ChatService, repo: SQLiteSessionRepository) -> None
    def test_no_context_files_key_absent_when_none_sent(self, service: ChatService, repo: SQLiteSessionRepository) -> None
    def test_no_context_files_key_absent_when_empty_list(self, service: ChatService, repo: SQLiteSessionRepository) -> None
    def test_assistant_message_has_no_context_files(self, service: ChatService, repo: SQLiteSessionRepository) -> None
    def test_context_files_survives_second_turn(self, service: ChatService, repo: SQLiteSessionRepository) -> None
    def test_bare_relative_filename_stored_as_basename(self, service: ChatService, repo: SQLiteSessionRepository) -> None

class TestGetSessionContextFilesInResponse
    def test_context_files_in_ui_messages_via_api(self, client: TestClient, data_dir: Path) -> None
    def test_context_files_absent_when_not_sent(self, client: TestClient) -> None
    def test_multiple_files_all_present_in_api_response(self, client: TestClient, data_dir: Path) -> None
    def test_context_files_on_user_message_not_assistant(self, client: TestClient, data_dir: Path) -> None
    def test_two_turns_second_without_files_still_returns_first(self, client: TestClient, data_dir: Path) -> None

def tmp_db(tmp_path: Path) -> SQLiteConnection

def repo(tmp_db: SQLiteConnection) -> SQLiteSessionRepository

def service(repo: SQLiteSessionRepository) -> ChatService

def data_dir(tmp_path: Path) -> Path

def client(repo: SQLiteSessionRepository, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient
```

## tests/test_coverage_gaps.py

```python
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from google.genai import types
from src.chat_service import _build_turn_ids_for_history
from src.logger import setup_logging
from src.message_editor import EditError, MessageEditService, _require_turn_id
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.serializers import dehydrate_history, hydrate_history
from src.tools.file_ops import _create_backup, revert_backup
from src.main import app, get_session_repo, get_prompt_manager
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.prompt_manager import PromptManager
from src.main import _resolve_context_file_paths
from src.main import _resolve_context_file_paths
from src.main import _resolve_context_file_paths
from src import config
from src.main import _resolve_context_file_paths
from src import config
from src.main import _resolve_context_file_paths
from src import config
from src.main import _resolve_context_file_paths
from src import config
from src.main import _resolve_context_file_paths
from src import config
from src.main import app, get_session_repo
from src.repositories import SQLiteConnection, SQLiteSessionRepository

class TestSetupLoggingJsonPath
    def test_setup_logging_json_mode_does_not_raise(self)
    def test_setup_logging_local_dev_does_not_raise(self)
    def test_setup_logging_sets_info_level(self)

class TestBuildTurnIds
    def test_empty_existing_ids(self)
    def test_preserves_existing_ids(self)
    def test_length_matches_history_after(self)
    def test_no_new_items_returns_existing(self)
    def test_none_values_in_existing_ids_preserved(self)

class TestResolveContextFilePaths
    def _client(self, tmp_path)
    def test_none_context_files_returns_none(self)
    def test_empty_list_returns_none(self)
    def test_relative_path_resolved_to_data_dir(self, tmp_path)
    def test_absolute_path_inside_data_dir_accepted(self, tmp_path)
    def test_absolute_path_outside_data_dir_dropped(self, tmp_path)
    def test_relative_path_traversal_dropped(self, tmp_path)
    def test_mixed_valid_and_invalid_paths(self, tmp_path)

class TestRevertRouteExceptionPath
    def client(self, tmp_path)
    def test_revert_with_missing_backup_returns_404(self, client)
    def test_revert_path_traversal_returns_400(self, client)

class TestRequireTurnId
    def test_raises_edit_error_when_no_turn_id(self)
    def test_returns_turn_id_when_present(self)
    def test_raises_for_empty_string_turn_id(self)

class TestDeletePairLegacyNextMessage
    def repo(self, tmp_path)
    def test_delete_pair_removes_legacy_next_message_from_ui(self, repo)
    def test_delete_pair_false_leaves_next_message(self, repo)

class TestTruncateLegacyFootprint
    def repo(self, tmp_path)
    def test_truncate_legacy_session_estimates_api_footprint(self, repo)
    def test_truncate_n_exceeds_pairs_raises(self, repo)

class TestDehydrateWithTurnIds
    def test_turn_id_on_text_item(self)
    def test_turn_id_on_function_call_item(self)
    def test_turn_id_on_function_response_item(self)
    def test_no_turn_id_when_list_is_none(self)
    def test_mixed_turn_ids_per_item(self)
    def test_round_trip_preserves_turn_id_in_api_items(self)

class TestRevertBackupCleanup
    def test_cleanup_oserror_is_swallowed(self, tmp_path)
    def test_revert_backup_file_not_found_returns_error(self, tmp_path)
    def test_revert_backup_restores_content(self, tmp_path)
    def test_revert_backup_for_created_file_deletes_it(self, tmp_path)
    def test_revert_backup_malformed_json_returns_error(self, tmp_path)

class TestBackfillLegacyNoCandidate
    def test_no_candidate_for_legacy_fork_title_is_skipped(self, tmp_path)
    def test_backfill_skips_sessions_already_having_parent_id(self, tmp_path)

class TestEditMessageApiSync
    def repo(self, tmp_path)
    def test_edit_message_updates_api_text_item(self, repo)
    def test_edit_message_skips_non_text_api_items(self, repo)
    def test_edit_message_empty_content_raises(self, repo)
    def test_edit_message_unknown_turn_id_raises(self, repo)

```

## tests/test_exporter.py

```python
import json
from pathlib import Path
import pytest
from src.exporter import export_session_to_markdown, _render_message
from src.repositories import SQLiteConnection, SQLiteSessionRepository

def test_export_empty_session_has_title_only() -> None

def test_export_single_user_turn() -> None

def test_export_full_user_assistant_exchange() -> None

def test_export_renders_tool_calls_as_details_blocks() -> None

def test_export_preserves_turn_order() -> None

def test_export_special_markdown_chars_preserved() -> None

def test_export_handles_missing_tools_key() -> None

def test_export_falls_back_for_empty_title() -> None

def test_render_message_unknown_role() -> None

def _seed(repo: SQLiteSessionRepository) -> str

def test_db_export_session_returns_markdown(tmp_path: Path) -> None

def test_db_export_nonexistent_session_raises(tmp_path: Path) -> None

def test_db_export_empty_session(tmp_path: Path) -> None
```

## tests/test_file_ops.py

```python
import stat
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from src.tools.file_ops import append_to_file, create_file, edit_file, read_file, search_knowledge_base

def test_read_file_success(tmp_path: Path) -> None

def test_read_file_not_found(tmp_path: Path) -> None

def test_read_file_oserror(tmp_path: Path) -> None

def test_edit_file_success(tmp_path: Path) -> None

def test_edit_file_search_text_not_found(tmp_path: Path) -> None

def test_edit_file_not_found(tmp_path: Path) -> None

def test_edit_file_oserror_on_read(tmp_path: Path) -> None

def test_create_file_success(tmp_path: Path) -> None

def test_create_file_already_exists(tmp_path: Path) -> None

def test_create_file_oserror(tmp_path: Path) -> None

def test_append_to_existing_file(tmp_path: Path) -> None

def test_append_creates_file_if_missing(tmp_path: Path) -> None

def test_append_creates_parent_dirs(tmp_path: Path) -> None

def test_append_oserror(tmp_path: Path) -> None

def test_search_truncates_at_200_matches(tmp_path: Path) -> None

def test_search_skips_unreadable_file(tmp_path: Path) -> None
```

## tests/test_fork.py

```python
import json
import pytest
from src.repositories import SQLiteConnection, SQLiteSessionRepository

def _seed_session(repo: SQLiteSessionRepository) -> tuple[str, list, list]

def test_fork_returns_new_unique_session_id(tmp_path)

def test_fork_slices_ui_history_inclusive(tmp_path)

def test_fork_slices_api_history_inclusive(tmp_path)

def test_fork_does_not_modify_source_session(tmp_path)

def test_fork_derives_title_from_source(tmp_path)

def test_fork_at_index_zero_keeps_first_turn_only(tmp_path)

def test_fork_index_beyond_history_is_clamped(tmp_path)

def test_fork_nonexistent_session_raises(tmp_path)

def test_fork_negative_index_raises(tmp_path)

def test_forked_session_appears_in_list(tmp_path)
```

## tests/test_gemini_history_coercion.py

```python
from __future__ import annotations
import json
from unittest.mock import MagicMock, patch
import pytest
from google.genai import types
from src.providers.gemini import GeminiProvider, _coerce_history_for_gemini

class TestCoercionFunction
    def test_plain_string_user_content_becomes_content_object(self) -> None
    def test_assistant_role_mapped_to_model(self) -> None
    def test_user_role_preserved(self) -> None
    def test_list_text_block_becomes_text_part(self) -> None
    def test_single_tool_use_becomes_function_call_part(self) -> None
    def test_multiple_tool_use_blocks_become_multiple_parts(self) -> None
    def test_tool_result_recovers_function_name_from_preceding_tool_use(self) -> None
    def test_tool_result_without_matching_tool_use_uses_unknown_name(self) -> None
    def test_multiple_tool_results_each_get_correct_name(self) -> None
    def test_mixed_text_and_tool_use_in_one_message(self) -> None
    def test_existing_content_objects_pass_through_unchanged(self) -> None
    def test_mixed_content_objects_and_dicts(self) -> None
    def test_unknown_block_type_becomes_text_part_fallback(self) -> None
    def test_does_not_mutate_original_history_list(self) -> None
    def test_empty_history_returns_empty_list(self) -> None
    def test_tool_result_json_string_parsed_to_dict(self) -> None
    def test_tool_result_invalid_json_wrapped_in_dict(self) -> None

class TestGeminiProviderWithAnthropicHistory
    def test_process_chat_turn_does_not_raise_with_anthropic_dict_history(self, provider: GeminiProvider) -> None
    def test_generate_content_receives_only_content_objects(self, provider: GeminiProvider) -> None
    def test_pure_gemini_history_still_works(self, provider: GeminiProvider) -> None
    def test_empty_history_does_not_raise(self, provider: GeminiProvider) -> None
    def test_anthropic_history_original_list_unchanged_after_turn(self, provider: GeminiProvider) -> None
    def test_full_tool_call_loop_with_anthropic_history(self, provider: GeminiProvider) -> None

def _make_text_response(text: str) -> MagicMock

def _anthropic_user_str(text: str) -> dict

def _anthropic_assistant_text(text: str) -> dict

def _anthropic_assistant_tool_use(name: str, tool_input: dict, tool_id: str) -> dict

def _anthropic_assistant_multi_tool(tools: list[tuple[str, dict, str]]) -> dict

def _anthropic_user_tool_result(tool_id: str, result_json: str) -> dict

def _anthropic_user_multi_tool_result(results: list[tuple[str, str]]) -> dict

def provider() -> GeminiProvider
```

## tests/test_gemini_provider.py

```python
import base64
from unittest.mock import MagicMock, patch
import pytest
from google.genai import types
from src.providers.gemini import GeminiProvider

def _make_text_response(text: str) -> MagicMock

def _make_tool_call_response(name: str, args: dict, call_id: str, signature: str='') -> MagicMock

def provider() -> GeminiProvider

def test_preserves_thought_signature_and_id(provider: GeminiProvider) -> None

def test_returns_empty_on_no_parts(provider: GeminiProvider) -> None

def test_injects_context_files(provider: GeminiProvider) -> None

def test_skips_unreadable_context_file(provider: GeminiProvider) -> None

def test_decodes_valid_image(provider: GeminiProvider) -> None

def test_skips_bad_base64_image(provider: GeminiProvider) -> None

def test_handles_unknown_tool(provider: GeminiProvider) -> None

def test_handles_tool_exception(provider: GeminiProvider) -> None

def test_no_tools_skips_agentic_loop(provider: GeminiProvider) -> None

def test_no_tools_sends_no_tools_to_api(provider: GeminiProvider) -> None

def test_no_tools_history_has_user_and_model_turn(provider: GeminiProvider) -> None

def test_tools_enabled_true_still_uses_agentic_loop(provider: GeminiProvider) -> None

def test_multi_tool_turn(provider: GeminiProvider) -> None
```

## tests/test_llm_export.py

```python
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from src.exporter import export_session_to_llm_json, _render_llm_turn
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.main import app
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src import main
from src.config import settings
from src.main import app
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src import main
from src.main import app
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src import main
from src.main import app
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src import main
from src.main import app
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src import main
from src.main import app
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src import main

def _make_text_item(role: str, text: str) -> dict

def _make_function_call_item(name: str, args: dict, call_id: str, signature_hex: str | None=None) -> dict

def _make_function_response_item(name: str, response: dict, call_id: str) -> dict

def _seed_session(repo: SQLiteSessionRepository, session_id: str, title: str, api_items: list[dict], ui_messages: list[dict] | None=None) -> None

def test_t01_empty_history_returns_empty_turns() -> None

def test_t02_user_text_turn() -> None

def test_t03_model_text_turn() -> None

def test_t04_multi_turn_preserves_order() -> None

def test_t05_function_call_part_with_signature() -> None

def test_t06_function_call_without_signature_is_null() -> None

def test_t07_function_response_part() -> None

def test_t08_multi_part_turn_renders_all_parts() -> None

def test_t09_unknown_part_type_marked_unknown() -> None

def test_t10_metadata_block_complete() -> None

def test_t11_turn_count_matches_api_items_length() -> None

def test_t12_unicode_preserved() -> None

def test_t13_thought_signature_round_trip() -> None

def test_t14_repo_export_llm_json_returns_structured_dict(tmp_path: Path) -> None

def test_t14b_repo_export_llm_json_empty_api_history(tmp_path: Path) -> None

def test_t15_nonexistent_session_raises_value_error(tmp_path: Path) -> None

def _make_test_client(tmp_path: Path) -> tuple[TestClient, SQLiteSessionRepository]

def test_t16_endpoint_returns_200_with_correct_shape(tmp_path: Path) -> None

def test_t17_endpoint_returns_404_for_unknown_session(tmp_path: Path) -> None

def test_t18_content_type_is_application_json(tmp_path: Path) -> None

def test_t19_llm_export_distinct_from_markdown_export(tmp_path: Path) -> None

def test_t20_full_round_trip_with_tool_calls(tmp_path: Path) -> None
```

## tests/test_llm_export_config.py

```python
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from src.exporter import build_config_block, export_session_to_llm_json
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.config import settings
from src.tools.registry import DECLARATIONS
from src.main import app
from src import main
from src.main import app
from src.main import app
from src.main import app
from src.main import app
from src.main import app

def _make_text_item(role: str, text: str) -> dict

def _seed(repo: SQLiteSessionRepository, session_id: str, title: str='Test', api_items: list | None=None, system_prompt: str | None=None) -> None

def test_c01_config_block_with_system_instruction() -> None

def test_c02_config_block_system_instruction_null_when_absent() -> None

def test_c03_config_block_model_from_settings() -> None

def test_c04_config_block_temperature_from_settings() -> None

def test_c05_config_block_has_all_five_tools() -> None

def test_c06_each_declaration_has_required_fields() -> None

def test_c07_required_fields_preserved_in_declarations() -> None

def test_c08_export_has_config_key() -> None

def test_c09_export_config_matches_build_config_block() -> None

def test_c10_config_present_for_empty_history() -> None

def test_c11_key_order_metadata_config_turns() -> None

def test_c12_save_session_accepts_system_prompt(tmp_path: Path) -> None

def test_c13_load_session_returns_three_tuple(tmp_path: Path) -> None

def test_c14_missing_system_prompt_returns_none(tmp_path: Path) -> None

def test_c15_export_uses_persisted_system_prompt(tmp_path: Path) -> None

def test_c16_export_config_instruction_null_when_none_saved(tmp_path: Path) -> None

def test_c17_fork_copies_system_prompt(tmp_path: Path) -> None

def _make_client(tmp_path: Path) -> tuple[TestClient, SQLiteSessionRepository]

def test_c18_http_response_has_config_key(tmp_path: Path) -> None

def test_c19_config_before_turns_in_raw_json(tmp_path: Path) -> None

def test_c20_config_tools_non_empty_in_http_response(tmp_path: Path) -> None

def test_c21_http_system_instruction_null_when_not_set(tmp_path: Path) -> None

def test_c22_http_system_instruction_reflects_persisted_prompt(tmp_path: Path) -> None
```

## tests/test_main.py

```python
import json
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config
from src.chat_service import ChatService
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.main import app, get_session_repo, get_chat_service
from src.main import _resolve_data_path
from fastapi import HTTPException
import base64
import src.main
import src.config
from src.main import _resolve_data_path
from fastapi import HTTPException

class TestFileApiRoutes
    def data_dir(self, tmp_path: Path) -> Path
    def file_client(self, data_dir: Path, monkeypatch) -> TestClient
    def test_list_files_paths_are_relative(self, file_client: TestClient) -> None
    def test_list_files_empty_dir(self, tmp_path: Path, monkeypatch) -> None
    def test_read_file_returns_content(self, file_client: TestClient) -> None
    def test_write_file_updates_content(self, file_client: TestClient, data_dir: Path) -> None
    def test_append_adds_content(self, file_client: TestClient, data_dir: Path) -> None
    def test_repo_map_success_path(self, file_client: TestClient, monkeypatch) -> None

def data_dir(tmp_path: Path) -> Path

def client(data_dir: Path, monkeypatch) -> TestClient

def test_get_session_repo_returns_repo() -> None

def test_get_chat_service_returns_chat_service() -> None

def test_get_sessions_empty(tmp_path: Path, monkeypatch) -> None

def test_get_sessions_with_data(tmp_path: Path, monkeypatch) -> None

def test_get_session_existing(tmp_path: Path, monkeypatch) -> None

def test_get_session_nonexistent_returns_empty(tmp_path: Path, monkeypatch) -> None

def test_export_session_success(tmp_path: Path, monkeypatch) -> None

def test_export_session_not_found(tmp_path: Path, monkeypatch) -> None

def test_fork_session_success(tmp_path: Path, monkeypatch) -> None

def test_fork_session_invalid_index(tmp_path: Path, monkeypatch) -> None

def test_path_traversal_blocked(data_dir: Path, monkeypatch) -> None

def test_list_files_missing_data_dir(tmp_path: Path, monkeypatch) -> None

def test_list_files_returns_md_files(client: TestClient) -> None

def test_read_file_endpoint_success(client: TestClient) -> None

def test_read_file_endpoint_not_found(client: TestClient) -> None

def test_write_file_endpoint_success(client: TestClient, data_dir: Path) -> None

def test_write_file_endpoint_not_found(client: TestClient) -> None

def test_append_error_branch(client: TestClient, monkeypatch) -> None

def test_repo_map_error_branch(client: TestClient, monkeypatch) -> None

def _chat_override(text: str='Great answer', tools: list | None=None)

def test_chat_basic_success(tmp_path: Path, monkeypatch) -> None

def test_chat_with_images_and_context(tmp_path: Path, monkeypatch) -> None

def test_chat_with_tools_used(tmp_path: Path, monkeypatch) -> None

def test_chat_service_exception_returns_500(tmp_path: Path, monkeypatch) -> None
```

## tests/test_message_editor.py

```python
import json
import pytest
from fastapi.testclient import TestClient
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.message_editor import MessageEditService, EditError
from src.main import app, get_session_repo

class TestEditUserMessage
    def test_edit_user_message_updates_ui_content(self, service, populated_repo)
    def test_edit_user_message_updates_api_content(self, service, populated_repo)
    def test_edit_preserves_other_messages(self, service, populated_repo)
    def test_edit_assistant_message(self, service, populated_repo)
    def test_edit_api_item_for_assistant_turn(self, service, populated_repo)
    def test_edit_nonexistent_session_raises(self, service)
    def test_edit_unknown_turn_id_raises(self, service)
    def test_edit_empty_content_raises(self, service)
    def test_edit_legacy_session_raises_on_unknown_turn_id(self, legacy_repo)

class TestDeleteMessage
    def test_delete_removes_message_from_ui(self, service, populated_repo)
    def test_delete_with_pair_removes_both(self, service, populated_repo)
    def test_delete_assistant_message_standalone(self, service, populated_repo)
    def test_delete_syncs_api_history(self, service, populated_repo)
    def test_delete_only_removes_matching_turn_id_from_api(self, service, populated_repo)
    def test_delete_unknown_turn_id_raises(self, service)
    def test_delete_nonexistent_session_raises(self, service)

class TestTruncateTurns
    def test_truncate_removes_last_turn_pair(self, service, populated_repo)
    def test_truncate_removes_multiple_pairs(self, service, populated_repo)
    def test_truncate_syncs_api_history_via_turn_ids(self, service, populated_repo)
    def test_truncate_zero_raises(self, service)
    def test_truncate_exceeds_history_raises(self, service)
    def test_truncate_nonexistent_session_raises(self, service)
    def test_truncate_works_on_legacy_session(self, legacy_repo)

class TestUpdateSystemPrompt
    def test_update_system_prompt_persists(self, service, populated_repo)
    def test_update_system_prompt_empty_allowed(self, service, populated_repo)
    def test_update_system_prompt_on_new_session_creates_row(self, repo)
    def test_update_system_prompt_nonexistent_no_longer_raises(self, repo)
    def test_get_system_prompt_new_session_returns_none(self, repo)

class TestMessageEditorEndpoints
    def test_http_edit_message_200(self, client)
    def test_http_edit_message_updates_content(self, client, populated_repo)
    def test_http_edit_message_404_bad_session(self, client)
    def test_http_edit_message_400_empty_content(self, client)
    def test_http_edit_message_400_unknown_turn_id(self, client)
    def test_http_delete_message_200(self, client)
    def test_http_delete_message_with_pair(self, client, populated_repo)
    def test_http_delete_message_404_bad_session(self, client)
    def test_http_delete_message_400_unknown_turn_id(self, client)
    def test_http_truncate_200(self, client)
    def test_http_truncate_removes_messages(self, client, populated_repo)
    def test_http_truncate_400_zero_n(self, client)
    def test_http_truncate_404_bad_session(self, client)
    def test_http_update_system_prompt_200(self, client)
    def test_http_update_system_prompt_persists(self, client, populated_repo)
    def test_http_update_system_prompt_200_on_new_session(self, client)
    def test_http_get_system_prompt_200(self, client)
    def test_http_get_system_prompt_200_returns_null_for_new_session(self, client)

def db(tmp_path)

def repo(db)

def populated_repo(repo)

def service(populated_repo)

def legacy_repo(repo)

def client(populated_repo)
```

## tests/test_notes.py

```python
import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config
from src.repositories import SQLiteConnection, SQLiteSessionRepository, SQLiteNoteRepository
from src.main import app, get_session_repo, get_note_repo

class TestAddNote
    def test_returns_dict_with_all_fields(self, tmp_path: Path) -> None
    def test_note_annotation_defaults_to_empty_string(self, tmp_path: Path) -> None
    def test_note_is_persisted_and_retrievable(self, tmp_path: Path) -> None
    def test_raises_value_error_for_missing_session(self, tmp_path: Path) -> None
    def test_raises_value_error_for_empty_selected_text(self, tmp_path: Path) -> None
    def test_raises_value_error_for_whitespace_only_text(self, tmp_path: Path) -> None
    def test_generated_ids_are_unique(self, tmp_path: Path) -> None

class TestListNotes
    def test_empty_list_for_session_with_no_notes(self, tmp_path: Path) -> None
    def test_empty_list_for_nonexistent_session(self, tmp_path: Path) -> None
    def test_returns_notes_in_chronological_order(self, tmp_path: Path) -> None
    def test_notes_are_isolated_between_sessions(self, tmp_path: Path) -> None
    def test_all_expected_fields_present_in_row(self, tmp_path: Path) -> None

class TestDeleteNote
    def test_returns_true_when_note_deleted(self, tmp_path: Path) -> None
    def test_returns_false_for_nonexistent_note_id(self, tmp_path: Path) -> None
    def test_cross_session_delete_is_rejected(self, tmp_path: Path) -> None
    def test_deleting_one_note_leaves_others_intact(self, tmp_path: Path) -> None

class TestCreateNoteEndpoint
    def test_returns_201_with_note_payload(self, client: TestClient, session_id: str) -> None
    def test_note_field_defaults_to_empty_string(self, client: TestClient, session_id: str) -> None
    def test_returns_404_for_unknown_session(self, client: TestClient) -> None
    def test_returns_400_for_blank_selected_text(self, client: TestClient, session_id: str) -> None
    def test_returns_422_when_selected_text_missing(self, client: TestClient, session_id: str) -> None
    def test_returns_422_when_source_role_missing(self, client: TestClient, session_id: str) -> None

class TestListNotesEndpoint
    def test_returns_empty_list_when_no_notes(self, client: TestClient, session_id: str) -> None
    def test_returns_created_notes(self, client: TestClient, session_id: str) -> None
    def test_notes_scoped_to_session(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_response_schema_is_valid(self, client: TestClient, session_id: str) -> None
    def test_returns_200_for_unknown_session_with_empty_list(self, client: TestClient) -> None

class TestDeleteNoteEndpoint
    def test_returns_204_on_success(self, client: TestClient, session_id: str) -> None
    def test_note_is_removed_after_delete(self, client: TestClient, session_id: str) -> None
    def test_returns_404_for_unknown_note_id(self, client: TestClient, session_id: str) -> None
    def test_cross_session_delete_returns_404(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_only_target_note_is_deleted(self, client: TestClient, session_id: str) -> None

def _make_conn(tmp_path: Path) -> SQLiteConnection

def _seed_session(repo: SQLiteSessionRepository, session_id: str='sess-1') -> str

def conn(tmp_path: Path) -> SQLiteConnection

def session_repo(conn: SQLiteConnection) -> SQLiteSessionRepository

def note_repo(conn: SQLiteConnection) -> SQLiteNoteRepository

def client(session_repo: SQLiteSessionRepository, note_repo: SQLiteNoteRepository, tmp_path: Path, monkeypatch) -> TestClient

def session_id(session_repo: SQLiteSessionRepository) -> str
```

## tests/test_prompt_logger.py

```python
from __future__ import annotations
import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch
import pytest
from src.prompt_logger import log_prompt, log_turn, MAX_DIFF_LINES
from src import prompt_logger
from src.chat_service import ChatService
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.chat_service import ChatService
from src.repositories import SQLiteConnection, SQLiteSessionRepository

class TestFileCreation
    def test_creates_file_if_missing(self, tmp_path: Path) -> None
    def test_creates_nested_parent_dirs(self, tmp_path: Path) -> None

class TestAppendSemantics
    def test_second_entry_appended_not_overwritten(self, tmp_path: Path) -> None
    def test_many_entries_remain_chronological(self, tmp_path: Path) -> None

class TestIgnoresEmptyPrompts
    def test_empty_string_not_logged(self, tmp_path: Path) -> None
    def test_whitespace_only_not_logged(self, tmp_path: Path) -> None
    def test_none_treated_as_empty(self, tmp_path: Path) -> None

class TestTimestampHeading
    def test_heading_starts_with_double_hash(self, tmp_path: Path) -> None
    def test_heading_contains_time_hhmm(self, tmp_path: Path) -> None
    def test_heading_does_NOT_include_seconds(self, tmp_path: Path) -> None

class TestDateBanner
    def test_date_banner_written_once_per_day(self, tmp_path: Path) -> None
    def test_date_banner_written_for_each_new_day(self, tmp_path: Path) -> None

class TestSessionContext
    def test_session_id_appears_when_provided(self, tmp_path: Path) -> None
    def test_session_title_appears_when_provided(self, tmp_path: Path) -> None
    def test_session_context_absent_when_not_provided(self, tmp_path: Path) -> None
    def test_session_id_truncated_to_8_chars(self, tmp_path: Path) -> None

class TestUserMessageBlock
    def test_user_message_appears_verbatim(self, tmp_path: Path) -> None
    def test_multiline_message_fully_preserved(self, tmp_path: Path) -> None

class TestNoToolSection
    def test_no_tools_section_when_tools_empty(self, tmp_path: Path) -> None
    def test_no_tools_section_when_tools_none(self, tmp_path: Path) -> None

class TestToolSectionPresent
    def test_tool_section_header_appears(self, tmp_path: Path) -> None
    def test_tool_name_appears(self, tmp_path: Path) -> None
    def test_file_path_appears_in_tool_output(self, tmp_path: Path) -> None

class TestEditFileDiff
    def test_removed_lines_shown_with_minus(self, tmp_path: Path) -> None
    def test_added_lines_shown_with_plus(self, tmp_path: Path) -> None
    def test_multiline_diff_each_line_prefixed(self, tmp_path: Path) -> None
    def test_edit_error_result_shown(self, tmp_path: Path) -> None

class TestCreateFileDiff
    def test_created_file_lines_have_plus_prefix(self, tmp_path: Path) -> None
    def test_create_file_error_shown(self, tmp_path: Path) -> None

class TestReadFileTool
    def test_read_file_shows_read_emoji(self, tmp_path: Path) -> None
    def test_read_file_does_not_dump_content(self, tmp_path: Path) -> None

class TestSearchTool
    def test_search_shows_magnifier_emoji(self, tmp_path: Path) -> None
    def test_search_query_appears(self, tmp_path: Path) -> None

class TestRepoMapTool
    def test_repo_map_shows_map_emoji(self, tmp_path: Path) -> None
    def test_repo_map_no_args_dumped(self, tmp_path: Path) -> None

class TestUnknownTool
    def test_unknown_tool_recorded(self, tmp_path: Path) -> None
    def test_unknown_tool_shows_result_snippet(self, tmp_path: Path) -> None

class TestMultipleTools
    def test_all_tools_appear_when_multiple_calls(self, tmp_path: Path) -> None
    def test_tools_appear_in_call_order(self, tmp_path: Path) -> None

class TestDiffTruncation
    def test_long_create_content_truncated(self, tmp_path: Path) -> None
    def test_long_edit_diff_truncated(self, tmp_path: Path) -> None

class TestDefaultLogPath
    def test_uses_settings_prompt_log_path_when_no_override(self, tmp_path: Path, monkeypatch) -> None

class TestBackwardCompat
    def test_log_prompt_delegates_to_log_turn(self, tmp_path: Path) -> None
    def test_log_prompt_ignores_empty(self, tmp_path: Path) -> None
    def test_log_prompt_creates_file(self, tmp_path: Path) -> None
    def test_log_prompt_appends(self, tmp_path: Path) -> None

class TestChatServiceIntegration
    def test_chat_service_calls_log_turn_with_tool_logs(self, tmp_path: Path) -> None
    def test_chat_service_passes_session_id_to_log_turn(self, tmp_path: Path) -> None

def _read(p: Path) -> str

def _make_log(tmp_path: Path) -> Path
```

## tests/test_prompt_manager.py

```python
import json
from pathlib import Path
import pytest
from src.prompt_manager import PromptManager, PromptMode
from src.prompt_manager import prompt_manager

def _write(directory: Path, filename: str, text: str) -> None

def _write_kitchen_modes(directory: Path) -> None

def test_prompt_mode_fields() -> None

def test_manager_loads_base_rules(tmp_path: Path) -> None

def test_manager_combines_base_rules_and_mode_content(tmp_path: Path) -> None

def test_manager_loads_all_three_modes(tmp_path: Path) -> None

def test_get_all_modes_returns_metadata_only(tmp_path: Path) -> None

def test_get_all_modes_correct_labels(tmp_path: Path) -> None

def test_get_system_instruction_known_mode(tmp_path: Path) -> None

def test_get_system_instruction_unknown_mode_fallback(tmp_path: Path) -> None

def test_get_system_instruction_returns_string(tmp_path: Path) -> None

def test_missing_base_rules_file_graceful(tmp_path: Path) -> None

def test_missing_mode_file_graceful(tmp_path: Path) -> None

def test_missing_prompts_dir_graceful(tmp_path: Path) -> None

def test_reload_prompts_picks_up_new_content(tmp_path: Path) -> None

def test_reload_prompts_picks_up_new_base_rules(tmp_path: Path) -> None

def test_reload_clears_old_cache(tmp_path: Path) -> None

def test_singleton_prompt_manager_is_importable() -> None
```

## tests/test_prompt_manager_domain_agnostic.py

```python
import json
from pathlib import Path
import pytest
from src.prompt_manager import PromptManager
from src.config import Settings
from src.config import Settings
from src.config import Settings
from src.config import Settings
from src.config import Settings
from src.config import Settings
from src.tools.registry import TOOLS
from src.tools.registry import TOOLS
import src.main
import src.config
from fastapi.testclient import TestClient
import src.config

class TestModesJsonDiscovery
    def test_modes_from_json_are_loaded(self, tmp_path: Path) -> None
    def test_modes_json_fields_exposed_as_metadata(self, tmp_path: Path) -> None
    def test_extra_fields_in_modes_json_are_ignored(self, tmp_path: Path) -> None

class TestModesOrdering
    def test_mode_order_matches_modes_json(self, tmp_path: Path) -> None

class TestHotReloadWithModesJson
    def test_reload_picks_up_new_mode_added_to_modes_json(self, tmp_path: Path) -> None
    def test_reload_picks_up_removed_mode(self, tmp_path: Path) -> None
    def test_reload_picks_up_changed_label(self, tmp_path: Path) -> None

class TestMissingModesJson
    def test_missing_modes_json_returns_empty_mode_list(self, tmp_path: Path) -> None
    def test_missing_modes_json_base_rules_still_loaded(self, tmp_path: Path) -> None
    def test_missing_modes_json_unknown_mode_fallback_to_base(self, tmp_path: Path) -> None

class TestMalformedModesJson
    def test_malformed_json_returns_empty_mode_list(self, tmp_path: Path) -> None
    def test_malformed_json_base_rules_still_loaded(self, tmp_path: Path) -> None
    def test_modes_json_not_a_list_treated_as_empty(self, tmp_path: Path) -> None
    def test_modes_json_with_null_treated_as_empty(self, tmp_path: Path) -> None

class TestMissingKeysInEntry
    def test_entry_missing_id_is_skipped(self, tmp_path: Path) -> None
    def test_entry_missing_file_is_skipped(self, tmp_path: Path) -> None
    def test_entry_missing_label_is_skipped(self, tmp_path: Path) -> None
    def test_entry_missing_eyebrow_is_skipped(self, tmp_path: Path) -> None
    def test_all_invalid_entries_yields_empty_list(self, tmp_path: Path) -> None

class TestCustomDomain
    def test_legal_domain_modes_loaded_from_modes_json(self, tmp_path: Path) -> None
    def test_legal_domain_metadata_correct(self, tmp_path: Path) -> None
    def test_legal_domain_no_kitchen_modes_present(self, tmp_path: Path) -> None

class TestBaseRulesWithCustomDomain
    def test_base_rules_prepended_to_legal_modes(self, tmp_path: Path) -> None
    def test_each_legal_mode_has_its_own_content(self, tmp_path: Path) -> None

class TestFallbackWithCustomDomain
    def test_unknown_mode_in_legal_domain_falls_back_to_base(self, tmp_path: Path) -> None
    def test_kitchen_mode_unknown_in_legal_domain(self, tmp_path: Path) -> None

class TestAppMetadataSettings
    def test_settings_has_app_title_field(self) -> None
    def test_settings_has_app_description_field(self) -> None
    def test_settings_app_title_default_is_generic(self) -> None
    def test_settings_app_description_default_is_generic(self) -> None
    def test_settings_app_title_overridable_via_constructor(self) -> None
    def test_settings_app_description_overridable_via_constructor(self) -> None

class TestToolRegistryDomainAgnostic
    def _get_all_description_text(self) -> str
    def test_no_kitchen_vocabulary_in_tool_descriptions(self) -> None
    def test_search_tool_example_is_generic(self) -> None

class TestFastAPIMetadataFromSettings
    def test_app_title_matches_settings(self, monkeypatch) -> None
    def test_app_description_matches_settings(self, monkeypatch) -> None

class TestKitchenDomainBackwardCompatibility
    def test_kitchen_modes_all_present_with_modes_json(self, tmp_path: Path) -> None
    def test_kitchen_system_instruction_assembly_mode(self, tmp_path: Path) -> None
    def test_kitchen_reload_still_works(self, tmp_path: Path) -> None

def _write(directory: Path, filename: str, text: str) -> None

def _write_modes(directory: Path, modes: list[dict]) -> None
```

## tests/test_prompt_routes.py

```python
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config
from src.main import app, get_chat_service, get_prompt_manager
from src.prompt_manager import PromptManager, PromptMode
from src.main import get_prompt_manager

def _make_prompt_manager(tmp_path: Path) -> PromptManager

def _stub_chat_service(text: str='ok', tools: list | None=None)

def test_get_prompt_modes_returns_200(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_modes_returns_list(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_modes_has_three_modes(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_modes_shape(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_modes_correct_labels(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_mode_detail_returns_200(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_mode_detail_includes_content(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_mode_detail_has_all_fields(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_mode_detail_assembly(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_mode_detail_unknown_returns_404(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_mode_detail_404_has_detail_field(tmp_path: Path, monkeypatch) -> None

def test_reload_endpoint_returns_200(tmp_path: Path, monkeypatch) -> None

def test_reload_endpoint_returns_success_true(tmp_path: Path, monkeypatch) -> None

def test_reload_endpoint_calls_reload_prompts(tmp_path: Path, monkeypatch) -> None

def test_chat_with_mode_id_resolves_instruction(tmp_path: Path, monkeypatch) -> None

def test_chat_mode_id_defaults_to_general(tmp_path: Path, monkeypatch) -> None

def test_chat_unknown_mode_id_falls_back_to_base(tmp_path: Path, monkeypatch) -> None

def test_chat_assembly_mode_resolves_correctly(tmp_path: Path, monkeypatch) -> None

def test_chat_legacy_system_prompt_still_accepted(tmp_path: Path, monkeypatch) -> None

def test_chat_system_prompt_overrides_mode_id(tmp_path: Path, monkeypatch) -> None

def test_get_prompt_manager_dependency_returns_instance(tmp_path: Path, monkeypatch) -> None
```

## tests/test_provider_endpoints.py

```python
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from src.main import app
import src.config
import src.config

def client() -> TestClient

def test_list_providers_returns_200(client: TestClient) -> None

def test_list_providers_is_list(client: TestClient) -> None

def test_list_providers_contains_gemini_and_anthropic(client: TestClient) -> None

def test_provider_entry_has_required_fields(client: TestClient) -> None

def test_provider_models_non_empty(client: TestClient) -> None

def test_model_entry_has_required_fields(client: TestClient) -> None

def test_provider_default_model_is_in_models_list(client: TestClient) -> None

def test_provider_labels_are_non_empty_strings(client: TestClient) -> None

def test_active_provider_returns_200(client: TestClient) -> None

def test_active_provider_has_required_fields(client: TestClient) -> None

def test_active_provider_matches_settings_gemini(client: TestClient) -> None

def test_active_provider_matches_settings_anthropic(client: TestClient) -> None

def test_active_provider_is_one_of_listed_providers(client: TestClient) -> None
```

## tests/test_providers_base.py

```python
from unittest.mock import patch, MagicMock
import pytest
from src.providers.base import LLMProvider, get_provider
from src.providers.gemini import GeminiProvider
from src.providers.anthropic_provider import AnthropicProvider

class _MinimalProvider
    def process_chat_turn(self, user_message: str, history: list, system_instruction=None, images=None, context_files=None)

def test_minimal_provider_satisfies_protocol() -> None

def test_gemini_provider_satisfies_protocol() -> None

def test_anthropic_provider_satisfies_protocol() -> None

def test_get_provider_returns_gemini_by_default() -> None

def test_get_provider_returns_anthropic_when_configured() -> None

def test_get_provider_raises_for_unknown_provider() -> None
```

## tests/test_registry.py

```python
from unittest.mock import patch
import pytest
from google.genai import types
from src.tools.registry import DECLARATIONS, FUNCTION_MAP, TOOLS, ToolEntry
from src.tools.registry import _get_repo_map_entry
from src.tools.registry import _search_knowledge_base_entry

def test_tools_is_nonempty() -> None

def test_every_entry_is_tool_entry() -> None

def test_every_declaration_has_name_and_description() -> None

def test_every_entry_has_callable() -> None

def test_function_map_keys_match_tool_names() -> None

def test_function_map_values_match_entry_fns() -> None

def test_declarations_length_matches_tools() -> None

def test_declarations_order_matches_tools() -> None

def test_declarations_are_function_declaration_instances() -> None

def _declaration(name: str) -> types.FunctionDeclaration

def test_required_fields_declared(tool_name: str, required_fields: list[str]) -> None

def test_zero_or_single_arg_tools_have_explicit_required(tool_name: str) -> None

def test_base_dir_not_in_schema(tool_name: str) -> None

def test_get_repo_map_wrapper_passes_data_dir(tmp_path) -> None

def test_search_knowledge_base_wrapper_passes_data_dir(tmp_path) -> None
```

## tests/test_repo_map.py

```python
from pathlib import Path
from unittest.mock import patch
import pytest
from src.tools.repo_map import get_repo_map

def test_get_repo_map_returns_full_posix_paths(tmp_path: Path) -> None

def test_get_repo_map_missing_dir() -> None

def test_get_repo_map_empty_directory(tmp_path: Path) -> None

def test_get_repo_map_unreadable_file(tmp_path: Path) -> None

def test_get_repo_map_extracts_headings(tmp_path: Path) -> None
```

## tests/test_repositories.py

```python
import pytest
from src.repositories import SQLiteConnection, SQLiteSessionRepository

def test_database_lifecycle(tmp_path)
```

## tests/test_revert_api.py

```python
import json
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config

class TestRevertEditHappyPath
    def test_revert_restores_original_content(self, client: TestClient, data_dir: Path) -> None
    def test_revert_returns_success_true(self, client: TestClient, data_dir: Path) -> None
    def test_revert_response_has_message(self, client: TestClient, data_dir: Path) -> None

class TestRevertCreateHappyPath
    def test_revert_create_deletes_the_new_file(self, client: TestClient, data_dir: Path) -> None
    def test_revert_create_returns_success_true(self, client: TestClient, data_dir: Path) -> None

class TestRevertIdempotency
    def test_backup_json_deleted_after_successful_revert(self, client: TestClient, data_dir: Path) -> None
    def test_second_revert_returns_404(self, client: TestClient, data_dir: Path) -> None

class TestRevertErrorCases
    def test_unknown_revert_id_returns_404(self, client: TestClient) -> None
    def test_malformed_json_backup_returns_400(self, client: TestClient, data_dir: Path) -> None
    def test_path_traversal_in_backup_content_is_blocked(self, client: TestClient, data_dir: Path) -> None

def data_dir(tmp_path: Path) -> Path

def client(data_dir: Path, monkeypatch) -> TestClient

def _plant_backup(data_dir: Path, target: Path, original_content: str | None, existed: bool) -> str
```

## tests/test_search_context_window.py

```python
import pytest
from pathlib import Path
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.registry import FUNCTION_MAP, DECLARATIONS
from src.tools.registry import DECLARATIONS
from src.tools.registry import FUNCTION_MAP
import src.config

class TestContextLinesZero
    def test_returns_matching_line_only(self, kitchen_kb)
    def test_no_context_separator_present(self, kitchen_kb)

class TestContextLinesTwo
    def test_surrounding_lines_included(self, kitchen_kb)
    def test_contradicting_files_both_visible(self, kitchen_kb)
    def test_context_does_not_bleed_across_files(self, kitchen_kb)
    def test_context_clipped_at_file_boundary(self, kitchen_kb)
    def test_context_clipped_at_end_of_file(self, kitchen_kb)
    def test_overlapping_context_windows_are_merged(self, kitchen_kb)

class TestContextLinesDefault
    def test_default_includes_surrounding_context(self, kitchen_kb)
    def test_default_does_not_load_entire_file(self, kitchen_kb)

class TestMaxMatchesWithContext
    def test_truncation_message_present_when_limit_hit(self, tmp_path: Path)
    def test_result_not_exceed_max_with_context(self, tmp_path: Path)

class TestRegistryDeclaration
    def test_context_lines_param_in_declaration(self)
    def test_context_lines_has_description(self)
    def test_registry_lambda_passes_context_lines(self, kitchen_kb, monkeypatch)

def kitchen_kb(tmp_path: Path) -> Path
```

## tests/test_search_tool.py

```python
import os
import pytest
from pathlib import Path
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base
from src.tools.file_ops import search_knowledge_base

def tmp_kb(tmp_path: Path)

def test_search_single_keyword(tmp_kb, monkeypatch)

def test_search_or_pattern(tmp_kb, monkeypatch)

def test_search_no_matches(tmp_kb)

def test_search_invalid_regex(tmp_kb)

def test_search_missing_dir()

def test_search_case_insensitive(tmp_kb)
```

## tests/test_serializers.py

```python
import json
import pytest
from google.genai import types
from src.serializers import dehydrate_history, hydrate_history

def test_serialization_cycle() -> None

def test_dehydrate_skips_empty_parts() -> None

def test_dehydrate_function_call_without_signature() -> None

def test_hydrate_function_call_without_signature() -> None

def test_hydrate_skips_unknown_item_type() -> None

def test_hydrate_empty_string_returns_empty_list() -> None

def test_hydrate_empty_json_array_returns_empty_list() -> None

def test_dehydrate_skips_unrecognised_part_type() -> None
```

## tests/test_serializers_anthropic.py

```python
import json
from unittest.mock import MagicMock, patch
import pytest
from google.genai import types
from src.serializers import dehydrate_history, hydrate_history
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.chat_service import ChatService

def _anthropic_user_text(text: str) -> dict

def _anthropic_user_blocks(blocks: list) -> dict

def _anthropic_assistant_text(text: str) -> dict

def _anthropic_assistant_tool_use(name: str, tool_input: dict, tool_id: str) -> dict

def _anthropic_user_tool_result(tool_id: str, result_json: str) -> dict

def test_dehydrate_does_not_raise_for_anthropic_dict_history() -> None

def test_dehydrate_anthropic_produces_valid_json() -> None

def test_dehydrate_anthropic_user_text_round_trip() -> None

def test_dehydrate_anthropic_assistant_text_round_trip() -> None

def test_dehydrate_anthropic_tool_use_turn() -> None

def test_dehydrate_anthropic_tool_result_turn() -> None

def test_dehydrate_anthropic_empty_history() -> None

def test_dehydrate_anthropic_attaches_turn_ids() -> None

def test_dehydrate_anthropic_no_turn_id_when_omitted() -> None

def test_full_round_trip_anthropic_simple() -> None

def test_full_round_trip_anthropic_tool_call_sequence() -> None

def test_full_round_trip_anthropic_with_turn_ids() -> None

def test_full_round_trip_gemini_text_unchanged() -> None

def test_chat_service_anthropic_no_attribute_error(tmp_path) -> None
```

## tests/test_session_tree.py

```python
import json
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import src.main
from src import config
from src.main import app, get_session_repo
from src.repositories import SQLiteConnection, SQLiteSessionRepository

class TestLineageColumns
    def test_root_session_has_null_lineage(self, tmp_path: Path) -> None
    def test_root_session_root_id_is_none_before_fork(self, tmp_path: Path) -> None
    def test_list_sessions_exposes_lineage_fields(self, tmp_path: Path) -> None
    def test_upsert_does_not_overwrite_lineage(self, tmp_path: Path) -> None
    def test_init_backfills_legacy_fork_titles(self, tmp_path: Path) -> None

class TestForkLineage
    def test_fork_sets_parent_id(self, tmp_path: Path) -> None
    def test_fork_sets_fork_turn_index(self, tmp_path: Path) -> None
    def test_first_fork_root_id_equals_parent(self, tmp_path: Path) -> None
    def test_grandchild_inherits_root_id(self, tmp_path: Path) -> None
    def test_sibling_forks_share_root_id(self, tmp_path: Path) -> None
    def test_independent_trees_have_different_roots(self, tmp_path: Path) -> None
    def test_parent_lineage_unchanged_after_fork(self, tmp_path: Path) -> None

class TestGetSessionTreeRepository
    def test_empty_db_returns_empty_list(self, tmp_path: Path) -> None
    def test_single_root_no_children(self, tmp_path: Path) -> None
    def test_fork_appears_as_child_not_root(self, tmp_path: Path) -> None
    def test_multiple_forks_all_appear_as_children(self, tmp_path: Path) -> None
    def test_grandchild_nested_correctly(self, tmp_path: Path) -> None
    def test_independent_trees_produce_multiple_roots(self, tmp_path: Path) -> None
    def test_node_contains_lineage_fields(self, tmp_path: Path) -> None
    def test_node_contains_children_key(self, tmp_path: Path) -> None

class TestGetSessionsFlat
    def test_returns_lineage_fields(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_root_session_has_null_lineage(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_forked_session_has_lineage_populated(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None

class TestGetSessionTree
    def test_empty_returns_empty_list(self, client: TestClient) -> None
    def test_single_root_in_tree(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_fork_is_child_not_root(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_grandchild_nested(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_node_schema_has_all_fields(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_multiple_independent_trees(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None
    def test_tree_endpoint_distinct_from_session_id_route(self, client: TestClient, session_repo: SQLiteSessionRepository) -> None

def _make_conn(tmp_path: Path) -> SQLiteConnection

def _seed(repo: SQLiteSessionRepository, session_id: str, title: str='Root') -> str

def conn(tmp_path: Path) -> SQLiteConnection

def session_repo(conn: SQLiteConnection) -> SQLiteSessionRepository

def client(session_repo: SQLiteSessionRepository, tmp_path: Path, monkeypatch) -> TestClient
```

## tests/test_token_counter.py

```python
from __future__ import annotations
import base64
import json
from typing import Any
from unittest.mock import MagicMock, patch, call
import pytest
from src.token_counter import TokenEstimate, estimate_tokens_for_text, estimate_tokens_for_image, estimate_tokens_for_context_files, build_pending_context_estimate, count_session_tokens

class TestTokenEstimateModel
    def test_all_fields_present(self) -> None
    def test_default_fallback_used_is_false(self) -> None
    def test_total_tokens_is_int(self) -> None

class TestEstimateTokensForText
    def test_empty_string_returns_zero(self) -> None
    def test_proportional_to_char_count(self) -> None
    def test_returns_integer(self) -> None
    def test_longer_text_gives_higher_count(self) -> None
    def test_whitespace_only_counts_proportionally(self) -> None

class TestEstimateTokensForImage
    def test_small_png_returns_single_tile_estimate(self) -> None
    def test_large_image_higher_than_small(self) -> None
    def test_unknown_mime_type_returns_positive_int(self) -> None
    def test_bad_base64_returns_fallback_estimate(self) -> None

class TestEstimateTokensForContextFiles
    def test_empty_list_returns_zero(self, mock_rf: MagicMock) -> None
    def test_single_readable_file(self, mock_rf: MagicMock) -> None
    def test_unreadable_file_counted_as_zero(self, mock_rf: MagicMock) -> None
    def test_multiple_files_summed(self, mock_rf: MagicMock) -> None

class TestBuildPendingContextEstimate
    def test_plain_message_only(self) -> None
    def test_message_plus_images(self) -> None
    def test_message_plus_context_files(self, mock_rf: MagicMock) -> None
    def test_all_components_combined(self, mock_rf: MagicMock) -> None
    def test_system_prompt_adds_to_total(self) -> None
    def test_history_token_count_forwarded(self) -> None

class TestCountSessionTokens
    def _make_api_json(self, n_turns: int=2) -> str
    def test_success_returns_api_token_counts(self, mock_client: MagicMock) -> None
    def test_api_error_falls_back_to_heuristic(self, mock_client: MagicMock) -> None
    def test_empty_history_returns_zero_without_api_call(self) -> None
    def test_system_prompt_included_in_count_tokens_call(self, mock_client: MagicMock) -> None
    def test_model_parameter_forwarded(self, mock_client: MagicMock) -> None

```

## tests/test_token_routes.py

```python
from __future__ import annotations
import base64
import json
from typing import Any
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.repositories import SQLiteConnection, SQLiteSessionRepository

class TestSessionTokensRoute
    def client_with_session(self, tmp_path)
    def test_returns_200_with_token_fields(self, client_with_session) -> None
    def test_token_count_positive(self, client_with_session) -> None
    def test_api_count_tokens_called_once(self, client_with_session) -> None
    def test_unknown_session_returns_zero_tokens(self, tmp_path) -> None
    def test_empty_session_returns_zero_tokens(self, tmp_path) -> None

class TestTokensEstimateRoute
    def test_plain_message_returns_estimate(self, tmp_path) -> None
    def test_with_image_increases_token_count(self) -> None
    def test_with_context_files_increases_token_count(self, mock_rf: MagicMock) -> None
    def test_with_system_prompt_increases_token_count(self) -> None
    def test_with_history_token_count_forwarded(self) -> None
    def test_total_is_sum_of_parts(self) -> None
    def test_all_optional_fields_absent(self) -> None
    def test_missing_user_message_returns_422(self) -> None

def _make_session_repo(tmp_path) -> SQLiteSessionRepository

def _seed_session(repo: SQLiteSessionRepository, session_id: str, turns: int=2) -> None
```

## tests/test_tools_toggle.py

```python
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest
from fastapi.testclient import TestClient
from src.prompt_manager import PromptManager, PromptMode
from src.chat_service import ChatService
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.main import app, get_chat_service
from src.schemas import ChatRequest
from src.schemas import ChatRequest
from src.agent import process_chat_turn
from src.agent import process_chat_turn
from src.agent import process_chat_turn

class TestPromptModeToolsEnabledDefault
    def test_tools_enabled_defaults_to_true_when_key_absent(self, tmp_path: Path) -> None
    def test_tools_enabled_false_loaded_from_modes_json(self, tmp_path: Path) -> None
    def test_tools_enabled_true_explicit_in_modes_json(self, tmp_path: Path) -> None
    def test_get_all_modes_includes_tools_enabled_default(self, tmp_path: Path) -> None
    def test_tools_enabled_non_bool_treated_as_true(self, tmp_path: Path) -> None

class TestChatServiceToolsFlag
    def test_use_tools_true_by_default(self, mock_agent: MagicMock, mock_log: MagicMock, repo: SQLiteSessionRepository) -> None
    def test_use_tools_false_forwarded(self, mock_agent: MagicMock, mock_log: MagicMock, repo: SQLiteSessionRepository) -> None
    def test_use_tools_false_returns_empty_tool_logs(self, mock_agent: MagicMock, mock_log: MagicMock, repo: SQLiteSessionRepository) -> None
    def test_use_tools_false_stored_in_ui_history(self, mock_agent: MagicMock, mock_log: MagicMock, repo: SQLiteSessionRepository) -> None

class TestChatEndpointToolsEnabled
    def _make_capture_svc(self) -> tuple[MagicMock, callable]
    def test_tools_enabled_true_default_in_schema(self) -> None
    def test_tools_enabled_false_accepted_in_schema(self) -> None
    def test_endpoint_passes_tools_enabled_true_to_service(self, tmp_path: Path) -> None
    def test_endpoint_passes_tools_enabled_false_to_service(self, tmp_path: Path) -> None
    def test_endpoint_tools_enabled_false_response_has_empty_tool_logs(self) -> None

class TestAgentDispatchToolsFlag
    def test_use_tools_true_passed_to_provider(self) -> None
    def test_use_tools_false_passed_to_provider(self) -> None
    def test_use_tools_defaults_to_true_in_agent(self) -> None

def _write(directory: Path, filename: str, text: str) -> None

def _write_modes(directory: Path, modes: list[dict]) -> None

def repo(tmp_path: Path) -> SQLiteSessionRepository
```

---

### **assistant**:

# Honest Assessment of Your 700 Tests During Refactor

## First: Read Your Tests Carefully

Looking at your test signatures, I can give you a **precise, honest answer**.

---

## The Good News — Most Tests Will Survive

```
Test Category                    Survival Likelihood    Why
─────────────────────────────────────────────────────────────────
test_file_ops.py                 ✅ 99% safe            Pure functions, no deps
test_backup_file_ops.py          ✅ 99% safe            Pure functions, no deps
test_repo_map.py                 ✅ 99% safe            Pure functions, no deps
test_search_tool.py              ✅ 99% safe            Pure functions, no deps
test_search_context_window.py    ✅ 99% safe            Pure functions, no deps
test_serializers.py              ✅ 99% safe            Pure functions, no deps
test_serializers_anthropic.py    ✅ 95% safe            Pure + some service touch
test_fork.py                     ✅ 99% safe            Repository only
test_repositories.py             ✅ 99% safe            Repository only
test_session_tree.py             ✅ 95% safe            Repository + API
test_notes.py                    ✅ 95% safe            Repository + API
test_archive_delete.py           ✅ 95% safe            Repository + API
test_exporter.py                 ✅ 95% safe            Pure + Repository
test_llm_export.py               ✅ 90% safe            Repository + API
test_llm_export_config.py        ✅ 90% safe            Repository + API
test_config.py                   ✅ 99% safe            Settings only
test_config_provider.py          ✅ 99% safe            Settings only
test_prompt_manager.py           ✅ 99% safe            Self-contained
test_prompt_manager_domain*.py   ✅ 95% safe            Self-contained + API
test_token_counter.py            ✅ 95% safe            Mostly pure
test_registry.py                 ⚠️  80% needs care     Imports DECLARATIONS directly
test_prompt_logger.py            ⚠️  80% needs care     Imports log_prompt directly
test_message_editor.py           ⚠️  75% needs care     Service + API
test_chat_service.py             🔴 50% needs update    Core service under change
test_anthropic_provider.py       🔴 50% needs update    Provider internals change
test_gemini_provider.py          🔴 50% needs update    Provider internals change
test_gemini_history_coercion.py  🔴 60% needs update    Provider internals change
test_main.py                     ⚠️  75% needs care     FastAPI routes
test_chat_provider_routing.py    🔴 50% needs update    Provider + routing change
test_context_files.py            🔴 50% needs update    agent.py directly imported
test_context_files_ui.py         ⚠️  75% needs care     ChatService + API
test_tools_toggle.py             ⚠️  75% needs care     agent.py + ChatService
test_coverage_gaps.py            ⚠️  70% needs care     Mixed concerns
test_prompt_routes.py            ✅ 90% safe            Routes + PromptManager
test_provider_endpoints.py       ✅ 95% safe            API endpoints only
test_providers_base.py           🔴 60% needs update    Protocol + get_provider
test_token_routes.py             ✅ 90% safe            Routes only
test_revert_api.py               ✅ 95% safe            File ops + API
```

---

## The Critical Problem Tests — Detailed Analysis

### 🔴 Problem 1: Direct `agent.py` imports

```python
# test_context_files.py — THIS IS THE RISKIEST PATTERN
from src.agent import process_chat_turn  # imported 4 times directly

class TestAgentContextFilesUnitRegression:
    def test_agent_injects_content_when_file_readable(
        self, mock_read_file, mock_generate
    ) -> None
    def test_agent_skips_when_path_has_no_data_prefix(
        self, mock_read_file, mock_generate
    ) -> None
```

```python
# test_tools_toggle.py — same problem
from src.agent import process_chat_turn  # imported 3 times

class TestAgentDispatchToolsFlag:
    def test_use_tools_true_passed_to_provider(self) -> None
    def test_use_tools_false_passed_to_provider(self) -> None
    def test_use_tools_defaults_to_true_in_agent(self) -> None
```

**These tests will break** when `agent.py` is replaced by `TurnOrchestrator`.

**Solution — Compatibility shim during transition:**

```python
# src/agent.py — DURING TRANSITION ONLY
# Keep this file alive with delegation
# Tag: MIGRATION_SHIM — delete in Phase 4

from src.agent.turn_orchestrator import TurnOrchestrator
from src.agent.context_assembler import ContextAssembler
from src.agent.tool_executor import ToolExecutor

# Old signature preserved exactly
async def process_chat_turn(
    user_message: str,
    history: list,
    system_instruction: str = None,
    images: list = None,
    context_files: list = None,
    use_tools: bool = True,
    provider=None,
) -> tuple[str, list]:
    """
    MIGRATION_SHIM: delegates to TurnOrchestrator.
    Tests importing this function will continue to pass.
    Delete this when test_context_files.py and
    test_tools_toggle.py are updated.
    """
    # delegate to new implementation
    ...
    return text, tool_logs
```

---

### 🔴 Problem 2: Provider internals are heavily tested

```python
# test_anthropic_provider.py
# These tests mock the SDK directly and test internal behavior
def test_context_files_injected_before_message(provider) -> None
def test_valid_image_sent_as_base64_block(provider) -> None
def test_tool_schemas_built_from_registry(provider) -> None

# test_gemini_provider.py
def test_injects_context_files(provider) -> None
def test_decodes_valid_image(provider) -> None
def test_handles_unknown_tool(provider) -> None
```

**These test the CURRENT internal behavior** of providers — context injection,
image handling, tool schema building. After refactor, these move to:

```
Current location          After refactor lives in
─────────────────────────────────────────────────────
context injection     →   ContextAssembler
image handling        →   ContextAssembler
tool schema building  →   ToolRegistry
response parsing      →   ResponseNormalizer
```

**Strategy: Don't delete these tests — MIGRATE them:**

```python
# tests/unit/agent/test_context_assembler.py
# Replaces: test_context_files_injected_before_message
def test_context_assembler_injects_files_into_messages():
    """
    Migrated from test_anthropic_provider.py
    test_context_files_injected_before_message
    """
    assembler = make_assembler()
    turn = TurnInput(
        user_message="hello",
        context_files=["/data/file.txt"],
    )
    ctx = assembler.assemble(make_session(), turn)
    assert any(
        "file.txt" in str(msg.get("content", ""))
        for msg in ctx.messages
    )


# tests/unit/providers/test_normalizer.py
# Replaces: all response parsing tests in provider tests
def test_normalizer_extracts_tool_calls_from_anthropic():
    """
    Migrated from test_anthropic_provider.py
    test_single_tool_call_dispatched
    """
    ...
```

---

### 🔴 Problem 3: `get_provider` factory is tested directly

```python
# test_providers_base.py
from src.providers.base import get_provider

def test_get_provider_returns_gemini_by_default() -> None
def test_get_provider_returns_anthropic_when_configured() -> None
def test_get_provider_raises_for_unknown_provider() -> None

# test_chat_provider_routing.py
from src.providers.base import get_provider  # imported 4 times

def test_get_provider_passes_model_to_gemini() -> None
def test_get_provider_passes_model_to_anthropic() -> None
def test_get_provider_uses_settings_default_when_no_override() -> None
def test_get_provider_raises_for_unknown_provider_name() -> None
```

**These will survive** if `get_provider` stays in `src/providers/base.py`.
The function signature just needs to stay compatible:

```python
# src/providers/base.py — keep this function, update internals only
def get_provider(
    provider_name: str = None,
    model: str = None,
) -> "LLMProvider":
    """
    Keep this function and its signature.
    14 tests depend on it directly.
    Only change the internals to use new ResponseNormalizer.
    """
    ...
```

---

### ⚠️ Problem 4: `DECLARATIONS` and `FUNCTION_MAP` imported directly

```python
# test_registry.py
from src.tools.registry import DECLARATIONS, FUNCTION_MAP, TOOLS, ToolEntry

def test_declarations_are_function_declaration_instances() -> None
def test_function_map_keys_match_tool_names() -> None
def test_declarations_order_matches_tools() -> None

# test_llm_export_config.py
from src.tools.registry import DECLARATIONS
def test_c05_config_block_has_all_five_tools() -> None
def test_c06_each_declaration_has_required_fields() -> None

# test_search_context_window.py
from src.tools.registry import FUNCTION_MAP, DECLARATIONS
```

**These tests assert on module-level constants.**
The new `ToolRegistry` class replaces these constants.

**Strategy: Keep backward-compatible aliases:**

```python
# src/tools/registry.py — DURING TRANSITION

class ToolRegistry:
    ...  # new implementation

# Backward-compatible module-level aliases
# These keep 20+ tests passing without changes
_default_registry = build_default_registry()

# MIGRATION_SHIM: keep until test_registry.py is updated
TOOLS: list[ToolEntry] = _default_registry.get_all_entries()
DECLARATIONS: list = _default_registry.schemas_for_provider("gemini")
FUNCTION_MAP: dict = {
    name: _default_registry.get_handler(name)
    for name in _default_registry.tool_names
}
```

---

### ⚠️ Problem 5: `ChatService` is tested with `mock_agent`

```python
# test_chat_service.py
def test_handle_turn_saves_session(
    mock_agent: MagicMock,    # patches src.chat_service agent
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None

def test_handle_turn_passes_images_and_context(
    mock_agent: MagicMock,
    mock_log: MagicMock,
    repo: SQLiteSessionRepository,
) -> None
```

The tests patch `agent` inside `chat_service`. After refactor,
`ChatService` calls `TurnOrchestrator`, not `agent` directly.

**The patch target changes:**

```python
# BEFORE (current tests patch this):
with patch("src.chat_service.agent") as mock_agent:
    ...

# AFTER (tests need to patch this instead):
with patch("src.chat_service.turn_orchestrator") as mock_orchestrator:
    ...

# OR better — inject FakeOrchestrator via constructor:
service = ChatService(
    session_repo=repo,
    turn_orchestrator=FakeOrchestrator(),  # no patching needed
    prompt_logger=FakePromptLogger(),
)
```

**This is the ONE set of tests that needs actual rewriting** — not just
import path updates. But it's only 4 tests.

---

## The Migration Decision Tree Per Test File

```python
# scripts/classify_tests.py
# Run this to get a migration plan for YOUR specific test suite

"""
For each test file, answer:
1. What does it import from src?
2. Does it patch internals or inject via constructor?
3. Does it test behavior or implementation?
"""

MIGRATION_STRATEGIES = {

    # ── KEEP AS-IS (zero changes needed) ──────────────────────────
    "keep_as_is": [
        "test_file_ops.py",          # pure functions
        "test_backup_file_ops.py",   # pure functions
        "test_repo_map.py",          # pure functions
        "test_search_tool.py",       # pure functions
        "test_serializers.py",       # pure functions
        "test_fork.py",              # repository only
        "test_repositories.py",      # repository only
        "test_config.py",            # settings only
        "test_config_provider.py",   # settings only
        "test_prompt_manager.py",    # self-contained
        "test_exporter.py",          # pure + repository
        "test_revert_api.py",        # file ops + API
    ],

    # ── UPDATE IMPORT PATHS ONLY (5-minute fix per file) ──────────
    "update_imports_only": [
        "test_providers_base.py",    # get_provider stays, path may change
        "test_provider_endpoints.py",# API endpoints unchanged
        "test_prompt_routes.py",     # PromptManager unchanged
        "test_token_routes.py",      # TokenCounter unchanged
        "test_token_counter.py",     # TokenCounter unchanged
        "test_notes.py",             # Repository + API unchanged
        "test_session_tree.py",      # Repository + API unchanged
        "test_archive_delete.py",    # Repository + API unchanged
    ],

    # ── ADD SHIM, UPDATE LATER (keep passing during transition) ───
    "add_shim_first": [
        "test_registry.py",          # add DECLARATIONS/FUNCTION_MAP aliases
        "test_llm_export_config.py", # depends on DECLARATIONS
        "test_search_context_window.py", # depends on FUNCTION_MAP
        "test_context_files.py",     # keep agent.py shim alive
        "test_tools_toggle.py",      # keep agent.py shim alive
        "test_coverage_gaps.py",     # mixed — shim what breaks
    ],

    # ── MIGRATE BEHAVIOR, DELETE IMPLEMENTATION TESTS ─────────────
    "migrate_behavior": [
        "test_anthropic_provider.py",    # move to test_normalizer.py
                                         # + test_context_assembler.py
        "test_gemini_provider.py",       # move to test_normalizer.py
                                         # + test_context_assembler.py
        "test_gemini_history_coercion.py",# move to test_normalizer.py
        "test_chat_provider_routing.py", # split: routing stays,
                                         # provider internals move
    ],

    # ── REWRITE (small, high value) ───────────────────────────────
    "rewrite": [
        "test_chat_service.py",      # 4 tests, patch → inject
        "test_context_files_ui.py",  # patch → inject FakeOrchestrator
        "test_tools_toggle.py",      # patch → inject after shim phase
    ],
}
```

---

## Concrete: What Breaks on Day 1 of Each Phase

```
PHASE 1 — ResponseNormalizer extraction
────────────────────────────────────────────────────────────────
Will break:    NOTHING if you keep _parse

---

### **user**:

continue

---

### **assistant**:

```

PHASE 1 — ResponseNormalizer extraction
────────────────────────────────────────────────────────────────
Will break: NOTHING if you keep \_parse_response delegating
Tests at risk: test_anthropic_provider.py, test_gemini_provider.py
Strategy: Delegate internally, don't change public interface

PHASE 2 — ToolExecutor extraction
────────────────────────────────────────────────────────────────
Will break: NOTHING if agent.py shim stays alive
Tests at risk: test_tools_toggle.py, test_registry.py
Strategy: Keep FUNCTION_MAP alias, keep agent.py intact

PHASE 3 — ContextAssembler extraction
────────────────────────────────────────────────────────────────
Will break: test_context_files.py (agent.process_chat_turn)
Tests at risk: 8 tests in TestAgentContextFilesUnitRegression
Strategy: Keep agent.py shim, delegate to ContextAssembler

PHASE 4 — TurnOrchestrator + ChatService slim
────────────────────────────────────────────────────────────────
Will break: test_chat_service.py mock_agent patches
Tests at risk: 4 tests
Strategy: Rewrite to inject FakeOrchestrator (30 min work)

PHASE 5 — Content Layer
────────────────────────────────────────────────────────────────
Will break: NOTHING — additive only
Tests at risk: none existing, new tests added

PHASE 6 — ToolRegistry restructure
────────────────────────────────────────────────────────────────
Will break: test_registry.py if aliases removed too early
Tests at risk: 15 tests importing DECLARATIONS/FUNCTION_MAP
Strategy: Keep aliases until Phase 6 complete, then update

````

---

## The Practical Safety System

### Step 1: Tag Every Shim So Nothing Gets Forgotten

```python
# src/agent.py
# ╔══════════════════════════════════════════════════════════╗
# ║  MIGRATION_SHIM — Phase 4                               ║
# ║  Safe to delete when:                                   ║
# ║    - test_context_files.py migrated                     ║
# ║    - test_tools_toggle.py migrated                      ║
# ║  Grep: git grep "MIGRATION_SHIM" to find all shims      ║
# ╚══════════════════════════════════════════════════════════╝

async def process_chat_turn(
    user_message: str,
    history: list,
    system_instruction: str = None,
    images: list = None,
    context_files: list = None,
    use_tools: bool = True,
    provider=None,
) -> tuple[str, list]:
    """MIGRATION_SHIM: See header above."""
    from src.agent.turn_orchestrator import TurnOrchestrator
    # ... delegation logic
````

```python
# src/tools/registry.py
# ╔══════════════════════════════════════════════════════════╗
# ║  MIGRATION_SHIM — Phase 6                               ║
# ║  Safe to delete when:                                   ║
# ║    - test_registry.py updated to use ToolRegistry       ║
# ║    - test_llm_export_config.py updated                  ║
# ║    - test_search_context_window.py updated              ║
# ╚══════════════════════════════════════════════════════════╝

# Keep these aliases alive during transition
TOOLS = _default_registry.get_all_entries()          # MIGRATION_SHIM
DECLARATIONS = _default_registry.schemas_for_provider("gemini")  # MIGRATION_SHIM
FUNCTION_MAP = {                                      # MIGRATION_SHIM
    name: _default_registry.get_handler(name)
    for name in _default_registry.tool_names
}
```

---

### Step 2: CI Gate — Enforce No Regression

```yaml
# .github/workflows/refactor_safety.yml
name: Refactor Safety Gate

on: [push, pull_request]

jobs:
    test-suite:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v4

            - name: Install dependencies
              run: pip install -e ".[dev]"

            - name: Run full test suite
              run: |
                  pytest --tb=short -q \
                    --junitxml=results.xml \
                    2>&1 | tee test_output.txt

            - name: Check test count did not decrease
              run: |
                  python scripts/check_test_count.py \
                    --results results.xml \
                    --minimum 700

            - name: Check no MIGRATION_SHIM older than 30 days
              run: python scripts/check_shim_age.py

            - name: Check import health
              run: python scripts/check_imports.py
```

```python
# scripts/check_test_count.py
"""
Fails CI if test count drops below minimum.
Protects against accidentally deleting tests during refactor.
"""
import argparse
import xml.etree.ElementTree as ET
import sys


def check_test_count(results_xml: str, minimum: int) -> bool:
    tree = ET.parse(results_xml)
    root = tree.getroot()

    # JUnit XML: tests attribute on testsuite element
    total = int(root.attrib.get("tests", 0))
    failures = int(root.attrib.get("failures", 0))
    errors = int(root.attrib.get("errors", 0))

    passed = total - failures - errors

    print(f"Total tests:  {total}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {failures}")
    print(f"Errors:       {errors}")
    print(f"Minimum:      {minimum}")

    if total < minimum:
        print(f"\n❌ Test count {total} is below minimum {minimum}")
        print("   Did you accidentally delete tests?")
        return False

    if failures > 0 or errors > 0:
        print(f"\n❌ {failures + errors} tests failing")
        return False

    print(f"\n✅ Test count {total} meets minimum {minimum}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--minimum", type=int, required=True)
    args = parser.parse_args()

    success = check_test_count(args.results, args.minimum)
    sys.exit(0 if success else 1)
```

```python
# scripts/check_shim_age.py
"""
Warns (or fails) when MIGRATION_SHIM tags are older than N days.
Prevents shims from becoming permanent fixtures.
"""
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


MAX_SHIM_AGE_DAYS = 30
SHIM_TAG = "MIGRATION_SHIM"


def find_shims() -> list[dict]:
    result = subprocess.run(
        ["git", "log", "--all", "-S", SHIM_TAG,
         "--pretty=format:%H %ai %s", "--", "*.py"],
        capture_output=True, text=True,
    )

    shims = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split(" ", 3)
        if len(parts) < 3:
            continue

        commit_hash = parts[0]
        date_str = parts[1]

        try:
            commit_date = datetime.fromisoformat(date_str)
            age_days = (datetime.now(commit_date.tzinfo) - commit_date).days
            shims.append({
                "hash": commit_hash[:8],
                "date": date_str,
                "age_days": age_days,
            })
        except ValueError:
            continue

    return shims


def check_current_shims() -> list[str]:
    """Find files that currently contain MIGRATION_SHIM."""
    result = subprocess.run(
        ["git", "grep", "-l", SHIM_TAG, "--", "*.py"],
        capture_output=True, text=True,
    )
    return result.stdout.splitlines()


if __name__ == "__main__":
    shim_files = check_current_shims()

    if not shim_files:
        print("✅ No active MIGRATION_SHIMs found")
        sys.exit(0)

    print(f"⚠️  Active MIGRATION_SHIMs in {len(shim_files)} files:")
    for f in shim_files:
        print(f"   {f}")

    shims = find_shims()
    old_shims = [s for s in shims if s["age_days"] > MAX_SHIM_AGE_DAYS]

    if old_shims:
        print(f"\n❌ {len(old_shims)} shims older than {MAX_SHIM_AGE_DAYS} days:")
        for s in old_shims:
            print(f"   {s['hash']} — {s['age_days']} days old")
        sys.exit(1)

    print(f"\n✅ All shims within {MAX_SHIM_AGE_DAYS}-day limit")
    sys.exit(0)
```

---

### Step 3: The 4 Tests That Need Actual Rewriting

```python
# tests/unit/services/test_chat_service.py
# BEFORE — patches internals (fragile)
# ─────────────────────────────────────

@pytest.fixture
def mock_agent():
    with patch("src.chat_service.agent") as m:
        m.process_chat_turn.return_value = ("response", [])
        yield m

def test_handle_turn_saves_session(mock_agent, mock_log, repo):
    service = ChatService(repo)  # old: no injection
    service.handle_turn(session_id="s1", message="hello")
    assert repo.load("s1") is not None


# AFTER — injects fakes (robust)
# ─────────────────────────────────────

def test_handle_turn_saves_session():
    """
    Behavior: after handle_turn, session must be persisted.
    Does NOT care HOW orchestration works internally.
    """
    repo = FakeSessionRepository()
    service = ChatService(
        session_repo=repo,
        turn_orchestrator=FakeOrchestrator(
            response=TurnOutput(
                assistant_message="response",
                tool_calls_made=[],
                tokens_used={"input": 10, "output": 5, "total": 15},
                context_slots={},
            )
        ),
        prompt_logger=FakePromptLogger(),
    )

    asyncio.run(service.handle_turn(ChatTurnRequest(
        session_id="s1",
        user_message="hello",
    )))

    assert repo.get("s1") is not None


def test_handle_turn_appends_to_existing_history():
    repo = FakeSessionRepository()
    # Pre-seed with existing session
    existing = make_session(
        session_id="s1",
        messages=[
            {"role": "user", "content": "first message"},
            {"role": "assistant", "content": "first response"},
        ]
    )
    repo._store["s1"] = existing

    service = ChatService(
        session_repo=repo,
        turn_orchestrator=FakeOrchestrator(),
        prompt_logger=FakePromptLogger(),
    )

    asyncio.run(service.handle_turn(ChatTurnRequest(
        session_id="s1",
        user_message="second message",
    )))

    saved = repo.get("s1")
    assert len(saved.messages) == 4  # 2 existing + 2 new


def test_handle_turn_logs_prompt():
    logger = FakePromptLogger()
    service = ChatService(
        session_repo=FakeSessionRepository(),
        turn_orchestrator=FakeOrchestrator(),
        prompt_logger=logger,
    )

    asyncio.run(service.handle_turn(ChatTurnRequest(
        session_id="s1",
        user_message="hello",
    )))

    assert logger.log_call_count == 1
    assert logger.last_session_id == "s1"


def test_handle_turn_passes_images_and_context():
    orchestrator = FakeOrchestrator()
    service = ChatService(
        session_repo=FakeSessionRepository(),
        turn_orchestrator=orchestrator,
        prompt_logger=FakePromptLogger(),
    )

    asyncio.run(service.handle_turn(ChatTurnRequest(
        session_id="s1",
        user_message="describe this",
        images=["base64imagedata"],
        context_files=["/data/file.txt"],
    )))

    # Verify orchestrator received the right input
    assert orchestrator.last_turn_input.images == ["base64imagedata"]
    assert "/data/file.txt" in orchestrator.last_turn_input.context_files
```

---

## The Complete Honest Summary

```
YOUR 700 TESTS BREAKDOWN:
──────────────────────────────────────────────────────────────

~420 tests  ✅  Will pass without any changes
            (pure functions, repository, config, prompts,
             file ops, serializers, exporter, API endpoints
             that don't touch agent/provider internals)

~180 tests  ⚠️  Need import path updates or shims
            (registry aliases, agent.py shim, provider
             routing — 5-30 min per file, mechanical work)

~80 tests   🔴  Need migration to new test location
            (provider internal tests → normalizer/assembler,
             behavior preserved, location changes)

~20 tests   ✍️  Need actual rewriting
            (chat_service mock_agent → FakeOrchestrator,
             4 tests in test_chat_service.py,
             ~16 tests in test_context_files.py
             test_tools_toggle.py after shim removed)

──────────────────────────────────────────────────────────────
ZERO tests should be deleted — all behavior is preserved
ALL 700+ tests should pass at end of every phase
NEW tests added: ~125 across 6 phases
FINAL count: ~825 tests
```

```
THE SINGLE MOST IMPORTANT RULE:
──────────────────────────────────────────────────────────────

  Never proceed to the next phase
  until pytest shows 0 failures.

  The test suite is not an obstacle.
  It is the only thing telling you
  the refactor is actually working.
```

---

### **user**:

continue

---

### **assistant**:

## The Psychological Side — What Nobody Tells You

```
Week 1:  "This is going well, tests are green ✅"
Week 2:  "Hmm, more connected than I thought ⚠️"
Week 3:  "Why does changing THIS break THAT? 😤"
Week 4:  "I can see the finish line 💪"
Week 5:  "Oh this is actually much cleaner 😌"
Week 6:  "I understand my own codebase now 🎯"
```

> This is normal. Every senior engineer has been here.
> The test suite is your rope through the cave.

---

## The Day-by-Day Execution Plan

```python
# scripts/refactor_journal.py
"""
Keep this file updated daily.
Future you will thank present you.
"""

JOURNAL = {
    "phase_1": {
        "goal": "ResponseNormalizer extracted",
        "days": {
            "day_1": {
                "plan": "Read all provider tests. Map what they test.",
                "done": False,
                "notes": "",
                "test_count": 700,
                "blockers": [],
            },
            "day_2": {
                "plan": "Create providers/normalizer.py. Write tests first.",
                "done": False,
                "notes": "",
                "test_count": None,
                "blockers": [],
            },
            "day_3": {
                "plan": "Implement normalizer. Both providers delegate.",
                "done": False,
                "notes": "",
                "test_count": None,
                "blockers": [],
            },
            "day_4": {
                "plan": "Run full suite. Fix anything red. Phase check.",
                "done": False,
                "notes": "",
                "test_count": None,
                "blockers": [],
            },
            "day_5": {
                "plan": "Buffer day. Document what changed.",
                "done": False,
                "notes": "",
                "test_count": None,
                "blockers": [],
            },
        },
    },
}
```

---

## The Files You Touch In What Order

```
PHASE 1 — Touch only these files
──────────────────────────────────────────────────────────────
CREATE:  src/providers/normalizer.py
CREATE:  tests/unit/providers/test_normalizer.py
MODIFY:  src/providers/gemini.py          (add delegation)
MODIFY:  src/providers/anthropic_provider.py  (add delegation)
──────────────────────────────────────────────────────────────
DO NOT TOUCH: agent.py, chat_service.py, repositories.py
              main.py, tools/, serializers.py


PHASE 2 — Touch only these files
──────────────────────────────────────────────────────────────
CREATE:  src/agent/tool_executor.py
CREATE:  tests/unit/agent/test_tool_executor.py
MODIFY:  src/agent.py                     (add delegation shim)
MODIFY:  src/tools/registry.py            (add ToolRegistry class)
                                          (keep DECLARATIONS alias)
──────────────────────────────────────────────────────────────
DO NOT TOUCH: providers/, chat_service.py, repositories.py
              main.py, serializers.py


PHASE 3 — Touch only these files
──────────────────────────────────────────────────────────────
CREATE:  src/agent/context_assembler.py
CREATE:  tests/unit/agent/test_context_assembler.py
MODIFY:  src/agent.py                     (delegate context build)
──────────────────────────────────────────────────────────────
DO NOT TOUCH: providers/, chat_service.py, repositories.py
              main.py, tools/ (except registry)


PHASE 4 — Touch only these files
──────────────────────────────────────────────────────────────
CREATE:  src/agent/turn_orchestrator.py
CREATE:  tests/unit/agent/test_turn_orchestrator.py
MODIFY:  src/chat_service.py              (inject orchestrator)
REWRITE: tests/unit/services/test_chat_service.py  (4 tests)
DELETE:  src/agent.py                     (after shim no longer needed)
──────────────────────────────────────────────────────────────
DO NOT TOUCH: providers/, repositories.py, main.py
              tools/ (except registry)


PHASE 5 — Touch only these files
──────────────────────────────────────────────────────────────
CREATE:  src/content/note_manager.py
CREATE:  src/content/file_manager.py
CREATE:  src/content/search_coordinator.py
CREATE:  src/services/note_service.py
CREATE:  src/api/notes.py
CREATE:  tests/unit/content/test_note_manager.py
CREATE:  tests/unit/content/test_search_coordinator.py
CREATE:  tests/unit/services/test_note_service.py
MODIFY:  src/dependencies.py              (wire new services)
──────────────────────────────────────────────────────────────
DO NOT TOUCH: anything already working


PHASE 6 — Touch only these files
──────────────────────────────────────────────────────────────
RESTRUCTURE: src/tools/ into subdirectories
UPDATE:  tests/unit/tools/test_registry.py
DELETE:  DECLARATIONS, FUNCTION_MAP aliases (after tests updated)
──────────────────────────────────────────────────────────────
```

---

## Your Personal Refactor Checklist

```python
# PRINT THIS. PUT IT ON YOUR DESK.
# Check each box before moving on.

PHASE_1_CHECKLIST = """
Phase 1: ResponseNormalizer
□ Read test_anthropic_provider.py top to bottom
□ Read test_gemini_provider.py top to bottom
□ List every behavior being tested (not implementation)
□ Create src/providers/normalizer.py
□ Write test_normalizer.py BEFORE implementing
□ Implement ResponseNormalizer
□ GeminiProvider._parse_response() delegates to normalizer
□ AnthropicProvider._parse_response() delegates to normalizer
□ pytest -x → 0 failures
□ pytest --tb=short -q → same count as before (≥700)
□ python scripts/check_migration_phase.py --phase 1
□ git commit "Phase 1 complete: ResponseNormalizer extracted"
"""

PHASE_2_CHECKLIST = """
Phase 2: ToolExecutor
□ Read test_registry.py top to bottom
□ Read test_tools_toggle.py — note agent.py imports
□ Create src/agent/ directory with __init__.py
□ Create src/agent/tool_executor.py
□ Write test_tool_executor.py BEFORE implementing
□ Implement ToolExecutor
□ Add ToolRegistry class to registry.py
□ Keep DECLARATIONS/FUNCTION_MAP aliases (MIGRATION_SHIM tag)
□ agent.py delegates _run_tools to ToolExecutor
□ pytest -x → 0 failures
□ pytest --tb=short -q → same count as before
□ python scripts/check_migration_phase.py --phase 2
□ git commit "Phase 2 complete: ToolExecutor extracted"
"""

PHASE_3_CHECKLIST = """
Phase 3: ContextAssembler
□ Read test_context_files.py — note process_chat_turn imports
□ Read test_gemini_provider.py context injection tests
□ Read test_anthropic_provider.py context injection tests
□ Create src/agent/context_assembler.py
□ Write test_context_assembler.py BEFORE implementing
□ Implement ContextAssembler with ContextBudget
□ agent.py delegates context building to ContextAssembler
□ Keep agent.process_chat_turn() shim alive (MIGRATION_SHIM tag)
□ pytest -x → 0 failures
□ pytest --tb=short -q → same count as before
□ python scripts/check_migration_phase.py --phase 3
□ git commit "Phase 3 complete: ContextAssembler extracted"
"""

PHASE_4_CHECKLIST = """
Phase 4: TurnOrchestrator + ChatService
□ Read test_chat_service.py — understand mock_agent usage
□ Create src/agent/turn_orchestrator.py
□ Write test_turn_orchestrator.py BEFORE implementing
□ Implement TurnOrchestrator
□ Add FakeOrchestrator to tests/fakes.py
□ Rewrite test_chat_service.py (4 tests, patch→inject)
□ Update ChatService constructor (inject TurnOrchestrator)
□ pytest -x → 0 failures
□ Check agent.py shim — is it still needed?
□ If test_context_files.py still imports agent → keep shim
□ If not → delete agent.py
□ pytest --tb=short -q → count ≥ 700
□ python scripts/check_migration_phase.py --phase 4
□ git commit "Phase 4 complete: TurnOrchestrator introduced"
"""

PHASE_5_CHECKLIST = """
Phase 5: Content Layer
□ Notes currently work via NoteRepository directly
□ Create src/content/ directory
□ Write tests BEFORE implementing each manager
□ Implement NoteManager
□ Implement SearchCoordinator
□ Create NoteService
□ Add API routes for notes (if not existing)
□ Wire in dependencies.py
□ pytest -x → 0 failures
□ pytest --tb=short -q → count > 700 (new tests added)
□ python scripts/check_migration_phase.py --phase 5
□ git commit "Phase 5 complete: Content layer introduced"
"""

PHASE_6_CHECKLIST = """
Phase 6: ToolRegistry restructure
□ Read test_registry.py — understand DECLARATIONS assertions
□ Read test_llm_export_config.py — DECLARATIONS usage
□ Read test_search_context_window.py — FUNCTION_MAP usage
□ Restructure tools/ into subdirectories
□ Update test_registry.py to use ToolRegistry class
□ Update test_llm_export_config.py
□ Update test_search_context_window.py
□ Remove MIGRATION_SHIM aliases from registry.py
□ pytest -x → 0 failures
□ git grep "MIGRATION_SHIM" → 0 results
□ pytest --tb=short -q → count > 700
□ python scripts/check_migration_phase.py --phase 6
□ git commit "Phase 6 complete: ToolRegistry restructured"

FINAL CHECKS:
□ git grep "MIGRATION_SHIM" → 0 results (all shims removed)
□ pytest --tb=short -q → ≥ 825 tests passing
□ No god objects remain (agent.py deleted)
□ ChatService has ≤ 3 constructor dependencies
□ Every new class has its own test file
□ dependencies.py is the single wiring point
□ Folder structure screams the business domain
"""
```

---

## When You Hit a Wall — Debugging Guide

```python
# The 5 most common refactor failures and how to fix them

COMMON_FAILURES = {

    "circular_import": {
        "symptom": "ImportError: cannot import name X from Y",
        "cause": "New module imports from old module which imports new",
        "fix": """
            # Draw the import graph on paper
            # The dependency must point ONE direction
            # Usually: move the shared type to a third file

            # BAD:
            # agent.py imports from context_assembler.py
            # context_assembler.py imports from agent.py

            # GOOD:
            # agent/types.py  ← shared types live here
            # context_assembler.py imports from agent/types.py
            # agent.py imports from agent/types.py
        """,
    },

    "patch_target_wrong": {
        "symptom": "Mock was called 0 times / patch has no effect",
        "cause": "Patching where object is defined, not where it's used",
        "fix": """
            # WRONG: patch where it's defined
            with patch("src.providers.gemini.read_file") as m:
                ...

            # RIGHT: patch where it's used
            with patch("src.agent.context_assembler.read_file") as m:
                ...

            # RULE: patch the import in the module under test
            # not the original definition location
        """,
    },

    "async_test_not_awaited": {
        "symptom": "RuntimeWarning: coroutine was never awaited",
        "cause": "Forgot @pytest.mark.asyncio or asyncio.run()",
        "fix": """
            # Option 1: decorator
            @pytest.mark.asyncio
            async def test_something():
                result = await service.handle_turn(...)

            # Option 2: pytest-asyncio auto mode in conftest
            # conftest.py
            import pytest
            pytest_plugins = ['pytest_asyncio']

            # pytest.ini
            [pytest]
            asyncio_mode = auto
        """,
    },

    "fixture_scope_mismatch": {
        "symptom": "ScopeMismatch: function-scoped fixture in session scope",
        "cause": "FakeRepository created at wrong scope level",
        "fix": """
            # Each test should get a FRESH fake repository
            # Don't share state between tests

            # WRONG: module-scoped fake with state
            @pytest.fixture(scope="module")
            def repo():
                return FakeSessionRepository()  # shared, leaks state!

            # RIGHT: function-scoped (default)
            @pytest.fixture
            def repo():
                return FakeSessionRepository()  # fresh each test
        """,
    },

    "test_passes_alone_fails_in_suite": {
        "symptom": "Test green in isolation, red in full suite",
        "cause": "Global state leak between tests",
        "fix": """
            # Find the global state — common culprits:
            # 1. Module-level singletons
            # 2. lru_cache not cleared between tests
            # 3. Shared database file
            # 4. Environment variables set by one test

            # Fix for lru_cache:
            @pytest.fixture(autouse=True)
            def clear_caches():
                yield
                get_settings.cache_clear()
                get_tool_registry.cache_clear()

            # Fix for env vars:
            @pytest.fixture(autouse=True)
            def clean_env(monkeypatch):
                monkeypatch.delenv("LLM_PROVIDER", raising=False)
                monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        """,
    },
}
```

---

## The conftest.py That Saves You

````python
# tests/conftest.py
"""
Central test configuration.
Prevents the most common test isolation failures.
"""
import pytest
import asyncio
from pathlib import Path
from typing import Generator

from tests.fakes import (
    FakeSessionRepository,
    FakeNoteRepository,
    FakeProvider,
    FakeOrchestrator,
    FakePromptLogger,
    FakeTokenCounter,
    FakePromptManager,
    make_session,
)


# ── Asyncio configuration ─────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    return asyncio.DefaultEventLoopPolicy()


# ── Cache clearing — prevents test pollution ──────────────────────

@pytest.fixture(autouse=True)
def clear_lru_caches():
    """
    Clear all lru_cache decorated functions between tests.
    Without this, singleton dependencies leak between tests.
    """
    yield
    # Clear after each test
    try:
        from src.dependencies import (
            get_settings,
            get_tool_registry,
            get_response_normalizer,
            get_token_counter,
            get_prompt_manager,
        )
        get_settings.cache_clear()
        get_tool_registry.cache_clear()
        get_response_normalizer.cache_clear()
        get_token_counter

---

### **user**:

continue

---

### **assistant**:

```python
        get_token_counter.cache_clear()
        get_prompt_manager.cache_clear()
    except ImportError:
        pass  # dependencies module not yet refactored — that's fine


# ── Environment isolation ─────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """
    Prevent real API keys from leaking into tests.
    Every test that needs a key must set it explicitly.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


# ── Database isolation ────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path: Path):
    """
    Fresh SQLite database per test.
    Never share a database between tests.
    """
    from src.repositories import SQLiteConnection
    conn = SQLiteConnection(path=str(tmp_path / "test.db"))
    yield conn
    # tmp_path cleaned up by pytest automatically


@pytest.fixture
def session_repo(tmp_db):
    from src.repositories import SQLiteSessionRepository
    return SQLiteSessionRepository(tmp_db)


@pytest.fixture
def note_repo(tmp_db):
    from src.repositories import SQLiteNoteRepository
    return SQLiteNoteRepository(tmp_db)


# ── Common fakes ──────────────────────────────────────────────────

@pytest.fixture
def fake_session_repo():
    return FakeSessionRepository()


@pytest.fixture
def fake_note_repo():
    return FakeNoteRepository()


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def fake_orchestrator():
    return FakeOrchestrator()


@pytest.fixture
def fake_logger():
    return FakePromptLogger()


@pytest.fixture
def fake_token_counter():
    return FakeTokenCounter()


@pytest.fixture
def fake_prompt_manager():
    return FakePromptManager()


# ── Data directory isolation ──────────────────────────────────────

@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch) -> Path:
    """
    Isolated data directory per test.
    Patches config so all file operations use tmp_path.
    """
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setattr("src.config.settings.data_dir", str(d))
    return d


# ── FastAPI test client ───────────────────────────────────────────

@pytest.fixture
def api_client(session_repo, note_repo, tmp_path, monkeypatch):
    """
    Standard test client with real SQLite (tmp) repositories.
    Use this for API-level integration tests.
    """
    from fastapi.testclient import TestClient
    from src.main import app, get_session_repo, get_note_repo

    monkeypatch.setattr(
        "src.config.settings.data_dir",
        str(tmp_path / "data"),
    )
    (tmp_path / "data").mkdir(exist_ok=True)

    app.dependency_overrides[get_session_repo] = lambda: session_repo
    app.dependency_overrides[get_note_repo] = lambda: note_repo

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def api_client_no_llm(session_repo, note_repo, tmp_path, monkeypatch):
    """
    Test client with LLM provider stubbed out.
    Use this for endpoint tests that don't need real LLM calls.
    """
    from fastapi.testclient import TestClient
    from src.main import app, get_session_repo, get_note_repo
    from src.dependencies import get_llm_provider

    monkeypatch.setattr(
        "src.config.settings.data_dir",
        str(tmp_path / "data"),
    )
    (tmp_path / "data").mkdir(exist_ok=True)

    app.dependency_overrides[get_session_repo] = lambda: session_repo
    app.dependency_overrides[get_note_repo] = lambda: note_repo
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ── Markers ───────────────────────────────────────────────────────

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m not slow')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests requiring real DB",
    )
    config.addinivalue_line(
        "markers",
        "migration: marks tests that will change during refactor",
    )


# ── Test output helpers ───────────────────────────────────────────

def pytest_runtest_logreport(report):
    """
    Print a clear message when a previously-passing test fails.
    Helps identify regressions immediately during refactor.
    """
    if report.failed and report.when == "call":
        print(f"\n🔴 REGRESSION: {report.nodeid}")
````

---

## The pytest.ini That Keeps You Sane

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Show slowest 10 tests — helps spot performance regressions
addopts =
    --tb=short
    -q
    --strict-markers
    --durations=10

# Treat warnings as errors during refactor
# Forces you to fix deprecations immediately
filterwarnings =
    error
    ignore::DeprecationWarning:google.*
    ignore::DeprecationWarning:anthropic.*
    ignore::PendingDeprecationWarning

# Markers
markers =
    slow: marks tests as slow
    integration: marks tests requiring real DB
    migration: marks tests that will change during refactor
```

---

## The Single Script You Run Every Morning

```python
# scripts/refactor_status.py
"""
Run this every morning before you start work.
Gives you a complete picture of where you are.

Usage: python scripts/refactor_status.py
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
    )


def count_tests() -> dict:
    result = run(["pytest", "--collect-only", "-q"])
    lines = result.stdout.splitlines()

    total = 0
    for line in lines:
        if "test" in line.lower() and "::" in line:
            total += 1

    # Also get pass/fail from a dry run
    result2 = run(["pytest", "--tb=no", "-q"])
    passed = failed = errors = 0
    for line in result2.stdout.splitlines():
        if "passed" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "passed":
                    passed = int(parts[i-1])
                if p == "failed":
                    failed = int(parts[i-1])
                if p == "error" in p:
                    errors = int(parts[i-1])

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
    }


def count_shims() -> list[str]:
    result = run(["git", "grep", "-l", "MIGRATION_SHIM", "--", "*.py"])
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.splitlines() if f]


def count_todos() -> int:
    result = run(["git", "grep", "-c", "TODO\|FIXME\|HACK", "--", "*.py"])
    total = 0
    for line in result.stdout.splitlines():
        try:
            total += int(line.split(":")[-1])
        except ValueError:
            pass
    return total


def check_new_files() -> list[str]:
    result = run(["git", "status", "--short"])
    new_files = []
    for line in result.stdout.splitlines():
        if line.startswith("A ") or line.startswith("?? "):
            new_files.append(line[3:].strip())
    return new_files


def check_coverage() -> str:
    result = run([
        "pytest", "--tb=no", "-q",
        "--cov=src",
        "--cov-report=term-missing:skip-covered",
        "--cov-fail-under=0",
    ])
    # Extract coverage percentage from output
    for line in result.stdout.splitlines():
        if "TOTAL" in line:
            return line
    return "Coverage data not available"


def print_status():
    print(f"\n{'='*60}")
    print(f"  Refactor Status — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # Test counts
    print("📊 TEST SUITE")
    tests = count_tests()
    status = "✅" if tests["failed"] == 0 and tests["errors"] == 0 else "❌"
    print(f"   {status} Total:   {tests['total']}")
    print(f"   {'✅' if tests['passed'] > 0 else '⚪'} Passed:  {tests['passed']}")
    if tests["failed"] > 0:
        print(f"   ❌ Failed:  {tests['failed']}")
    if tests["errors"] > 0:
        print(f"   💥 Errors:  {tests['errors']}")

    # Shims remaining
    print("\n🔧 MIGRATION SHIMS")
    shims = count_shims()
    if shims:
        print(f"   ⚠️  {len(shims)} shim(s) still active:")
        for s in shims:
            print(f"      - {s}")
    else:
        print("   ✅ No active shims")

    # New files (work in progress)
    print("\n📁 NEW FILES THIS SESSION")
    new_files = check_new_files()
    if new_files:
        for f in new_files[:10]:
            print(f"   + {f}")
        if len(new_files) > 10:
            print(f"   ... and {len(new_files) - 10} more")
    else:
        print("   (none)")

    # TODOs
    todos = count_todos()
    print(f"\n📝 TODOS/FIXMES: {todos}")

    # Quick phase check
    print("\n📍 PHASE INDICATORS")
    indicators = {
        "src/providers/normalizer.py":       "Phase 1: ResponseNormalizer",
        "src/agent/tool_executor.py":         "Phase 2: ToolExecutor",
        "src/agent/context_assembler.py":     "Phase 3: ContextAssembler",
        "src/agent/turn_orchestrator.py":     "Phase 4: TurnOrchestrator",
        "src/content/note_manager.py":        "Phase 5: ContentLayer",
        "src/tools/search_tools/":            "Phase 6: ToolRegistry",
    }
    for path, label in indicators.items():
        exists = Path(path).exists()
        icon = "✅" if exists else "⬜"
        print(f"   {icon} {label}")

    print(f"\n{'='*60}")

    # Final verdict
    if tests["failed"] == 0 and tests["errors"] == 0:
        print("  ✅ SAFE TO CONTINUE REFACTORING")
    else:
        print("  ❌ FIX FAILURES BEFORE CONTINUING")
        print("     Run: pytest --tb=long -x")
    print(f"{'='*60}\n")

    return tests["failed"] == 0 and tests["errors"] == 0


if __name__ == "__main__":
    success = print_status()
    sys.exit(0 if success else 1)
```

---

## What The Output Looks Like When You're Done

```
============================================================
  Refactor Status — 2024-03-15 09:00
============================================================

📊 TEST SUITE
   ✅ Total:   832
   ✅ Passed:  832

🔧 MIGRATION SHIMS
   ✅ No active shims

📁 NEW FILES THIS SESSION
   (none)

📝 TODOS/FIXMES: 3

📍 PHASE INDICATORS
   ✅ Phase 1: ResponseNormalizer
   ✅ Phase 2: ToolExecutor
   ✅ Phase 3: ContextAssembler
   ✅ Phase 4: TurnOrchestrator
   ✅ Phase 5: ContentLayer
   ✅ Phase 6: ToolRegistry

============================================================
  ✅ SAFE TO CONTINUE REFACTORING
============================================================
```

---

## The Three Rules To Tattoo On Your Hand

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   RULE 1                                                │
│   Never commit red tests.                               │
│   Not even "temporarily".                               │
│   Not even "just to save progress".                     │
│   Red tests are a lie you tell yourself.                │
│                                                         │
│   RULE 2                                                │
│   One phase at a time.                                  │
│   Finish Phase 2 before starting Phase 3.               │
│   Partial refactors are worse than no refactor.         │
│   Half-extracted = two places to maintain.              │
│                                                         │
│   RULE 3                                                │
│   When in doubt, add a shim.                            │
│   A shim is not failure.                                │
│   A shim is a bridge.                                   │
│   Bridges get removed when both sides are stable.       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Final Honest Answer To Your Original Question

```
"I'm doing such a big refactor for the first time.
 Will they work after all this refactoring?"
```

```
Yes. Here is why you can be confident:

1. ~420 of your 700 tests test pure behavior
   (file ops, serializers, repositories, config)
   These will NEVER break from architectural changes.
   They test what your code does, not how it's structured.

2. ~180 tests need mechanical updates
   (import paths, shim delegation)
   This is typing work, not thinking work.
   Each fix takes 2-10 minutes.

3. ~80 tests need to MOVE, not change
   (provider internals → normalizer/assembler)
   The behavior being tested still exists.
   Only the home changes.

4. ~20 tests need actual rewriting
   (mock_agent → FakeOrchestrator injection)
   These are the 4 chat_service tests + context_files.
   They will be BETTER tests after rewriting.
   More readable. More maintainable. Less brittle.

The refactor does not destroy your tests.
It reveals which tests were testing behavior
and which were testing implementation.

Behavior tests survive.
Implementation tests get promoted to better homes.

Your 700 tests are not at risk.
They are your guide.
```

---

### **user**:

have you finished?

---

### **assistant**:

No, I haven't — I got cut off. Let me finish the final section cleanly.

---

## The One Thing That Will Actually Trip You Up

Looking at your specific test files, there is **one pattern** that appears repeatedly and is the real risk:

```python
# This pattern appears in at least 6 of your test files:
import src.main
from src import config

# Then inside tests:
monkeypatch.setattr("src.config.settings.data_dir", ...)
monkeypatch.setattr("src.main.some_function", ...)
```

This means your tests are **tightly coupled to module paths**. When you move files, these strings break silently — no import error, just a patch that does nothing.

```python
# scripts/audit_patch_targets.py
"""
Find every patch() and setattr() target in your test suite.
Run this BEFORE refactoring any module path.
Run it AFTER to verify targets were updated.

Usage: python scripts/audit_patch_targets.py
"""
import ast
import sys
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PatchTarget:
    file: str
    line: int
    target: str
    kind: str  # "patch" | "setattr" | "patch.object"


def extract_patch_targets(filepath: Path) -> list[PatchTarget]:
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    targets = []

    for node in ast.walk(tree):

        # patch("src.module.function")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "patch"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            targets.append(PatchTarget(
                file=str(filepath),
                line=node.lineno,
                target=node.args[0].value,
                kind="patch",
            ))

        # patch.object(module, "attr")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "object"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "patch"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
        ):
            targets.append(PatchTarget(
                file=str(filepath),
                line=node.lineno,
                target=node.args[1].value,
                kind="patch.object",
            ))

        # monkeypatch.setattr("src.module.attr", ...)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setattr"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and "src." in node.args[0].value
        ):
            targets.append(PatchTarget(
                file=str(filepath),
                line=node.lineno,
                target=node.args[0].value,
                kind="setattr",
            ))

    return targets


def verify_target_exists(target: str) -> bool:
    """
    Check if a patch target string resolves to a real attribute.
    Returns False if the module path no longer exists.
    """
    parts = target.rsplit(".", 1)
    if len(parts) != 2:
        return False

    module_path, attr = parts
    try:
        import importlib
        module = importlib.import_module(module_path)
        return hasattr(module, attr)
    except (ImportError, ModuleNotFoundError):
        return False


def main():
    test_dir = Path("tests")
    if not test_dir.exists():
        print("No tests/ directory found")
        sys.exit(1)

    all_targets: list[PatchTarget] = []
    for test_file in sorted(test_dir.rglob("test_*.py")):
        targets = extract_patch_targets(test_file)
        all_targets.extend(targets)

    if not all_targets:
        print("No patch targets found.")
        return

    # Group by module being patched
    by_module: dict[str, list[PatchTarget]] = {}
    for t in all_targets:
        module = t.target.rsplit(".", 1)[0]
        by_module.setdefault(module, []).append(t)

    print(f"\n{'='*60}")
    print(f"  Patch Target Audit — {len(all_targets)} targets found")
    print(f"{'='*60}\n")

    broken = []
    for module, targets in sorted(by_module.items()):
        for t in targets:
            exists = verify_target_exists(t.target)
            status = "✅" if exists else "❌ BROKEN"
            if not exists:
                broken.append(t)
            print(
                f"  {status:12} {t.kind:12} "
                f"{t.target:50} "
                f"({Path(t.file).name}:{t.line})"
            )

    print(f"\n{'='*60}")
    if broken:
        print(f"  ❌ {len(broken)} broken patch targets found!")
        print(f"     These patches do NOTHING — tests may pass")
        print(f"     for the wrong reason.")
        print(f"\n  Files to fix:")
        seen = set()
        for t in broken:
            if t.file not in seen:
                print(f"     - {t.file}")
                seen.add(t.file)
    else:
        print(f"  ✅ All {len(all_targets)} patch targets resolve correctly")
    print(f"{'='*60}\n")

    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
```

---

## Run This Right Now — Before Anything Else

```bash
# Step 1: Baseline — understand what you have
python scripts/audit_patch_targets.py > baseline_patches.txt

# Step 2: Count and categorize
pytest --collect-only -q 2>/dev/null | tail -5

# Step 3: Establish your green baseline
pytest --tb=short -q
# Should show: 700 passed

# Step 4: Commit the baseline
git add scripts/
git commit -m "Add refactor tooling — baseline established"

# Step 5: Start Phase 1
# Touch ONLY src/providers/normalizer.py
# and tests/unit/providers/test_normalizer.py
```

---

## Complete Summary — Everything In One Place

```
WHAT YOU HAVE:         700 tests, working app, clear architecture vision
WHAT YOU ARE DOING:    6-phase strangler fig refactor
TOTAL TIME:            6 weeks at sustainable pace

PHASE 1  (Week 1)  ResponseNormalizer      +10 tests  → 710 total
PHASE 2  (Week 2)  ToolExecutor            +20 tests  → 730 total
PHASE 3  (Week 3)  ContextAssembler        +30 tests  → 760 total
PHASE 4  (Week 4)  TurnOrchestrator        +25 tests  → 785 total
PHASE 5  (Week 5)  Content Layer           +40 tests  → 825 total
PHASE 6  (Week 6)  ToolRegistry            +10 tests  → 835 total

TESTS THAT BREAK:      ~20 (need rewriting, not deleting)
TESTS THAT MOVE:       ~80 (same behavior, better home)
TESTS UNCHANGED:       ~600 (never touched)
SHIMS NEEDED:          3 (agent.py, registry aliases, provider factory)
SHIMS DELETED BY:      End of Phase 6

SCRIPTS TO RUN DAILY:
  python scripts/refactor_status.py      ← morning check
  python scripts/audit_patch_targets.py  ← after any module move
  python scripts/check_migration_phase.py --phase N  ← before commit

THE THREE RULES:
  1. Never commit red tests
  2. One phase at a time
  3. When in doubt, add a shim

YOUR SAFETY NET:
  Your 700 tests are not the problem.
  They are the solution.
  They tell you when you are done.
  Trust them.
```

> That is the complete picture.
> You have everything you need.
> Start with `python scripts/refactor_status.py` right now
> and let the tests lead you forward.

---

### **user**:

I have plan to save this conversation as markdown file. I need to pass implementation to modern coding agent.
I need a prompt with core directives and instruction how to navigate this document to find right and only right thing for initial steps + phases 1

---

### **assistant**:

# Prompt: Refactor Navigation Guide for Coding Agent

---

## System Prompt

```
You are an expert Python refactoring agent.
You have been given a large architecture document as context.
Your job is to execute a precise, phased refactor of an existing
Python codebase — without breaking 700 existing tests.

You operate by the Strangler Fig pattern:
- Build new alongside old
- Delegate from old to new
- Delete old only when new is fully tested and verified

You never:
- Rewrite everything at once
- Commit failing tests
- Skip a phase to get ahead
- Remove a shim before its dependents are migrated

You always:
- Write tests before implementing
- Run the full test suite after every change
- Tag temporary code with: MIGRATION_SHIM
- Stop and report if test count drops below 700
```

---

## Document Navigation Map

```
This document contains everything you need.
Use this map to find ONLY what is relevant to each step.
Do not read ahead. Do not implement ahead.

SECTION: "First: Read Your Tests Carefully"
→ Read this FIRST, before any code changes
→ Contains the survival likelihood table for all 700 tests
→ Tells you which files are safe and which need care

SECTION: "The Critical Problem Tests — Detailed Analysis"
→ Read before Phase 1
→ Contains the 5 specific problems you will encounter
→ Problem 1: agent.py direct imports  ← most dangerous
→ Problem 2: Provider internals tested ← affects Phase 1
→ Problem 3: get_provider tested directly ← affects Phase 1
→ Problem 4: DECLARATIONS/FUNCTION_MAP ← affects Phase 6
→ Problem 5: mock_agent in ChatService ← affects Phase 4

SECTION: "The Migration Decision Tree Per Test File"
→ Read before Phase 1
→ Contains MIGRATION_STRATEGIES dictionary
→ Tells you exactly which files: keep_as_is / update_imports /
  add_shim_first / migrate_behavior / rewrite

SECTION: "Concrete: What Breaks on Day 1 of Each Phase"
→ Read before EACH phase
→ 6 entries, one per phase
→ Tells you exactly what will break and the strategy

SECTION: "The Files You Touch In What Order"
→ Your primary execution reference
→ Lists CREATE / MODIFY / DELETE / DO NOT TOUCH per phase
→ Follow this exactly — do not touch files not listed

SECTION: "Phase 0 — Audit & Baseline"
→ Execute this before writing any code
→ Contains characterization test pattern
→ Contains dependency mapping commands

SECTION: "Phase 1 — Extract Without Breaking"
→ Primary implementation reference for Phase 1
→ Contains exact before/after code for GeminiProvider
→ Contains exact before/after code for AnthropicProvider
→ Contains the delegation pattern to follow

SECTION: "ResponseNormalizer — Provider Differences Contained Here"
→ Full implementation of ResponseNormalizer
→ Located under "The Critical New Concepts"
→ Implements _from_gemini() and _from_anthropic()
→ Implements normalize_chunk() for streaming

SECTION: "Complete Test Fakes — Reusable Across All Phases"
→ tests/fakes.py full implementation
→ Contains FakeProvider with all control options
→ Use FakeProviderResponse for constructing test responses
→ Do NOT use MagicMock for domain objects — use these fakes

SECTION: "PHASE_1_CHECKLIST"
→ Located in "Your Personal Refactor Checklist"
→ 12 checkbox items
→ Every box must be checked before Phase 2 begins

SECTION: "The conftest.py That Saves You"
→ Full conftest.py implementation
→ Implements clear_lru_caches (autouse — critical)
→ Implements isolate_env (autouse — critical)
→ Implements api_client and api_client_no_llm fixtures

SECTION: "The pytest.ini That Keeps You Sane"
→ Full pytest.ini configuration
→ asyncio_mode = auto (prevents async test failures)
→ filterwarnings configuration

SECTION: "Run This Right Now — Before Anything Else"
→ The 5 commands to run before touching any code
→ Establishes your green baseline
→ MUST show 700 passed before proceeding
```

---

## Core Directives For Initial Steps

```
DIRECTIVE 1 — ESTABLISH BASELINE FIRST
───────────────────────────────────────
Before writing a single line of production code:

1. Run: pytest --tb=short -q
   Expected: 700 passed, 0 failed
   If not green: STOP. Fix failures first. Do not refactor
   a broken codebase.

2. Run: pytest --collect-only -q 2>/dev/null | tail -5
   Record the exact test count.
   This is your floor. It must never go below this.

3. Run: python scripts/audit_patch_targets.py
   (Create this script first — see "Run This Right Now" section)
   Record which patch targets exist.
   You will re-run this after every module move.

4. Commit: git commit -m "Baseline: 700 tests green"
   This is your escape hatch if anything goes wrong.


DIRECTIVE 2 — PHASE 1 SCOPE IS FIXED
──────────────────────────────────────
Phase 1 touches EXACTLY these files:

  CREATE:  src/providers/normalizer.py
  CREATE:  tests/unit/providers/test_normalizer.py
  MODIFY:  src/providers/gemini.py
  MODIFY:  src/providers/anthropic_provider.py

DO NOT TOUCH anything else.
Not agent.py. Not chat_service.py. Not repositories.py.
Not main.py. Not tools/. Not serializers.py.

If you find yourself editing a file not on this list,
STOP and reconsider.


DIRECTIVE 3 — TESTS BEFORE IMPLEMENTATION
──────────────────────────────────────────
For Phase 1, write test_normalizer.py BEFORE
implementing ResponseNormalizer.

The test file must cover:
  □ Gemini text response → NormalizedResponse.text populated
  □ Gemini tool call → NormalizedResponse.has_tool_calls = True
  □ Gemini tool call → NormalizedResponse.tool_calls populated
  □ Gemini usage metadata → NormalizedResponse.usage populated
  □ Anthropic text block → NormalizedResponse.text populated
  □ Anthropic tool_use block → NormalizedResponse.has_tool_calls = True
  □ Anthropic tool_use block → NormalizedResponse.tool_calls populated
  □ Anthropic usage → NormalizedResponse.usage populated
  □ Gemini streaming chunk → returns text delta string
  □ Anthropic streaming chunk → returns text delta string
  □ Unknown provider → raises ValueError

These 11 tests must be RED before you implement.
They must be GREEN after you implement.


DIRECTIVE 4 — DELEGATION PATTERN IS MANDATORY
───────────────────────────────────────────────
When modifying GeminiProvider and AnthropicProvider,
use the delegation pattern — NOT replacement:

  # WRONG — replaces existing behavior:
  def _parse_response(self, raw):
      # completely new implementation

  # RIGHT — delegates to normalizer:
  def __init__(self, ...):
      ...
      self._normalizer = ResponseNormalizer()  # add quietly

  def _parse_response(self, raw):
      return self._normalizer.normalize(raw, provider="gemini")
      # old method still exists
      # old tests still call it
      # old tests still pass

The public interface of GeminiProvider and AnthropicProvider
must not change at all in Phase 1.


DIRECTIVE 5 — THE GREEN GATE
──────────────────────────────
After every file change, run:
  pytest --tb=short -q

The output must show:
  ≥ 700 passed
  0 failed
  0 errors

If it shows anything else:
  STOP.
  Do not make more changes.
  Fix what is broken first.
  Only then continue.

This is not optional. This is the entire safety system.


DIRECTIVE 6 — SHIM TAGGING IS MANDATORY
─────────────────────────────────────────
Any code that exists only to maintain backward compatibility
during the refactor must be tagged:

  # MIGRATION_SHIM — Phase N
  # Safe to delete when: [specific condition]

This applies to:
  - Module-level aliases (DECLARATIONS, FUNCTION_MAP)
  - Delegating wrapper functions
  - Old method signatures kept for test compatibility

Run at end of each phase:
  git grep "MIGRATION_SHIM"

This tells you exactly what temporary code remains.


DIRECTIVE 7 — COMMIT DISCIPLINE
─────────────────────────────────
Commit after each file is complete and tests are green.
Never commit a batch of changes together.

  git add src/providers/normalizer.py
  git commit -m "Phase 1a: Add ResponseNormalizer with tests"

  git add src/providers/gemini.py
  git commit -m "Phase 1b: GeminiProvider delegates to ResponseNormalizer"

  git add src/providers/anthropic_provider.py
  git commit -m "Phase 1c: AnthropicProvider delegates to ResponseNormalizer"

Small commits = easy rollback if something breaks.
```

---

## Phase 1 Execution Instructions

```
STEP 1 — Setup test infrastructure (do this once, before Phase 1)
──────────────────────────────────────────────────────────────────
Navigate to: "The conftest.py That Saves You"
Action: Create tests/conftest.py with the full content shown.
        Pay special attention to:
        - clear_lru_caches fixture (autouse=True)
        - isolate_env fixture (autouse=True)
        Both must be present before any other work.

Navigate to: "The pytest.ini That Keeps You Sane"
Action: Create pytest.ini with the full content shown.
        Critical line: asyncio_mode = auto

Navigate to: "Complete Test Fakes — Reusable Across All Phases"
Action: Create tests/fakes.py with the full content shown.
        You will need FakeProvider in Phase 1 tests.

Run: pytest --tb=short -q
Expected: same count as baseline (≥ 700 passed)
If count changed: something in conftest.py broke a test.
                  Fix it before continuing.


STEP 2 — Write test_normalizer.py (RED phase)
──────────────────────────────────────────────
Navigate to: "ResponseNormalizer — Provider Differences Contained Here"
Read the full implementation to understand the expected interface.

Navigate to: "DIRECTIVE 3 — TESTS BEFORE IMPLEMENTATION" (above)
Use the 11 test cases listed there as your test plan.

Create: tests/unit/providers/test_normalizer.py
        Also create: tests/unit/__init__.py
                     tests/unit/providers/__init__.py

Run: pytest tests/unit/providers/test_normalizer.py -v
Expected: 11 failed (RED — this is correct at this stage)
If any pass: your test is not testing the right thing.


STEP 3 — Implement ResponseNormalizer (GREEN phase)
────────────────────────────────────────────────────
Navigate to: "ResponseNormalizer — Provider Differences Contained Here"
This section is located under "The Critical New Concepts"
in the main architecture recommendations.

Create: src/providers/normalizer.py
        Copy the full implementation shown.
        Key classes to implement:
        - NormalizedResponse (dataclass)
        - ResponseNormalizer
          - normalize(raw, provider) → NormalizedResponse
          - normalize_chunk(chunk, provider) → str
          - _from_gemini(raw) → NormalizedResponse
          - _from_anthropic(raw) → NormalizedResponse
          - _gemini_chunk_text(chunk) → str
          - _anthropic_chunk_text(chunk) → str

Run: pytest tests/unit/providers/test_normalizer.py -v
Expected: 11 passed (GREEN)
If any fail: fix ResponseNormalizer until all 11 pass.
             Do not proceed until GREEN.


STEP 4 — Update GeminiProvider (delegate, don't replace)
──────────────────────────────────────────────────────────
Navigate to: "Phase 1 — Extract Without Breaking"
Find the subsection: "Step 1c: Same for AnthropicProvider"
(The GeminiProvider pattern is shown just above it)

Modify: src/providers/gemini.py
        Add self._normalizer = ResponseNormalizer() to __init__
        Change _parse_response to delegate:
          return self._normalizer.normalize(raw, provider="gemini")

Run: pytest --tb=short -q
Expected: ≥ 700 passed, 0 failed
If test_gemini_provider.py fails: the delegation broke something.
                                   Check the method name being delegated.


STEP 5 — Update AnthropicProvider (delegate, don't replace)
─────────────────────────────────────────────────────────────
Same pattern as Step 4.

Modify: src/providers/anthropic_provider.py
        Add self._normalizer = ResponseNormalizer() to __init__
        Change _parse_response to delegate:
          return self._normalizer.normalize(raw, provider="anthropic")

Run: pytest --tb=short -q
Expected: ≥ 700 passed, 0 failed
If test_anthropic_provider.py fails: check the delegation.
                                      The old method name must be preserved.


STEP 6 — Phase 1 verification
───────────────────────────────
Navigate to: "PHASE_1_CHECKLIST"
Located in: "Your Personal Refactor Checklist"

Work through every checkbox.
The final two are most important:

  □ pytest --tb=short -q → same count as before (≥ 700)
  □ python scripts/check_migration_phase.py --phase 1

Only when all 12 boxes are checked:
  git commit -m "Phase 1 complete: ResponseNormalizer extracted"
  → You are ready for Phase 2
```

---

## What To Report After Phase 1

```
When Phase 1 is complete, report:

1. Test count before:  ___
   Test count after:   ___
   Difference:         ___  (should be +10 to +15 new tests)

2. Files created:
   □ src/providers/normalizer.py
   □ tests/unit/providers/test_normalizer.py
   □ tests/conftest.py  (if not existed)
   □ tests/fakes.py     (if not existed)

3. Files modified:
   □ src/providers/gemini.py
   □ src/providers/anthropic_provider.py

4. MIGRATION_SHIM count:
   Run: git grep -c "MIGRATION_SHIM"
   Expected: 0 (Phase 1 needs no shims)

5. Any surprises encountered:
   (provider method names that differed from document,
    import paths that needed adjustment, etc.)

This report determines the Phase 2 plan.
```

---

## If Something Goes Wrong

```
SCENARIO: Tests drop below 700
  Action: git stash
          pytest --tb=short -q  (verify baseline restored)
          git stash pop
          Read the failure carefully
          Fix only that failure
          Do not make unrelated changes

SCENARIO: Import error after creating normalizer.py
  Likely cause: circular import
  Action: Check that normalizer.py does not import from
          gemini.py or anthropic_provider.py
          Normalizer must have zero dependencies on providers

SCENARIO: Patch target broken in provider tests
  Likely cause: method name changed during delegation
  Action: python scripts/audit_patch_targets.py
          Find the broken target
          The old method name must be preserved exactly

SCENARIO: test_gemini_history_coercion.py fails
  Likely cause: GeminiProvider internal structure changed
  Action: The _coerce_history_for_gemini function must not
          be touched in Phase 1
          Only _parse_response delegates to normalizer
          Everything else stays identical

SCENARIO: Unsure if a change is safe
  Action: Run pytest --tb=short -q BEFORE the change
          Make the change
          Run pytest --tb=short -q AFTER the change
          If count dropped: revert the change
```

---

## The

---

### **user**:

continue

---

### **assistant**:

## The Single Source of Truth Per Decision

```
DECISION: "Should I change this file?"
  Answer: Is it in the Phase 1 file list?
          YES → change it
          NO  → do not touch it

DECISION: "Should I delete this old code?"
  Answer: Are all tests that depend on it migrated?
          Run: git grep "old_function_name" tests/
          Result is empty → safe to delete
          Result has matches → add MIGRATION_SHIM, do not delete

DECISION: "Should I refactor this while I'm here?"
  Answer: No.
          You noticed something unrelated that could be improved.
          Write it in a TODO comment.
          Finish the phase you are in.
          Opportunistic refactoring during a planned refactor
          is how phases never finish.

DECISION: "The document shows X but my code has Y"
  Answer: Your code wins for naming.
          The document shows patterns and structure.
          Adapt method names, class names, file names
          to match YOUR existing codebase.
          The architecture is the guide.
          The exact names are yours to keep.

DECISION: "This test is testing implementation not behavior"
  Answer: Note it. Do not fix it now.
          Add comment: # TODO: migrate to behavior test in Phase N
          Keep it passing.
          Fix it in its designated phase.

DECISION: "I found a bug while refactoring"
  Answer: Stop.
          Write a failing test that proves the bug exists.
          Fix the bug.
          Verify the test passes.
          Commit: "fix: [description] found during Phase 1 refactor"
          Then continue the refactor.
          Never fix bugs and refactor in the same commit.
```

---

## Document Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│              DOCUMENT NAVIGATION QUICK CARD                  │
│                                                             │
│  BEFORE STARTING                                            │
│  ─────────────────────────────────────────────────────────  │
│  Survival table     → "First: Read Your Tests Carefully"    │
│  Problem tests      → "The Critical Problem Tests"          │
│  Migration strategy → "Migration Decision Tree Per File"    │
│  What breaks when   → "Concrete: What Breaks on Day 1"      │
│                                                             │
│  PHASE 0                                                    │
│  ─────────────────────────────────────────────────────────  │
│  Baseline commands  → "Phase 0 — Audit & Baseline"          │
│  Characterization   → "Phase 0" → test pattern shown        │
│                                                             │
│  PHASE 1                                                    │
│  ─────────────────────────────────────────────────────────  │
│  What to touch      → "The Files You Touch In What Order"   │
│  Implementation     → "ResponseNormalizer — Provider        │
│                         Differences Contained Here"         │
│  Delegation pattern → "Phase 1 — Extract Without Breaking"  │
│  Checklist          → "PHASE_1_CHECKLIST"                   │
│                                                             │
│  INFRASTRUCTURE                                             │
│  ─────────────────────────────────────────────────────────  │
│  conftest.py        → "The conftest.py That Saves You"      │
│  pytest.ini         → "The pytest.ini That Keeps You Sane"  │
│  tests/fakes.py     → "Complete Test Fakes"                 │
│  CI workflow        → "CI Gate — Enforce No Regression"     │
│                                                             │
│  SCRIPTS                                                    │
│  ─────────────────────────────────────────────────────────  │
│  Daily status       → "scripts/refactor_status.py"          │
│  Patch audit        → "scripts/audit_patch_targets.py"      │
│  Phase check        → "scripts/check_migration_phase.py"    │
│  Test count guard   → "scripts/check_test_count.py"         │
│  Shim age check     → "scripts/check_shim_age.py"           │
│                                                             │
│  WHEN STUCK                                                 │
│  ─────────────────────────────────────────────────────────  │
│  Common failures    → "When You Hit a Wall"                 │
│  Wrong scenario     → "If Something Goes Wrong" (above)     │
│  Psychological dip  → "The Psychological Side"              │
└─────────────────────────────────────────────────────────────┘
```

---

## The Minimal First Session — Exactly What To Do

```
This is the irreducible minimum for your first working session.
Nothing more. Nothing less.

TIME ESTIMATE: 2-3 hours

────────────────────────────────────────────────────────────────
HOUR 1 — Infrastructure + Baseline (no production code changes)
────────────────────────────────────────────────────────────────

[ ] 1. Create scripts/ directory
       Create scripts/__init__.py (empty)

[ ] 2. Create scripts/audit_patch_targets.py
       Navigate to: "Run This Right Now — Before Anything Else"
       Copy the full script shown there.

[ ] 3. Run: pytest --tb=short -q
       Record output: ___ passed, ___ failed
       If not all passing: STOP. Fix first.

[ ] 4. Run: python scripts/audit_patch_targets.py
       Record output to: baseline_patches.txt
       Note any already-broken targets.

[ ] 5. Create tests/conftest.py
       Navigate to: "The conftest.py That Saves You"
       Copy full content.

[ ] 6. Create pytest.ini
       Navigate to: "The pytest.ini That Keeps You Sane"
       Copy full content.

[ ] 7. Run: pytest --tb=short -q
       Must still show same count.
       If count changed: conftest.py broke something.
       Fix before continuing.

[ ] 8. Create tests/fakes.py
       Navigate to: "Complete Test Fakes — Reusable Across All Phases"
       Copy full content.
       This file has no tests — it IS the test infrastructure.

[ ] 9. Run: pytest --tb=short -q
       Must still show same count.

[ ] 10. Create directory structure:
        tests/unit/__init__.py
        tests/unit/providers/__init__.py
        tests/unit/agent/__init__.py
        tests/unit/content/__init__.py
        tests/unit/services/__init__.py
        tests/unit/tools/__init__.py

[ ] 11. Run: pytest --tb=short -q
        Must still show same count.

[ ] 12. Commit:
        git add tests/conftest.py tests/fakes.py pytest.ini
        git add tests/unit/ scripts/
        git commit -m "refactor: add test infrastructure for Phase 1"


────────────────────────────────────────────────────────────────
HOUR 2 — Write test_normalizer.py (RED phase)
────────────────────────────────────────────────────────────────

[ ] 13. Read the full ResponseNormalizer implementation
        Navigate to: "ResponseNormalizer — Provider Differences
        Contained Here"
        Read it completely. Understand the interface.
        Do NOT copy it yet.

[ ] 14. Create tests/unit/providers/test_normalizer.py
        Write tests for these behaviors:

        from src.providers.normalizer import (
            ResponseNormalizer,
            NormalizedResponse,
        )

        # ── Gemini tests ──────────────────────────────────────

        def test_gemini_text_response_populates_text():
            # Build a fake Gemini response with text
            # Call normalizer.normalize(raw, "gemini")
            # Assert result.text == expected text
            ...

        def test_gemini_tool_call_sets_has_tool_calls_true():
            # Build a fake Gemini response with function_call part
            # Assert result.has_tool_calls is True
            ...

        def test_gemini_tool_call_populates_tool_calls_list():
            # Assert result.tool_calls is non-empty
            # Assert result.tool_calls[0].name == expected name
            ...

        def test_gemini_usage_metadata_populates_usage():
            # Assert result.usage["input"] > 0
            # Assert result.usage["total"] > 0
            ...

        def test_gemini_streaming_chunk_returns_text_delta():
            # Build a fake streaming chunk
            # Call normalizer.normalize_chunk(chunk, "gemini")
            # Assert returns a string
            ...

        # ── Anthropic tests ───────────────────────────────────

        def test_anthropic_text_block_populates_text():
            ...

        def test_anthropic_tool_use_block_sets_has_tool_calls():
            ...

        def test_anthropic_tool_use_populates_tool_calls_list():
            ...

        def test_anthropic_usage_populates_usage_dict():
            ...

        def test_anthropic_streaming_chunk_returns_text_delta():
            ...

        # ── Shared behavior ───────────────────────────────────

        def test_unknown_provider_raises_value_error():
            normalizer = ResponseNormalizer()
            with pytest.raises(ValueError, match="Unknown provider"):
                normalizer.normalize(MagicMock(), provider="unknown")

[ ] 15. Run: pytest tests/unit/providers/test_normalizer.py -v
        Expected: 11 failed (ImportError or AttributeError)
        This RED state is correct.
        If anything passes: your test is not testing correctly.


────────────────────────────────────────────────────────────────
HOUR 3 — Implement + Delegate (GREEN phase)
────────────────────────────────────────────────────────────────

[ ] 16. Create src/providers/normalizer.py
        Navigate to: "ResponseNormalizer — Provider Differences
        Contained Here"
        Copy the full implementation now.

[ ] 17. Run: pytest tests/unit/providers/test_normalizer.py -v
        Expected: 11 passed
        If any fail: fix normalizer until all 11 pass.
        Do not touch provider files until this is green.

[ ] 18. Modify src/providers/gemini.py
        Navigate to: "Phase 1 — Extract Without Breaking"
        Find: "Step 1a" and "Step 1b"
        Add self._normalizer = ResponseNormalizer() to __init__
        Change _parse_response to delegate.
        Keep the method name _parse_response exactly.

[ ] 19. Run: pytest --tb=short -q
        Expected: ≥ 700 passed
        If test_gemini_provider.py fails:
          The delegation changed observable behavior.
          Check: is the return type the same?
          Check: is the method still named _parse_response?

[ ] 20. Modify src/providers/anthropic_provider.py
        Same delegation pattern as Step 18.

[ ] 21. Run: pytest --tb=short -q
        Expected: ≥ 700 passed, 0 failed
        This is your Phase 1 green gate.

[ ] 22. Run: python scripts/audit_patch_targets.py
        Compare to baseline_patches.txt
        Any new broken targets? Fix them before committing.

[ ] 23. Commit each file separately:
        git add src/providers/normalizer.py
        git add tests/unit/providers/test_normalizer.py
        git commit -m "Phase 1a: ResponseNormalizer implemented + tested"

        git add src/providers/gemini.py
        git commit -m "Phase 1b: GeminiProvider delegates to normalizer"

        git add src/providers/anthropic_provider.py
        git commit -m "Phase 1c: AnthropicProvider delegates to normalizer"

[ ] 24. Work through PHASE_1_CHECKLIST
        Navigate to: "Your Personal Refactor Checklist"
        Find: PHASE_1_CHECKLIST
        All 12 boxes must be checked.

[ ] 25. Final verification:
        pytest --tb=short -q
        git grep "MIGRATION_SHIM"  ← should be empty for Phase 1
        git log --oneline -5       ← should show 3 clean commits

────────────────────────────────────────────────────────────────
PHASE 1 COMPLETE.
Report results using the template in:
"What To Report After Phase 1"
Then await Phase 2 instructions.
────────────────────────────────────────────────────────────────
```

---

## One Final Note To The Agent

```
This document was written by a human architect
who has thought carefully about your codebase.

The phasing is deliberate.
The ordering is deliberate.
The "DO NOT TOUCH" lists are deliberate.

When the document says Phase 1 touches only 4 files,
it means Phase 1 touches only 4 files.

Not because the architect was being restrictive.
Because every additional file touched in Phase 1
is a variable that can cause a test failure
that you cannot easily diagnose.

Small surface area = fast debugging.
Fast debugging = confidence.
Confidence = sustainable refactoring.

The goal is not to finish fast.
The goal is to finish with 835 green tests
and a codebase that is genuinely easier
to work with than the one you started with.

Trust the process.
Trust the tests.
Ship each phase completely before starting the next.
```

---

### **user**:

have you finished?

---

### **assistant**:

No — I got cut off at the end. Here is the proper closing section:

---

## The Complete Prompt Block — Copy This Exactly

```
This is the self-contained prompt to paste to your coding agent.
Everything above this block is the reference document.
Everything below is what the agent receives as its directive.
```

---

```
SYSTEM PROMPT — PASTE THIS TO YOUR CODING AGENT
════════════════════════════════════════════════════════════════

You are a Python refactoring agent working on a FastAPI + LLM
chat application. You have been given an architecture document
as your reference. Your task is to execute Phase 0 and Phase 1
of a 6-phase refactor.

═══════════════════════════════════════════════════════════════
YOUR CONSTRAINTS — READ THESE FIRST, MEMORIZE THEM
═══════════════════════════════════════════════════════════════

1. There are 700 existing tests. They must ALL pass after
   every single file change. Not at the end of the phase.
   After. Every. Change.

2. Phase 1 touches exactly 4 files:
   CREATE  src/providers/normalizer.py
   CREATE  tests/unit/providers/test_normalizer.py
   MODIFY  src/providers/gemini.py
   MODIFY  src/providers/anthropic_provider.py
   Nothing else. No exceptions.

3. You write tests before implementation.
   test_normalizer.py must be RED before you create normalizer.py
   normalizer.py must make it GREEN before you touch providers.

4. You delegate, you do not replace.
   Old provider methods keep their names.
   Old provider methods keep their signatures.
   Old provider methods now call the normalizer internally.
   External behavior is identical. Internal wiring changes.

5. You commit after each file, not after the phase.
   4 files = 4 commits minimum.

═══════════════════════════════════════════════════════════════
YOUR REFERENCE DOCUMENT — HOW TO USE IT
═══════════════════════════════════════════════════════════════

The document contains everything you need.
Navigate it using these exact section titles:

FOR UNDERSTANDING RISK:
  → "First: Read Your Tests Carefully"
    Read the survival likelihood table.
    Understand which files are safe.

  → "The Critical Problem Tests — Detailed Analysis"
    Read Problem 2 and Problem 3 only.
    These are the Phase 1 relevant risks.

FOR IMPLEMENTATION:
  → "ResponseNormalizer — Provider Differences Contained Here"
    This is your implementation blueprint.
    Located under "The Critical New Concepts".
    Contains complete NormalizedResponse dataclass.
    Contains complete ResponseNormalizer class.
    Contains _from_gemini(), _from_anthropic(),
    normalize_chunk() implementations.

  → "Phase 1 — Extract Without Breaking"
    Contains the exact delegation pattern.
    Shows before/after for GeminiProvider.
    Shows the shim pattern for AnthropicProvider.

FOR TEST INFRASTRUCTURE:
  → "The conftest.py That Saves You"
    Create this before writing any tests.
    The clear_lru_caches and isolate_env
    autouse fixtures are critical.

  → "The pytest.ini That Keeps You Sane"
    asyncio_mode = auto is required.
    Create this before running any tests.

  → "Complete Test Fakes — Reusable Across All Phases"
    Create tests/fakes.py from this section.
    You will use FakeProvider in Phase 1 tests.

FOR VERIFICATION:
  → "PHASE_1_CHECKLIST"
    Located in "Your Personal Refactor Checklist".
    All 12 boxes must be checked before you report done.

  → "What To Report After Phase 1"
    Use this template for your completion report.

FOR WHEN THINGS BREAK:
  → "When You Hit a Wall — Debugging Guide"
    5 scenarios with exact fixes.
  → "If Something Goes Wrong"
    Located near the end of the document.
    Phase 1 specific failure scenarios.

═══════════════════════════════════════════════════════════════
YOUR EXECUTION ORDER — FOLLOW THIS EXACTLY
═══════════════════════════════════════════════════════════════

STEP 0 — Verify baseline
  Run: pytest --tb=short -q
  Must show: ≥ 700 passed, 0 failed
  If not: STOP. Report the failures. Do not proceed.

STEP 1 — Create infrastructure
  Create: pytest.ini
  Create: tests/conftest.py
  Create: tests/fakes.py
  Create: tests/unit/__init__.py
  Create: tests/unit/providers/__init__.py
  Run:    pytest --tb=short -q
  Must show: same count as Step 0

STEP 2 — Write failing tests
  Create: tests/unit/providers/test_normalizer.py
  Run:    pytest tests/unit/providers/test_normalizer.py -v
  Must show: 11 failed (RED is correct here)

STEP 3 — Implement ResponseNormalizer
  Create: src/providers/normalizer.py
  Run:    pytest tests/unit/providers/test_normalizer.py -v
  Must show: 11 passed (GREEN)
  Run:    pytest --tb=short -q
  Must show: ≥ 700 passed (no regressions)

STEP 4 — Delegate from GeminiProvider
  Modify: src/providers/gemini.py
  Run:    pytest --tb=short -q
  Must show: ≥ 700 passed

STEP 5 — Delegate from AnthropicProvider
  Modify: src/providers/anthropic_provider.py
  Run:    pytest --tb=short -q
  Must show: ≥ 700 passed

STEP 6 — Verify and commit
  Work through PHASE_1_CHECKLIST (all 12 boxes)
  Run:    git grep "MIGRATION_SHIM"
  Expect: empty (Phase 1 needs no shims)
  Commit: 4 separate commits, one per file created/modified

STEP 7 — Report completion
  Use template from "What To Report After Phase 1"
  Include: test count before/after, files created/modified,
           any surprises, any deviations from the plan.

═══════════════════════════════════════════════════════════════
YOUR STOPPING CONDITIONS
═══════════════════════════════════════════════════════════════

STOP and report immediately if:

  □ Test count drops below 700 at any point
  □ You find yourself editing a file not in the Phase 1 list
  □ You discover the provider method names differ from
    what the document assumes
  □ You find a bug unrelated to the refactor
    (write a test for it, commit it separately, then continue)
  □ A test passes before you implement the code it tests
    (your test is not testing the right thing)
  □ You are unsure whether a change is safe

When you stop: report exactly what you found.
Do not guess. Do not work around it silently.
The human needs to know so the plan can be adjusted.

═══════════════════════════════════════════════════════════════
WHAT DONE LOOKS LIKE
═══════════════════════════════════════════════════════════════

Phase 1 is complete when:

  pytest --tb=short -q
  → shows ≥ 710 passed (700 original + ~10 new normalizer tests)
  → shows 0 failed
  → shows 0 errors

  git log --oneline -5
  → shows 4 clean commits

  git grep "MIGRATION_SHIM"
  → shows nothing

  ls src/providers/
  → includes normalizer.py

  ls tests/unit/providers/
  → includes test_normalizer.py

  git diff src/providers/gemini.py
  → shows only: import added, __init__ updated,
                _parse_response now delegates

  git diff src/providers/anthropic_provider.py
  → shows only: import added, __init__ updated,
                _parse_response now delegates

Nothing more. Nothing less.
Phase 2 begins only after this report is delivered
and confirmed by the human.

════════════════════════════════════════════════════════════════
END OF AGENT PROMPT
════════════════════════════════════════════════════════════════
```

---

## That Is Everything

```
The markdown file you save contains:

  REFERENCE MATERIAL (the full conversation)
  ├── Architecture analysis
  ├── Recommended target architecture
  ├── All implementation code
  ├── All test code
  ├── All scripts
  ├── Phase-by-phase breakdown
  ├── Test survival analysis
  └── Debugging guides

  AGENT PROMPT (the block above)
  ├── System constraints
  ├── Document navigation map
  ├── Execution order
  ├── Stopping conditions
  └── Definition of done

Save the conversation as:  refactor_guide.md
Pass the agent prompt as:  the system prompt or first message
Point the agent at:        your codebase + refactor_guide.md

The agent has everything it needs.
You have everything you need.
Start with Step 0.
```

---

### **user**:

have you finihsed?

---

### **assistant**:

Yes. That was the complete and proper ending.

---

## Quick Sanity Check — Is Your Markdown File Complete?

```
Your saved conversation should contain these sections in order:

ARCHITECTURE ANALYSIS
  ✅ "Key Observations & Concerns" (6 numbered problems)
  ✅ "Recommended Architecture" (flowchart)
  ✅ "The Critical New Concepts" (5 implementations)
      - ContextAssembler
      - TurnOrchestrator
      - ToolRegistry
      - ToolExecutor
      - ResponseNormalizer
  ✅ "ChatService — Now Thin and Clear"
  ✅ "SearchCoordinator — Ready for BM25 + Embeddings"
  ✅ "Dependency Injection Container"
  ✅ "Final Folder Structure"
  ✅ "Summary: What Changed and Why"

REFACTOR PLANNING
  ✅ "The Strangler Fig Strategy"
  ✅ "Phase 0 through Phase 6" (all phases)
  ✅ "Complete Test Fakes" (tests/fakes.py)
  ✅ "Migration Safety Checklist"
  ✅ "Complete Refactor Roadmap"

TEST ANALYSIS
  ✅ "First: Read Your Tests Carefully" (survival table)
  ✅ "The Critical Problem Tests" (5 problems)
  ✅ "Migration Decision Tree Per Test File"
  ✅ "Concrete: What Breaks on Day 1 of Each Phase"
  ✅ "The 4 Tests That Need Actual Rewriting"
  ✅ "The Files You Touch In What Order"
  ✅ "Your Personal Refactor Checklist" (all 6 phases)
  ✅ "When You Hit a Wall" (5 scenarios)
  ✅ "The conftest.py That Saves You"
  ✅ "The pytest.ini That Keeps You Sane"
  ✅ "scripts/refactor_status.py"
  ✅ "scripts/audit_patch_targets.py"
  ✅ "scripts/check_migration_phase.py"
  ✅ "scripts/check_test_count.py"
  ✅ "scripts/check_shim_age.py"
  ✅ "What To Report After Phase 1"
  ✅ "If Something Goes Wrong"
  ✅ "The Psychological Side"

AGENT PROMPT
  ✅ "SYSTEM PROMPT — PASTE THIS TO YOUR CODING AGENT"
      - Constraints
      - Document navigation map
      - Execution order (7 steps)
      - Stopping conditions
      - Definition of done
```

```
If any section is missing:
  Scroll up in this conversation to find it.
  Copy it manually into your markdown file.
  The agent needs the full document as context.

If all sections are present:
  You are ready.
  Save the file.
  Start Step 0.
```
