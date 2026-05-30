# Tools — Improvement Proposals

Analysis of gaps and failure modes discovered during evaluation against a real
Python codebase. Each section names the tool, describes the concrete problem
observed, explains the impact, and proposes the fix.

Priority is rated **High / Medium / Low** based on frequency of the problem
and how badly it degrades the tool's core value proposition.

---

## 1. `pysum` — Single-file targeting not supported

### Problem

`pysum` accepts only a directory as its positional argument. Passing a single
`.py` file fails:

```
$ pysum src/repositories.py
usage: pysum [-h] [-p] [project_dir]
pysum: error: unrecognized arguments: src/repositories.py
```

The workaround is the `--pipe` flag:

```bash
find src/ -name "repositories.py" | pysum --pipe
```

This is non-obvious, undiscoverable, and requires an extra shell command for
the single most common use-case: "show me this one file before I touch it."

### Impact

**High.** The natural agent workflow is `repo-map` to locate a file, then
`pysum <that-file>` to inspect it. Both `repo-map` and `py-diagram` accept
a single file via `--source`. `pysum` being the exception forces an
inconsistent and verbose workaround that every new user will hit.

### Proposed Fix

Accept both a directory and one or more file paths as positional arguments.
When a positional argument ends in `.py`, treat it as a file path rather than
a directory:

```bash
pysum src/repositories.py              # single file
pysum src/repositories.py src/schemas.py  # multiple files
pysum src/                             # existing directory behaviour unchanged
```

Internally this means: if `project_dir` is a `.py` file, bypass the directory
walk and process that file directly. If multiple positional arguments are
given, process each in order.

---

## 2. `pysum` — Produces empty output for Pydantic / dataclass / attrs classes

### Problem

`pysum` renders class field definitions as `pass` when those fields are
declared as class-level annotations (Pydantic `BaseModel`, `dataclasses`,
`attrs`). On a schema-heavy file, the entire output is noise:

```python
## src/schemas.py
class ChatRequest(BaseModel)
    pass

class SessionSummary(BaseModel)
    pass
# ... 20 more empty classes
```

The actual field information exists in the source but is invisible to `pysum`
because it only captures method signatures, not class-body annotations.

### Impact

**High.** In any modern Python API or domain-model codebase, Pydantic models
and dataclasses are the primary data carriers. `pysum` on these files consumes
tokens while returning zero actionable information. The user must fall back to
`py-diagram --format token`, which means `pysum` is silently useless for a
large and growing category of Python code.

### Proposed Fix

Two options in order of preference:

**Option A (preferred):** When processing a class that inherits from a known
base (`BaseModel`, `TypedDict`, or any class with `@dataclass`/`@attr.s`
decorator), extract class-level annotated assignments and emit them as typed
fields rather than `pass`:

```python
## src/schemas.py
class ChatRequest(BaseModel)
    session_id: str
    message: str
    mode_id: str
    system_prompt: str | None
    images: list[ChatImagePart] | None
```

**Option B (simpler):** When a class body consists entirely of annotated
assignments with no methods, emit the annotations verbatim instead of `pass`.
This requires no special-casing of base classes and handles all annotation
patterns uniformly.

Either option removes the need for the two-tool workaround documented in the
field guide (`pysum` for functions, `py-diagram` for models).

---

## 3. `py-diagram` — Protocol implementation relationships not detected

### Problem

`py-diagram` draws inheritance arrows for nominal subclassing
(`class Foo(Bar)`) but not for structural Protocol implementation. When a
concrete class satisfies a `Protocol` by structural match rather than explicit
inheritance, no relationship edge is drawn:

```
[CLASS] SessionRepository(Protocol)
    METHODS: save_session(...), load_session(...), ...   ← 10 methods

[CLASS] SQLiteSessionRepository                          ← no arrow to Protocol
    METHODS: save_session(...), load_session(...), ...   ← same 10 methods
```

The relationship exists and is verifiable by method list comparison, but the
diagram does not express it. An LLM reading the diagram cannot know
`SQLiteSessionRepository` is the implementation of `SessionRepository` without
manually comparing both method lists.

### Impact

**High.** Protocol-based design is the idiomatic Python way to express
interfaces without coupling to ABCs. It is used in FastAPI dependency
injection, repository patterns, plugin systems, and anywhere
`typing.Protocol` replaces Java-style interfaces. Not detecting this
relationship means the diagram misrepresents the architecture for a large
class of Python codebases.

### Proposed Fix

Add a structural Protocol-matching pass after class collection:

1. For each class marked as `(Protocol)`, collect its method names as a set.
2. For each non-Protocol class, check whether its method names are a superset
   of any Protocol's method set.
3. If yes, emit a `--implements-->` relationship edge.

In `token` format:

