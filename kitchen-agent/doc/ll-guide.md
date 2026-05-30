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
requires. Reading bodies (`cat`, `read`) is the last resort, not the first.

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
        Richest class view per token. Fix for pysum's Pydantic/dataclass blind spot.

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
- A function that appears in many files under the same name → shared utility
  or potential coupling point

**Typical usage:**

```bash
repo-map                          # scan current directory
repo-map --root src/              # specific subtree
repo-map --skip tests migrations  # exclude noise directories
repo-map --show-imports           # add import lines when dependency overview matters
```

**When to stop here:** if your question is locating-class — "where does X
live?", "which file owns this?", "what is the public surface of module Y?" —
`repo-map` answers it without burning tokens on bodies or imports. Move to
`pysum` only when you need types or dependency information.

---

## 2. `pysum` — Imports + Full Typed Signatures

**What it does:** per-file Markdown code blocks with all imports and full
typed signatures. No function bodies.

**The import block is the high-value section.** Imports are the fastest way
to read a module's dependency graph without parsing code. Look for:

- A module importing from many other internal modules → high coupling, change
  risk radiates outward
- A lower-layer module (repository, storage) importing from a higher-layer
  module (exporter, presenter) → layer inversion, SRP violation
- Repeated identical imports across many files → candidate for a shared
  utility or injection point
- A very long single import line listing many names from one module → tight
  coupling to that module's internals

**Known blind spot:** `pysum` shows only method signatures, not field
definitions. Classes built with Pydantic `BaseModel`, `dataclasses`, or
`attrs` will appear as empty `pass` bodies. Always follow with
`py-diagram --format token` when the file is schema- or model-heavy.

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
method signatures. Four output formats available; `token` is the correct
choice for LLM context in nearly every case.

**What to look for in the output:**

_Interface / Protocol compliance:_

```
[CLASS] UserRepository(Protocol)
    METHODS: find_by_id(...), save(...), delete(...)

[CLASS] PostgresUserRepository
    METHODS: find_by_id(...), save(...)       ← delete() is missing
```

A side-by-side method list makes gaps immediately visible without reading
source. This is the primary use case — run it before and after any refactor
touching an abstract interface.

