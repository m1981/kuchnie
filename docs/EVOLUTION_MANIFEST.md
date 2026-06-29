# Monorepo Evolution Manifest

Generated: 2026-06-29  
Sources: git log (177 commits) + zsh_history (11,638 entries)

---

## Definitive Cutoff Dates

| Project | Cutoff Date | Status | Last Signal | Days Stale |
|---------|------------|--------|-------------|------------|
| **kuchnie-core** | — | 🟢 ACTIVE | Jun 29: git + make server | 0 |
| **catalog** | — | 🟢 ACTIVE | Jun 29: git commit | 0 |
| **kitchen-agent** | — | 🟢 ACTIVE | Jun 27: cd into (external repo) | 2 |
| **kitchen-cad** | Jun 28 | 🟡 CUT | Jun 28: doc-only commit, shell last Jun 23 | 1 |
| **kitchen-plugin** | Jun 24 | 🟡 CUT | Jun 24: gitignore commit, only 1 shell touch ever | 5 |
| **krono-compositor** | Jun 23 | 🟡 CUT | Jun 23: docs restructure, Blender last Jun 22 | 6 |
| **kitchen-app** | May 12 | 🔴 DEAD | May 12: pricing fix (cosmetic later) | 48 |

## Shell Activity Patterns

The zsh_history reveals **how** each project was used — not just when:

```
kitchen-agent    ████████████████████████████████████████ 40 cd's  ← daily driver, human+agent
kitchen-cad      ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  8 cd's  ← burst Jun 17-23, then agent
krono-compositor ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  6 cd's  ← two sprints
kitchen-app      ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  3 cd's  ← created then ignored
kitchen-plugin   █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  1 cd    ← agent-only (mkdir+cd)
catalog          █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  1 cd    ← new, agent-driven
```

### Key Insight: Agent-Driven vs Human-Driven

| Project | Shell Touches | Git Commits | Pattern |
|---------|--------------|-------------|---------|
| kitchen-agent | 40 | 0* | **Human daily driver** (external repo) |
| kitchen-cad | 8 | 16 | **Human burst → agent takeover** |
| krono-compositor | 6 | 59 | **Human sprints → agent commits** |
| kitchen-app | 3 | 53 | **Human created → agent bulk commits** |
| kitchen-plugin | 1 | 41 | **100% agent-created** (mkdir+cd only) |
| catalog | 1 | 24 | **Agent-created** (make dev once) |

*kitchen-agent migrated to external repo Jun 24

**Pattern**: Newer projects (kitchen-plugin, catalog) are almost entirely agent-created — you start a pi session, give it a system prompt, and the agent does the rest. Older projects (kitchen-app, krono-compositor) show more human shell activity.

### The "pi --system-prompt" Sessions

Your shell history shows **when you launched coding agent sessions**:

```
Jun 22 01:03  "Act as smart commercial grade blender plugin coding agent"
              → Created kitchen-plugin entirely in this session

Jun 21 22:27  "Act as commercial grade coding agent"  (145137s = 40h session!)
              → krono-compositor work + kitchen-cad

Jun 25 01:13  "PDF catalogs scraping agent with cabinet making terminology"
              → Material data extraction for catalog

Jun 26 00:15  "Act as commercial grade coding agent"
              → catalog work

Jun 29 00:40  "Act as commercial grade coding agent"
              → kuchnie-core + catalog (current session)
```

## Project Timeline (Git + Shell Combined)

```
2026-05          2026-06
May 8    May 25  Jun 17  Jun 22  Jun 25  Jun 29
  │        │       │       │       │       │
  ▼        ▼       ▼       ▼       ▼       ▼
  kitchen  krono   kitchen kitchen kuchnie catalog
  -app     -comp   -cad    -plugin -core
  (5d)     (2d)    (11d)   (2d)    (4d)    (3d)

  ←─human─→←human→←burst─→←agent→←agent→←agent→
   sprint   sprint  +agent  only    only    only
   3 cd's   6 cd's  8 cd's  1 cd   via     1 cd
                                        Makefile
```

## Detailed Cutoff Analysis

