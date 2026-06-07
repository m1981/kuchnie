"""
src/providers/anthropic_provider.py
=====================================
AnthropicProvider — wraps the Anthropic Claude SDK agentic loop.

Anthropic messages API vs Gemini
---------------------------------
The Anthropic API is fundamentally different from Gemini in several ways:

1. **History format** — history is a list of plain ``MessageParam``-shaped
   dicts, not SDK objects.

2. **Tool schema format** — Anthropic uses its own ``ToolParam`` schema
   (``{"name", "description", "input_schema"}``) rather than Gemini's
   ``FunctionDeclaration``.  Conversion lives in ``schema_converters.py``.

3. **System instruction** — passed as the top-level ``system`` kwarg, not
   inside the messages list.

4. **max_tokens** — required by the Anthropic API (Gemini does not require it).
"""
from __future__ import annotations

import base64
import json
from typing import Any, Iterator

import anthropic
import structlog
from dotenv import load_dotenv

from src.config import settings
from src.agent.tool_executor import ToolCall, ToolExecutor, ToolResult
from src.providers.normalizer import ResponseNormalizer
from src.providers.schema_converters import (
    declaration_to_anthropic_tool as _declaration_to_anthropic_tool,
    schema_to_json_schema as _schema_to_json_schema,
)
from src.tools.file_ops import read_file

load_dotenv()

logger = structlog.get_logger(__name__)


