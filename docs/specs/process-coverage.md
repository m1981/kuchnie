# Spec: Process coverage map (L1) — stages, owners, boundaries

> Reader: anyone deciding where a new feature belongs or whether a stage is
> in scope | Enables: routing work by stage ownership and reading each
> boundary decision with its live ledger premise instead of tribal knowledge
> | Update-trigger: a stage's owner, in/out status, or a cited id changes

## Intent

The single scope authority for the sales→CNC pipeline. One row per process
stage: owner component, in/out decision, boundary. Decided with Michał
2026-07-12 (L1 questionnaire). Business model constraint shaping everything:
**all-melamine fronts cut from SwissKrono/Egger/Kronospan boards, one
supplier, edge-banding only — no lacquer/PVC fronts, no front
subcontracting.**

| Stage | Owner | Status | Boundary decision |
|---|---|---|---|
| 1. First visit (decors) | `krono-compositor-mvp` + `catalog` | in, live | output = decor selection set |
| 2. Pomiar | `kitchen-erp` (project record) | in, v1 | attachments only (photos, appliance sheets, dimension PDF); geometry stays in Blender |
| 3. Layout & design | external `home_builder_5` → `home-builder-adapter` | in, committed | hb5 is THE layout tool; ERP canvas stays a quick-estimate sketchpad; investment goes to extraction fidelity; the adapter now carries positions — two Runs + corner from a two-wall scene (r4, `home-builder-adapter/docs/specs/adapter-position-extraction.md`) |
| 4. Decomposition | `kuchnie-core` | in, live | v1 types: dolna drzwiowa/szufladowa/legrabox, górna drzwiowa + **corner blind (new)**; other types stay ERP estimates |
| 5. Purchasing | `kitchen-erp` | in, v1 | artifacts: cutting-service package (rozrys CSV per the contract below + DXF, single hop — the service supplies board, cuts, edges, drills; offer/ACCEPT loop) + per-dealer hardware CSVs (producer codes, min-stock top-up); prices via multi-source ingestion to one landing schema — catalog stays price-free. Renegotiated 2026-07-16 at the UC-4 dressing (was: board order to a single supplier — no raw-board purchase exists) |
| 6. Cutting & edging | external service | boundary | rozrys CSV `Lp;Element;Długość;Szerokość;Grubość;Ilość;Materiał;Usłojenie;Okleina×4;Uwagi`, one-time column mapping at the e-rozkrój-class service; **nesting is a permanent non-goal** |
| 7. CAM / drilling | `kitchen-cam` | in, live | ops from core decomposition → DXF |
| 8. Assembly outputs | `kitchen-cam` | in, later milestone | panel labels + per-cabinet sheets, after decomposition earns trust |
| 9. Worktops | `kuchnie-core` BOM + `catalog` | in, v1 | laminate per-lm: `kitchen_bom` consumes `WorktopSegment` (length × price/lm + cutout count); same three brands from the same CNC shop, decors via catalog; stone/quartz = external quote line |
| 10. Delivery & installation | — | **out, permanent** | never modeled |
| 11. Handover archive | `kitchen-erp` (project record) | in, v1 | project record references kitchen JSON + cut lists + decor set |

**Project spine (cross-cutting):** minimal Project/Order entity in
`kitchen-erp` — customer, status, dates, artifact references — threading
stages 1→11. The ERP's Reflex app entry point is
`kitchen-erp/kitchen_erp/kitchen_erp.py` (required by `rxconfig.py`;
adopted at the 2026-07-16 dark-triage).

**Non-goals (tripwire-free by intent, refer by title):** nesting;
lacquer/PVC front workflows; stone worktop computation; installation
scheduling; ERP canvas as a layout tool; bidirectional hb5 IO (revisit
only if a real need appears — see pattern-conformance row 10); built
rendering — photoreal client presentation stays in hb5/Blender renders
permanently, krono stays 2.5D decor choice (ratified 2026-07-29,
`docs/adr/035-playbook-operating-decisions.md`).

## Decisions

- ADR-001 — panel is the atom (keeps hierarchy flat; stage 4 shape).
- ADR-009 — adapter is the ACL; hb5 owns rooms/placement (stage 3).
- ADR-011 — kitchen-erp owns ops artifacts (stages 2, 5, 11).
- ADR-013 — drawer-box roles (stage 4 pricing correctness).

## Ground truths

- tr-8ed0a7ff — home_builder_5 present (stage 3 input exists).
- tr-239065a8 — extraction reads bbox + toe kick (stage 3 contract works; successor of the pre-rule-8 claim that watched a generated log).
- tr-b2e3dbff — dolna_legrabox emits stretchers + plinth (stage 4 buildable).
- tr-3ef7b607 — confirmat + groove ops emitted (stage 7 input exists).
- tr-fc74bc2e — recipe engine unwired (stage 4 debt: two formula engines).
- tr-00421995 — validation scattered (stage 4→7 gate debt).
- tr-15d48651 — Panel.grain wired, Usłojenie emitted (stage 6 unblocked;
  supersedes the diverged no-grain-field fact via wk-5dc557d6).
- tr-8dfe366d — back-panel formula groove-seated with luz, 698×578 = reference
  (stage 4 defect closed; supersedes the diverged oversize-back fact via
  wk-090ed9f4).
- tr-e3c86dfd — catalog schema 1.5.0 (stages 1, 5, 9 data home).

## Work

- wk-02a62298 — Project/Order spine in kitchen-erp
- wk-39ed9155 — supplier price-file import
- wk-4c37f4ee — kitchen_bom consumes WorktopSegment per-lm
- wk-31467921 — corner-blind decomposer
- wk-81a47ab8 — adapter extraction fidelity round 2
- (bd twins in .beads, created with this spec)

## Acceptance

Pre-written `done --claim` texts, scoped to evidence commands:

- "kitchen-erp defines a Project/Order entity with customer, status, dates
  and artifact-reference fields, and the UI can create and list projects"
- "kitchen-erp imports a supplier price file (CSV/XLS) updating Material
  prices by catalog_variant_id, covered by a test with a fixture file"
- "kitchen_bom output includes a worktop position computed from
  WorktopSegment length at a per-lm rate, covered by a hand-computed test"
- "TYPE_REGISTRY contains a corner-blind decomposer emitting filler and
  reduced-back panels, with a hand-computed dimension test"
- "adapter extraction carries drawer-stack data from hb5 scenes into
  CabinetInstance.drawers, verified by the walking-skeleton blender leg
  without hand re-entry"
