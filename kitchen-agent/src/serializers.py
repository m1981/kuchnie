# src/serializers.py
import json
from google.genai import types


def dehydrate_history(history: list) -> str:
    """Converts Google SDK objects into a JSON string safe for database storage."""
    simple_list = []

    for content in history:
        part = content.parts[0]

        if part.text:
            simple_list.append({
                "role": content.role,
                "type": "text",
                "data": part.text
            })

        elif part.function_call:
            simple_list.append({
                "role": content.role,
                "type": "function_call",
                "name": part.function_call.name,
                "args": part.function_call.args,
                "id": part.function_call.id,
                # Convert bytes to hex string for JSON compatibility
                "signature": part.thought_signature.hex() if part.thought_signature else None
            })

        elif part.function_response:
            simple_list.append({
                "role": content.role,
                "type": "function_response",
                "name": part.function_response.name,
                "response": part.function_response.response,
                "id": part.function_response.id
            })

    return json.dumps(simple_list)


def hydrate_history(json_string: str) -> list:
    """Rebuilds Google SDK objects from the database JSON string."""
    if not json_string:
        return []

    simple_list = json.loads(json_string)
    history = []

    for item in simple_list:
        if item["type"] == "text":
            history.append(
                types.Content(role=item["role"], parts=[types.Part(text=item["data"])])
            )

        elif item["type"] == "function_call":
            # Convert hex string back to raw bytes
            sig_bytes = bytes.fromhex(item["signature"]) if item.get("signature") else None

            fc = types.FunctionCall(name=item["name"], args=item["args"], id=item["id"])
            history.append(
                types.Content(role=item["role"], parts=[types.Part(function_call=fc, thought_signature=sig_bytes)])
            )

        elif item["type"] == "function_response":
            fr = types.FunctionResponse(name=item["name"], response=item["response"], id=item["id"])
            history.append(
                types.Content(role=item["role"], parts=[types.Part(function_response=fr)])
            )

    return history