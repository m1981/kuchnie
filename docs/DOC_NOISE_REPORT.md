# Document Noise Report (Corrected)

Generated: 2026-06-29  
Method: `git log --follow --diff-filter=A` for true origin, `--diff-filter=M` for last content change, `--diff-filter=R` for renames  
Purpose: Identify *.md files that may mislead LLM models about current system state.

---

## Key Corrections from v1

1. **Root `AGENTS.md`** has TWO lifecycles — original (May 23, deleted Jun 6) was a kitchen-agent wiki; current (Jun 25) is a fresh kuchnie-core guide. **The current file is accurate.**

2. **krono-compositor `docs/`** files were mostly **renamed** from `doc/` → `docs/` on Jun 23, not created. True origin: May 26. Only 3 files were truly new.

3. **kitchen-app `docs/archived/`** files were **moved** to archive on Jun 18, not created. True origin: May 10 (active sprint).

4. **docs/archive/** files were **moved** from root `docs/` on Jun 29, not created. True origin varies.

---

## Classification

| Category | Trust | Description |
|----------|-------|-------------|
| 🟢 **GROUND TRUTH** | High | Docs that describe working code, updated alongside it |
| 🟡 **STALE BUT VALID** | Medium | Docs from active phase, never updated — still describe the code as-built |
| 🔴 **POST-ACTIVE NOISE** | Low | Docs created at/after cutoff — may describe desired state, not actual state |
| ⚫ **RELOCATED** | Varies | Docs moved/renamed — check true origin date |

---

## 🔴 POST-ACTIVE NOISE (genuinely new content created at/after cutoff)

### Root — Fresh planning docs (Jun 29)

| File | True Origin | Last Modified | Noise Type |
|------|------------|---------------|------------|
| `docs/00-brief2.md` | Jun 29 | — | **Aspirational scope rethinking** — prompts to "rethink scope" |
| `docs/02_pattern_mapping.md` | Jun 29 | — | **Pro CAD feature wishlist** — maps Polyboard/PRO100 features |

**Verdict**: These are prompts/plans, not documentation of working code. `00-brief2.md` asks to "rethink scope and boundaries." `02_pattern_mapping.md` maps professional CAD features that don't exist in the codebase.

### Root — Unvalidated glossary (Jun 29)

| File | True Origin | Last Modified | Noise Type |
|------|------------|---------------|------------|
| `docs/GLOSSARY.md` | Jun 29 | Jun 29 | Bounded context glossary — created and modified today |

**Verdict**: Created today, modified today. May be accurate but hasn't been validated against code.

### krono-compositor — Truly new "last wish" docs (Jun 23)

| File | True Origin | Last Modified | Noise Type |
|------|------------|---------------|------------|
| `krono-compositor-mvp/CHANGELOG.md` | Jun 23 | — | Retrospective summary |
| `krono-compositor-mvp/ROADMAP.md` | Jun 23 | — | **Aspirational plans** (HDRI, etc.) |
| `krono-compositor-mvp/docs/architecture.md` | Jun 23 | — | **Rewritten** — old was 113 lines, new is 28 lines |
| `krono-compositor-mvp/docs/blender-scene-reference.md` | Jun 23 | — | Reference data |

**Note**: 6 other krono docs (`PIPELINE_RULES.md`, `conflicting_paradigms.md`, `prompt_blender.md`, `prompt_web.md`, `rendering-improvements.md`, `what_next.md`) were **renamed** from `doc/` → `docs/` — their true origin is May 26 or Jun 21. These are NOT noise.

**Verdict**: `ROADMAP.md` is pure aspiration. `architecture.md` was rewritten from 113→28 lines at cutoff — the old version was more detailed. `blender-scene-reference.md` is reference data, likely accurate.

### features/archive/ — Specs for unbuilt features (Jun 29)

All 28 files in `features/archive/` were created on Jun 29 in a single commit. These are **specs for features that don't exist yet**:

| Feature | Files | Status |
|---------|-------|--------|
| F001-construction-method | adr, spec, status, tasks | Spec only |
| F002-recipe-engine | adr, spec, status | Spec only |
| F003-template-registry | adr, spec, status | Spec only |
| F004-validation-gates | adr, spec, status | Spec only |
| F005-material-resolver | adr, spec, status | Spec only |
| F007-blender-adapter | adr, spec, status | Spec only |
| F008-cli-export | adr, spec, status | Spec only |

**Verdict**: 100% noise for understanding current code. These describe what **should** be built.

---

## ⚫ RELOCATED (moved/renamed, true origin matters)

### docs/archive/ — Moved from root docs (Jun 29)

These were **moved** to archive, not created. Check true origin:

| File | True Origin | Renamed | Content Age |
|------|------------|---------|-------------|
| `docs/archive/ROADMAP.md` | Jun 25 | Yes | 4 days old at move |
| `docs/archive/rules.md` | Jun 25 | Yes | 4 days old at move |
| `docs/archive/llm-thinking-process.md` | Jun 24 | Yes | 5 days old at move |
| `docs/archive/PHASES.md` | Jun 29 | Yes | Same day — likely just moved |
| `docs/archive/00_LLM_NAVIGATION.md` | Jun 29 | Yes | Same day — likely just moved |
| `docs/archive/01_architecture.md` | Jun 29 | Yes | Same day — likely just moved |
| `docs/archive/05_cold_review_2026-06-28.md` | Jun 29 | Yes | Review notes from Jun 28 |
| `docs/archive/06_kitchen_plugin_discovery.md` | Jun 29 | Yes | Discovery notes |
| `docs/archive/07_integration_plan.md` | Jun 29 | Yes | Integration plan |
| `docs/archive/08_architecture_diagram.md` | Jun 29 | Yes | Old diagram |

**Verdict**: Already archived by the team. True origin dates tell you when the content was relevant. LLM should skip unless asked about history.

### kitchen-app/docs/archived/ — Moved from docs/ (Jun 18)

| File | True Origin | Renamed | Content Age |
|------|------------|---------|-------------|
| `kitchen-app/docs/archived/ARCHITECTURE_SUMMARY.md` | May 10 | Yes | 39 days old at move |
| `kitchen-app/docs/archived/INTEGRATION_EXAMPLE.md` | May 10 | Yes | 39 days old at move |
| `kitchen-app/docs/archived/MIGRATION_GUIDE.md` | May 10 | Yes | 39 days old at move |
| `kitchen-app/docs/archived/QUICK_REFERENCE.md` | May 10 | Yes | 39 days old at move |
| `kitchen-app/docs/archived/prompt2.md` | May 10 | Yes | 39 days old at move |

**Verdict**: These were written during the May 8-12 sprint, moved to archive on Jun 18. They accurately describe kitchen-app as it was built.

---

## 🟡 STALE BUT VALID (from active phase, never updated)

### kitchen-app — Frozen process docs

| File | True Origin | Last Modified | Status |
|------|------------|---------------|--------|
| `kitchen-app/doc/rules-reflex-app.md` | May 8 | — | Never updated |
| `kitchen-app/doc/rules-kitchen.md` | May 9 | — | Never updated |
| `kitchen-app/doc/prompt.md` | May 9 | — | Never updated |

**Verdict**: Frozen since creation. Accurately describes the dead project.

### kitchen-cad — Frozen reference docs

| File | True Origin | Last Modified | Status |
|------|------------|---------------|--------|
| `kitchen-cad/docs/LEGRABOX_SPEC.md` | Jun 17 | — | Never updated |
| `kitchen-cad/docs/analiza_konfiguratora_formatek.md` | Jun 17 | — | Never updated |
| `kitchen-cad/docs/test-plan.md` | Jun 18 | — | Never updated |
| `kitchen-cad/docs/DOCUMENTATION_GUIDELINES.md` | Jun 23 | — | Never updated |
| `kitchen-cad/docs/00-overview.md` | Jun 24 | — | Never updated |

**Verdict**: `LEGRABOX_SPEC.md` is likely accurate (specs don't change). Others are frozen snapshots.

### kitchen-cad — Post-freeze docs (Jun 24)

| File | True Origin | Last Modified | Status |
|------|------------|---------------|--------|
| `kitchen-cad/docs/CABINET-VARIANTS.md` | Jun 24 | Jun 28 | Updated once — cabinet taxonomy from screenshots |

**Verdict**: Created at code freeze, updated once 4 days later. Describes what the configurator app shows, not what kitchen-cad implements.

---

## 🟢 GROUND TRUTH (trust these)

### Actively maintained docs (modified alongside code)

| File | True Origin | Last Modified | Why Trust |
|------|------------|---------------|-----------|
| `AGENTS.md` (root) | Jun 25 | — | **Re-created Jun 25** as kuchnie-core guide. Fresh. |
| `catalog/AGENTS.md` | Jun 26 | Jun 27 | Modified alongside catalog code |
| `CHANGELOG.md` (root) | Jun 25 | Jun 29 | Append-only, updated today |
| `kitchen-plugin/docs/architecture.md` | Jun 22 | Jun 23 | Updated with DDD refactor |
| `kitchen-plugin/docs/config-syntax.md` | Jun 22 | Jun 24 | Reference doc, kept current |
| `kitchen-plugin/ROADMAP.md` | Jun 23 | Jun 23 | May contain aspirational items |
| `kitchen-cad/docs/architecture.md` | Jun 18 | Jun 24 | Updated with code changes |
| `kitchen-cad/docs/DESIGN.md` | Jun 17 | Jun 24 | Updated with code changes |
| `kitchen-cad/docs/PROJECT_LOG.md` | Jun 17 | Jun 23 | Log of changes |
| `docs/adr/001-008.md` | Jun 25-29 | — | Immutable decisions, verified by tests |
| `docs/00-brief.md` | Jun 24 | Jun 26 | Updated project brief |

---

## Summary: LLM Context Rules

```
EXCLUDE (noise):
  docs/00-brief2.md                           ← aspirational scope rethinking
  docs/02_pattern_mapping.md                  ← pro CAD feature wishlist  
  docs/GLOSSARY.md                            ← unvalidated, created today
  features/archive/** (28 files)              ← specs for unbuilt features
  krono-compositor-mvp/ROADMAP.md             ← aspirational, project dormant
  krono-compositor-mvp/docs/architecture.md   ← rewritten at cutoff, 113→28 lines

EXCLUDE (already archived, skip unless asked):
  docs/archive/**                             ← relocated, already archived
  docs/archive2/**                            ← relocated, already archived
  kitchen-app/docs/archived/**                ← relocated, already archived

INCLUDE WITH CAVEAT (stale but valid):
  kitchen-app/doc/rules-*.md                  ← frozen, describes dead project
  kitchen-cad/docs/LEGRABOX_SPEC.md           ← frozen, but specs don't change
  kitchen-cad/docs/CABINET-VARIANTS.md        ← screenshot analysis, not code docs
  krono-compositor-mvp/docs/blender-scene-reference.md ← reference data, likely accurate
  krono-compositor-mvp/docs/PIPELINE_RULES.md ← true origin May 26, still relevant
  krono-compositor-mvp/docs/conflicting_paradigms.md ← true origin May 26

TRUST FULLY:
  AGENTS.md (root, Jun 25 re-creation)        ← fresh kuchnie-core guide
  catalog/AGENTS.md                           ← actively maintained
  docs/adr/*.md                               ← immutable decisions
  */CHANGELOG.md                              ← append-only facts
  kitchen-plugin/docs/architecture.md         ← actively maintained
  kitchen-cad/docs/architecture.md            ← actively maintained
  kitchen-cad/docs/DESIGN.md                  ← actively maintained
  docs/00-brief.md                            ← updated project brief
```
