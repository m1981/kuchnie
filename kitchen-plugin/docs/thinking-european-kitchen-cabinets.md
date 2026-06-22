# European Kitchen Cabinet — Thinking Process

A cabinet maker's perspective on what needs modeling for rendering.

**Goal:** Understand the real-world system well enough to design a config
format that any agent (human or AI) can use to describe a kitchen layout,
and a Blender plugin that recreates it faithfully — modeling only what's
externally visible.

---

## Key Principle: External Only

For rendering, we need to model what the camera sees:

| Model                            | Skip              |
| -------------------------------- | ----------------- |
| Cabinet carcass (box shape)      | Internal shelves  |
| Door / drawer fronts (with gaps) | Drawer mechanisms |
| Plinth / baseboard               | Hinges            |
| Countertop with overhangs        | Internal dividers |
| Handles / edge pulls             | Cable management  |
| Filler strips at walls           | Ventilation holes |
| End panels (where visible)       | Shelf pins        |
| Backsplash                       | Drawer runners    |

---

## The 32mm System

European kitchens follow the **32mm system** (also called the "32mm boring
system"). This is the foundation:

- All drilling is in multiples of 32mm
- Hinge boring: 32mm apart
- Shelf pin holes: 32mm apart
- Drawer slide positions: 32mm increments
- This means all vertical positions are multiples of 32mm from a reference line

**For rendering:** This doesn't affect mesh generation directly, but it means
all dimensions are "round" in the 32mm grid. A config should use mm as the
unit (not meters or inches).

---

## Standard Dimensions (mm)

### Base Cabinets

```
                    ┌───── countertop (30-40mm thick) ─────┐
                    │                                       │
                    │  20-30mm overhang                     │
                    │  ┌─────────────────────────────────┐  │
                    │  │         door / drawers           │  │
  720mm (body)      │  │                                 │  │
                    │  │                                 │  │
                    │  └─────────────────────────────────┘  │
                    │                                       │
                    ├── 100-150mm plinth ───────────────────┤
                    │  (set back 50-80mm from front)        │
                    │                                       │
                    └──────────── 560-580mm deep ───────────┘
```

| Parameter                    | Standard  | Comfort   |
| ---------------------------- | --------- | --------- |
| Body height                  | 720mm     | 780mm     |
| Plinth height                | 100-150mm | 100-150mm |
| Total height (to countertop) | 820-870mm | 880-930mm |
| Body depth                   | 560mm     | 560mm     |
| With countertop depth        | 600mm     | 600mm     |
| Countertop thickness         | 30-40mm   | 20-40mm   |
| Countertop front overhang    | 20-30mm   | 20-30mm   |
| Countertop side overhang     | 0-30mm    | 0-30mm    |
| Plinth setback from front    | 50-80mm   | 50-80mm   |

### Standard Widths (module sizes)

```
300  400  450  500  600  800  900  1000  1200mm
```

Most common: **600mm** (matches appliance width: ovens, dishwashers)

### Wall Cabinets

```
                    ┌─────────────────────────────────┐
                    │                                 │
  360-720mm         │         door / lift-up          │
  (height)          │                                 │
                    │                                 │
                    └─────────────────────────────────┘
                    └── 300-350mm deep ──────────────┘
```

| Parameter                | Standard                          |
| ------------------------ | --------------------------------- |
| Heights                  | 360, 500, 600, 720mm              |
| Depth                    | 300-350mm (shallow), 560mm (tall) |
| Mounting height          | 450-600mm above countertop        |
| Bottom to countertop gap | 450-600mm                         |

### Tall / Pantry Cabinets

```
                    ┌─────────────────────────────────┐
                    │       top section (door)         │
  2000-2200mm       │                                 │
  (full height)     ├─────────────────────────────────┤
                    │       middle (pull-out)          │
                    │                                 │
                    ├─────────────────────────────────┤
                    │       bottom (drawers/door)      │
                    └─────────────────────────────────┘
                    └── 560-580mm deep ──────────────┘
```

---

## Cabinet Types

### 1. Base Cabinet — Single Door

```
  ┌───────────────┐
  │               │
  │    door       │   ← hinge left or right
  │               │
  │               │
  └───────────────┘
```

- Width: 300-600mm
- Door opens left or right
- 1-3 shelves inside (not modeled)

### 2. Base Cabinet — Double Doors

```
  ┌───────┬───────┐
  │       │       │
  │ left  │ right │   ← two doors, hinges on outer edges
  │       │       │
  │       │       │
  └───────┴───────┘
```

- Width: 600-1200mm
- Each door is half width

### 3. Base Cabinet — Drawers

```
  ┌───────────────┐
  │   drawer 1    │   ← smallest, top
  ├───────────────┤
  │   drawer 2    │   ← medium
  ├───────────────┤
  │   drawer 3    │   ← tallest, bottom
  └───────────────┘
```

- Width: 400-1200mm
- 2-4 drawer fronts
- Drawer heights: can be equal or graduated
- **Gap between drawer fronts: 2-3mm**

### 4. Base Cabinet — Drawer + Door

```
  ┌───────────────┐
  │   drawer      │   ← top drawer, narrower
  ├───────────────┤
  │               │
  │    door       │   ← full-height door below
  │               │
  └───────────────┘
```

- Very common configuration
- Top drawer is usually 100-150mm high
- Door below is the rest

### 5. Sink Base Cabinet

```
  ┌───────┬───────┐
  │ false │ false │   ← false front (decorative, doesn't open)
  │ front │ front │
  ├───────┴───────┤
  │               │
  │    door       │   ← double door below sink
  │               │
  └───────────────┘
```

- Width: 600-1000mm
- No top drawer (sink cutout)
- Sometimes a tip-out tray at top

### 6. Corner Base — Blind Corner

```
  ┌─────────────────────── sx ──────────────────────┐
  │                                                  │
  │  ┌── blind zone ──┐     ┌── visible zone ──┐    │
  │  │                │     │                   │    │
  │  │  (hidden       │     │  door here        │    │
  │  │   behind       │     │                   │    │
  │  │   adjacent)    │     │                   │    │
  │  └────────────────┘     └───────────────────┘    │
  │                                                  │
  └──────────────────────────────────────────────────┘
```

- Total width: 900-1200mm
- Blind depth: 300-400mm
- Door width: visible section only
- **Key:** the blind section is hidden behind the adjacent cabinet run

### 7. Corner Base — Diagonal

```
        ┌──────────┐
       /            \
      /    door      \
     /                \
    └──────────────────┘
```

- Width at corner: 900-1200mm
- Door is diagonal (45°)
- Already implemented as types 9/10 in plugin

### 8. Wall Cabinet — Standard

```
  ┌───────────────┐
  │               │
  │    door       │
  │               │
  └───────────────┘
```

- Single or double doors
- Heights: 360, 500, 600, 720mm
- Depth: 300-350mm

### 9. Wall Cabinet — Lift-Up Door

```
  ┌───────────────┐
  │               │
  │    lift-up    │   ← opens upward (AVENTOS by Blum)
  │    door       │
  │               │
  └───────────────┘
```

- Common in European kitchens
- Handle at bottom edge of door
- Door swings up, not sideways

### 10. Wall Cabinet — Glass Front

```
  ┌───────────────┐
  │ ┌───────────┐ │
  │ │   glass   │ │
  │ │   panel   │ │
  │ └───────────┘ │
  └───────────────┘
```

- Aluminum or wood frame
- Glass center panel
- Contents visible (mugs, plates)
- May have internal lighting

### 11. Tall Cabinet — Oven Housing

```
  ┌───────────────┐
  │   top door    │
  ├───────────────┤
  │               │
  │    oven       │   ← cutout for built-in oven
  │    opening    │
  │               │
  ├───────────────┤
  │  bottom door  │
  └───────────────┘
```

- Width: 600mm (standard oven)
- Opening height: ~600mm
- Total height: 2000-2200mm

### 12. Tall Cabinet — Fridge Housing

```
  ┌───────────────┐
  │   top panel   │   ← decorative panel above fridge
  ├───────────────┤
  │               │
  │    fridge     │   ← cutout for built-in fridge
  │    opening    │
  │               │
  └───────────────┘
```

- Width: 600-700mm
- Depth: 560-600mm

### 13. Island Cabinet

```
  ┌───────────────────────────┐
  │                           │
  │   front (door/drawers)    │   ← main working side
  │                           │
  ├───────────────────────────┤
  │   back panel (finished)   │   ← visible, needs end panel
  └───────────────────────────┘
```

- All sides must be finished
- Can have seating overhang (200-300mm)
- May have sink or cooktop

---

## Gaps and Spacing (Critical for Rendering)

This is what makes a kitchen look realistic vs. a CAD drawing:

### Between Cabinet Fronts

| Gap Type                         | Size  | Notes                                 |
| -------------------------------- | ----- | ------------------------------------- |
| Door to door (adjacent cabinets) | 0mm   | Cabinets butted together, doors flush |
| Drawer front to drawer front     | 2-3mm | Clearance gap                         |
| Door to drawer front             | 2-3mm | In same cabinet                       |
| Door to door (in same cabinet)   | 2-3mm | Double door cabinet                   |
| Countertop to countertop         | 0mm   | Mitered or butted                     |

### Front Face Alignment

All cabinet fronts are **flush** in European frameless systems:

```
  side view:
  ┌──┐ ┌──┐ ┌──┐
  │  │ │  │ │  │   ← all fronts aligned on same plane
  │  │ │  │ │  │
  └──┘ └──┘ └──┘
  ───────────────  ← flush line
```

### Countertop Overhang

```
  top view:
  ┌─────────────────┐
  │                 │  ← countertop extends
  │  ┌───────────┐  │
  │  │  cabinet  │  │  ← 20-30mm front overhang
  │  └───────────┘  │
  │                 │  ← 0-30mm side overhang (at ends only)
  └─────────────────┘
```

### Plinth Setback

```
  side view:
  ┌────────────────────┐
  │                    │  ← cabinet body
  │                    │
  │                    │
  └────────────────────┘
       ┌──────────┐      ← plinth set back 50-80mm
       │          │
       └──────────┘
```

---

## Handle Types

### 1. Edge Pull (Gola System)

```
  side view of drawer:
  ┌──────────────────┐
  │                  │
  │                  │
  │                  │
  └──────┐           │
         │  ← gola   │   ← recessed profile along top edge
         └───────────┘
```

- **Gola A**: For wall cabinets (aluminum profile at bottom)
- **Gola C**: For base cabinets (aluminum profile at top of drawer)
- No visible handle — just a recessed groove
- Very common in modern European kitchens
- Profile: aluminum, color-matched or contrasting

### 2. Rail Handle (Bar)

```
  front view:
  ┌───────────────────┐
  │                   │
  │  ═══════════════  │   ← horizontal bar
  │                   │
  └───────────────────┘
```

- Lengths: 96, 128, 160, 192, 224, 256, 320mm
- Projection: 30-40mm from surface
- Centered on door/drawer, or offset
- Material: stainless steel, brushed nickel, matte black

### 3. Edge Pull (Recessed)

```
  side view:
  ┌──────────────────┐
  │                  │
  │                  │
  │                  │
  └──┐               │
     │  ← recessed   │   ← finger pull recessed into edge
     └───────────────┘
```

- J-pull or C-pull profile
- Cut into the door/drawer edge itself
- No protruding handle

### 4. Knob

```
  front view:
  ┌───────────────────┐
  │                   │
  │         ●         │   ← round knob
  │                   │
  └───────────────────┘
```

- Diameter: 30-50mm
- Projection: 20-30mm
- Material: metal, wood, ceramic

### 5. Bar Handle (Mounted)

```
  front view:
  ┌───────────────────┐
  │                   │
  │      ┌─────┐      │   ← bar mounted on surface
  │      └─────┘      │
  │                   │
  └───────────────────┘
```

- Two mounting points (posts)
- Length: 128-320mm
- Projection: 30-50mm

### 6. Push-to-Open

```
  ┌───────────────────┐
  │                   │
  │                   │   ← no handle at all
  │                   │
  └───────────────────┘
```

- Touch to open (mechanical or electric)
- Cleanest look
- Common in handleless modern kitchens

---

## Handle Positioning Rules

### Doors

```
  Base cabinet door:        Wall cabinet door:
  ┌───────────┐             ┌───────────┐
  │           │             │           │
  │           │             │           │
  │           │             │           │
  │     ●     │  ← 100mm   │           │
  │           │    from     │     ●     │  ← 100mm from bottom
  │           │    hinge    │           │
  └───────────┘    side     └───────────┘
```

- **Base doors**: handle ~100-200mm from bottom, on hinge-side edge
- **Wall doors**: handle ~100mm from bottom, on hinge-side edge
- **Tall doors**: handle ~1000mm from floor (comfort height)

### Drawers

```
  ┌───────────────────┐
  │                   │
  │   ═══════════════ │  ← handle centered horizontally
  │                   │     or on edge (Gola system)
  └───────────────────┘
```

- **Centered**: handle in middle of drawer front
- **Edge pull**: along top edge of drawer front
- **Gola**: recessed profile along top edge

---

## Kitchen Layout Patterns

### Single Row (Galley)

```
  ┌──┬──┬──┬──┬──┬──┐
  │  │  │  │  │  │  │  ← all cabinets along one wall
  └──┴──┴──┴──┴──┴──┘
```

### L-Shape

```
  ┌──┬──┬──┬──┐
  │  │  │  │  │
  ├──┼──┼──┼──┘
  │  │
  │  │
  └──┘
```

### U-Shape

```
  ┌──┬──┬──┬──┬──┐
  │  │  │  │  │  │
  │  └──┴──┴──┘  │
  │              │
  └──────────────┘
```

### Island

```
  ┌──┬──┬──┬──┬──┐
  │  │  │  │  │  │  ← perimeter cabinets
  │  │  │  │  │  │
  └──┴──┴──┴──┴──┘

       ┌──────┐
       │      │  ← island
       └──────┘
```

---

## Material System (Rendering Only)

For rendering, we need materials for:

| Part       | Material                      | Typical Colors                 |
| ---------- | ----------------------------- | ------------------------------ |
| Carcass    | Laminate/melamine             | White, grey, wood grain        |
| Door front | Laminate, lacquer, wood       | White, grey, wood, matte black |
| Countertop | HPL, compact laminate, quartz | White, grey, concrete, wood    |
| Plinth     | Aluminum or matching          | Aluminum, white, grey          |
| Handle     | Metal                         | Stainless, matte black, brass  |
| Backsplash | Tile, glass, HPL              | Various                        |

---

## Config Design Implications

Based on this analysis, a kitchen config needs:

1. **Global settings**: unit (mm), countertop spec, plinth spec, material palette
2. **Layout type**: single row, L-shape, U-shape, island
3. **Per-cabinet**: width, type, door style, handle type, gap specs
4. **Positioning**: relative to previous cabinet or absolute
5. **Rotation**: for L/U shapes, how cabinets turn at corners
6. **Wall info**: for wall cabinets, mounting height
7. **Filler strips**: at walls, width, material
8. **End panels**: where visible (end of run, island sides)

The config should **not** specify internal geometry — that's the plugin's job.
