# LLM Context Tools — Field Guide

Practical guide to code-surfacing tools, ordered by when to reach for each one.
Based on analysis of this specific codebase (FastAPI backend + Svelte frontend,
SQLite persistence, Gemini agent loop).

---

## Mental Model

These tools compress source code into representations small enough to fit in an
LLM context window while remaining rich enough to reason about structure.
Think of them as a zoom ladder:

```
repo-map          →  project skeleton              (~400 tokens)
pysum             →  imports + signatures          (~1 200 tokens)
py-diagram token  →  class fields + inheritance    (~600 tokens)
callgraph         →  runtime behaviour             (only with probe.py)
```

Start wide, zoom in only as needed. Never reach for `callgraph` until you have
a `probe.py` — see section 4.

---

## Decision Tree

```
New to the codebase or cold-starting a task?
    └─► repo-map                              (always first)

Need to write code that calls into a module?
    └─► pysum <file>                          (imports tell you the dep graph)

Working with a class — fields, inheritance, Protocol check?
    └─► py-diagram --format token             (richest per token)

Generating docs / architecture diagram?
    └─► py-diagram --format mermaid           (paste into GitHub / Obsidian)
    └─► gen-diagram . | dot -Tpng -o out.png  (only if you need a PNG)

Token budget tight, need smallest possible class view?
    └─► py-diagram --format token             (not mermaid, not dot)

Which files should I include — ignoring tests, frontend, generated code?
    └─► lsproj | pysum --pipe                 (respects .projlist whitelist)

What is slow / what calls what at runtime?
    └─► callgraph --target probe.py --include 'src.*'
        (only useful with a probe script — see section 4)
```

---

## 1. `repo-map` — Always Start Here

**What it does:** one line per function/class with its signature and line
number. No bodies, no imports. Entire project in a single read.

**On this codebase it immediately showed:**

- `main.py` spans lines 81–810 with 25+ endpoint functions — the God-route
  smell is visible before reading a single line of code
- `ChatService` has exactly one public method (`handle_turn`) — thin service layer
- Module-level globals (`= logger`, `= app`, `= _client`) reveal statefulness

```bash
repo-map                          # scan current directory
repo-map --root src/              # backend only
repo-map --skip tests migrations  # cut noise
repo-map --show-imports           # add import lines when deps matter
```

**When to stop here:** if your question is structural — "where does X live?",
"how many endpoints are there?", "which file owns class Y?" — `repo-map`
answers it. Move to `pysum` only when you need types or imports.

---

## 2. `pysum` — Imports + Full Typed Signatures

**What it does:** per-file Markdown blocks with all imports and typed
signatures. No function bodies.

**On this codebase the imports section is the high-value output:**

- `main.py` imports 22 schemas in one line — a coupling signal invisible to `repo-map`
- `repositories.py` imports from `src.exporter` — the repo layer does
  rendering, an SRP violation surfaced by the import line alone
- `agent.py` imports `DECLARATIONS` and `FUNCTION_MAP` directly from
  `src.tools.registry` — tight coupling to the tool registry

**Known blind spot on this project:** `schemas.py` is Pydantic-heavy. `pysum`
shows all schema classes as `pass` bodies because field definitions aren't
method signatures. Always follow with `py-diagram --format token` when
working in the schemas or repositories modules.

```bash
pysum src/                        # full backend
pysum src/repositories.py         # single file before touching it
lsproj | pysum --pipe             # scoped to .projlist whitelist
find src/ -name '*.py' | pysum --pipe   # backend Python only, no frontend noise
```

---

## 3. `py-diagram --format token` — Class Topology, Best Per Token

**What it does:** class hierarchy with inheritance chains, typed fields, and
method signatures in the most compact text form. Four output formats; `token`
is the right choice for LLM context in almost every case.

**On this codebase this is the highest-value tool per token spent:**

Protocol contract verification — the single best use on this project:

```
[CLASS] SessionRepository(Protocol)
    METHODS: save_session(...), load_session(...), fork_session(...) — 10 methods

[CLASS] SQLiteSessionRepository
    METHODS: save_session(...), load_session(...), fork_session(...) — 10 methods
```

Method-for-method match is visible without reading the source. If
`SQLiteSessionRepository` were missing a method, you'd catch it here.

Field shapes on Pydantic models — fixes `pysum`'s blind spot:

```
[CLASS] ChatRequest(BaseModel)
    FIELDS: session_id:str, message:str, mode_id:str, system_prompt:str | None,
            images:list[ChatImagePart] | None, context_files:list[str] | None
```

**Known limitation:** Protocol structural typing is not drawn as an inheritance
arrow. `SQLiteSessionRepository` implements `SessionRepository(Protocol)` by
structural match, not `class SQLiteSessionRepository(SessionRepository)` — so
no edge appears in the diagram. Verify by comparing method lists manually.

```bash
py-diagram --format token                          # whole project
py-diagram --format token --source src/repositories.py   # single file
py-diagram --format token --skip tests migrations  # exclude noise
py-diagram --format mermaid > doc/architecture.md  # for GitHub rendering
py-diagram --format token > arch.txt               # save for reuse across turns
```

**Format selection:**

| Goal                      | Format                    |
| ------------------------- | ------------------------- |
| LLM context window        | `token`                   |
| GitHub PR / Obsidian      | `mermaid`                 |
| PNG via Graphviz pipeline | `dot`                     |
| Never for LLM             | `dot` (verbose, wasteful) |

---

## 4. `callgraph` — Runtime Behaviour, Only With a Probe Script

**What it does:** traces an actual execution and produces a JSON report of
every function called, with call counts, total time, and caller lists.

