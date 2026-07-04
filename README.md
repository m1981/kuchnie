# kuchnie — Kitchen Cabinet Manufacturing Monorepo

Monorepo for a kitchen cabinet manufacturing pipeline: from interactive
customer previews and Blender scene design, through domain decomposition
into physical panels, to BOM costing and CNC drilling output. The domain
hub is `kuchnie_core` (pure Python); every other component depends on it,
never the other way.

---

## Components

| Component | Type | Role (per ADR-011 stage table) |
|---|---|---|
| `kuchnie-core/` | A — Domain hub | Kitchen, Panel, decomposition, BOM, standards, validator. Pure Python. |
| `kitchen-cam/` | A — CAM enrichment | Machining ops (System32, hinges, handles), DXF for CNC. Downstream of `kuchnie_core`. |
| `catalog/` | C — Material catalog service | Kronospan/Egger decors, worktops, pairings, availability. FastAPI + SQLite. |
| `kitchen-erp/` | D — BOM + ops UI | Cost estimation, purchasing, rules admin. Reflex + SQLModel. |
| `krono-compositor-mvp/` | C+F — Sales tool | First-visit 2.5D previews + decor picker + screenshots. FastAPI + OpenCV + Alpine.js. |
| `home-builder-adapter/` | F — Blender extractor | Walks `home_builder_5` `.blend` tree → `kuchnie_core.Kitchen`. Only `bpy`-dependent component. |

Per-component test status at the freeze point:
[`docs/freeze/TEST-BASELINE-2026-07.md`](docs/freeze/TEST-BASELINE-2026-07.md).
For current status, run the suites — test counts are not maintained in
this file.

**External:** `/Users/michal/PycharmProjects/home_builder_5` — third-party
licensed Blender addon for interactive kitchen layout (Stage 2). Untouched
per F007 Rule 4.

**Dependency direction:** every peripheral component imports `kuchnie_core`.
No cycles. `kuchnie_core` imports only stdlib + Pydantic + PyYAML.

**Workflow stages:** Sales (`krono-compositor-mvp`) → Design (`home_builder_5`)
→ Extract (`home-builder-adapter`) → Refine + BOM (`kitchen-erp`) → CAM (`kitchen-cam`).

---

## Read order for new sessions

1. [`AGENTS.md`](AGENTS.md) — operational rules, architecture constraints, file map
2. [`RESUME.md`](RESUME.md) — living status doc: what to do next, priority order, DO-NOT list
3. [`docs/freeze/DOC-TRUST-REPORT.md`](docs/freeze/DOC-TRUST-REPORT.md) — which `.md` files to trust
4. The ADR of your workstream (in `docs/adr/`)

---

## Freeze artifacts

All freeze documentation lives in `docs/freeze/`:

| File | Purpose |
|---|---|
| [`FREEZE-PLAN.md`](docs/freeze/FREEZE-PLAN.md) | The original freeze plan |
| [`TEST-BASELINE-2026-07.md`](docs/freeze/TEST-BASELINE-2026-07.md) | Per-component test results at freeze |
| [`MIGRATION-STATUS-2026-07.md`](docs/freeze/MIGRATION-STATUS-2026-07.md) | ADR-008–012 execution status snapshot at freeze (immutable) |
| [`DOC-TRUST-REPORT.md`](docs/freeze/DOC-TRUST-REPORT.md) | Trust audit of all 109 tracked `.md` files |
| [`RESUME.md`](RESUME.md) | Living status doc + resume checklist (repo root) |
