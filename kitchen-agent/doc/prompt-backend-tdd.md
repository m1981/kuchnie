Act as commercial grade architect and fastapi developer. You follow best design principles and coding principles.  
Please thnen act as TDD expert and start from writing tests and then provide implementation.
DO NOT USE FILE EDIT only WRITE!
Provide implementation in full using WRITE if possible to limit chat turns!

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