**Critical limitation on this codebase:** the existing `report.json` was
generated by running the FastAPI app directly. It captured 659 records of
which only 59 were `src.*` — and all 59 were `call_count: 1` (module-load
events). None of the business logic paths (`handle_turn`, `save_session`,
`process_chat_turn`, tool dispatch) were exercised because no HTTP requests
were made.

**Callgraph is only useful when you write a probe script first:**

```python
# probe.py — minimal exercise of the business logic path
import os
os.environ.setdefault("GEMINI_API_KEY", "fake")

from unittest.mock import patch, MagicMock
from src.repositories import SQLiteConnection, SQLiteSessionRepository
from src.chat_service import ChatService

db = SQLiteConnection(":memory:")
repo = SQLiteSessionRepository(db)

fake_response = ("Agent reply", [{"role": "user", "parts": [{"text": "hi"}]}])

with patch("src.agent.process_chat_turn", return_value=fake_response):
    svc = ChatService(repo)
    svc.handle_turn("session-1", "hello")
```

Then:

```bash
callgraph --target probe.py \
          --include 'src.*' \
          --json report.json \
          --mermaid hotspots.md
```

This will trace the real path: `handle_turn → dehydrate_history →
save_session → load_session → log_turn`.

**Filtering the JSON output** (the raw file is 659 records, mostly stdlib):

```bash
python3 -c "
import json
d = json.load(open('report.json'))
app = [r for r in d['call_graph'] if r['name'].startswith('src.')]
print(json.dumps(app[:20], indent=2))
"
```

**When callgraph is worth it:**

- Performance investigation: `time_total` on `save_session` vs `load_session`
- Validating a refactor didn't change call patterns
- Understanding the tool-dispatch loop in `agent.py` under real load

**When to skip it:** if your question is structural ("what are the fields?",
"what does this module import?") — static tools answer it faster and cheaper.

---

## 5. `lsproj` — Scoping Gate

**What it does:** emits a filtered file list matching the `.projlist`
whitelist. Pipe into other tools to scope them precisely.

**On this codebase:** the `.projlist` is well-structured into four sections —
Python backend, Svelte frontend, prompts/knowledge, and docs. Without it,
`pysum` run on the whole repo would include frontend `.ts`/`.svelte` files
that `pysum` cannot process and test files that add noise.

```bash
lsproj                            # verify what's in scope
lsproj | pysum --pipe             # summarise only meaningful files
lsproj -e '*.md'                  # temporarily exclude markdown
find src/ -name '*.py' | pysum --pipe   # ad-hoc backend-only scope
```

**Note:** `lsproj` lists frontend files (`.ts`, `.svelte`) per `.projlist`,
but `pysum` and `py-diagram` are Python-only tools and silently skip them.
The frontend layer has no equivalent code-surfacing tool in this toolset.

---

## 6. Tools to Skip or Use Rarely

### `gen-diagram` (Graphviz DOT)

Skip for LLM context — DOT syntax is verbose. On this codebase, 41 classes
produce ~200 lines of mostly empty schema nodes with no edges between them
because Pydantic inheritance is flat.

Use only when you need a PNG for documentation:

```bash
gen-diagram . --skip tests | dot -Tpng -o doc/arch.png
```

### `py-diagram --format mermaid`

Same information as `token` format at 1.5× the token cost. Use only when
the output goes to a human-readable document, not an LLM prompt.

### `callgraph` without `probe.py`

Produces startup-only traces. 90% of records are stdlib module loading.
The business logic you care about — `handle_turn`, `save_session`,
`process_chat_turn` — will show `call_count: 1` at best. No value.

---

## Recipes for Common Tasks on This Codebase

### "I need to add a new API endpoint"

```bash
repo-map --root src/main.py          # see existing endpoint pattern
pysum src/schemas.py                  # → useless, schemas are Pydantic
py-diagram --format token --source src/schemas.py   # → use this instead
pysum src/repositories.py             # understand what the repo layer exposes
```

### "I need to refactor the repository layer"

```bash
py-diagram --format token --source src/repositories.py
# Side-by-side: Protocol methods vs SQLiteSessionRepository methods
# Verify full contract coverage before and after refactor
```

### "Is this module safe to change — what depends on it?"

```bash
pysum src/exporter.py                 # see what it imports
grep -r "from src.exporter" src/      # see who imports it
```

### "What is the full request/response shape for endpoint X?"

```bash
py-diagram --format token --source src/schemas.py
# All 22 schema classes with typed fields in one read (~300 tokens)
```

### "Generate architecture docs"

```bash
py-diagram --format mermaid --skip tests > doc/architecture.md
# or
gen-diagram . --skip tests | dot -Tpng -o doc/arch.png
```

### "Understand runtime call chain for a real chat turn"

```bash
# 1. Write probe.py (see section 4)
# 2. Run:
callgraph --target probe.py --include 'src.*' --json report.json
# 3. Filter:
python3 -c "
import json
d = json.load(open('report.json'))
app = [r for r in d['call_graph'] if r['name'].startswith('src.')]
print(json.dumps(sorted(app, key=lambda r: r['call_count'], reverse=True)[:15], indent=2))
"
```

---

## Token Budget Reference

| Tool + flags                                | This project output      | Token estimate |
| ------------------------------------------- | ------------------------ | -------------- |
| `repo-map --root src/`                      | ~80 lines                | ~550           |
| `pysum src/`                                | ~150 lines               | ~1 200         |
| `py-diagram --format token --skip tests`    | ~120 lines               | ~900           |
| `py-diagram --format mermaid --skip tests`  | ~180 lines               | ~1 400         |
| `gen-diagram . --skip tests`                | ~200 lines (empty nodes) | ~1 600         |
| `callgraph --json` filtered to `src.*`      | ~60 lines                | ~500           |
| `callgraph --json` unfiltered (659 records) | ~2 200 lines             | ~17 000        |
