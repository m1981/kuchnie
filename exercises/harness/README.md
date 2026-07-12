# exercises/harness

Shared code for golden-first e2e exercises. The convention (principles,
phases, directory contract, golden CSV schema) lives in
**`docs/e2e-exercise-convention.md`** — read that first.

```bash
.venv/bin/python exercises/harness/scaffold.py <scenario-name>   # new exercise
.venv/bin/python -m pytest exercises/harness/tests -q            # self-tests
```

Modules: `gaps` (GAP logging), `golden` (panels.csv + grain-aware diff),
`writers` (rozrys/BOM/CNC), `hb5` (Blender-only bootstrap + workarounds),
`scaffold` (templates). The pre-harness exercises `walking-skeleton-d60/`
and `e2e-d60-legrabox/` are claim-watched artifacts — do not retrofit them.
