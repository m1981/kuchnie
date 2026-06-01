"""
tests/unit/tools/test_tool_registry.py
========================================
Unit tests for the ToolRegistry class in src/tools/registry.py.

The ToolRegistry is the class-based interface that replaces direct
access to TOOLS, FUNCTION_MAP, and DECLARATIONS module constants.
It supports handler lookup, schema generation per provider, and
tool discovery.

Phase 2 scope: verify the ToolRegistry class wraps the existing
module-level constants correctly and provides the same behavior.
"""
import pytest
from google.genai import types

from src.tools.registry import (
    DECLARATIONS,
    FUNCTION_MAP,
    TOOLS,
    ToolCategory,
    ToolEntry,
    ToolRegistry,
    build_default_registry,
)


# ---------------------------------------------------------------------------
# ToolRegistry — handler lookup
# ---------------------------------------------------------------------------

class TestGetHandler:
    def test_returns_callable_for_known_tool(self):
        registry = build_default_registry()
        handler = registry.get_handler("read_file")
        assert callable(handler)

    def test_raises_for_unknown_tool(self):
        registry = build_default_registry()
        with pytest.raises(ValueError, match="Unknown tool"):
            registry.get_handler("nonexistent_tool")

    def test_handler_matches_function_map(self):
        """ToolRegistry.get_handler must return the same callable as FUNCTION_MAP."""
        registry = build_default_registry()
        for name in FUNCTION_MAP:
            assert registry.get_handler(name) is FUNCTION_MAP[name]


# ---------------------------------------------------------------------------
# ToolRegistry — schema generation
# ---------------------------------------------------------------------------

class TestSchemasForProvider:
    def test_gemini_returns_function_declarations(self):
        registry = build_default_registry()
        schemas = registry.schemas_for_provider("gemini")
        assert len(schemas) == len(TOOLS)
        for schema in schemas:
            assert isinstance(schema, types.FunctionDeclaration)

    def test_anthropic_returns_tool_param_dicts(self):
        registry = build_default_registry()
        schemas = registry.schemas_for_provider("anthropic")
        assert len(schemas) == len(TOOLS)
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "input_schema" in schema
            assert "parameters" not in schema  # Anthropic uses input_schema

    def test_unknown_provider_raises(self):
        registry = build_default_registry()
        with pytest.raises(ValueError, match="Unknown provider"):
            registry.schemas_for_provider("openai")


# ---------------------------------------------------------------------------
# ToolRegistry — tool discovery
# ---------------------------------------------------------------------------

class TestToolDiscovery:
    def test_tool_names_matches_function_map_keys(self):
        registry = build_default_registry()
        assert set(registry.tool_names) == set(FUNCTION_MAP.keys())

    def test_tool_names_ordered(self):
        registry = build_default_registry()
        assert registry.tool_names == [e.declaration.name for e in TOOLS]

    def test_get_all_entries_returns_tool_entries(self):
        registry = build_default_registry()
        entries = registry.get_all_entries()
        assert all(isinstance(e, ToolEntry) for e in entries)
        assert len(entries) == len(TOOLS)


# ---------------------------------------------------------------------------
# ToolRegistry — registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_register_adds_tool(self):
        registry = ToolRegistry()
        assert len(registry.tool_names) == 0

        entry = ToolEntry(
            declaration=types.FunctionDeclaration(
                name="test_tool",
                description="A test tool.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={}),
            ),
            fn=lambda: {"ok": True},
        )
        registry.register(entry)
        assert "test_tool" in registry.tool_names
        handler = registry.get_handler("test_tool")
        assert handler() == {"ok": True}


# ---------------------------------------------------------------------------
# build_default_registry
# ---------------------------------------------------------------------------

class TestBuildDefaultRegistry:
    def test_returns_tool_registry_instance(self):
        registry = build_default_registry()
        assert isinstance(registry, ToolRegistry)

    def test_has_all_five_tools(self):
        registry = build_default_registry()
        assert len(registry.tool_names) == 5

    def test_gemini_schemas_match_declarations_constant(self):
        """The class-based API must produce the same schemas as the module constant."""
        registry = build_default_registry()
        class_schemas = registry.schemas_for_provider("gemini")
        # DECLARATIONS is the module-level constant
        assert len(class_schemas) == len(DECLARATIONS)
        for cs, decl in zip(class_schemas, DECLARATIONS):
            assert cs is decl  # same objects


# ---------------------------------------------------------------------------
# ToolCategory enum
# ---------------------------------------------------------------------------

class TestToolCategory:
    def test_enum_values_exist(self):
        assert ToolCategory.DISCOVERY is not None
        assert ToolCategory.FILE_OPERATIONS is not None
        assert ToolCategory.SEARCH is not None

    def test_enum_values_are_unique(self):
        values = [c.value for c in ToolCategory]
        assert len(values) == len(set(values))