class AnthropicProvider:
    """
    LLM provider backed by the Anthropic Claude SDK.

    Implements the ``LLMProvider`` Protocol so ``TurnOrchestrator`` can use
    it via ``complete()`` and ``complete_with_tools()``.

    Tool schemas are built once at construction time from the captured
    declarations.
    """

    def __init__(
        self,
        model_override: str | None = None,
        registry: Any | None = None,
    ) -> None:
        api_key = settings.anthropic_api_key or None
        self._client = anthropic.Anthropic(api_key=api_key)
        # Resolved at construction; visible to tests via provider._model.
        self._model: str = model_override or settings.anthropic_model
        self._normalizer = ResponseNormalizer()

        if registry is not None:
            self._registry = registry
        else:
            from src.tools.registry import build_default_registry
            self._registry = build_default_registry()

        self._declarations = [
            e.declaration
            for e in self._registry.get_all_entries()
            if e.declaration is not None
        ]
        self._tool_executor = ToolExecutor(registry=self._registry)
        self._tool_schemas: list[dict[str, Any]] = self._build_tool_schemas()

    def _build_tool_schemas(self) -> list[dict[str, Any]]:
        """Build Anthropic tool schema list from captured declarations."""
        schemas: list[dict[str, Any]] = []

        for declaration in self._declarations:
            schemas.append(_declaration_to_anthropic_tool(declaration))

        return schemas

    # ── Common format → Anthropic format conversion ──────────────────

    @staticmethod
    def _common_to_anthropic(msg: dict, user_content: list | None = None) -> dict:
        """
        Convert a common format message to Anthropic format.

        Common format:
            {"role": "user", "content": "Hello"}
            {"role": "assistant", "content": "", "tool_calls": [...]}
            {"role": "tool", "tool_call_id": "...", "content": "result"}

        Anthropic format:
            {"role": "user", "content": "Hello"}
            {"role": "assistant", "content": [{"type": "tool_use", ...}]}
            {"role": "user", "content": [{"type": "tool_result", ...}]}
        """
        role = msg.get("role", "user")
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls")
        tool_call_id = msg.get("tool_call_id")

        # Handle tool response messages
        if role == "tool" and tool_call_id:
            return {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": content,
                }],
            }

        # Handle assistant messages with tool calls
        if tool_calls:
            blocks: list[dict[str, Any]] = []
            if content and isinstance(content, str):
                blocks.append({"type": "text", "text": content})
            for tc in tool_calls:
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": tc.get("name", "unknown"),
                    "input": tc.get("arguments", {}),
                })
            return {"role": "assistant", "content": blocks}

        # Handle user messages with optional enrichment
        if role == "user" and user_content:
            enriched = list(user_content)
            enriched.append({"type": "text", "text": content})
            return {"role": "user", "content": enriched}

        # Regular messages — pass through
        return dict(msg)

    # ── LLMProvider interface (for TurnOrchestrator) ─────────────────────

    def complete(self, context: "AssembledContext") -> Any:
        """
        Single turn completion via the Anthropic Messages API.
        Returns raw SDK response — normalizer handles parsing.
        """
        from src.agent.context_assembler import AssembledContext

        # Build user content with context files and images
        user_content: list[dict[str, Any]] = []

        if context.context_files:
            snippets: list[str] = []
            for fp in context.context_files:
                result = read_file(fp)
                if "content" in result:
                    snippets.append(f"=== {fp} ===\n{result['content']}")
                else:
                    logger.warning("context_file_unreadable", path=fp, error=result.get("error"))
            if snippets:
                block = "[Context files injected by user]\n\n" + "\n\n".join(snippets)
                user_content.append({"type": "text", "text": block})

        if context.images:
            for img in context.images:
                try:
                    base64.b64decode(img["data"], validate=True)
                    user_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img["mime_type"],
                            "data": img["data"],
                        },
                    })
                except Exception as exc:
                    logger.warning("image_decode_failed", error=str(exc))

        # Build conversation state from context messages
        # Convert from common format to Anthropic format
        self._conversation_state: list[dict[str, Any]] = []
        for msg in context.messages:
            converted = self._common_to_anthropic(msg, user_content)
            self._conversation_state.append(converted)
            if msg.get("role") == "user" and user_content:
                user_content = []  # Only enrich once

        if user_content:
            self._conversation_state.append({"role": "user", "content": user_content})

        # Only send tools if orchestrator has set tool_schemas on context.
        # When use_tools=False, context.tool_schemas will be None.
        tool_schemas = self._tool_schemas if context.tool_schemas is not None else []

        response = self._client.messages.create(
            model=self._model,
            max_tokens=settings.anthropic_max_tokens,
            tools=tool_schemas,
            messages=self._conversation_state,
            system=context.system_prompt or None,
        )

        # Store response in conversation state for tool loop continuity
        assistant_content: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        self._conversation_state.append({"role": "assistant", "content": assistant_content})

        return response

    def complete_with_tools(
        self,
        context: "AssembledContext",
        tool_calls: list["ToolCall"],
        tool_results: list["ToolResult"],
    ) -> Any:
        """
        Continue generation after tool execution.
        Builds tool result message, appends to conversation state.
        """
        from src.agent.context_assembler import AssembledContext

        # Build tool result message
        result_content: list[dict[str, Any]] = []
        for tr in tool_results:
            result_content.append({
                "type": "tool_result",
                "tool_use_id": tr.tool_call_id,
                "content": tr.content,
            })
        self._conversation_state.append({"role": "user", "content": result_content})

        # Only send tools if orchestrator has set tool_schemas on context.
        tool_schemas = self._tool_schemas if context.tool_schemas is not None else []

        response = self._client.messages.create(
            model=self._model,
            max_tokens=settings.anthropic_max_tokens,
            tools=tool_schemas,
            messages=self._conversation_state,
            system=context.system_prompt or None,
        )

        # Store response in conversation state for next iteration
        assistant_content: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        self._conversation_state.append({"role": "assistant", "content": assistant_content})

        return response

    def stream(self, context: "AssembledContext") -> Iterator[Any]:
        """
        Stream a single turn via the Anthropic Messages API.
        Yields raw SDK events — normalizer handles text extraction.
        """
        from src.agent.context_assembler import AssembledContext

        # Build user content with context files and images
        user_content: list[dict[str, Any]] = []

        if context.context_files:
            snippets: list[str] = []
            for fp in context.context_files:
                result = read_file(fp)
                if "content" in result:
                    snippets.append(f"=== {fp} ===\n{result['content']}")
                else:
                    logger.warning("context_file_unreadable", path=fp, error=result.get("error"))
            if snippets:
                block = "[Context files injected by user]\n\n" + "\n\n".join(snippets)
                user_content.append({"type": "text", "text": block})

        if context.images:
            for img in context.images:
                try:
                    base64.b64decode(img["data"], validate=True)
                    user_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img["mime_type"],
                            "data": img["data"],
                        },
                    })
                except Exception as exc:
                    logger.warning("image_decode_failed", error=str(exc))

        # Build conversation state from context messages
        self._conversation_state: list[dict[str, Any]] = []
        for msg in context.messages:
            converted = self._common_to_anthropic(msg, user_content)
            self._conversation_state.append(converted)
            if msg.get("role") == "user" and user_content:
                user_content = []  # Only enrich once

        if user_content:
            self._conversation_state.append({"role": "user", "content": user_content})

        # Only send tools if orchestrator has set tool_schemas on context.
        # When use_tools=False, context.tool_schemas will be None.
        tool_schemas = self._tool_schemas if context.tool_schemas is not None else []

        logger.info(
            "anthropic_stream_start",
            model=self._model,
            messages_count=len(self._conversation_state),
        )

        # Use messages.stream() for streaming
        with self._client.messages.stream(
            model=self._model,
            max_tokens=settings.anthropic_max_tokens,
            tools=tool_schemas,
            messages=self._conversation_state,
            system=context.system_prompt or None,
        ) as stream:
            for event in stream:
                yield event

        # After streaming, get the final message for conversation state
        # The stream context manager provides access to the final message
        try:
            final_message = stream.get_final_message()

            # Yield __final_message__ so orchestrator can detect tool calls
            # without trying to normalize the last raw stream event.
            yield {"type": "__final_message__", "message": final_message}

            assistant_content: list[dict[str, Any]] = []
            for block in final_message.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            self._conversation_state.append({"role": "assistant", "content": assistant_content})
        except Exception:
            logger.warning("anthropic_stream_final_message_failed")

    def stream_with_tools(
        self,
        context: "AssembledContext",
        tool_calls: list["ToolCall"],
        tool_results: list["ToolResult"],
    ) -> Iterator[Any]:
        """
        Continue streaming after tool execution.
        Yields raw SDK events.
        """
        from src.agent.context_assembler import AssembledContext

        # Build tool result message
        result_content: list[dict[str, Any]] = []
        for tr in tool_results:
            result_content.append({
                "type": "tool_result",
                "tool_use_id": tr.tool_call_id,
                "content": tr.content,
            })
        self._conversation_state.append({"role": "user", "content": result_content})

        # Only send tools if orchestrator has set tool_schemas on context.
        tool_schemas = self._tool_schemas if context.tool_schemas is not None else []

        # Use messages.stream() for streaming
        with self._client.messages.stream(
            model=self._model,
            max_tokens=settings.anthropic_max_tokens,
            tools=tool_schemas,
            messages=self._conversation_state,
            system=context.system_prompt or None,
        ) as stream:
            for event in stream:
                yield event

        # After streaming, get the final message for conversation state
        try:
            final_message = stream.get_final_message()

            # Yield __final_message__ so orchestrator can detect tool calls
            yield {"type": "__final_message__", "message": final_message}

            assistant_content: list[dict[str, Any]] = []
            for block in final_message.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            self._conversation_state.append({"role": "assistant", "content": assistant_content})
        except Exception:
            logger.warning("anthropic_stream_final_message_failed")
