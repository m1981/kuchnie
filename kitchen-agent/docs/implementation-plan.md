# Implementation Plan — Agent Hardening

Priority-ordered plan to bring the Kitchen Agent from "good" to
"production-grade" based on the architecture assessment.

**Estimated total effort:** 3-5 days
**Approach:** Incremental, each phase independently deployable

---

## Phase 1: Token Budget Enforcement in Tool Loop (HIGH)

**Why first:** Anthropic's research shows token usage explains 80% of
performance variance. This is the single biggest improvement you can make.

**Problem:** During the agentic loop, tool results accumulate in
`self._conversation_state` without any size check. After 5-10 iterations
with large tool results (e.g., `search_knowledge_base` returning 200
matches), you can exceed the model's context window.

### Changes

#### 1.1 Add token counting to tool results

**File:** `src/agent/tool_executor.py`

```python
@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    content: str
    is_error: bool = False
    token_count: int = 0  # NEW: estimated token count
```

Estimate tokens in `content` using the existing `TokenCounter` (injected
via protocol). Rough heuristic: `len(content) // 4` is fine for English.

#### 1.2 Add context budget check in TurnOrchestrator

**File:** `src/agent/turn_orchestrator.py`

After each tool iteration, check if accumulated tool results exceed a
configurable budget (e.g., 30% of total context window):

```python
def _check_tool_budget(self, tool_details: list[ToolCallDetail], context: AssembledContext) -> bool:
    """Returns True if we're still within budget."""
    total_tool_tokens = sum(d.token_count for d in tool_details)
    budget = context.slots_used.get(ContextSlot.TOOL_RESULTS, 0)
    max_tool_tokens = int(self._context_budget.total * 0.30)  # 30% of context
    return total_tool_tokens < max_tool_tokens
```

#### 1.3 Truncate large tool results

**File:** `src/agent/tool_executor.py`

When a tool result exceeds a threshold (e.g., 4000 tokens), truncate
with a clear message:

```python
def _truncate_result(self, content: str, max_tokens: int) -> str:
    if len(content) // 4 > max_tokens:
        truncated = content[:max_tokens * 4]
        return truncated + f"\n\n... [truncated — original was {len(content)} chars]"
    return content
```

#### 1.4 Add compaction for long tool loops

**File:** `src/agent/turn_orchestrator.py`

When approaching budget, compact older tool results:

```python
def _compact_tool_results(self, tool_details: list[ToolCallDetail]) -> list[dict]:
    """Replace verbose tool results with summaries for older iterations."""
    if len(tool_details) <= 3:
        return []  # Don't compact short loops

    # Keep last 2 tool results in full, summarize the rest
    compacted = []
    for detail in tool_details[:-2]:
        compacted.append({
            "role": "tool",
            "tool_call_id": detail.id,
            "content": f"[Tool: {detail.name}] Result was {len(detail.result_content)} chars",
        })
    return compacted
```

### Tests

- `test_tool_result_truncated_when_over_limit`
- `test_tool_loop_stops_when_budget_exceeded`
- `test_compaction_preserves_recent_results`
- `test_token_count_populated_on_tool_result`

### Effort: 1 day

---

## Phase 2: Retry with Backoff in ToolExecutor (MEDIUM)

**Why second:** Simple to implement, high reliability payoff, and sets
the foundation for async tool execution.

**Problem:** Transient failures (file locks, disk full, network timeouts
for future web tools) cause immediate error returns to the LLM, wasting
a full LLM round-trip.

### Changes

#### 2.1 Add retry configuration

**File:** `src/agent/tool_executor.py`

```python
@dataclass
class RetryConfig:
    max_attempts: int = 2          # 1 original + 1 retry
    base_delay: float = 0.5        # seconds
    max_delay: float = 5.0         # seconds
    retryable_errors: tuple = (IOError, OSError, TimeoutError)
```

#### 2.2 Add retry loop to `_execute_one`

**File:** `src/agent/tool_executor.py`

