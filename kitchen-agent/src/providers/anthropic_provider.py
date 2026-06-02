"""
src/providers/anthropic_provider.py
=====================================
AnthropicProvider — wraps the Anthropic Claude SDK agentic loop.

Anthropic messages API vs Gemini
---------------------------------
The Anthropic API is fundamentally different from Gemini in several ways that
shape this implementation:

1. **History format** — history is a list of plain ``MessageParam``-shaped
   dicts, not SDK objects:
   ``[{"role": "user"|"assistant", "content": str | list[ContentBlock]}]``

2. **Tool call representation** — when Claude wants to call a tool it returns
   a ``ToolUseBlock`` inside ``message.content``.  The ``stop_reason`` is
   ``"tool_use"``.

3. **Tool result injection** — tool results are fed back as a *user* turn with
   a ``tool_result`` content block::
     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": ..., "content": ...}]}

4. **Tool schema format** — Anthropic uses its own ``ToolParam`` schema
   (``{"name", "description", "input_schema"}``) rather than Gemini's
   ``FunctionDeclaration``.  We build these from ``FUNCTION_MAP`` keys and
   ``DECLARATIONS`` descriptions at provider construction time.

5. **System instruction** — passed as the top-level ``system`` kwarg, not
   inside the messages list.

6. **max_tokens** — required by the Anthropic API (Gemini does not require it).
   Controlled via ``settings.anthropic_max_tokens``.

History mutation
----------------
Like GeminiProvider, this provider mutates the *history* list in place so
that ``chat_service.py`` and the serializers see the updated conversation.
The stored dicts are JSON-serialisable, which is compatible with the existing
``dehydrate_history`` / ``hydrate_history`` serializers (those serializers
handle Gemini Content objects specifically, but ``chat_service.py`` stores
the raw JSON from ``dehydrate_history`` which is already agnostic of the
provider).

NOTE: The serializers currently only understand Gemini ``types.Content``
objects.  For the Anthropic provider we store the plain-dict history directly
— the existing ``dehydrate_history`` will not be called on it. This is by
design: the provider owns its history format.  A future refactor could
introduce a provider-agnostic serializer, but that is out of scope here.

Tool schema construction
------------------------
We convert the Gemini-style ``FunctionDeclaration`` objects from the registry
to Anthropic ``ToolParam`` format.  This happens in ``_build_tool_schemas()``
and is cached on the instance.

Specifically, Anthropic requires ``input_schema`` to be a JSON Schema object.
We map Gemini's ``types.Schema`` to an equivalent ``{"type": "object",
"properties": {...}, "required": [...]}`` dict.
"""
from __future__ import annotations

import base64
import json
from typing import Any

import anthropic
import structlog
from dotenv import load_dotenv

from src.config import settings
from src.agent.tool_executor import ToolCall, ToolExecutor, ToolResult
from src.providers.normalizer import ResponseNormalizer
from src.tools.file_ops import read_file
from src.tools.registry import DECLARATIONS, FUNCTION_MAP

load_dotenv()

logger = structlog.get_logger(__name__)

# Anthropic type enum string → JSON Schema type string
_GENAI_TYPE_TO_JSON: dict[str, str] = {
    "STRING": "string",
    "NUMBER": "number",
    "INTEGER": "integer",
    "BOOLEAN": "boolean",
    "ARRAY": "array",
    "OBJECT": "object",
}


# ---------------------------------------------------------------------------
# Adapter: FUNCTION_MAP → ToolRegistryProtocol
# ---------------------------------------------------------------------------

class _FunctionMapAdapter:
    """
    Adapts the module-level FUNCTION_MAP dict to the ToolRegistryProtocol
    so ToolExecutor can look up handlers.

    This adapter reads FUNCTION_MAP at call time (not at construction), so
    tests that patch FUNCTION_MAP via ``patch("src.providers.anthropic_provider.FUNCTION_MAP", ...)``
    still work — the adapter sees the patched version.
    """

    def get_handler(self, name: str):
        if name not in FUNCTION_MAP:
            raise ValueError(f"Unknown tool: {name!r}")
        return FUNCTION_MAP[name]