```
[CLASS] SQLiteSessionRepository [module=src.repositories] implements SessionRepository
```

In `mermaid` format:

```
SQLiteSessionRepository ..|> SessionRepository : implements
```

False positives are possible (two unrelated classes that happen to share
method names), but they are rare in practice and far less harmful than the
current false negatives (failing to show a real contract relationship). A
confidence threshold based on the fraction of Protocol methods matched
(e.g. ≥ 80%) would reduce noise further.

---

## 4. `py-diagram` — `__init__` dependency injection invisible in all formats

### Problem

`py-diagram` captures field-level annotations (`FIELDS:`) and method
signatures (`METHODS:`), but does not capture constructor parameters as
dependency edges. When a class receives its dependencies through `__init__`
without storing them as typed instance attributes, those dependencies are
completely invisible:

```python
class ChatService:
    def __init__(self, session_repo: SessionRepository) -> None:
        self._repo = session_repo   # stored but not annotated at class level
```

`py-diagram` output:

```
[CLASS] ChatService [module=src.chat_service]
    METHODS: handle_turn(...)->tuple[str, list[dict]]
```

`session_repo: SessionRepository` — the sole dependency of `ChatService` —
does not appear anywhere in the diagram. The architectural connection between
`ChatService` and `SessionRepository` is invisible.

### Impact

**Medium.** Constructor injection is the dominant pattern for dependency
management in Python services. The diagram accurately shows fields that are
declared at class level (Pydantic, dataclasses), but silently drops injected
dependencies that are stored as private instance attributes. This creates a
misleadingly simple picture of service-layer classes.

### Proposed Fix

Parse `__init__` parameter annotations and emit them as `DEPS:` entries in
the `token` format, and as composition edges in `mermaid`/`dot`:

```
[CLASS] ChatService [module=src.chat_service]
    DEPS: session_repo:SessionRepository
    METHODS: handle_turn(...)->tuple[str, list[dict]]
```

In `mermaid`:

```
ChatService ..> SessionRepository : depends
```

Limit this to parameters typed with classes defined within the scanned
project (not `str`, `int`, `Path`, etc.) to avoid noise.

---

## 5. `callgraph` — No warning when entry point produces startup-only traces

### Problem

When `callgraph` is run against a module that imports but never executes
business logic (server bootstrap, `__main__` that starts a blocking process),
the tool completes silently and writes a `report.json` that contains hundreds
of stdlib import records and `call_count: 1` for every application class.
There is no warning that the output is startup-only and does not represent
runtime behaviour.

The user receives a large JSON file (~2 000 lines, ~16 000 tokens) that
appears to be a complete call graph but contains no actionable data. The
failure is silent and the output is plausibly real-looking.

### Impact

**High.** This is the single most likely way callgraph will be misused. A
user who does not know to write a `probe.py` script will run callgraph
against the obvious entry point, receive a large file, and either:
(a) feed it unfiltered to an LLM at enormous token cost with no signal, or
(b) filter it to the application package and find only `call_count: 1`
records, concluding (incorrectly) that the tool is broken.

### Proposed Fix

After execution, compute the ratio of application-namespace records
(those matching `--include` patterns) to total records. If:

- Fewer than 5 application-namespace functions were traced, **or**
- All application-namespace records have `call_count: 1` (module-load only)

Emit a prominent warning to stderr before writing output:

```
⚠  callgraph warning: only 3 application functions were traced, all with
   call_count=1. This looks like a startup-only trace with no business
   logic executed.

   Did you mean to run callgraph against a server entry point?
   If so, write a probe.py that exercises a specific code path instead.
   See: https://... or run: callgraph --help-probe
```

The output files should still be written so the user can inspect them, but
the warning makes the failure mode explicit rather than silent.

---

## 6. `callgraph` — No `--filter-app` flag for automatic stdlib exclusion

### Problem

Every useful use of `callgraph` requires the same post-processing step:
filter the raw JSON to the application namespace before reading or feeding
to an LLM. The current workflow requires writing a separate Python snippet:

```bash
python3 -c "
import json
d = json.load(open('report.json'))
app = [r for r in d['call_graph'] if r['name'].startswith('mypackage.')]
top = sorted(app, key=lambda r: r['call_count'], reverse=True)
print(json.dumps(top[:20], indent=2))
"
```

This is a ~6-line boilerplate that every user must write independently. The
`--include` flag already accepts the application namespace pattern at
collection time, but it does not filter the output — it only limits which
frames are traced.

### Impact

**Medium.** The raw output is 659 records (~16 000 tokens). The filtered
output is ~15–50 records (~400 tokens). That is a 40× token reduction for
identical information. Without a built-in filter, every agent and user must
independently rediscover and write the same filtering boilerplate.

