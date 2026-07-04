# ADR-005: Builder sidebar is free composition + templates, not the backend wizard

**Status**: Accepted
**Date**: 2026-07-05

> Reader: anyone extending the builder GUI (`public/index.html`) or wiring it
> to the configurator API.
> Enables: deciding UI changes without accidentally re-imposing the wizard's
> step order on the sidebar.
> Update-trigger: never edited; superseded by a new ADR if the builder's
> interaction model changes.

---

## Context

Two interaction models exist for assembling a kitchen's materials:

1. **Backend wizard** (`api/routers/configurator.py`, ADR-002): a rigid
   ordered state machine — `front → carcass → worktop → edge → side_panel →
   plinth → done`. Each step validates and constrains the next (e.g. carcass
   options come from pairings of the chosen front). Built first; 6 endpoints,
   fully tested.
2. **Builder sidebar** (`public/index.html`, spec
   `docs/specs/builder-gui.md`): four slots (`base_front`, `wall_front`,
   `carcass`, `worktop`) fillable in any order by clicking catalog cards,
   with auto-advance as a convenience only — plus saved templates that fill
   all slots in one click.

The walking-skeleton spec framed the sidebar as merely a thinner UI slice of
the same flow. That undersells the actual reason it exists.

## Decision

**The top-level motivation for the sidebar is: templates make repeat work
cheap.** Free slot composition + saved templates is the primary interaction
model of the builder, chosen deliberately *over* the rigid wizard flow the
backend already implements.

The economics of a kitchen workshop: most kitchens sold are variations of a
handful of proven material combinations ("Dąb Craft + Biel", "Kaszmir mat +
czarny blat"). A wizard makes every kitchen cost the same effort as the
first one — start at step 1, click through every gate. The sidebar makes the
*combination* the first-class object: load a template, swap one slot, save
as a new template. Repeat work converges toward one click per changed
material.

## Consequences

- **The wizard is a service, not a UX.** The configurator API remains the
  validation and recommendation engine (pairings, availability, BOM). When
  the sidebar syncs with it, the sync must adapt to the user's free order —
  the UI never forces the user back into step order.
- **Templates are first-class sidebar citizens**: the saved-template list,
  one-click load, and save-current-combination stay in the sidebar
  permanently; they are not a leftover of the walking skeleton.
- Slot guards (role filtering, pairing hints) should be **advisory, not
  blocking** — a locked flow would reintroduce the wizard by the back door.
- Scenario S4 (`docs/scenarios-edge-cases.md`, start-from-template-and-swap)
  is the canonical happy path, not S2's guided sequence.

## Alternatives considered

- **Reuse the wizard in the UI** (thin client over `PATCH /select`):
  rejected — correct for a first-visit guided sale
  (`krono-compositor-mvp`'s job), wrong for the repeat-work builder.
- **Templates as a backend-only feature** (`/configurator/templates`):
  insufficient alone — templates must be editable *in place* (swap one slot)
  to make repeat work cheap, which requires free composition in the UI.