### kitchen-app — CUTOFF: May 12, 2026
```
May  8 20:42  cd kitchen-app           ← created
May  8 21:02  uv add reflex            ← bootstrapped
May  8-12     53 git commits           ← sprint
May 12        last real code           ← STOPPED
Jun  1 14:25  cd kitchen-app           ← looked, no changes
Jun 18        docs archived            ← acknowledged stale
Jun 19        Prettier format          ← cosmetic only
Jun 23 20:27  cd kitchen-app           ← looked again, still nothing
```
**Verdict**: 5-day sprint, then abandoned. 3 shell touches after stopping = "checking if I should revive it" visits.

### krono-compositor-mvp — CUTOFF: June 23, 2026
```
May 25 20:12  cd krono-compositor      ← created
May 25-26     gen_kitchen.py × 8 runs  ← Sprint 1 (heavy Blender)
Jun 19 21:46  cd krono-compositor      ← revisit
Jun 21 22:24  cd krono-compositor      ← Sprint 2 starts
Jun 21 23:44  blender                  ← GUI session
Jun 22 01:02  git clone archimesh      ← exploring extensions
Jun 22 23:54  blender --background     ← CLI rendering
Jun 23 03:12  Blender CLI export       ← last Blender run
Jun 23 15:45  docs restructure         ← last git commit
```
**Verdict**: Two distinct sprints. Sprint 1 (May 25-26) = heavy gen_kitchen.py. Sprint 2 (Jun 21-23) = Blender CLI + DDD refactor. Then silence.

### kitchen-cad — CUTOFF: June 28, 2026
```
Jun 17 13:01  cd kitchen-cad           ← created
Jun 17-18     source code + tests      ← initial build
Jun 19 20:18  cd kitchen-cad           ← continued
Jun 21 22:23  cd kitchen-cad           ← continued
Jun 22 01:59  cd kitchen-cad           ← continued
Jun 23 16:50  cd kitchen-cad           ← screenshots added
Jun 23 20:23  cd kitchen-cad           ← last shell touch
Jun 24        agent: 5 new configs     ← agent took over
Jun 28        agent: dimension specs   ← last commit (doc-only)
```
**Verdict**: Human burst Jun 17-23 (8 shell touches), then agent continued docs. Code frozen since Jun 24. The Jun 28 commit is doc refinement, not code.

### kitchen-plugin — CUTOFF: June 24, 2026
```
Jun 22 01:02  mkdir + cd kitchen-plugin ← ONLY shell touch
Jun 22 01:03  pi --system-prompt "blender plugin agent" ← entire project created by agent
Jun 22-24     41 git commits            ← all agent-driven
Jun 23 03:12  Blender CLI last run
Jun 24        last git commit
```
**Verdict**: 100% agent-created. You started a pi session with "blender plugin coding agent" and the agent built the entire project. Only 1 shell command (mkdir+cd). This is the most agent-native project.

### catalog — CUTOFF: not yet (ACTIVE)
```
Jun 26 01:37  pnpm catalog:dev          ← first dev server
Jun 26 01:46  cd catalog                ← only shell touch
Jun 26 02:41  make dev (last)           ← dev server
Jun 26-29     24 git commits            ← active development
```
**Verdict**: Born 3 days ago, actively evolving. Agent-driven (1 shell touch).

## LLM Context Recommendations

Feed this into your LLM system prompt:

```
## Project Freshness (verified via git + shell history)

ACTIVE (trust docs):
- kuchnie-core: last work today. Canonical engine.
- catalog: last work today. FastAPI catalog service.

CUTOFF (verify docs against code):
- kitchen-cad: cutoff Jun 28. Docs updated, code frozen Jun 24.
- kitchen-plugin: cutoff Jun 24. Agent-created, only 1 shell touch ever.
- krono-compositor: cutoff Jun 23. Two sprints, now dormant.

DEAD (historical only):
- kitchen-app: cutoff May 12. Abandoned after 5-day sprint.

AGENT vs HUMAN:
- kitchen-plugin, catalog: 100% agent-created. Trust the code, not the docs (agent writes code first).
- kitchen-cad: human burst Jun 17-23, agent continued. Docs may reflect agent's understanding, not yours.
- krono-compositor: human sprints. More likely to have implicit knowledge not captured in docs.
```