```python
def _execute_one(self, tool_call: ToolCall) -> ToolResult:
    last_error = None
    for attempt in range(self._retry_config.max_attempts):
        try:
            handler = self._registry.get_handler(tool_call.name)
            result = handler(**tool_call.arguments)
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=str(result),
                is_error=False,
            )
        except self._retry_config.retryable_errors as e:
            last_error = e
            if attempt < self._retry_config.max_attempts - 1:
                delay = min(
                    self._retry_config.base_delay * (2 ** attempt),
                    self._retry_config.max_delay,
                )
                log.warning("tool_retry", tool=tool_call.name, attempt=attempt + 1, delay=delay)
                time.sleep(delay)
        except Exception as e:
            # Non-retryable error — fail immediately
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=f"Tool error: {type(e).__name__}: {e}",
                is_error=True,
            )

    # All retries exhausted
    return ToolResult(
        tool_call_id=tool_call.id,
        name=tool_call.name,
        content=f"Tool error after {self._retry_config.max_attempts} attempts: {last_error}",
        is_error=True,
    )
```

#### 2.3 Inject RetryConfig via DI

**File:** `src/dependencies.py`

```python
@lru_cache()
def get_tool_executor() -> ToolExecutor:
    registry = get_tool_registry()
    return ToolExecutor(registry=registry, retry_config=RetryConfig(max_attempts=2))
```

#### 2.4 Make retryable errors configurable per tool (optional)

Some tools (file reads) are always retryable. Others (file creates) are
not (idempotency concerns). Add optional `retryable` flag to `ToolEntry`.

### Tests

- `test_retry_on_ioerror_succeeds_second_attempt`
- `test_no_retry_on_non_retryable_error`
- `test_retry_config_respected`
- `test_retry_delay_exponential`
- `test_all_retries_exhausted_returns_error`

### Effort: 0.5 day

---

## Phase 3: Observability — Cost Tracking & Trace Context (MEDIUM)

**Why third:** You can't optimize what you can't measure. This enables
data-driven decisions about which tools are expensive.

**Problem:** You have `structlog` with timing, but no per-turn cost
tracking, no tool latency breakdown, no way to trace a request across
the full lifecycle.

### Changes

#### 3.1 Add TurnMetrics dataclass

**File:** `src/agent/turn_orchestrator.py`

```python
@dataclass
class TurnMetrics:
    turn_id: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_calls_count: int = 0
    tool_total_ms: float = 0.0
    tool_details: list[dict] = field(default_factory=list)  # [{name, ms, tokens, is_error}]
    llm_calls_count: int = 0
    llm_total_ms: float = 0.0
    context_slots: dict = field(default_factory=dict)
```

#### 3.2 Populate metrics during orchestration

**File:** `src/agent/turn_orchestrator.py`

Instrument the existing `log_timing` calls to also populate metrics:

```python
# In the tool loop:
with log_timing(self._log, "orchestrator_tools_executed") as timing:
    start = time.monotonic()
    calls, results = self._execute_tool_calls(normalized, tool_details)
    elapsed_ms = (time.monotonic() - start) * 1000

    metrics.tool_calls_count += len(results)
    metrics.tool_total_ms += elapsed_ms
    metrics.tool_details.extend([
        {"name": tc.name, "ms": elapsed_ms / len(results), "tokens": 0, "is_error": tr.is_error}
        for tc, tr in zip(normalized.tool_calls, results)
    ])
```

#### 3.3 Add cost estimation

**File:** `src/agent/turn_orchestrator.py`

```python
# Provider pricing (per 1M tokens)
PROVIDER_PRICING = {
    "gemini": {"input": 0.15, "output": 0.60},
    "anthropic": {"input": 3.00, "output": 15.00},
    "mimo": {"input": 0.20, "output": 0.80},
}

def _estimate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PROVIDER_PRICING.get(provider, {"input": 0, "output": 0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
```

#### 3.4 Return metrics in TurnOutput

**File:** `src/agent/turn_orchestrator.py`

```python
@dataclass
class TurnOutput:
    # ... existing fields ...
    metrics: TurnMetrics | None = None  # NEW
```

#### 3.5 Log metrics in ChatService

**File:** `src/chat_service.py`

