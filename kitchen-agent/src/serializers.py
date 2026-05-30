"""
src/serializers.py
==================
Round-trip serialization for conversation history stored in SQLite.

Two provider formats are supported
------------------------------------
**Gemini** — history items are ``types.Content`` SDK objects.
  Serialised as: ``{"type": "text"|"function_call"|"function_response", "role": ..., ...}``

**Anthropic** — history items are plain ``dict`` objects (MessageParam shape).
  Serialised as: ``{"__provider": "anthropic", "role": ..., "content": ...}``

The discriminator on load is the ``"__provider"`` key:
  - present and ``"anthropic"``  → return the dict as-is (plain dict)
  - absent                       → reconstruct a ``types.Content`` object (Gemini)

This keeps the on-disk format backward-compatible: legacy sessions without
``"__provider"`` are always treated as Gemini.

Refactor — Decision 1: turn_id identity
----------------------------------------
Every dehydrated item carries an optional ``turn_id`` field — a stable UUID
that groups all ``api_history`` items belonging to the same logical UI turn.
The ``turn_id`` is transparent to the hydration step (it is passed through
in the raw JSON and used by ``MessageEditService``).

Backward compatibility
----------------------
``hydrate_history`` accepts legacy items that have no ``turn_id`` field and
silently fills in ``None`` so old sessions continue to load without error.

Limitations
-----------
* Only the *first* part of each Gemini ``Content`` is persisted.
* ``thought_signature`` bytes are encoded as a hex string for JSON safety.
* Anthropic items are stored verbatim — their structure is already
  JSON-serialisable (plain dicts / strings / lists).
"""

import json
import structlog

from google.genai import types

logger = structlog.get_logger(__name__)

# Sentinel stored on every Anthropic item so hydrate_history can distinguish
# provider formats without inspecting content shape.
_ANTHROPIC_PROVIDER_KEY = "__provider"
_ANTHROPIC_PROVIDER_VAL = "anthropic"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_gemini_content(item: object) -> bool:
    """Return True when *item* is a Gemini SDK ``types.Content`` object."""
    return isinstance(item, types.Content)


def _dehydrate_gemini(content: types.Content, turn_id: str | None) -> dict | None:
    """
    Serialise a single Gemini ``types.Content`` object to a plain dict.

    Returns ``None`` when the item should be skipped (no parts, unknown type).
    """
    if not content.parts:
        logger.warning("Skipping Content with no parts (role=%s)", content.role)
        return None

    part = content.parts[0]

    if part.text is not None:
        item: dict = {
            "role": content.role,
            "type": "text",
            "data": part.text,
        }

    elif part.function_call is not None:
        item = {
            "role": content.role,
            "type": "function_call",
            "name": part.function_call.name,
            "args": part.function_call.args,
            "id": part.function_call.id,
            # thought_signature is raw bytes — encode as hex for JSON safety.
            "signature": (
                part.thought_signature.hex()
                if part.thought_signature
                else None
            ),
        }

    elif part.function_response is not None:
        item = {
            "role": content.role,
            "type": "function_response",
            "name": part.function_response.name,
            "response": part.function_response.response,
            "id": part.function_response.id,
        }

    else:
        logger.warning(
            "Skipping unrecognised part type for role=%s — not persisted.",
            content.role,
        )
        return None

    if turn_id is not None:
        item["turn_id"] = turn_id

    return item


def _dehydrate_anthropic(message: dict, turn_id: str | None) -> dict:
    """
    Serialise a single Anthropic MessageParam dict for DB storage.

    The dict is stored verbatim with an extra ``__provider`` sentinel so
    ``hydrate_history`` can reconstruct it correctly.
    """
    item = {
        _ANTHROPIC_PROVIDER_KEY: _ANTHROPIC_PROVIDER_VAL,
        **message,
    }
    if turn_id is not None:
        item["turn_id"] = turn_id
    return item


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def dehydrate_history(history: list, turn_ids: list[str] | None = None) -> str:
    """
    Convert a conversation history to a JSON string for DB storage.

    Accepts either:
      - a list of ``types.Content`` objects   (Gemini provider)
      - a list of plain ``dict`` objects       (Anthropic provider)
      - a mix is NOT supported and not expected; each session is single-provider

    Args:
        history:  Provider-specific history list.
        turn_ids: Optional parallel list of ``turn_id`` strings — one per
                  item.  When provided, each serialised dict carries a
                  ``"turn_id"`` key for stable identity.

    Returns:
        JSON string of the dehydrated history.
    """
    simple_list: list[dict] = []

    for idx, content in enumerate(history):
        turn_id: str | None = turn_ids[idx] if turn_ids is not None else None

        if _is_gemini_content(content):
            item = _dehydrate_gemini(content, turn_id)
            if item is not None:
                simple_list.append(item)
        elif isinstance(content, dict):
            simple_list.append(_dehydrate_anthropic(content, turn_id))
        else:
            logger.warning(
                "dehydrate_history: skipping unknown item type %s", type(content).__name__
            )

    return json.dumps(simple_list)


def hydrate_history(json_string: str) -> list:
    """
    Rebuild a conversation history from a DB JSON string.

    Dispatches each item to the Gemini or Anthropic reconstruction path
    based on the ``__provider`` sentinel written by ``dehydrate_history``.

    Gemini items  → ``types.Content`` objects (SDK)
    Anthropic items → plain dicts (MessageParam shape)

    ``turn_id`` and ``__provider`` fields present in stored items are stripped
    before returning Anthropic dicts so providers never see internal metadata.
    """
    if not json_string or json_string.strip() in ("", "[]"):
        return []

    simple_list: list[dict] = json.loads(json_string)
    history: list = []

    for item in simple_list:
        if item.get(_ANTHROPIC_PROVIDER_KEY) == _ANTHROPIC_PROVIDER_VAL:
            # Anthropic path — return a plain dict, strip internal keys.
            clean = {
                k: v for k, v in item.items()
                if k not in (_ANTHROPIC_PROVIDER_KEY, "turn_id")
            }
            history.append(clean)

        else:
            # Gemini path — reconstruct SDK objects.
            item_type = item.get("type")

            if item_type == "text":
                history.append(
                    types.Content(
                        role=item["role"],
                        parts=[types.Part(text=item["data"])],
                    )
                )

            elif item_type == "function_call":
                sig_bytes = (
                    bytes.fromhex(item["signature"]) if item.get("signature") else None
                )
                fc = types.FunctionCall(
                    name=item["name"],
                    args=item["args"],
                    id=item["id"],
                )
                history.append(
                    types.Content(
                        role=item["role"],
                        parts=[types.Part(function_call=fc, thought_signature=sig_bytes)],
                    )
                )

            elif item_type == "function_response":
                fr = types.FunctionResponse(
                    name=item["name"],
                    response=item["response"],
                    id=item["id"],
                )
                history.append(
                    types.Content(
                        role=item["role"],
                        parts=[types.Part(function_response=fr)],
                    )
                )

            else:
                logger.warning("Unknown history item type '%s' — skipped.", item_type)

    return history
