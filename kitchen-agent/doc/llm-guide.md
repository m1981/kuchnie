# LLM Context Tools — Field Guide

Tools for compressing a Python codebase into representations small enough to
fit in a context window yet rich enough to reason about architecture, structure,
and behaviour. This guide is ordered by when to reach for each tool, not by
what each tool technically does.

---

## Mental Model: The Zoom Ladder

```
repo-map          →  project skeleton              (~400 tokens)   start here
pysum             →  imports + signatures          (~1 200 tokens) zoom in
py-diagram token  →  class fields + inheritance    (~600 tokens)   zoom in on types
callgraph         →  runtime behaviour             (expensive)     only when static is not enough
```

Always start at the top of the ladder and descend only as far as the task
requires. Reading full source bodies is the last resort, not the first.

---

## Decision Tree

Use this before reaching for any tool:

```
Starting a new task or unfamiliar with the codebase?
    └─► repo-map
        Gives you the full skeleton. Stop here if your question is structural.

Need to write code that calls into a module?
    └─► pysum <file or directory>
        Imports reveal the dependency graph. Signatures reveal the calling contract.

Working with a class — inheritance, fields, interface compliance?
    └─► py-diagram --format token
        Richest class view per token. Fixes pysum's Pydantic/dataclass blind spot.

Token budget is tight?
    └─► py-diagram --format token   (never --format dot for LLM context)

Need to scope which files matter — exclude tests, migrations, generated code?
    └─► lsproj | pysum --pipe       (reads .projlist whitelist)

Need to understand what actually runs — hotspots, call chains, timing?
    └─► callgraph --target probe.py --include 'yourpackage.*'
        Only valuable when pointed at a probe script. See section 4.

Need a diagram for docs, PRs, or wikis?
    └─► py-diagram --format mermaid        (paste into GitHub / Obsidian)
    └─► gen-diagram . | dot -Tpng -o a.png (only if PNG is specifically required)
```

---

## 1. `repo-map` — Always Start Here

**What it does:** one section per file, each function and class as a single
line with its signature and line number. No bodies, no imports by default.

**What to look for in the output:**

- A file whose line range spans hundreds of lines with many functions → God
  object or God module, likely a refactor target
- A class with only one or two public methods → thin facade or delegation layer
- Module-level assignments (`= logger`, `= app`, `= client`) → statefulness,
  singletons, global side effects at import time
- A function name that appears across many files → shared utility or
  potential unintended coupling

**Typical usage:**

```bash
repo-map                          # scan current directory
repo-map --root src/              # specific subtree
repo-map --skip tests migrations  # exclude noise directories
repo-map --show-imports           # add import lines when dependency overview matters
```

**When to stop here:** if your question is structural — "where does X live?",
"which file owns this class?", "what is the public surface of module Y?" —
`repo-map` answers it without spending tokens on bodies or imports. Move to
`pysum` only when you need type signatures or dependency information.

---

## 2. `pysum` — Imports + Full Typed Signatures

**What it does:** per-file Markdown code blocks with all imports and full
typed signatures. No function bodies.

**The import block is the high-value section.** Imports are the fastest way
to read a module's dependency graph without parsing code. Look for:

- A module importing from many other internal modules → high coupling; change
  risk radiates outward
- A lower-layer module (repository, storage) importing from a higher-layer
  module (exporter, renderer) → layer inversion, SRP violation
- Repeated identical imports across many files → candidate for a shared
  utility or injection point
- A very long single import line listing many names from one module → tight
  coupling to that module's internals

**Known blind spot:** `pysum` shows only method signatures, not field
definitions. Classes built with Pydantic `BaseModel`, `dataclasses`, or
`attrs` will appear as empty `pass` bodies. Always follow with
`py-diagram --format token` when the file contains schema or model classes.

**Typical usage:**

```bash
pysum src/                              # full source tree
pysum src/some_module.py                # single file before touching it
lsproj | pysum --pipe                   # scope to .projlist whitelist
find src/ -name '*.py' \
  -not -path '*/tests/*' | pysum --pipe # ad-hoc scope without .projlist
```

---

## 3. `py-diagram --format token` — Class Topology, Best Per Token

**What it does:** class hierarchy with inheritance chains, typed fields, and
method signatures in the most compact text form. Four output formats are
available; `token` is the correct choice for LLM context in nearly every case.

**What to look for in the output:**

_Interface / Protocol compliance:_