```python
self._log.info(
    "turn_metrics",
    provider=turn_output.provider_name,
    model=turn_output.model_name,
    input_tokens=turn_output.metrics.input_tokens,
    output_tokens=turn_output.metrics.output_tokens,
    estimated_cost_usd=turn_output.metrics.estimated_cost_usd,
    tool_calls=turn_output.metrics.tool_calls_count,
    tool_total_ms=turn_output.metrics.tool_total_ms,
)
```

### Tests

- `test_turn_metrics_populated`
- `test_cost_estimation_accuracy`
- `test_tool_details_in_metrics`
- `test_metrics_in_turn_output`

### Effort: 0.5 day

---

## Phase 4: Async Tool Execution (LOW-MEDIUM)

**Why fourth:** Nice-to-have for performance, but your tools are fast
(local I/O). Matters more when you add web/API tools.

**Problem:** Multiple tool calls in a single iteration execute sequentially.

### Changes

#### 4.1 Make ToolExecutor async-ready

**File:** `src/agent/tool_executor.py`

```python
import asyncio

class ToolExecutor:
    def __init__(self, registry: ToolRegistryProtocol, retry_config: RetryConfig | None = None):
        self._registry = registry
        self._retry_config = retry_config or RetryConfig()

    async def execute_all(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute all tool calls concurrently."""
        return await asyncio.gather(*[self._execute_one_async(tc) for tc in tool_calls])

    async def _execute_one_async(self, tool_call: ToolCall) -> ToolResult:
        # Run sync handlers in thread pool
        return await asyncio.to_thread(self._execute_one, tool_call)

    def execute_all_sync(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Fallback for sync contexts."""
        return [self._execute_one(tc) for tc in tool_calls]
```

#### 4.2 Update TurnOrchestrator to use async

**File:** `src/agent/turn_orchestrator.py`

The orchestrator's `run()` method is currently sync. Two options:

- **Option A:** Make `run()` async (requires `asyncio.run()` in ChatService)
- **Option B:** Keep `run()` sync, use `asyncio.run()` internally for tool execution

**Recommendation:** Option B — minimal disruption.

```python
# In run():
tool_results = asyncio.run(self._tools.execute_all(tool_calls))
```

#### 4.3 Update streaming path

**File:** `src/agent/turn_orchestrator.py`

The `stream()` method already yields events asynchronously. Use
`asyncio.run()` for tool execution in the stream path too.

### Tests

- `test_execute_all_runs_concurrently`
- `test_execute_all_sync_fallback`
- `test_concurrent_tool_calls_all_return_results`

### Effort: 0.5 day

---

## Phase 5: Tool Evaluation Harness (MEDIUM-LOW)

**Why fifth:** Enables data-driven tool improvements. Anthropic's blog
emphasizes this as critical for production agents.

**Problem:** You test tool _implementations_ but not tool _usage quality_.

### Changes

#### 5.1 Create eval scenarios

**File:** `tests/eval/tool_eval_scenarios.py`

```python
@dataclass
class EvalScenario:
    name: str
    user_message: str
    expected_tools: list[str]          # tools that should be called
    expected_args: dict | None = None  # expected args (partial match)
    max_iterations: int = 5
    success_criteria: Callable[[str], bool]  # function that checks the response

SCENARIOS = [
    EvalScenario(
        name="read_then_edit",
        user_message="Update the hinges section to mention Blum CLIP top",
        expected_tools=["search_knowledge_base", "read_file", "edit_file"],
        expected_args={"search_knowledge_base": {"query": "hinge"}},
        success_criteria=lambda response: "Blum" in response and "CLIP" in response,
    ),
    EvalScenario(
        name="discover_before_read",
        user_message="What files are available about drawer runners?",
        expected_tools=["get_repo_map"],
        max_iterations=2,
        success_criteria=lambda response: "runner" in response.lower(),
    ),
]
```

#### 5.2 Create eval runner

**File:** `tests/eval/test_tool_eval.py`

