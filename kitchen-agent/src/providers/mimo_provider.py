"""
src/providers/mimo_provider.py
===============================
MimoProvider — wraps the Xiaomi Mimo API (OpenAI-compatible).

Xiaomi Mimo provides an OpenAI-compatible chat completions API.
This provider uses the ``openai`` SDK with a custom ``base_url``.

Models
------
- ``mimo-v2.5-pro`` — 1M context, 128K output, function calling
- ``mimo-v2.5``     — 1M context, lighter/cheaper

History format
--------------
Mimo uses OpenAI's message format: plain dicts with
``{"role": ..., "content": ...}`` — same as Anthropic's storage format.
"""
from __future__ import annotations

import base64
import json
from typing import Any

import structlog
from dotenv import load_dotenv
from openai import OpenAI

from src.config import settings
from src.agent.tool_executor import ToolCall, ToolExecutor, ToolResult
from src.tools.file_ops import read_file

load_dotenv()

logger = structlog.get_logger(__name__)


def _build_default_registry():
    """Lazy-load the default ToolRegistry."""
    from src.tools.registry import build_default_registry
    return build_default_registry()


class MimoProvider:
    """
    LLM provider backed by the Xiaomi Mimo API (OpenAI-compatible).

    Implements the ``LLMProvider`` Protocol so ``TurnOrchestrator`` can use
    it via ``complete()`` and ``complete_with_tools()``.
    """

    def __init__(self, model_override: str | None = None) -> None:
        self._client = OpenAI(
            api_key=settings.mimo_api_key,
            base_url=settings.mimo_base_url,
        )
        self._model: str = model_override or settings.mimo_model
        self._registry = _build_default_registry()
        self._tool_executor = ToolExecutor(registry=self._registry)

    def _build_tool_schemas(self) -> list[dict[str, Any]]:
        """Build OpenAI-compatible tool schemas from registry declarations."""
        schemas: list[dict[str, Any]] = []
        for entry in self._registry.get_all_entries():
            decl = entry.declaration
            # Convert Gemini FunctionDeclaration to OpenAI function format
            params = self._schema_to_dict(decl.parameters) if decl.parameters else {"type": "object", "properties": {}}
            schemas.append({
                "type": "function",
                "function": {
                    "name": decl.name,
                    "description": decl.description or "",
                    "parameters": params,
                },
            })
        return schemas

    @staticmethod
    def _schema_to_dict(schema: Any) -> dict[str, Any]:
        """Convert a google.genai types.Schema to a plain dict."""
        if schema is None:
            return {"type": "object", "properties": {}}

        result: dict[str, Any] = {}
        raw_type = str(getattr(schema, "type", "OBJECT"))
        type_str = raw_type.split(".")[-1] if "." in raw_type else raw_type
        type_map = {
            "STRING": "string", "NUMBER": "number", "INTEGER": "integer",
            "BOOLEAN": "boolean", "ARRAY": "array", "OBJECT": "object",
        }
        result["type"] = type_map.get(type_str.upper(), "string")

        if result["type"] == "object":
            props = getattr(schema, "properties", {}) or {}
            result["properties"] = {}
            for name, prop in props.items():
                result["properties"][name] = MimoProvider._schema_to_dict(prop)
            required = getattr(schema, "required", []) or []
            if required:
                result["required"] = list(required)

        desc = getattr(schema, "description", None)
        if desc:
            result["description"] = desc

        return result

    def _build_messages(self, context: "AssembledContext") -> list[dict[str, Any]]:
        """Build OpenAI-format messages from AssembledContext."""
        messages: list[dict[str, Any]] = []

        # System prompt
        if context.system_prompt:
            messages.append({"role": "system", "content": context.system_prompt})

        # Context files injection
        context_block = ""
        if context.context_files:
            snippets: list[str] = []
            for fp in context.context_files:
                result = read_file(fp)
                if "content" in result:
                    snippets.append(f"=== {fp} ===\n{result['content']}")
                else:
                    logger.warning("context_file_unreadable", path=fp, error=result.get("error"))
            if snippets:
                context_block = "[Context files injected by user]\n\n" + "\n\n".join(snippets)

        # Conversation messages
        for msg in context.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Enrich last user message with context files and images
            if role == "user" and (context_block or context.images):
                parts: list[dict[str, Any]] = []
                if context_block:
                    parts.append({"type": "text", "text": context_block})
                    context_block = ""  # Only inject once
                if context.images:
                    for img in context.images:
                        try:
                            base64.b64decode(img["data"], validate=True)
                            parts.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{img['mime_type']};base64,{img['data']}",
                                },
                            })
                        except Exception as exc:
                            logger.warning("image_decode_failed", error=str(exc))
                    context.images = []  # Only inject once
                parts.append({"type": "text", "text": content})
                messages.append({"role": role, "content": parts})
            else:
                messages.append({"role": role, "content": content})

        return messages

    def complete(self, context: "AssembledContext") -> Any:
        """
        Single turn completion via the Mimo API.
        Returns raw OpenAI-style response — normalizer handles parsing.
        """
        from src.agent.context_assembler import AssembledContext

        messages = self._build_messages(context)

        # Only send tools if the orchestrator has set tool_schemas on the context.
        # When use_tools=False, context.tool_schemas will be None.
        if context.tool_schemas is not None:
            tool_schemas = self._build_tool_schemas()
        else:
            tool_schemas = []

        self._conversation_state = messages

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tool_schemas if tool_schemas else None,
            temperature=settings.mimo_temperature,
            max_tokens=settings.mimo_max_tokens,
        )

        # Store assistant response in conversation state
        if response.choices:
            msg = response.choices[0].message
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            self._conversation_state.append(assistant_msg)

        return response

    def complete_with_tools(
        self,
        context: "AssembledContext",
        tool_calls: list["ToolCall"],
        tool_results: list["ToolResult"],
    ) -> Any:
        """
        Continue generation after tool execution.
        Builds tool result messages, appends to conversation state.
        """
        from src.agent.context_assembler import AssembledContext

        # Append tool results as tool messages
        for tr in tool_results:
            self._conversation_state.append({
                "role": "tool",
                "tool_call_id": tr.tool_call_id,
                "content": tr.content,
            })

        tool_schemas = self._build_tool_schemas()

        response = self._client.chat.completions.create(
            model=self._model,
            messages=self._conversation_state,
            tools=tool_schemas if tool_schemas else None,
            temperature=settings.mimo_temperature,
            max_tokens=settings.mimo_max_tokens,
        )

        # Store assistant response in conversation state
        if response.choices:
            msg = response.choices[0].message
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            self._conversation_state.append(assistant_msg)

        return response