```
[CLASS] UserRepository(Protocol)
    METHODS: find_by_id(...), save(...), delete(...)

[CLASS] PostgresUserRepository
    METHODS: find_by_id(...), save(...)       ← delete() is missing
```

A side-by-side method list makes gaps immediately visible without reading
source. Run this before and after any refactor that touches an abstract
interface.

_Field shapes on data models — fixes pysum's blind spot:_

```
[CLASS] CreateOrderRequest(BaseModel)
    FIELDS: customer_id:str, items:list[OrderItem], discount:float | None
```

Pydantic models, dataclasses, and attrs classes expose their fields here
but not in `pysum`.

_Composition relationships:_

```
[RELATIONSHIPS]
  OrderResponse --composes--> OrderItem (items)
  InvoiceResponse --composes--> OrderResponse (order)
```

Composition edges reveal which response objects nest which sub-objects —
useful when tracing serialisation chains.

**Known limitation — structural typing:** Python Protocol is satisfied by
structural match, not explicit inheritance. A class that implements a Protocol
without declaring `(SomeProtocol)` in its definition will not have an
inheritance arrow in the diagram. Verify compliance by comparing method lists
manually.

**Format selection:**

| Goal                        | Format                              |
| --------------------------- | ----------------------------------- |
| LLM context window          | `token`                             |
| GitHub PR / Obsidian / docs | `mermaid`                           |
| Graphviz PNG pipeline       | `dot`                               |
| Never use for LLM           | `dot` (verbose, low signal density) |

**Typical usage:**

```bash
py-diagram --format token                          # whole project
py-diagram --format token --source src/models.py   # single file
py-diagram --format token --skip tests migrations  # exclude noise
py-diagram --format token > arch.txt               # save for reuse across turns
py-diagram --format mermaid > docs/architecture.md # for human-readable docs
```

---

## 4. `callgraph` — Runtime Behaviour, Only With a Probe Script

**What it does:** traces an actual execution and produces a JSON report of
every function called, with call count, total time, and caller list, sorted
by call frequency.

**The cardinal rule:** `callgraph` must be pointed at a script that
exercises the code path you care about. Pointing it at a server entry point
(`main.py`, `app.py`, `manage.py`) captures only module-load time — the
output will be hundreds of stdlib import records and no traces of business
logic.

**How to write a probe script:**

A probe script is a small, self-contained Python file that:

1. Sets up the minimum required state (in-memory store, mocked external calls)
2. Calls the function or code path you want to trace
3. Exits cleanly

```python
# probe.py — adapt package names and classes to the target codebase
import os
os.environ.setdefault("EXTERNAL_API_KEY", "fake-key")  # prevent real API calls

from unittest.mock import patch
from mypackage.repository import InMemoryRepository
from mypackage.service import OrderService

repo = InMemoryRepository()
service = OrderService(repo)

# Mock I/O or network calls that would block or fail
with patch("mypackage.notifications.send_email"):
    service.place_order(customer_id="c1", items=[{"sku": "A", "qty": 2}])
    service.cancel_order(order_id="o1")
```

**Running callgraph against the probe:**

```bash
callgraph --target probe.py \
          --include 'mypackage.*' \
          --json report.json \
          --mermaid hotspots.md
```

**Filtering the JSON output** — raw output contains hundreds of stdlib records:

```bash
python3 -c "
import json
d = json.load(open('report.json'))
# Replace 'mypackage' with the actual top-level package name
app = [r for r in d['call_graph'] if r['name'].startswith('mypackage.')]
top = sorted(app, key=lambda r: r['call_count'], reverse=True)
print(json.dumps(top[:20], indent=2))
"
```

**What the output tells you:**

- `call_count` — which functions are on the critical path; primary target for
  optimisation
- `time_total` — where wall-clock time is actually spent; may differ sharply
  from call_count (one slow I/O call outweighs a thousand fast dict lookups)
- `callers` — who calls this function; reveals fan-in and coupling

**When callgraph is worth the effort:**

- Investigating a performance regression — `time_total` isolates the slow layer
- Validating a refactor preserved call patterns — run before and after, diff
  the filtered JSON
- Understanding a multi-step workflow where static reading loses the thread
  (middleware chains, plugin dispatch, recursive processing)
- Confirming a code path believed to be dead is never actually called

**When to skip callgraph:**

- The question is structural ("what are the fields?", "what does this import?")
  — static tools answer faster and cheaper
- External dependencies cannot be easily mocked — the probe is harder to write
  than reading the source