_Field shapes on data models (fixes pysum's blind spot):_

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
without inheriting from it will not have an inheritance arrow in the diagram.
Verify compliance by comparing method lists manually.

**Format selection:**

| Goal                        | Format                              |
| --------------------------- | ----------------------------------- |
| LLM context window          | `token`                             |
| GitHub PR / Obsidian / docs | `mermaid`                           |
| Graphviz PNG pipeline       | `dot`                               |
| Never use for LLM           | `dot` (verbose, low signal density) |

**Typical usage:**

```bash
py-diagram --format token                             # whole project
py-diagram --format token --source src/models.py      # single file
py-diagram --format token --skip tests migrations     # exclude noise
py-diagram --format token > arch.txt                  # save for reuse across turns
py-diagram --format mermaid > docs/architecture.md    # for human-readable docs
```

---

## 4. `callgraph` — Runtime Behaviour, Only With a Probe Script

**What it does:** traces an actual execution and produces a JSON report of
every function called, with call count, total time, and caller list, sorted
by call frequency.

**The cardinal rule:** `callgraph` must be pointed at a script that
exercises the code path you care about. Pointing it at a server entry point
(`main.py`, `app.py`, `manage.py`) captures only module-load time — you will
get hundreds of stdlib import records and zero traces of your business logic.

**How to write a probe script:**

A probe script is a small, self-contained Python file that:

1. Sets up the minimum required state (in-memory database, mocked external
   calls, test fixtures)
2. Calls the function or code path you want to profile
3. Exits cleanly

```python
# probe.py — template, adapt to your codebase
import os
os.environ.setdefault("EXTERNAL_API_KEY", "fake-key")   # prevent real calls

from unittest.mock import patch

# Import the real classes you want to trace
from mypackage.repository import InMemoryRepository
from mypackage.service import OrderService

# Minimal setup
repo = InMemoryRepository()
service = OrderService(repo)

# Mock any I/O or external dependencies that would block or error
with patch("mypackage.notifications.send_email"):
    # Exercise the path you care about
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
# Replace 'mypackage' with your actual top-level package name
app = [r for r in d['call_graph'] if r['name'].startswith('mypackage.')]
top = sorted(app, key=lambda r: r['call_count'], reverse=True)
print(json.dumps(top[:20], indent=2))
"
```

**What the output tells you:**

- `call_count` — which functions are called most often; hotspots for
  optimisation and for understanding the critical path
- `time_total` — where wall-clock time is actually spent; may differ from
  call_count (one slow DB call beats a thousand fast dict lookups)
- `callers` — who calls this function; tells you fan-in, helps locate
  coupling

**When callgraph is worth the effort:**

- Investigating a performance regression — `time_total` isolates the slow layer
- Validating a refactor preserved call patterns — run before and after, diff
  the JSON
- Understanding a complex multi-step workflow where static reading loses the
  thread (e.g. middleware chains, plugin dispatch, recursive processing)
- Confirming that a code path you think is dead actually is never called

**When to skip callgraph entirely:**

- Your question is structural ("what are the fields?", "what does this
  import?") — static tools are faster and cheaper
- You cannot easily mock the external dependencies (database, third-party API,
  file system with side effects) — the probe will be harder to write than just
  reading the code
- The codebase has no `.venv` or the target requires complex environment setup

---

## 5. `lsproj` — Scoping Gate

**What it does:** emits a filtered file list based on the `.projlist`
whitelist and `.gitignore` exclusions in the current directory. Designed to
be piped into other tools.

**Why this matters:** most Python projects contain files you never want in
an LLM context — test fixtures, database migrations, generated protobuf
stubs, vendored dependencies, build artefacts. Without scoping, `pysum` or
`repo-map` on a full repository will include all of this noise, consuming
tokens and burying signal.

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
find src/ -name '*.py' -not -path '*/migrations/*' \
          -not -path '*/tests/*' | pysum --pipe
```

**Note on non-Python files:** `lsproj` will list any file matching the
whitelist (`.ts`, `.svelte`, `.yaml`, etc.) but `pysum` and `py-diagram` are
Python-only and will silently skip non-Python files. Use `lsproj` output as
a reference, but pipe only `.py` files into Python-specific tools.

---

## 6. Tools to Use Rarely or Skip

### `gen-diagram` — Graphviz DOT output

Produces verbose DOT syntax. A 20-class project generates ~200 lines of
text at ~1 600 tokens — the same structural information that `py-diagram
--format token` delivers in ~600 tokens.

Use only when you need a rendered PNG for human-facing documentation:

```bash
gen-diagram . --skip tests | dot -Tpng -o docs/architecture.png
```

Never feed DOT output directly to an LLM. Use `--format token` instead.

### `py-diagram --format mermaid`

Carries the same information as `--format token` at approximately 1.5×
the token cost due to Mermaid syntax overhead. Reserve for output that
a human will read (GitHub PRs, Obsidian notes, wiki pages).

### `callgraph` without a probe script

Running `callgraph` against a server entry point or application bootstrap
captures only module-load traces. The output will be dominated by stdlib
import machinery (`importlib`, `FileFinder`, `SourceFileLoader`) with
`call_count: 1` for every application class. This tells you nothing about
runtime behaviour and costs 15 000+ tokens if fed unfiltered to an LLM.

---

## Recipes for Common Tasks

### Cold start — understanding an unknown codebase

```bash
repo-map --skip tests migrations
# Read the output. Identify: largest files, class counts, public surface.
# Then zoom in on the most interesting module:
pysum src/the_interesting_module.py
```

### Before touching a class

```bash
# 1. Find which file owns it
repo-map | grep -A3 "ClassName"

# 2. Get full signatures and what the file imports
pysum src/that_file.py

# 3. If the class is a model or has fields
py-diagram --format token --source src/that_file.py
```

### Verifying an interface is fully implemented

```bash
py-diagram --format token --source src/interfaces.py
# Compare Protocol method list against concrete class method list.
# Any method in Protocol not in the concrete class is a gap.
```

### Dependency audit before a refactor

```bash
pysum src/the_module_to_change.py   # what does it depend on?
grep -r "from src.the_module" src/  # what depends on it?
# The grep gives fan-in; pysum imports give fan-out.
```

### Understanding data shapes — Pydantic / dataclass heavy code

```bash
py-diagram --format token --source src/schemas.py
# pysum would show all classes as empty — py-diagram shows all fields.
```

### Investigating a performance problem

```bash
# 1. Write probe.py that exercises the slow path (see section 4)
# 2. Run:
callgraph --target probe.py --include 'mypackage.*' --json report.json
# 3. Find the slow functions:
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

### Token-budget-critical context preparation

```bash
# Smallest useful structural view of the whole project
repo-map --skip tests migrations > context.txt

# Add class topology without blowing the budget
py-diagram --format token --skip tests >> context.txt

# Total: ~1 100 tokens for a 20-file project
```

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
roughly the same as `pysum` alone, but give you more — signatures _and_
fields. Use both when the budget allows.