def _schema_to_json_schema(schema: Any) -> dict[str, Any]:
    """
    Convert a google.genai ``types.Schema`` to a JSON Schema dict.

    Handles the subset of Schema types actually used in the tool registry
    (OBJECT with STRING properties).  Extend when richer types are needed.
    """
    if schema is None:
        return {"type": "object", "properties": {}}

    # types.Schema has a .type attribute that is a types.Type enum.
    raw_type = str(getattr(schema, "type", "OBJECT"))
    # The enum value may be e.g. "Type.STRING" or just "STRING"
    type_str = raw_type.split(".")[-1] if "." in raw_type else raw_type
    json_type = _GENAI_TYPE_TO_JSON.get(type_str.upper(), "string")

    result: dict[str, Any] = {"type": json_type}

    if json_type == "object":
        props_raw = getattr(schema, "properties", {}) or {}
        properties: dict[str, Any] = {}
        for prop_name, prop_schema in props_raw.items():
            properties[prop_name] = _schema_to_json_schema(prop_schema)

        result["properties"] = properties

        required_raw = getattr(schema, "required", []) or []
        if required_raw:
            result["required"] = list(required_raw)

    description = getattr(schema, "description", None)
    if description:
        result["description"] = description

    return result


def _declaration_to_anthropic_tool(declaration: Any) -> dict[str, Any]:
    """
    Convert a ``types.FunctionDeclaration`` to an Anthropic ``ToolParam`` dict.
    """
    input_schema = _schema_to_json_schema(getattr(declaration, "parameters", None))
    # Ensure required top-level fields are present for Anthropic.
    if "properties" not in input_schema:
        input_schema["properties"] = {}
    input_schema["type"] = "object"

    return {
        "name": declaration.name,
        "description": declaration.description or "",
        "input_schema": input_schema,
    }