- The project has no `.venv` or requires complex environment setup to import

---

## 5. `lsproj` — Scoping Gate

**What it does:** emits a filtered file list based on the `.projlist`
whitelist and `.gitignore` exclusions in the current directory. Designed to
be piped into other tools.

**Why this matters:** most projects contain files you never want in an LLM
context — test fixtures, database migrations, generated protobuf stubs,
vendored dependencies, build artefacts. Without scoping, `pysum` or `repo-map`
run on a full repository will include all of this noise.

**`.projlist` syntax:**

```
src/**/*.py        # recursive glob
*.py               # match by filename anywhere in the tree
!tests/fixtures/   # negation — exclude even if whitelisted
# comment          # ignored
```

**Typical usage:**

```bash
lsproj                              # verify what is currently in scope
lsproj | pysum --pipe               # summarise only whitelisted files
lsproj | xargs wc -l                # line count of in-scope files
lsproj -e '*.md'                    # ad-hoc extra exclusion for this run
```

**When `.projlist` does not exist:** fall back to explicit `find` scoping:

```bash
find src/ -name '*.py' \
  -not -path '*/migrations/*' \
  -not -path '*/tests/*' | pysum --pipe
```

**Note on non-Python files:** `lsproj` will list any file matching the
whitelist (`.ts`, `.yaml`, `.svelte`, etc.) but `pysum` and `py-diagram` are
Python-only tools and silently skip non-Python files. Use `lsproj` output as
a reference, but pipe only `.py` files into Python-specific tools.

---

## 6. Tools to Use Rarely or Skip

### `gen-diagram` — Graphviz DOT output

Produces verbose DOT syntax. A 20-class project generates ~200 lines at
~1 600 tokens — the same information that `py-diagram --format token`
delivers in ~600 tokens. Never feed DOT output to an LLM.

Use only when you need a rendered PNG for human-facing documentation:

```bash
gen-diagram . --skip tests | dot -Tpng -o docs/architecture.png
```

### `py-diagram --format mermaid`

Carries the same information as `--format token` at approximately 1.5×
the token cost due to Mermaid syntax overhead. Reserve for output that
a human will read (GitHub PRs, Obsidian notes, wiki pages).

### `callgraph` without a probe script

Running `callgraph` against a server entry point captures only module-load
traces. The output is dominated by stdlib import machinery (`importlib`,
`FileFinder`, `SourceFileLoader`) with `call_count: 1` for every application
class. No business logic is traced. Costs 15 000+ tokens if fed unfiltered.

---

## Recipes for Common Tasks

### Cold start — understanding an unknown codebase

```bash
repo-map --skip tests migrations
# Identify: largest files, class counts, public surface.
# Zoom in on the most interesting module:
pysum src/the_module.py
```

### Before modifying a class

```bash
# 1. Locate the file
repo-map | grep -A3 "ClassName"

# 2. Read imports and signatures
pysum src/that_file.py

# 3. If the class uses Pydantic / dataclass / attrs
py-diagram --format token --source src/that_file.py
```

### Verifying an interface is fully implemented

```bash
py-diagram --format token --source src/interfaces.py
# Compare Protocol method list against concrete class method list.
# Any method present in Protocol but absent in the concrete class is a gap.
```

### Dependency audit before a refactor

```bash
pysum src/the_module_to_change.py    # what does it depend on? (fan-out)
grep -r "from src.the_module" src/   # what depends on it?    (fan-in)
```

### Understanding data shapes in schema-heavy code

```bash
py-diagram --format token --source src/schemas.py
# pysum shows these classes as empty — py-diagram shows all typed fields.
```

### Investigating a performance problem

```bash
# 1. Write probe.py exercising the slow path (see section 4)
callgraph --target probe.py --include 'mypackage.*' --json report.json

# 2. Find the slowest functions
python3 -c "
import json
d = json.load(open('report.json'))
app = [r for r in d['call_graph'] if r['name'].startswith('mypackage.')]
slow = sorted(app, key=lambda r: r['time_total'], reverse=True)
print(json.dumps(slow[:10], indent=2))
"
```

### Generating architecture documentation

```bash
# Mermaid — paste into GitHub or Obsidian
py-diagram --format mermaid --skip tests > docs/architecture.md

# PNG — for wikis or presentations
gen-diagram . --skip tests | dot -Tpng -o docs/architecture.png
```

---

## 7. Token-Efficient Usage for LLM Agents

This section is specifically for an LLM agent operating under a context
budget. Follow these rules to extract maximum signal per token spent.

