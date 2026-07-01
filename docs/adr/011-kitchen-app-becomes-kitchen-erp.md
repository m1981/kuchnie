# ADR-011: Kitchen-app becomes kitchen-erp; sales role reassigned to krono-compositor-mvp

## Status

Accepted 2026-07-01

## Context

The original brief (`docs/00-brief-understanding.md`, commit `f44dd8b`)
assigned `kitchen-app` the role of a **sales tool**:

> Stage 1 — Selling (`kitchen-app`, web app)
> Predefined 2.5D layouts + decor picker + 2.5D preview + screenshots for the
> customer. No engineering data yet.

In practice, `kitchen-app/` grew into a full **ERP-style ops application**:

- Reflex UI (React-backed Python framework)
- SQLModel database (Materials, HardwareSet, HardwareRule, Cabinet, Project,
  ProjectDefaults)
- BOM generation (`kitchen_erp.bom_generator.BOMGenerator` with recipes)
- Rules engine (`kitchen_erp.rules_engine.RulesEngine`)
- Purchasing strategies (`SheetMaterialStrategy`, `LinearMaterialStrategy`,
  `CountertopStrategy`, `ExactQuantityStrategy`)
- Admin UI for Material / HardwareSet / HardwareRule CRUD
- Cost tracing at cabinet and project level

The revised brief (`git show 878ccb3:docs/00-brief2.md`) acknowledged this
implicitly:

> ## kitchen-app (works, need refinement)
> Next Easy kitchen cost estimation and BOM was my idea to help user take
> smarter expensive decision.

Meanwhile, the sales-tool role (first-visit 2.5D previews + decor picker) is
already served by `krono-compositor-mvp/` — its Alpine.js SPA does exactly the
"predefined I/L/U layouts + sidebar decor swap" flow described in `00-brief2.md`.

Additional scope-creep signal: `kitchen-app/kitchen_app/state.py` contains a
runtime toggle between two BOM computation paths:

```python
def set_use_new_bom(self, value: bool)
def open_selected_cabinet_cost_trace(self)       # old path
def open_selected_cabinet_cost_trace_new(self)   # new path (recipe-based)
def open_project_cost_trace(self)                 # old path
def open_project_cost_trace_new(self)             # new path (recipe-based)
```

This is a mid-migration state. One path must be canonical; the other must
be deleted. Currently both are live and can be selected by the user.

## Decision

**Rename `kitchen-app/` → `kitchen-erp/`.** Accept the ERP scope. Reassign the
sales-tool role explicitly to `krono-compositor-mvp/`.

### Component roles after this ADR

| Component | Role | Stage in workflow |
|---|---|---|
| `krono-compositor-mvp/` | **Sales tool** — first-visit interactive 2.5D previews, decor picker, screenshots | Stage 1 (Sales) |
| `home_builder_5` (external, licensed) | Interactive kitchen layout GUI | Stage 2 (Design) |
| `home-builder-adapter/` (per ADR-009) | Blender scene → `kuchnie_core.Kitchen` extractor | Stage 2 handoff |
| `kitchen-erp/` (this ADR) | **BOM · cost · purchasing · rules admin · ops UI** | Stage 2 refinement + Stage 4 (Purchasing) |
| `kitchen-cam/` (per ADR-010) | CAM enrichment — machining ops, DXF for CNC | Stage 3 (CAM) |
| `catalog/` | Material catalog service — decors, worktops, pairings, availability | Shared kernel |
| `kuchnie_core` | Domain hub — Kitchen, Panel, ConstructionMethod, decomposition, BOM | Shared kernel |

### Migration actions

**Rename**

- Directory: `kitchen-app/` → `kitchen-erp/`
- `pyproject.toml` name field: `kitchen-app` → `kitchen-erp`
- `rxconfig.py` app_name: verify no hardcoded name mismatch

**Internal package restructure**

The current layout has two packages inside `kitchen-app/`:

```
kitchen-app/
├── kitchen_app/       ← Reflex UI (state, pages, admin_ui, admin_state)
└── kitchen_erp/       ← Business logic (models, bom_generator, rules_engine, purchasing)
```

Rename to align with the new component name:

```
kitchen-erp/
├── ui/                ← was kitchen_app/ (Reflex pages + state)
└── core/              ← was kitchen_erp/ (business logic)
```

Or keep two packages but rename to `kitchen_erp_ui/` and `kitchen_erp_core/`.
Concrete name choice deferred to migration time; the principle is that both
package names reflect the same component identity.

