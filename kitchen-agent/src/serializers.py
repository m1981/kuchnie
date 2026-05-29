"""
src/serializers.py
==================
Round-trip serialization for Google Gemini SDK ``Content`` objects.

The SDK uses opaque Python objects that cannot be stored directly in SQLite.
We flatten each ``Content`` into a plain dict, JSON-encode for storage, and
reconstruct on load.

Limitations / design decisions
-------------------------------
* Only the *first* part of each ``Content`` is persisted.  Multi-part turns
  (e.g. text + inline image in the same model message) are not yet supported
  by this application — if that changes, extend the per-part loop below.
* ``thought_signature`` bytes are encoded as a hex string for JSON safety.
"""

import json
import structlog


from google.genai import types

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Dehydrate (SDK objects → JSON string)
# ---------------------------------------------------------------------------

def dehydrate_history(history: list) -> str:
    """Converts a Gemini conversation history to a JSON string for DB storage."""
    simple_list: list[dict] = []

    for content in history:
        if not content.parts:
            logger.warning("Skipping Content with no parts (role=%s)", content.role)
            continue

        part = content.parts[0]

        if part.text is not None:
            simple_list.append(
                {
                    "role": content.role,
                    "type": "text",
                    "data": part.text,
                }
            )

        elif part.function_call is not None:
            simple_list.append(
                {
                    "role": content.role,
                    "type": "function_call",
                    "name": part.function_call.name,
                    "args": part.function_call.args,
                    "id": part.function_call.id,
                    # thought_signature is raw bytes — encode as hex for JSON.
                    "signature": (
                        part.thought_signature.hex()
                        if part.thought_signature
                        else None
                    ),
                }
            )

        elif part.function_response is not None:
            simple_list.append(
                {
                    "role": content.role,
                    "type": "function_response",
                    "name": part.function_response.name,
                    "response": part.function_response.response,
                    "id": part.function_response.id,
                }
            )

        else:
            logger.warning(
                "Skipping unrecognised part type for role=%s — not persisted.",
                content.role,
            )

    return json.dumps(simple_list)


# ---------------------------------------------------------------------------
# Hydrate (JSON string → SDK objects)
# ---------------------------------------------------------------------------

def hydrate_history(json_string: str) -> list:
    """Rebuilds a Gemini conversation history from a DB JSON string."""
    if not json_string or json_string.strip() in ("", "[]"):
        return []

    simple_list: list[dict] = json.loads(json_string)
    history: list = []

    for item in simple_list:
        item_type = item.get("type")

        if item_type == "text":
            history.append(
                types.Content(
                    role=item["role"],
                    parts=[types.Part(text=item["data"])],
                )
            )

        elif item_type == "function_call":
            # Restore hex-encoded bytes back to raw bytes.
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
