# Doc Routing Prompt (for LLM sessions)

Include this in your system prompt or paste when making changes:

```
## Doc Routing Rules

When I ask you to make changes, update the RIGHT docs:

1. **CHANGELOG.md** — ALWAYS append one line under [Unreleased]
2. **Relevant spec** (docs/specs/) — ONLY if behavior/contract changed
3. **ADR** (docs/adr/) — ONLY if a decision was made
4. **AGENTS.md** — ONLY if architecture constraints changed

NEVER touch:
- docs/vision/ (strategy, update separately)
- docs/archive/ (historical, never modify)
- Test files (tests ARE documentation)

Max 3 doc files per change. If more, ask me first.

After changes, list which docs you updated and why.
```

---

## Project-Specific Routing

### When working in kuchnie-core (root):
```
Update: CHANGELOG.md, docs/adr/NNN-*.md (if decision), AGENTS.md (if constraints changed)
Skip: docs/vision/, docs/archive/
```

### When working in catalog/:
```
Update: catalog/CHANGELOG.md, catalog/docs/specs/*.md (if API/behavior changed), catalog/docs/adr/NNN-*.md (if decision)
Skip: docs/vision/, docs/archive/, catalog/docs/materials/ (unless material data changed)
```

### When working in kitchen-cam/:
```
Update: kitchen-cam/CHANGELOG.md, kitchen-cam/AGENTS.md (if migration status changed), kitchen-cam/docs/specs/*.md (if formula/behavior changed)
Skip: kitchen-cam/docs/archive/, docs/vision/
```

### When working in home-builder-adapter/:
```
Update: home-builder-adapter/CHANGELOG.md, home-builder-adapter/AGENTS.md (if extraction rules changed)
Skip: home-builder-adapter/docs/archive/, docs/vision/
```

### When working in kitchen-erp/:
```
Update: kitchen-erp/CHANGELOG.md
Skip: kitchen-erp/docs/archive/, kitchen-erp/docs/archived/, docs/vision/
```

### When working in krono-compositor-mvp/:
```
Update: krono-compositor-mvp/CHANGELOG.md, krono-compositor-mvp/docs/specs/*.md (if pipeline/scene changed)
Skip: krono-compositor-mvp/docs/archive/, docs/vision/
```

---

## Quick Checklist (paste after making changes)

```
Docs updated:
- [ ] CHANGELOG.md — appended under [Unreleased]
- [ ] Relevant spec — updated if behavior changed
- [ ] ADR — created if new decision
- [ ] AGENTS.md — updated if constraints changed

Docs NOT touched (correct):
- [ ] vision/ — strategy docs, update separately
- [ ] archive/ — historical, never modify
- [ ] Test files — tests ARE documentation
```