```python
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_tool_eval(scenario: EvalScenario):
    """Run a scenario and check that the agent uses tools correctly."""
    orchestrator = build_test_orchestrator()

    turn_input = TurnInput(
        user_message=scenario.user_message,
        use_tools=True,
        mode="default",
    )
    session = {"messages": [], "session_id": "eval-test"}

    result = orchestrator.run(session, turn_input)

    # Check tool calls
    actual_tools = [tc.name for tc in result.tool_calls_made]
    for expected in scenario.expected_tools:
        assert expected in actual_tools, f"Expected tool '{expected}' not called. Got: {actual_tools}"

    # Check iterations
    assert len(result.tool_calls_made) <= scenario.max_iterations

    # Check success criteria
    assert scenario.success_criteria(result.assistant_message), (
        f"Success criteria failed for '{scenario.name}'"
    )
```

#### 5.3 Add eval to CI (optional)

Run eval suite on a schedule (not every commit — these are slow and
non-deterministic):

```yaml
# .github/workflows/tool-eval.yml
on:
    schedule:
        - cron: '0 6 * * 1' # Weekly Monday 6am
    workflow_dispatch:
```

### Effort: 1 day

---

## Phase 6: MCP Adapter (LOW — Future)

**Why last:** The ecosystem is moving toward MCP, but your custom registry
works fine today. This is a future-proofing play.

### Conceptual Design

```python
# src/tools/mcp_adapter.py

class MCPAdapter:
    """Adapts MCP server tools to ToolRegistry format."""

    def __init__(self, mcp_server_url: str):
        self._client = MCPClient(mcp_server_url)

    async def discover_tools(self) -> list[ToolEntry]:
        """Convert MCP tools to ToolEntry objects."""
        mcp_tools = await self._client.list_tools()
        entries = []
        for tool in mcp_tools:
            declaration = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=self._mcp_schema_to_gemini(tool.inputSchema),
            )
            entries.append(ToolEntry(
                declaration=declaration,
                fn=lambda **kwargs: self._client.call_tool(tool.name, kwargs),
                category=ToolCategory.FILE_OPERATIONS,
            ))
        return entries
```

### Integration Point

**File:** `src/tools/registry.py`

```python
def build_default_registry(
    search_coordinator: Any | None = None,
    mcp_servers: list[str] | None = None,
) -> ToolRegistry:
    registry = ToolRegistry()

    # Register built-in tools
    for entry in _ALL_ENTRIES:
        registry.register(entry)

    # Register MCP tools
    if mcp_servers:
        for server_url in mcp_servers:
            adapter = MCPAdapter(server_url)
            mcp_entries = asyncio.run(adapter.discover_tools())
            for entry in mcp_entries:
                registry.register(entry)

    return registry
```

### Effort: 1-2 days (depends on MCP SDK maturity)

---

## Summary — Prioritized Roadmap

| Phase | What                      | Effort   | Impact     | Risk                              |
| ----- | ------------------------- | -------- | ---------- | --------------------------------- |
| **1** | Token budget in tool loop | 1 day    | HIGH       | Low — additive change             |
| **2** | Retry with backoff        | 0.5 day  | MEDIUM     | Low — isolated to ToolExecutor    |
| **3** | Cost tracking & metrics   | 0.5 day  | MEDIUM     | Low — observability only          |
| **4** | Async tool execution      | 0.5 day  | LOW-MEDIUM | Medium — changes execution model  |
| **5** | Tool eval harness         | 1 day    | MEDIUM     | Low — tests only                  |
| **6** | MCP adapter               | 1-2 days | LOW        | Medium — ecosystem still evolving |

**Recommended order:** 1 → 2 → 3 → 5 → 4 → 6

Phases 1-3 are the core hardening. Phase 5 enables measurement.
Phase 4 is a performance optimization. Phase 6 is future-proofing.

---

## Dependencies Between Phases

```
Phase 1 (Token Budget)
    │
    ├── Phase 2 (Retry) — independent, can be parallel
    │
    ├── Phase 3 (Metrics) — benefits from Phase 1 (tool token counts)
    │
    └── Phase 4 (Async) — builds on Phase 2 (retry in async context)

Phase 5 (Eval Harness) — independent, can start anytime

Phase 6 (MCP) — independent, but benefits from Phase 4 (async discovery)
```
