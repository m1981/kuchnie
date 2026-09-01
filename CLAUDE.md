# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

> **Read `AGENTS.md` first — it is the canonical agent guide for this repo.**
> **Since 2026-09-01:** the truth-ledger v1 installation is FROZEN (`.truth/FROZEN.md`); the live verifier is `scripts/tl2` (truth-ledger2 installation #2) — see AGENTS.md's first block for the two-repository contract.
> **Session start:** open `STATUS.md` (generated dashboard, five PM
> questions — §3 names the next work and its start commands), then
> `scripts/truth ready`. **Vocabulary:** any unknown term or letter code
> (L/G/M/R/UC/P families) → `docs/GLOSSARY.md`; if it's not there, ask —
> never invent a meaning.
> **Work-finding precedence:** use `scripts/truth ready`, not `bd ready`. It is
> `bd ready` filtered by the truth ledger's premise validity — issues standing
> on stale/diverged facts are HELD. See `docs/beads-integration-guide.md`.
> **New feature discussed?** Before designing or coding, follow AGENTS.md →
> "Feature specs": find/create the spec per `docs/spec-convention.md`, wire
> ledger ids, then gate with `bash scripts/spec-health.sh`.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->


## Build & Test

```bash
# Suites (run from the component dir; root .venv covers core/cam/adapter):
cd kuchnie-core          && ../.venv/bin/python -m pytest tests/ -q   # ~700 tests
cd kitchen-cam           && ../.venv/bin/python -m pytest tests/ -q
cd home-builder-adapter  && .venv/bin/python -m pytest tests/ -q      # own venv (uv sync --extra dev)
cd kitchen-erp           && .venv/bin/python -m pytest tests/ -q      # own venv

# Quality gates (repo root):
bash scripts/spec-health.sh      # specs vs ledger — must be 0 failures
bash scripts/doc-health.sh       # live markdown corpus
bash scripts/exercise-gate.sh    # flagship e2e outputs == committed baseline
bash scripts/session-close.sh    # end-of-session survival gate (docs/development-process.md)

# Pipeline regression harness (after any decomposer/extraction change):
cd exercises/walking-skeleton-d60
/Applications/Blender.app/Contents/MacOS/Blender --background --python blender_leg.py
/path/to/repo/.venv/bin/python run_production_leg.py   # diff generated/ vs reference/

# New e2e exercise (golden-first, docs/e2e-exercise-convention.md):
.venv/bin/python exercises/harness/scaffold.py <scenario-name>
.venv/bin/python exercises/harness/runner.py <scenario-name> [--strict]  # one-command run
.venv/bin/python -m pytest exercises/harness/tests -q   # harness self-tests
```

Blender 5.1.2 lives at `/Applications/Blender.app`; home_builder_5 is driven
headless via `addon_utils.enable` + its type classes, never the modal
operators (see `home-builder-adapter/docs/hb5-headless-scripting.md`).

## Architecture Overview

See `AGENTS.md` (canonical) — six components around the `kuchnie_core`
domain hub; scope authority is `docs/specs/process-coverage.md` (L1 map).

## Conventions & Patterns

See `docs/spec-convention.md` (ledger-wired specs), `docs/adr/` (decisions;
accepted ADRs are immutable — write a superseding ADR), and
`docs/file-naming-convention.md`.

## Reading rules — bounded reads (QB-013)

Mirrored from `AGENTS.md`; kept here too because this file is not
template-managed and so cannot be overwritten by a `copier update`.

**Never let a bounded read support an unbounded claim.** If the conclusion says
*never*, *none*, *empty*, *all* or *does not exist*, the read behind it must be
unfiltered. Concretely, from three same-day failures:

- Verify by **re-query**, never by reading a command's output. A `tail -1` on a
  multi-id `bd close` hid a silent failure and left a P1 item blocked.
- Before asserting absence, **read the whole block** — a `grep -A 4` on a YAML
  trigger produced a published claim that a gate "has never run" when it runs
  on every push.
- Anchor greps on the **field or column**, never the bare substring, and run a
  **positive control** you know matches. `grep -c 'unverified'` matched claim
  text, not status, and mis-reported a gate for weeks.

Full incident record: `docs/question-bank.md` QB-013, which generalises QB-011.
The rule is also stored via `bd remember --key bounded-reads`, so it arrives
through `bd prime` at session start rather than depending on this file being
opened.