### Proposed Fix

Add a `--top N` flag that, when combined with `--json`, writes a
pre-filtered JSON file containing only the top N records from the
application namespace (as defined by `--include` patterns), sorted by
`call_count` descending:

```bash
callgraph --target probe.py \
          --include 'mypackage.*' \
          --json report.json \
          --top 20
# Writes report.json with only the top 20 app-namespace records.
# No post-processing required.
```

Default `--top` to `0` (disabled, write all records) to preserve backward
compatibility. When `--top N` is set, also log to stderr:
`Wrote top 20 of 312 application records (637 stdlib records excluded).`

---

## 7. `repo-map` — No cross-file import summary mode

### Problem

`repo-map --show-imports` adds import lines per file, which is useful for
reading one file's dependencies. However there is no mode that aggregates
imports across all files to answer the question: "which internal modules are
most depended on?" This is the fan-in question — critical for identifying
which modules are load-bearing and risky to change.

Currently answering this requires piping `repo-map --show-imports` through
shell commands (`grep`, `awk`, `sort`, `uniq -c`) that are non-trivial for
an LLM agent to compose correctly.

### Impact

**Medium.** Fan-in analysis is a standard pre-refactor step. Without it,
an agent cannot assess change risk without reading every file's imports
individually.

### Proposed Fix

Add a `--import-summary` flag that, instead of per-file import blocks,
emits a ranked summary of internal imports across the entire scanned tree:

```
Internal import frequency (fan-in):
  8  src.config          (settings)
  6  src.repositories    (SessionRepository, SQLiteSessionRepository)
  4  src.tools.registry  (DECLARATIONS, FUNCTION_MAP)
  3  src.exporter        (export_session_to_markdown, export_session_to_llm_json)
  2  src.schemas         (ChatRequest, ChatResponse, ...)
```

Only internal imports (those starting with the scanned package root) would
be counted. Stdlib and third-party imports would be excluded.

Token cost: ~20–40 lines regardless of project size. Directly actionable:
the top entries are the highest-risk modules to change.

---

## 8. `lsproj` — No fallback behaviour when `.projlist` is absent

### Problem

When `.projlist` does not exist in the current directory, `lsproj` emits
nothing and exits silently. The user receives no output and no explanation:

```bash
$ lsproj
$  # empty — no error, no warning
```

This is indistinguishable from a correctly configured project that happens
to match no files. An agent receiving empty output from `lsproj` has no way
to know whether the tool is misconfigured or the directory is genuinely empty.

### Impact

**Medium.** An agent that tries `lsproj | pysum --pipe` and gets no output
will either fail silently (producing an empty summary) or retry with a
different approach, wasting turns. The correct fallback — `find src/ -name
'*.py' | pysum --pipe` — requires the agent to diagnose the root cause,
which it cannot do without a clear signal.

### Proposed Fix

When `.projlist` is absent, emit a diagnostic to stderr and fall back to a
sensible default rather than emitting nothing:

```
lsproj: no .projlist found in /path/to/project.
Falling back to: **/*.py (excluding common noise dirs: tests, migrations,
__pycache__, .venv, node_modules).

To configure: create .projlist with glob patterns. Run 'lsproj --help' for syntax.
```

Stdout should still contain the fallback file list so pipes continue to work.
Alternatively, add a `--strict` flag that causes `lsproj` to exit with an
error code when no `.projlist` is found, enabling explicit handling in scripts.

---

## Summary Table

| Tool         | Problem                                     | Priority | Effort                             |
| ------------ | ------------------------------------------- | -------- | ---------------------------------- |
| `pysum`      | No single-file targeting                    | High     | Low — argument parsing only        |
| `pysum`      | Empty output for Pydantic/dataclass fields  | High     | Medium — add annotation extraction |
| `py-diagram` | Protocol implementations not detected       | High     | Medium — add structural match pass |
| `py-diagram` | `__init__` injected deps invisible          | Medium   | Medium — parse constructor params  |
| `callgraph`  | Silent startup-only trace, no warning       | High     | Low — post-run heuristic check     |
| `callgraph`  | No built-in output filter (`--top N`)       | Medium   | Low — filter before JSON write     |
| `repo-map`   | No cross-file import fan-in summary         | Medium   | Medium — aggregation pass          |
| `lsproj`     | Silent empty output when `.projlist` absent | Medium   | Low — add fallback + stderr msg    |

### Implementation order recommendation

Fix `pysum` single-file targeting first (High priority, Low effort — highest
ROI). Then the `callgraph` startup warning (High priority, Low effort). Then
`pysum` Pydantic fields and `py-diagram` Protocol detection together, since
they address the same root gap: the tools misrepresent the two most common
Python design patterns (Pydantic data models and Protocol-based interfaces).
