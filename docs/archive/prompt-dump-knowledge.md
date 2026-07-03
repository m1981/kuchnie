# Knowledge Routing Prompt

Use this prompt when you want the LLM to organize and persist knowledge to the correct location.

---

## Quick Version (paste this)

```
Dump all knowledge from this session to the correct locations:

VISION (docs/vision/) — aspirations, strategy, user journeys:
- "We want to...", "The goal is...", "Users should be able to..."

DECISIONS (docs/adr/ or {project}/docs/adr/) — choices with reasoning:
- "We chose X because Y", "We decided against Z"

SPECS ({project}/docs/specs/) — contracts, acceptance criteria:
- "The API should...", "When X happens, Y must occur"

ARCHITECTURE ({project}/docs/architecture/) — current state:
- "The system currently...", "X is implemented as..."

CHANGELOG ({project}/CHANGELOG.md) — what changed today:
- "Added...", "Fixed...", "Changed..."

RULES:
- If you're not sure where it goes, ask
- Don't restate code — if the code is clear, skip it
- Don't create docs for things that don't exist yet (that's vision/)
- Use the exact directory structure, don't create new folders
- For cross-project knowledge, use root docs/
- For project-specific knowledge, use {project}/docs/
```

---

## Extended Version (with examples)

```
Organize all knowledge from this session into the documentation structure.

## Routing Rules

### 1. VISION → docs/vision/
Put here: strategy, user journeys, competitive analysis, roadmap aspirations.

Signals:
- "We want to build..."
- "The end state should be..."
- "Users need to..."
- "Compared to [competitor]..."

Format: `docs/vision/NN-descriptive-name.md`

### 2. DECISIONS → docs/adr/ or {project}/docs/adr/
Put here: architectural decisions with context and reasoning.

Signals:
- "We chose X over Y because..."
- "The tradeoff is..."
- "We decided against..."
- "This is immutable because..."

Format: `NN-short-title.md`
Template:
  # {Decision Title}
  ## Context
  ## Decision
  ## Consequences

### 3. SPECS → {project}/docs/specs/
Put here: contracts, API definitions, acceptance criteria, data models.

Signals:
- "The endpoint should..."
- "When X, the system must..."
- "Acceptance criteria:"
- "The schema is..."

Format: `descriptive-name.md`
Include: request/response schemas, error cases, edge cases.

### 4. ARCHITECTURE → {project}/docs/architecture/
Put here: descriptions of current implementation, data flow, module responsibilities.

Signals:
- "Currently, X handles..."
- "The flow is: A → B → C"
- "X depends on Y"
- "The implementation uses..."

Format: `descriptive-name.md`
Rule: Only describe what EXISTS, not what's planned.

### 5. CHANGELOG → {project}/CHANGELOG.md
Put here: what was added/changed/fixed today.

Format: Append under today's date.
```
## [YYYY-MM-DD]
### Added
- Feature X
### Changed  
- Modified Y
### Fixed
- Bug Z
```

### 6. CROSS-PROJECT → docs/
Put here: knowledge that spans multiple projects.

Signals:
- "All projects share..."
- "The convention is..."
- "When adding a new project..."

## Anti-patterns (DON'T)
- Don't create a doc that restates code
- Don't put specs in vision/
- Don't put aspirations in specs/
- Don't create docs for features that don't exist (that's a spec, not architecture)
- Don't duplicate — if it's in CHANGELOG, don't also write a separate "what's new" doc
```

---

## Usage Examples

### After a feature session:
```
We just built the configurator session API. Dump all knowledge to proper locations.
```

### After a planning session:
```
We discussed the roadmap for Q3. Dump decisions and vision updates.
```

### After a debugging session:
```
We found and fixed the worktop compatibility bug. Document what changed and why.
```

### After a research session:
```
We analyzed Polyboard's approach to material matching. Dump findings to vision/ and any decisions to adr/.
```
