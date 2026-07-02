# Test baseline — freeze-2026-07

Snapshot of test-suite state at the moment development was paused. **No fixes were
applied**; failures are recorded as-is.

- Freeze date: 2026-07-03
- Tag: `freeze-2026-07`
- Preceding commits: `6fd6269` (chore: docs) → `e746622` (chore: housekeeping) → this file's commit

## Convention

For every component, tests were invoked via `python -m pytest tests -q` from the
component's own `.venv`. `python -m pytest` (rather than `pytest` script) was
used to avoid stale shebangs left behind by past directory renames — the venvs
themselves are untouched.

Two exceptions are noted in the table (`⚠`) — see "Notes" below.

## Untracked test files at freeze

**None found.** `git ls-files -o --exclude-standard | grep -Ei 'test|fixture' | wc -l`
returned `0`. The "commit untracked test suites as-is" step from the freeze plan
was therefore skipped.

## Baseline table

| Component | Command | Collected | Passed | Failed | Errored | xfail / xpass | Notes |
|---|---|---:|---:|---:|---:|---|---|
| kuchnie_core (root) | `.venv/bin/python -m pytest tests -q` | 663 | 663 | 0 | 0 | 0 / 0 | clean |
| catalog | `../.venv/bin/python -m pytest tests -q` ⚠ | 227 | 227 | 0 | 0 | 0 / 0 | own `.venv` has no `pytest` installed (see Notes N1); used root venv as fallback |
| kitchen-cam | `.venv/bin/python -m pytest tests -q` | 340 | 292 | 0 | 0 | 35 xfail / 13 xpass | clean; xpasses may deserve review post-freeze |
| kitchen-erp | `.venv/bin/python -m pytest tests -q --continue-on-collection-errors` ⚠ | 53 + 1 collection-error module | 38 | 3 | 13 (+1 collection) | 0 / 0 | see N2, N3 |
| krono-compositor-mvp | `.venv/bin/python -m pytest tests -q` | 9 | 7 | 2 | 0 | 0 / 0 | see N4 |
| home-builder-adapter | `.venv/bin/python -m pytest tests -q` | 0 | 0 | 0 | 0 | 0 / 0 | see N5 |

Raw pytest logs are kept under `/tmp/freeze-tests/*.log` on the freeze machine
(not committed).

## Notes

### N1 — `catalog/.venv` missing pytest
`catalog/.venv/bin/python -c "import pytest"` → `ModuleNotFoundError: No module
named 'pytest'`. The venv itself works (Python 3.13.7 symlink is valid) but
pytest was never installed into it. All catalog tests were collected/run via
the root `.venv` and passed. **Not fixed.**

### N2 — kitchen-erp collection failure
`tests/test_rules_engine.py` fails to import:

```
ImportError: cannot import name 'HARDWARE_RULES' from
  'kitchen_erp.core.rules_engine'
```

Test module was not updated after the ADR-011 rename `kitchen-app/` →
`kitchen-erp/` / package unification. Without `--continue-on-collection-errors`
the whole suite is aborted. **Not fixed.**

### N3 — kitchen-erp runtime failures/errors (13 errors + 3 failures)
Most errors are SQLAlchemy-related in `tests/test_bom_generator.py` and
`tests/test_integration_bom.py` (truncated summary: `sqlalchem…`). One
integration test fails: `test_no_back_panel_for_oven_cabinet`. Full summary
was captured to `/tmp/freeze-tests/kitchen-erp-full.log`. **Not fixed.**

### N4 — krono-compositor-mvp failures
- `tests/integration/test_pipeline_integration.py::test_full_pipeline_with_real_files` — failed
- `tests/performance/test_performance.py::test_4k_rendering_performance` — failed (perf test; environment-sensitive)

**Not fixed.**

### N5 — home-builder-adapter has no test sources
`home-builder-adapter/tests/` contains only `__init__.py` plus a stale
`__pycache__/` directory holding 23 orphaned `.pyc` files from a previous life
(cabinet_construction, config_parser, kitchen, l_shape, manifest_*, wall_*,
etc.).

Git history explains this: commit `8da1a61 "Phase d"` deleted all
`kitchen-plugin/tests/*.py` files (proof: `git log --diff-filter=D
--name-status --all -- 'kitchen-plugin/tests/'`). During the subsequent
`kitchen-plugin/` → `home-builder-adapter/` rename (ADR-009) only the empty
`tests/__init__.py` shell was carried over. The `.pyc` files under
`__pycache__/` are stale bytecode.

**Interpretation:** the component effectively has no test suite at freeze
time. This is preserved as-is; no attempt was made to resurrect the deleted
`.py` sources. If desired post-freeze, they can be recovered from any
`kitchen-plugin/tests/*.py` blob prior to `8da1a61`.

## Flagged during rescue (see also `attic/README.md`)

- `attic/kitchen-plugin/` — a byte-identical resurrection of the archived
  `home-builder-adapter/docs/archive/wall-centric-model.md` was found at the
  pre-rename path `kitchen-plugin/docs/wall-centric-model.md`, and the archive
  copy had been deleted in the working tree. Flagged as **"resurrected
  duplicate, suspected session accident"**. Archive was restored;
  `kitchen-plugin/` moved (not deleted) to `attic/`.
- `attic/all-signatures.md`, `attic/evidence-01-tree.txt` — regenerable
  build/audit dumps found untracked at repo root.

## Deliberately uncommitted at freeze — inventory

Nothing. After the two chore commits (`6fd6269`, `e746622`) `git status
--porcelain` was empty. No file was intentionally left dirty.

`git status --ignored=matching --porcelain` still lists the expected
per-component `.venv/`, `__pycache__/`, `.pytest_cache/`, `.DS_Store`,
`node_modules/`, `catalog/db/catalog.db*`, `kitchen-erp/database.db`,
`kitchen-erp/htmlcov/` — all covered by `.gitignore` rules.
