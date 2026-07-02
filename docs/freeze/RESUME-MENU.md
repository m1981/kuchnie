# Resume Menu — freeze-2026-07

> Pick up where we left off. Items ordered by dependency (do top items first).

---

## Blocked on ADR-010 deletion queue

These items execute after `kitchen_cam.models/panel_calculator/csv_generator` are deleted.

- **Rewrite kitchen-cam docs after deletion queue executes** — `kitchen-cam/README.md`, `kitchen-cam/ROADMAP.md`, `kitchen-cam/docs/specs/overview.md` are currently STALE (stamped) because they describe the deprecated modules as primary. Rewrite them to describe the post-deletion CAM-only scope once the deletion lands. (D4 from trust audit)

## Non-blocking, do anytime

- **Rename kitchen-erp recipes to "cost recipes"** — after `BOMGenerator` integrates `kuchnie_core.decompose()`, rename `kitchen_erp/core/recipes.json` and `recipe_loader.py` references to "cost recipes" to kill the name collision with `kuchnie_core/recipe.py`. (D5 from trust audit)

## Pydantic tension — needs a decision

- **ADR candidate: pydantic-boundary** — `kuchnie_core/schema.py` imports Pydantic (now declared in `pyproject.toml` per D1). ADR-012 alternative 12a rationale says "no Pydantic dep by design." The tension is real: `schema.py` uses `BaseModel` for YAML/JSON schema validation at the boundary, while `model.py` uses plain dataclasses for the domain core. Whether Pydantic stays at the schema boundary (acceptable) or gets refactored out (ADR-012 purity) is a resume decision. Possibly a one-page ADR.

---

*From trust audit 2026-07-03. See `docs/freeze/DOC-TRUST-REPORT.md` for full evidence.*
