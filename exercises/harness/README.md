# exercises/harness

Shared code for golden-first e2e exercises. The convention (principles,
phases, directory contract, golden CSV schema) lives in
**`docs/e2e-exercise-convention.md`** — read that first.

```bash
.venv/bin/python exercises/harness/scaffold.py <scenario-name>   # new exercise
.venv/bin/python exercises/harness/runner.py <scenario-name>     # one-command run
.venv/bin/python -m pytest exercises/harness/tests -q            # self-tests
```

Runner options: `--strict` (failures exit nonzero + KUCHNIE_STRICT=1 in the
legs), `--skip-blender` / `--skip-inspect` (fast lane for decomposer-only
changes). Every run writes `generated/run-manifest.json` (repo SHA, Blender
version, hb5 SHA, per-step exits).

Environment (see `config.py`): `KUCHNIE_HB5_PATH` (home_builder_5 checkout,
default: sibling of this repo), `BLENDER_BIN`, `KUCHNIE_STRICT=1`.

Modules: `config` (env-overridable paths), `labels` (single-source domain
labels), `gaps` (GapLog: gap = finding, fail = strict-escalatable failure),
`golden` (panels.csv + grain-aware, closest-first diff), `ops`
(machining-ops oracle — the G8 catcher), `hardware` (accessory oracle — the
G13 meter), `writers` (rozrys/BOM/CNC), `hb5` (Blender-only bootstrap +
workarounds), `runner`, `scaffold`. The pre-harness exercises
`walking-skeleton-d60/` and `e2e-d60-legrabox/` are claim-watched artifacts
— do not retrofit them.

Deliberate trade-off: the harness is consumed via `sys.path` from the legs
(no pyproject/install step) — exercises stay runnable from a bare checkout
inside Blender's bundled Python, which cannot pip-install into a venv.
