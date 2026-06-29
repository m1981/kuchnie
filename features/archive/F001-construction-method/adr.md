# ADR — F001 — Construction Method as a First-Class Domain Entity

**Date:** 2026-06-28
**Status:** `Proposed`
**Feature:** F001
**Author:** solo dev

---

## Context

Five reference systems (PRO100, Polyboard, Winner Flex, TopSolid'Wood, PaletteCAD) and the Blender plugin all mix construction parameters into cabinet type definitions or expose them as flat global settings (e.g., the plugin's `config_parser.py` DEFAULTS dict: `corpusThickness`, `frontThickness`, `backThickness`, `grooveOffset`, `frontOverlay`).

This couples WHAT a cabinet is to HOW it is built. Changing from cam-lock to dowel construction requires editing every cabinet type. For a solo developer serving Wrocław customers — where CNC supplier choice (and therefore drilling pattern) is a per-project decision — this coupling is a recurring source of rewrites.

Polyboard's clean separation of construction method from cabinet type is the pattern we want to steal.

---

## Decision

We will introduce `ConstructionMethod` as a first-class, immutable Pydantic entity in `src/kuchnie_core/construction.py`. A `Kitchen` references one method by ID (`default_construction_method_id`). `CabinetInstance` inherits this reference; per-cabinet override is **out of scope for v1.0** but the field exists on `CabinetInstance` (`construction_method_id`) to make the future override trivial to enable.

Methods are stored as **YAML files** in `src/kuchnie_core/construction_methods/`, loaded by a module-level `ConstructionMethodRegistry`. IDs are human-readable slugs (`dowel_camlock_18`, `confirmat_18`).

`kitchen_config.yaml` is formally versioned at v1.0 by this decision and becomes our **Published Language** between Core and all consumers.

---

## Alternatives Considered

| Option | Why rejected |
|---|---|
| **A. Keep flat dict** (mirror plugin's `DEFAULTS`) | Couples WHAT to HOW. Cannot swap methods without rewriting consumers. The exact pain we are solving. |
| **B. Embed method fields directly in `CabinetInstance`** | Duplicates the same values across every cabinet. Changing a thickness becomes a sweep. Defeats the swap-once promise. |
| **C. `ConstructionMethod` as a Python class hierarchy** (subclass per method) | Adding a new method requires editing Python. We want carpenters to add YAMLs. |
| **D. Store methods in catalog/** | Catalog is for materials (decors/edges), not construction. Different lifecycle, different ownership. Would blur the bounded context. |
| **E. Per-cabinet method only (no project default)** | Forces the configurator to ask "which method?" for every cabinet add. UX cost too high. Project-level default with future override is the right compromise. |
| **F. Use the plugin's `config_parser.py` as the source of truth** | Violates Rule 4 from `00_LLM_NAVIGATION.md` (plugin is a renderer, not domain). The plugin keeps its own copy; the render adapter feeds it. |
| **G. UUID method IDs** | Pure friction. Carpenters will read these IDs in YAML. Slugs win. |
| **H. Versioned method IDs (`dowel_camlock_18@v2`)** | Premature. v1.0 has no method-evolution use case. If a method changes meaning, give it a new name. Captured as backlog. |

---

## Consequences

### Positive
- Swapping construction (cam-lock → dowel) is a one-line YAML change at the project level.
- Recipes (F002) and validation gates (F004) can read method fields without knowing the cabinet template.
- The render adapter (F007) has a single, stable place to look up plugin-bound thickness values.
- New construction methods can be added by carpenters writing YAML, no Python edits.
- Test fixtures are explicit: every cabinet test now declares its method.

### Negative
- One extra indirection on every panel-calculation read (`cabinet.method.side_thickness` instead of `SETTINGS["corpusThickness"]`). Negligible cost; explicit beats implicit.
- Existing YAML examples need migration (we auto-fill the default ID at load time — see "Affected Files").
- The plugin's `config_parser.py` and our `ConstructionMethod` will visibly diverge; future LLMs may try to "reconcile" them. Anti-corruption layer (the render adapter) makes this explicit and the LLM Hint section below forbids it.

### Neutral
- File count grows: each method is a YAML. Acceptable — they are read-only data.
- `kitchen_config.yaml` schema bumps from "undefined" to v1.0. Forces us to commit a schema document. Net positive.

---

## Affected Files (canonical)

- `src/kuchnie_core/construction.py` — `ConstructionMethod`, `JoineryType`, `BackType`, `ConstructionMethodRegistry`
- `src/kuchnie_core/construction_methods/dowel_camlock_18.yaml` — default
- `src/kuchnie_core/construction_methods/confirmat_18.yaml` — alternative
- `src/kuchnie_core/model.py` — `CabinetInstance.construction_method_id`, `Kitchen.default_construction_method_id`
- `src/kuchnie_core/loader.py` — auto-fill default method ID for legacy YAMLs missing the field
- `tests/core/test_construction_method.py`
- `tests/core/test_yaml_roundtrip.py`
- `examples/kitchen_nowak.yaml` — first v1.0-compliant example
- `docs/schemas/kitchen_config.v1.0.yaml` — published schema (Pydantic-exported JSON Schema)
- `docs/GLOSSARY.md` — entries for `ConstructionMethod`, `JoineryType`, `BackType`, `ConstructionMethodRegistry`
- `docs/01_architecture.md` — Context Map shows `ConstructionMethod` in Core

---

## LLM Hints

> Direct instructions for future LLM sessions in this decision area.

- **When asked "where should panel thicknesses live?"** → `ConstructionMethod` in Core. Never in cabinet types, never as flat globals.
- **When asked "should we sync this with the plugin's `config_parser.py`?"** → **No.** The render adapter (F007) reads the `ConstructionMethod` and translates to the plugin's scene settings. Plugin internals stay untouched (Rule 4).
- **When asked "can a cabinet override the project method?"** → Not in v1.0. The field `CabinetInstance.construction_method_id` exists and defaults to the project's method. A future feature (post-v1.0) can lift this restriction by simply allowing the field to differ. Do not implement override logic now.
- **When asked "should we add a new method?"** → Add a YAML file in `construction_methods/`. Do not modify the Pydantic model unless adding a new field that all methods will share.
- **When asked "can we version methods?"** → Not in v1.0. If a method's semantics change, create a new slug. Versioning is a backlog item.
- **Do not propose:**
  - Replacing YAML storage with a database.
  - Async loading of methods (synchronous module-level singleton is fine).
  - Method inheritance / mixins (YAML duplication is acceptable — methods are short).
  - Auto-derivation of methods from cabinet properties.
- **Related ADRs:**
  - **F002 (Recipe Engine)** depends on this — recipes will read method fields via the context object passed to the formula engine.
  - **F004 (Validation Gates)** depends on this — Gate 1 (Cabinet) validates that the cabinet's method exists in the registry.
  - **F005 (Material Resolver)** is independent but lands in the same `kitchen_config.yaml` v1.0 schema.
  - **F007 (Blender Adapter)** is the ACL — converts `ConstructionMethod` to plugin scene settings. **Plugin internals are not modified.**

---

## Sign-off

- [ ] `docs/GLOSSARY.md` updated with 4 new terms.
- [ ] Tests in place: `tests/core/test_construction_method.py`, `tests/core/test_yaml_roundtrip.py`.
- [ ] At least 2 YAML methods committed.
- [ ] `examples/kitchen_nowak.yaml` validates.
- [ ] `docs/schemas/kitchen_config.v1.0.yaml` published.
- [ ] Status moved from `Proposed` → `Accepted` (above) on first successful use in F002.
