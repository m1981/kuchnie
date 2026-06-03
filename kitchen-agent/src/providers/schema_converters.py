"""
Provider-specific schema conversion utilities.

Exists solely to break the circular import between:
  src/tools/registry.py  (imports _declaration_to_anthropic_tool)
  src/providers/anthropic_provider.py  (imports from registry)

Neither registry.py nor anthropic_provider.py import from each other
for schema conversion after this module exists.

No imports from src.tools.registry or src.providers.* in this file.
"""
from __future__ import annotations

from typing import Any

# Anthropic type enum string → JSON Schema type string
_GENAI_TYPE_TO_JSON: dict[str, str] = {
    "STRING": "string",
    "NUMBER": "number",
    "INTEGER": "integer",
    "BOOLEAN": "boolean",
    "ARRAY": "array",
    "OBJECT": "object",
}


def schema_to_json_schema(schema: Any) -> dict[str, Any]:
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
            properties[prop_name] = schema_to_json_schema(prop_schema)

        result["properties"] = properties

        required_raw = getattr(schema, "required", []) or []
        if required_raw:
            result["required"] = list(required_raw)

    description = getattr(schema, "description", None)
    if description:
        result["description"] = description

    return result


def declaration_to_anthropic_tool(declaration: Any) -> dict[str, Any]:
    """
    Convert a ``types.FunctionDeclaration`` to an Anthropic ``ToolParam`` dict.
    """
    input_schema = schema_to_json_schema(getattr(declaration, "parameters", None))
    # Ensure required top-level fields are present for Anthropic.
    if "properties" not in input_schema:
        input_schema["properties"] = {}
    input_schema["type"] = "object"

    return {
        "name": declaration.name,
        "description": declaration.description or "",
        "input_schema": input_schema,
    }