class AnthropicProvider:
    """
    LLM provider backed by the Anthropic Claude SDK.

    Implements the same ``LLMProvider`` Protocol as ``GeminiProvider`` so
    ``chat_service.py`` and ``agent.py`` can use it without modification.

    Tool schemas are built once at construction time from the shared tool
    registry (``DECLARATIONS`` from ``src/tools/registry.py``).  Only tools
    present in ``FUNCTION_MAP`` will be registered — the schema list is filtered
    to match the callable map.
    """

    def __init__(self, model_override: str | None = None) -> None:
        api_key = settings.anthropic_api_key or None
        self._client = anthropic.Anthropic(api_key=api_key)
        self._tool_schemas: list[dict[str, Any]] = self._build_tool_schemas()
        # Resolved at construction; visible to tests via provider._model.
        self._model: str = model_override or settings.anthropic_model
        self._normalizer = ResponseNormalizer()
        self._tool_executor = ToolExecutor(registry=_FunctionMapAdapter())

    def _build_tool_schemas(self) -> list[dict[str, Any]]:
        """Build Anthropic tool schema list from the central registry."""
        schemas: list[dict[str, Any]] = []

        # Only register tools that have a callable implementation.
        callable_names = set(FUNCTION_MAP.keys())

        for declaration in DECLARATIONS:
            if declaration.name in callable_names:
                schemas.append(_declaration_to_anthropic_tool(declaration))

        # Fall back: if DECLARATIONS is empty or doesn't match, build minimal
        # schemas from FUNCTION_MAP keys directly (for testing with fake maps).
        if not schemas and callable_names:
            for name in sorted(callable_names):
                schemas.append({
                    "name": name,
                    "description": f"Tool: {name}",
                    "input_schema": {"type": "object", "properties": {}},
                })

        return schemas

    def process_chat_turn(
        self,
        user_message: str,
        history: list,
        system_instruction: str | None = None,
        images: list[dict] | None = None,
        context_files: list[str] | None = None,
        use_tools: bool = True,
    ) -> tuple[str, list[dict]]:
        """
        Drives a single conversational turn via the Anthropic Messages API.

        Mutates *history* in place (list of MessageParam dicts).

        Returns:
            ``(final_text, tool_logs)``
        """
        logger.info("anthropic_turn_start", message_preview=user_message[:60])

        # ── Build user-turn content blocks ────────────────────────────────────

        user_content: list[dict[str, Any]] = []

        # 1a. Context files injected as a text block before the user message.
        if context_files:
            snippets: list[str] = []
            for fp in context_files:
                result = read_file(fp)
                if "content" in result:
                    snippets.append(f"=== {fp} ===\n{result['content']}")
                else:
                    logger.warning("context_file_unreadable", path=fp, error=result.get("error"))
            if snippets:
                block = "[Context files injected by user]\n\n" + "\n\n".join(snippets)
                user_content.append({"type": "text", "text": block})

        # 1b. The user's text message.
        user_content.append({"type": "text", "text": user_message})

        # 1c. Optional inline images.
        if images:
            for img in images:
                try:
                    # Validate the base64 — raises binascii.Error on bad data.
                    base64.b64decode(img["data"], validate=True)
                    user_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img["mime_type"],
                            "data": img["data"],
                        },
                    })
                except Exception as exc:  # noqa: BLE001
                    logger.warning("image_decode_failed", error=str(exc))

        # Anthropic accepts a plain string if there is only one text block with
        # no images; use a list otherwise for full control.
        if len(user_content) == 1 and user_content[0]["type"] == "text":
            user_turn: dict[str, Any] = {"role": "user", "content": user_content[0]["text"]}
        else:
            user_turn = {"role": "user", "content": user_content}

        history.append(user_turn)

        tools_used: list[dict] = []

        # Re-build tool schemas in case FUNCTION_MAP was patched (tests).
        tool_schemas = self._build_tool_schemas()

        # ── Direct call branch (use_tools=False) ───────────────────────────
        # One API call, no loop, no tool dispatch, empty tool_logs.
        if not use_tools:
            logger.info("anthropic_direct_call", model=self._model)
            direct_kwargs: dict = {
                "model":      self._model,
                "max_tokens": settings.anthropic_max_tokens,
                "tools":      [],
                "messages":   history,
                "system":     system_instruction,
            }
            response = self._client.messages.create(**direct_kwargs)
            normalized = self._normalizer.normalize(response, provider="anthropic")
            final_text: str = normalized.text.strip() if normalized.text else ""
            logger.info("anthropic_direct_response", length=len(final_text))
            history.append({
                "role": "assistant",
                "content": [{"type": "text", "text": final_text}],
            })
            return final_text, []

        # ── Agentic loop ──────────────────────────────────────────────────────

        while True:
            logger.info("anthropic_api_call", model=self._model)

            create_kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": settings.anthropic_max_tokens,
                "tools": tool_schemas if use_tools else [],
                "messages": history,
                "system": system_instruction,
            }

            response = self._client.messages.create(**create_kwargs)

            # Use normalizer to classify the response.
            normalized = self._normalizer.normalize(response, provider="anthropic")

            # ── Tool call branch ──────────────────────────────────────────────
            if normalized.has_tool_calls:
                # Append the assistant's tool-use turn to history.
                # We still iterate raw blocks for history mutation
                # (preserving block-level detail).
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

                history.append({"role": "assistant", "content": assistant_content})

                # Dispatch each tool using ToolExecutor.
                tool_results: list[dict[str, Any]] = []
                for tc in normalized.tool_calls:
                    logger.info("anthropic_tool_call", tool=tc.name, args=str(tc.arguments)[:120])

                    tool_exec_result = self._tool_executor._execute_one(
                        ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
                    )

                    if tool_exec_result.is_error:
                        result = {"error": tool_exec_result.content}
                        logger.warning("anthropic_tool_error", tool=tc.name, error=tool_exec_result.content)
                    else:
                        # ToolExecutor returns stringified results — parse back to dict
                        # for consistent tool_logs format
                        try:
                            import ast
                            result = ast.literal_eval(tool_exec_result.content)
                        except (ValueError, SyntaxError):
                            result = {"content": tool_exec_result.content}

                    tools_used.append({
                        "name": tc.name,
                        "args": tc.arguments,
                        "result": result,
                    })
                    logger.info("anthropic_tool_result", snippet=str(result)[:120])

                    # Anthropic expects tool results as JSON string content.
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": json.dumps(result),
                    })

                # Feed tool results back as a user turn.
                history.append({"role": "user", "content": tool_results})

                # Loop — call the API again with updated history.

            # ── Final text branch ─────────────────────────────────────────────
            else:
                final_text: str = normalized.text.strip() if normalized.text else ""
                logger.info("anthropic_final_response", length=len(final_text))

                history.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": final_text}],
                })
                return final_text, tools_used

    # ── LLMCompleter interface (for TurnOrchestrator) ─────────────────────

    def complete(self, context: "AssembledContext") -> Any:
        """
        New interface for TurnOrchestrator.
        Calls Anthropic API with pre-assembled context.
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
        self._conversation_state: list[dict[str, Any]] = []
        for msg in context.messages:
            if msg.get("role") == "user" and user_content:
                # Enrich the last user message with context files/images
                enriched = list(user_content)
                enriched.append({"type": "text", "text": msg.get("content", "")})
                self._conversation_state.append({"role": "user", "content": enriched})
                user_content = []  # Only enrich once
            else:
                self._conversation_state.append(dict(msg))

        # If user_content wasn't consumed (no user message in context),
        # add it as a separate turn
        if user_content:
            self._conversation_state.append({"role": "user", "content": user_content})

        tool_schemas = self._build_tool_schemas()

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

        tool_schemas = self._build_tool_schemas()

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