### Rule 1: Never open a file before running repo-map

Reading a source file costs 5–50× more tokens than the equivalent `repo-map`
entry. Always establish location and shape first:

```bash
repo-map --skip tests migrations    # ~400 tokens for a 20-file project
```

Only open a specific file after `repo-map` confirms it contains what you need.

### Rule 2: Use py-diagram token instead of pysum for class-heavy files

`pysum` on a file full of Pydantic models or dataclasses returns empty class
bodies — wasted tokens. `py-diagram --format token` on the same file returns
all fields and method signatures. When in doubt about which to use:

- File contains mostly functions → `pysum`
- File contains mostly classes with fields → `py-diagram --format token`
- Mixed → `py-diagram --format token` (it covers both)

### Rule 3: Scope before summarising

Running `pysum` or `repo-map` on an unscoped directory includes tests,
migrations, and vendored code. These consume tokens without adding signal.
Always scope first:

```bash
# Preferred — use whitelist if it exists
lsproj | pysum --pipe

# Fallback — explicit exclusion
find src/ -name '*.py' -not -path '*/tests/*' | pysum --pipe
```

### Rule 4: Save structural context across turns

When a task spans multiple turns, write the structural summary to a file on
the first turn and reference it on subsequent turns rather than re-running
the tools:

```bash
# Turn 1 — pay the cost once
repo-map --skip tests > .context/map.txt
py-diagram --format token --skip tests >> .context/map.txt

# Turn 2+ — read the saved file, cost is just the file read
```

### Rule 5: Filter callgraph output before reading

The raw `report.json` from `callgraph` is ~2 000 lines and 16 000 tokens.
Never read it directly. Always filter to the application package before
consuming:

```bash
python3 -c "
import json
d = json.load(open('report.json'))
app = [r for r in d['call_graph'] if r['name'].startswith('mypackage.')]
top = sorted(app, key=lambda r: r['call_count'], reverse=True)
print(json.dumps(top[:15], indent=2))
"
# Result: ~400 tokens instead of 16 000
```

### Rule 6: Zoom in surgically, not broadly

Avoid running `pysum src/` when you only need one module. The cost scales
linearly with files included:

```bash
# Too broad when you only need one class
pysum src/

# Surgical — costs ~5× less
pysum src/the_specific_module.py
```

### Rule 7: Combine repo-map + py-diagram token as the default context pair

When a task requires understanding both structure and types, these two tools
together give near-complete project knowledge at the lowest combined token
cost:

```bash
repo-map --skip tests migrations    # ~400 tokens  — location + structure
py-diagram --format token \
  --skip tests migrations           # ~600 tokens  — types + fields + interfaces
# Total: ~1 000 tokens
# Equivalent to one medium source file read
```

Reach for `pysum` only when you need the import graph specifically — otherwise
the `repo-map` + `py-diagram` pair is more complete at lower cost.

### Token cost escalation order

Stop at the first level that answers the question:

```
1. repo-map                              ~400 tokens   structural questions
2. py-diagram --format token             ~600 tokens   type/field questions
3. pysum <single file>                   ~200 tokens   imports of one file
4. pysum src/                          ~1 200 tokens   full dependency graph
5. read <single file>                  ~500–5 000      last resort, specific logic
6. callgraph (filtered, top 15)          ~400 tokens   runtime questions only
```

Never skip to level 5 (reading source) when levels 1–3 have not been
exhausted. The combination of `repo-map` + `py-diagram` at levels 1–2
answers the majority of architecture and refactoring questions.

---

## Token Budget Reference

| Tool + flags                               | Small project (~20 files) | Token estimate |
| ------------------------------------------ | ------------------------- | -------------- |
| `repo-map`                                 | ~60 lines                 | ~400           |
| `pysum`                                    | ~150 lines                | ~1 200         |
| `py-diagram --format token`                | ~80 lines                 | ~600           |
| `py-diagram --format mermaid`              | ~120 lines                | ~900           |
| `gen-diagram`                              | ~200 lines                | ~1 600         |
| `callgraph --json` filtered to app package | ~50 lines                 | ~400           |
| `callgraph --json` unfiltered              | ~2 000 lines              | ~16 000        |

**Rule of thumb:** `repo-map` + `py-diagram --format token` together cost
roughly the same as `pysum` alone, but deliver more — signatures _and_
typed fields. Default to this pair unless you specifically need the import
graph, which only `pysum` provides.
