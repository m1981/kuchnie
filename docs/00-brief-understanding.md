# Brief Understanding — Kitchen Design & Manufacturing Pipeline

## My Understanding

You're a **solo cabinet maker in Wrocław** who wants to build a lean, custom software pipeline to run the full kitchen business — from first customer visit through to CNC-ready files — without paying for expensive off-the-shelf suites like IMOS or Cyncly.

Here's how I read your three-stage workflow:

---

## Stage 1 — Selling (`kitchen-app`, web app)

> _"Help the customer fall in love with a layout during the first visit."_

- You walk into a new flat with a tape measure and a tablet
- You need **predefined 2.5D layouts** (not full 3D — smart, fast)
- Customer picks decors from **Kronospan / Egger** catalogs (melamine-faced chipboard, HPL — the bread and butter of Polish kitchen production)
- Backend renders a **high-quality 2.5D preview** with the chosen textures
- Output: **screenshots for the customer** — no engineering data yet

This is essentially a **sales tool** — quick, visual, enough to get a "yes, we like option B."

---

## Stage 2 — Designing (`kitchen-plugin`, second app)

> _"Turn the approved concept into a real cabinet configuration."_

- A **2D layout editor** where you define kitchen rows (L-shape, galley, U-shape — but no islands or slanted walls in v1)
- Drag-and-drop **standard cabinet types** from a sidebar (base units, wall units, tall units, oven housing, corner units…)
- **Arrow-based positioning** — slide cabinets left/right within a row
- **Global dimensions** (worktop height, plinth, cabinet depth) + **per-cabinet overrides** (custom widths, internal shelves, drawer stacks)
- **Live cost estimation** — system knows board prices and accessory costs (hinges, runners, handles)
- Output: an **intermediate format** (JSON/YAML/XML — not DXF, not G-code, not a CAD file) that describes rows → cabinets → parts → materials

This intermediate format is the **single source of truth** for everything downstream.

---

## Stage 3 — CAM Preparation (CLI tools)

> _"Turn the design into files a CNC shop in Wrocław can actually cut."_

- You manually **tweak the intermediate file** — add vent holes, LED grooves, address wall obstacles
- CLI tool #1: generate **cut lists as CSV** compatible with Polish cutting optimization software (**e-rozrys / e-rozkroj** — nesting services)
- CLI tool #2: generate **System32 drilling data** — shelf pin holes, hinge boring, dowel holes, panel rabbets
- **Cost estimation refines** with real nesting results + accessory totals — crucial because **you** buy the board, not the CNC shop
- You send **DXF files** (or similar) to the CNC company, get their price, confirm, and they manufacture

---

## Key Design Decisions

| Decision                           | Why It's Smart                                                                                      |
| ---------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Intermediate format** as the hub | Keeps design, rendering, and CAM loosely coupled — you can evolve each independently                |
| **2.5D not full 3D** for sales     | Fast to render, fast to iterate, good enough for customer approval                                  |
| **Blender for renders**            | Free, scriptable, excellent with PBR textures — Kronospan/Egger have material libraries for Blender |
| **CLI tools for CAM**              | No GUI overhead — you're the only user, scripts are faster                                          |
| **CSV for nesting**                | e-rozrys/e-rozkroj are widely used by Polish CNC shops — interop matters more than elegance         |
| **You buy the material**           | Common in Poland — you control margins, but you need accurate cost estimation _before_ ordering     |
| **No islands / slants in v1**      | Scope control — 80% of Wrocław flats are rectangular kitchens anyway                                |

---

## What Needs to Be Built

```
┌─────────────────────────────────────────────────────┐
│                 kitchen-app (web)                    │
│  Predefined layouts + decor picker + 2.5D preview   │
└──────────────┬──────────────────────────────────────┘
               │ shares layout structure
               ▼
┌─────────────────────────────────────────────────────┐
│              kitchen-plugin (web/app)                │
│  2D row editor + cabinet config + cost estimation   │
│  Output: INTERMEDIATE FORMAT (JSON/YAML)             │
└──────────────┬──────────────────────────────────────┘
               │ intermediate format
               ▼
┌─────────────────────────────────────────────────────┐
│              Blender Backend (Python)                │
│  Read intermediate → apply Kronospan/Egger textures │
│  → generate renders for customer approval            │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│              CLI Tools (Python)                      │
│  1. Cut list CSV → e-rozrys / e-rozkroj             │
│  2. System32 drilling → DXF for CNC company         │
│  3. Cost estimation (board + accessories + nesting)  │
└─────────────────────────────────────────────────────┘
```

---

## Open Questions

1. **The intermediate format** — do you already have a schema in mind, or should we design it together? This is the most critical piece.
2. **2.5D rendering** — do you want Blender Cycles/EEVEE photorealistic, or a stylized top-down/angled view?
3. **Standard cabinet library** — do you have a catalog of your typical units (dimensions, hardware, construction method)?
4. **System32 specifics** — what's your boring pattern? (e.g., 32mm from top/bottom, 5mm shelf pins, Blum or Hettich hinges?)
5. **CNC company** — which shop in Wrocław? What format do they actually accept? (DXF? MPR? HOMAG? Biesse?)