**Deprecate old BOM path**

Delete the old (non-recipe) BOM logic:

- Remove `Cabinet.calculate_cost()` from `kitchen_erp/models.py` (the direct
  computation path)
- Remove `open_selected_cabinet_cost_trace()`, `open_project_cost_trace()`
  from `state.py` (keep only the `_new` variants and drop the suffix)
- Remove `set_use_new_bom` flag and `use_new_bom` field
- Keep `BOMGenerator` (recipe-based); it becomes the only path.

**Integrate with kuchnie_core**

`BOMGenerator` currently computes panels locally via recipes. Per ADR-009 and
ADR-010, `kuchnie_core.decompose()` is the canonical decomposition. Follow-up:

- `BOMGenerator.generate()` should call `kuchnie_core.decompose(cabinet)` to
  produce panels, then wrap them in `BOMAssembly` with pricing.
- `kitchen_erp` `Cabinet` SQLModel maps to `kuchnie_core.CabinetInstance` via
  an adapter function (`to_kuchnie_core(cabinet_sqlmodel) -> CabinetInstance`).
- `Material` SQLModel becomes a local cache/mirror of `catalog/` data (see
  ADR-008), not a separate authoritative material store.

These integrations are **follow-up work**, not blocking this ADR. This ADR
just declares the intent and names the component.

**Reassign sales-tool responsibility**

- Update `krono-compositor-mvp/README.md` to explicitly claim the "Stage 1
  sales tool" role.
- Note in `kitchen-erp/README.md`: "Not a sales tool. See
  `krono-compositor-mvp/` for the first-visit customer interaction."

## Consequences

**Positive**

- Honest naming: `kitchen-erp` reflects what the code actually does.
- Sales tool role is unambiguous: `krono-compositor-mvp/` owns it.
- Two-BOM-systems ambiguity resolved by declaring the recipe-based path
  canonical and deleting the other.
- Path is set for `kitchen-erp` to consume `kuchnie_core` for domain
  computations, eliminating the third parallel BOM implementation.

**Negative**

- One-time rename churn: import paths, config files, deployment scripts
  update.
- Deleting the old `Cabinet.calculate_cost()` breaks anything that still
  calls it (verify: `state.py` and `demo_bom_system.py` are the known
  callers; both migrate to `BOMGenerator`).
- The follow-up `kuchnie_core` integration is real work; this ADR does not
  execute it, only declares its direction.

**Neutral**

- The scope creep is now **codified**, not accidental. Future LLM sessions
  will not attempt to shrink `kitchen-erp` back into a "sales tool" role
  because the ADR explicitly reassigns that.

## Alternatives considered

**11a: Extract all business logic (`kitchen_erp/*`) into `kuchnie_core`,
leaving only Reflex UI in the current package.**
Rejected because ~80% of the ERP business logic (SQLModel entities,
purchasing strategies, rules engine, materials CRUD) is web-app-specific and
does not belong in a pure Python domain library. Moving it would either
contaminate `kuchnie_core` with SQLModel (adding SQLAlchemy dependency to
every consumer) or require a large extraction of adapter code that adds no
value. The high-value extraction — `BOMGenerator` calling
`kuchnie_core.decompose()` — is captured as follow-up integration work
within this ADR, not a separate package.

**11c: Split into two apps — `kitchen-sales` (customer-facing) and
`kitchen-erp` (internal ops).**
Rejected because a solo developer cannot maintain two Reflex apps.
`krono-compositor-mvp/` already exists and already serves the customer-facing
role well (Alpine.js SPA, no build step, ~300 ms render). Creating a third
web app is duplication.

## References

- Original brief: `docs/00-brief-understanding.md` (commit `f44dd8b`)
- Revised brief: `git show 878ccb3:docs/00-brief2.md`
- Duplicate BOM systems evidence: `kitchen-app/kitchen_app/state.py`
  (`use_new_bom`, `_new` method suffixes)
- Precedent for accepting scope creep in naming: ADR-010 renames
  `kitchen-cad` → `kitchen-cam` for the same "honest naming" reason.
- Related ADRs:
  - ADR-008 (Material master catalog) — reinforces that `catalog/` is the
    single source of material truth; `kitchen-erp.Material` becomes a
    mirror.
  - ADR-009 (`home-builder-adapter`) — establishes the pattern that domain
    logic lives in `kuchnie_core`, peripheral components consume it.
  - ADR-010 (`kitchen-cam`) — establishes the same downstream-consumer
    pattern for CAM outputs.
