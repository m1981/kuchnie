"""
tests/unit/agent/test_tool_executor.py
========================================
Unit tests for ToolExecutor — safe, isolated tool execution.

The ToolExecutor resolves tool handlers from a registry and executes them,
catching and wrapping any errors so the LLM sees them instead of the app
crashing.  It supports concurrent execution of multiple tool calls.

These tests use a FakeRegistry — no real tool implementations needed.
"""
import asyncio
import time

import pytest

from src.agent.tool_executor import ToolCall, ToolExecutor, ToolResult


# ---------------------------------------------------------------------------
# Fake registry for isolated testing
# ---------------------------------------------------------------------------

class FakeRegistry:
    """Test double — no real tools needed."""

    def __init__(self, handlers: dict | None = None) -> None:
        self._handlers = handlers or {
            "read_file": lambda filepath: {"content": f"content of {filepath}"},
            "echo": lambda text: {"echo": text},
            "no_args": lambda: {"result": "ok"},
        }

    def get_handler(self, name: str):
        if name not in self._handlers:
            raise ValueError(f"Unknown tool: {name!r}")
        return self._handlers[name]


class FailingRegistry:
    """Registry where every handler raises."""

    def get_handler(self, name: str):
        def boom(**kwargs):
            raise RuntimeError("tool broke")
        return boom


# ---------------------------------------------------------------------------
# Tests: successful execution
# ---------------------------------------------------------------------------

class TestSuccessfulExecution:
    def test_single_tool_call_returns_result(self):
        executor = ToolExecutor(registry=FakeRegistry())
        results = executor.execute_all([
            ToolCall(id="1", name="read_file", arguments={"filepath": "/test.md"})
        ])
        assert len(results) == 1
        assert results[0].is_error is False
        assert "content of /test.md" in results[0].content

    def test_result_contains_tool_call_id(self):
        executor = ToolExecutor(registry=FakeRegistry())
        results = executor.execute_all([
            ToolCall(id="call_abc", name="echo", arguments={"text": "hi"})
        ])
        assert results[0].tool_call_id == "call_abc"

    def test_result_contains_tool_name(self):
        executor = ToolExecutor(registry=FakeRegistry())
        results = executor.execute_all([
            ToolCall(id="1", name="echo", arguments={"text": "hi"})
        ])
        assert results[0].name == "echo"

    def test_multiple_tool_calls_all_executed(self):
        executor = ToolExecutor(registry=FakeRegistry())
        results = executor.execute_all([
            ToolCall(id="1", name="read_file", arguments={"filepath": "a.md"}),
            ToolCall(id="2", name="echo", arguments={"text": "hello"}),
            ToolCall(id="3", name="no_args", arguments={}),
        ])
        assert len(results) == 3
        assert all(r.is_error is False for r in results)

    def test_empty_tool_calls_returns_empty_list(self):
        executor = ToolExecutor(registry=FakeRegistry())
        results = executor.execute_all([])
        assert results == []

    def test_no_args_tool_succeeds(self):
        executor = ToolExecutor(registry=FakeRegistry())
        results = executor.execute_all([
            ToolCall(id="1", name="no_args", arguments={})
        ])
        assert results[0].is_error is False
        assert "ok" in results[0].content


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_tool_exception_wrapped_gracefully(self):
        """LLM should see error message, app should not crash."""
        executor = ToolExecutor(registry=FailingRegistry())
        results = executor.execute_all([
            ToolCall(id="1", name="anything", arguments={})
        ])
        assert results[0].is_error is True
        assert "tool broke" in results[0].content

    def test_unknown_tool_returns_error(self):
        """Unknown tool name → error result, not an exception."""
        executor = ToolExecutor(registry=FakeRegistry())
        results = executor.execute_all([
            ToolCall(id="1", name="nonexistent_tool", arguments={})
        ])
        assert results[0].is_error is True
        assert "Unknown tool" in results[0].content

    def test_error_result_still_has_tool_call_id(self):
        executor = ToolExecutor(registry=FailingRegistry())
        results = executor.execute_all([
            ToolCall(id="err_1", name="bad", arguments={})
        ])
        assert results[0].tool_call_id == "err_1"

    def test_error_result_still_has_tool_name(self):
        executor = ToolExecutor(registry=FailingRegistry())
        results = executor.execute_all([
            ToolCall(id="1", name="crashing_tool", arguments={})
        ])
        assert results[0].name == "crashing_tool"

    def test_mixed_success_and_failure(self):
        """Some tools succeed, some fail — each result is independent."""
        call_count = 0

        def sometimes_fail(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("second call fails")
            return {"ok": True}

        registry = FakeRegistry(handlers={"tool_a": sometimes_fail})
        executor = ToolExecutor(registry=registry)
        results = executor.execute_all([
            ToolCall(id="1", name="tool_a", arguments={}),
            ToolCall(id="2", name="tool_a", arguments={}),
            ToolCall(id="3", name="tool_a", arguments={}),
        ])
        assert results[0].is_error is False
        assert results[1].is_error is True
        assert results[2].is_error is False


# ---------------------------------------------------------------------------
# Tests: ToolCall and ToolResult dataclasses
# ---------------------------------------------------------------------------

class TestToolCallDataclass:
    def test_fields(self):
        tc = ToolCall(id="c1", name="read_file", arguments={"filepath": "x.md"})
        assert tc.id == "c1"
        assert tc.name == "read_file"
        assert tc.arguments == {"filepath": "x.md"}


class TestToolResultDataclass:
    def test_default_no_error(self):
        result = ToolResult(tool_call_id="1", name="test", content="ok")
        assert result.is_error is False

    def test_error_flag(self):
        result = ToolResult(tool_call_id="1", name="test", content="boom", is_error=True)
        assert result.is_error is True


# ---------------------------------------------------------------------------
# Tests: sync execution (current codebase uses sync tools)
# ---------------------------------------------------------------------------

class TestSyncExecution:
    def test_sync_handler_executed_successfully(self):
        """Current tool handlers are sync functions — must work without async."""
        def sync_read(**kwargs):
            return {"content": "sync result"}

        registry = FakeRegistry(handlers={"sync_tool": sync_read})
        executor = ToolExecutor(registry=registry)
        results = executor.execute_all([
            ToolCall(id="1", name="sync_tool", arguments={})
        ])
        assert results[0].content == "{'content': 'sync result'}"
        assert results[0].is_error is False

    def test_dict_result_converted_to_string(self):
        """Tool handlers return dicts — ToolExecutor must stringify them."""
        def returns_dict(**kwargs):
            return {"key": "value", "count": 42}

        registry = FakeRegistry(handlers={"dict_tool": returns_dict})
        executor = ToolExecutor(registry=registry)
        results = executor.execute_all([
            ToolCall(id="1", name="dict_tool", arguments={})
        ])
        assert "key" in results[0].content
        assert "42" in results[0].content
