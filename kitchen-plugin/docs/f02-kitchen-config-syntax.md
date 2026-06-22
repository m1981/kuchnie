# Kitchen Layout Config — Syntax Design

Design for a JSON config format that describes a European kitchen layout.
The plugin reads this config and recreates the kitchen in Blender.

**Philosophy:** Describe WHAT, not HOW. The config is the contract between
the designer (human or AI agent) and the renderer (Blender plugin).

---

## 1. Schema Overview

```json
{
  "version": "1.0",
  "units": "mm",
  "name": "Kuchnia Warsaw 3.2m",

  "settings": { ... },
  "materials": { ... },

  "runs": [
    {
      "label": "back wall",
      "base": [ ... ],
      "upper": [ ... ]
    },
    {
      "label": "left wall",
      "turn": "left",
      "base": [ ... ],
      "upper": [ ... ]
    }
  ]
}
```

**Key concepts:**

- **Run** = a segment of cabinets along one wall
- **Base** = floor-level cabinets (plinth + carcass + countertop)
- **Upper** = wall-mounted cabinets (above countertop)
- **Tall** = floor-to-ceiling cabinets (oven housing, pantry)
- **Turn** = direction change between runs (at a corner)

---

## 2. Global Settings

```json
"settings": {
  "baseBodyHeight": 720,
  "baseDepth": 560,
  "wallHeight": 720,
  "wallDepth": 300,
  "tallHeight": 2000,
  "tallDepth": 560,

  "plinthHeight": 120,
  "plinthSetback": 60,

  "counterThickness": 30,
  "counterOverhangFront": 20,
  "counterOverhangEnd": 30,

  "wallMountHeight": 1400,

  "cabinetGap": 0,
  "frontGap": 2
}
```

| Property               | Default | Description                                 |
| ---------------------- | ------- | ------------------------------------------- |
| `baseBodyHeight`       | 720     | Carcass height without plinth (mm)          |
| `baseDepth`            | 560     | Carcass depth, not including countertop     |
| `wallHeight`           | 720     | Wall cabinet height                         |
| `wallDepth`            | 300     | Wall cabinet depth                          |
| `tallHeight`           | 2000    | Tall cabinet height                         |
| `tallDepth`            | 560     | Tall cabinet depth                          |
| `plinthHeight`         | 120     | Plinth/baseboard height                     |
| `plinthSetback`        | 60      | How far plinth is set back from front       |
| `counterThickness`     | 30      | Countertop thickness                        |
| `counterOverhangFront` | 20      | Countertop overhang past cabinet front      |
| `counterOverhangEnd`   | 30      | Countertop overhang at open ends            |
| `wallMountHeight`      | 1400    | Height from floor to bottom of wall cabinet |
| `cabinetGap`           | 0       | Gap between carcass boxes (usually flush)   |
| `frontGap`             | 2       | Visible gap between door/drawer fronts      |

**Note on backward compatibility:** Old configs using `"gap": 2` will automatically migrate to `"frontGap": 2` with `"cabinetGap": 0`. The new settings take precedence if both are specified.

---

## 3. Materials

```json
"materials": {
  "carcass":    { "color": [0.90, 0.90, 0.88] },
  "front":      { "color": [0.85, 0.85, 0.82] },
  "counter":    { "color": [0.72, 0.70, 0.68] },
  "plinth":     { "color": [0.60, 0.60, 0.60] },
  "handle":     { "color": [0.25, 0.25, 0.25] },
  "glass":      { "color": [0.90, 0.95, 1.00], "alpha": 0.15 },
  "backsplash": { "color": [0.80, 0.80, 0.78] },
  "filler":     { "color": [0.85, 0.85, 0.82] }
}
```

Each color is `[R, G, B]` or `[R, G, B, A]` in 0–1 range.
Materials are referenced by name; the plugin creates Blender Cycles materials.

---

## 4. Run Structure

A run is a linear segment of cabinets along one wall.

### First run

```json
{
  "label": "back wall",
  "base": [ ... ],
  "upper": [ ... ]
}
```

No `turn` — the first run defines the starting direction.

### Subsequent runs

```json
{
  "label": "left wall",
  "turn": "left",
  "base": [ ... ],
  "upper": [ ... ]
}
```

`turn` is relative to the **direction of travel** of the previous run:

- `"left"` — turn 90° left
- `"right"` — turn 90° right

### Sections within a run

| Section | Height                | Contents                             |
| ------- | --------------------- | ------------------------------------ |
| `base`  | floor to countertop   | Base cabinets, sink, corner, drawers |
| `upper` | wall mount to ceiling | Wall cabinets                        |
| `tall`  | floor to ceiling      | Oven housing, pantry, fridge         |

A run can have any combination of sections.

### Corner cabinets

Corner cabinets are the **last** cabinet in a `base` array. The next run
specifies the turn direction. The plugin handles the geometry.

```json
{
    "runs": [
        {
            "label": "back wall",
            "base": [
                { "type": "base-door", "width": 600 },
                { "type": "corner-blind", "width": 900, "blindDepth": 400 }
            ]
        },
        {
            "label": "left wall",
            "turn": "left",
            "base": [{ "type": "base-door", "width": 600 }]
        }
    ]
}
```

---

## 5. Cabinet Types

### Naming Convention

```
{level}-{front-type}

level:        base | wall | tall | corner | filler
front-type:   door | door-double | drawers | drawer-door |
              sink | glass | lift-up | oven | fridge | pantry
```

### Complete Type List

| Type               | Level | Description                        |
| ------------------ | ----- | ---------------------------------- |
| `base-door`        | base  | Single door, left or right opening |
| `base-door-double` | base  | Double doors, center hinged        |
| `base-drawers`     | base  | 2–4 drawer fronts                  |
| `base-drawer-door` | base  | Top drawer + door below            |
| `base-sink`        | base  | Double door, sink cutout           |
| `corner-blind`     | base  | Blind corner cabinet               |
| `corner-diagonal`  | base  | 45° diagonal corner                |
| `wall-door`        | wall  | Single door, left or right         |
| `wall-door-double` | wall  | Double doors                       |
| `wall-drawers`     | wall  | Drawers at wall height             |
| `wall-glass`       | wall  | Glass front panel                  |
| `wall-lift-up`     | wall  | Lift-up door (AVENTOS style)       |
| `tall-oven`        | tall  | Built-in oven housing              |
| `tall-fridge`      | tall  | Built-in fridge housing            |
| `tall-pantry`      | tall  | Full-height pantry                 |
| `filler`           | base  | Filler strip at wall/end           |

---

## 6. Cabinet Properties Reference

### Common Properties (all types)

```json
{
    "type": "base-door",
    "width": 600,
    "depthOffset": 0,
    "heightOffset": 0,
    "xShift": 0,
    "yShift": 0,
    "zShift": 0,
    "handle": { "type": "rail", "position": "auto" },
    "material": null
}
```

| Property       | Type   | Default  | Description                       |
| -------------- | ------ | -------- | --------------------------------- |
| `type`         | string | required | Cabinet type (see table above)    |
| `width`        | number | required | Cabinet width in mm               |
| `depthOffset`  | number | 0        | Adjust depth relative to default  |
| `heightOffset` | number | 0        | Adjust height relative to default |
| `xShift`       | number | 0        | Shift along wall direction        |
| `yShift`       | number | 0        | Shift perpendicular to wall       |
| `zShift`       | number | 0        | Shift vertically                  |
| `handle`       | object | null     | Handle specification              |
| `material`     | string | null     | Override material name            |

### base-door

```json
{
    "type": "base-door",
    "width": 600,
    "door": "right",
    "shelves": 1,
    "handle": { "type": "rail", "position": "auto" }
}
```

| Property  | Type   | Default   | Description                             |
| --------- | ------ | --------- | --------------------------------------- |
| `door`    | string | `"right"` | `"left"` or `"right"` opening direction |
| `shelves` | number | 1         | Number of shelves (for inventory)       |

### base-door-double

```json
{
    "type": "base-door-double",
    "width": 800,
    "shelves": 2,
    "handle": { "type": "rail", "position": "auto" }
}
```

### base-drawers

```json
{
    "type": "base-drawers",
    "width": 600,
    "drawers": 3,
    "handle": { "type": "rail", "position": "centered" }
}
```

| Property  | Type            | Default | Description                                    |
| --------- | --------------- | ------- | ---------------------------------------------- |
| `drawers` | number or array | 3       | Count (equal heights) or `[h1, h2, ...]` in mm |

```json
// Equal drawers:
"drawers": 3

// Graduated (tallest at bottom):
"drawers": [150, 200, 300]

// Precise heights:
"drawers": [120, 160, 200, 240]
```

### base-drawer-door

```json
{
    "type": "base-drawer-door",
    "width": 600,
    "drawerHeight": 150,
    "door": "right",
    "shelves": 1,
    "handle": { "type": "gola" }
}
```

| Property       | Type   | Default   | Description                         |
| -------------- | ------ | --------- | ----------------------------------- |
| `drawerHeight` | number | 150       | Height of the top drawer (mm)       |
| `door`         | string | `"right"` | Door opening direction below drawer |

### base-sink

```json
{
    "type": "base-sink",
    "width": 800,
    "door": "double",
    "handle": { "type": "rail" }
}
```

| Property | Type   | Default    | Description                        |
| -------- | ------ | ---------- | ---------------------------------- |
| `door`   | string | `"double"` | `"double"`, `"left"`, or `"right"` |

### corner-blind

```json
{
    "type": "corner-blind",
    "width": 900,
    "blindDepth": 400,
    "blindSide": "left",
    "door": "right",
    "shelves": 1,
    "handle": { "type": "rail" }
}
```

| Property     | Type   | Default   | Description                        |
| ------------ | ------ | --------- | ---------------------------------- |
| `blindDepth` | number | 300       | Depth of hidden section (mm)       |
| `blindSide`  | string | `"left"`  | Which side the blind section is on |
| `door`       | string | `"right"` | Door opening direction             |
| `shelves`    | number | 1         | Shelf count                        |

The `blindSide` determines which end of the cabinet is hidden:

- `"left"` — blind zone on left, door on right
- `"right"` — blind zone on right, door on left

### corner-diagonal

```json
{
    "type": "corner-diagonal",
    "width": 900,
    "door": "double",
    "shelves": 1,
    "handle": { "type": "rail" }
}
```

The plugin cuts the diagonal automatically based on `baseDepth`.

### wall-door

```json
{
    "type": "wall-door",
    "width": 600,
    "door": "right",
    "shelves": 1,
    "handle": { "type": "rail" }
}
```

### wall-door-double

```json
{
    "type": "wall-door-double",
    "width": 800,
    "shelves": 2,
    "handle": { "type": "rail" }
}
```

### wall-drawers

```json
{
    "type": "wall-drawers",
    "width": 600,
    "drawers": 2,
    "handle": { "type": "rail" }
}
```

### wall-glass

```json
{
    "type": "wall-glass",
    "width": 600,
    "door": "right",
    "glassRatio": 0.15,
    "handle": { "type": "rail" }
}
```

| Property     | Type   | Default | Description                    |
| ------------ | ------ | ------- | ------------------------------ |
| `glassRatio` | number | 0.15    | Frame-to-glass ratio (0.1–0.3) |

### wall-lift-up

```json
{
    "type": "wall-lift-up",
    "width": 600,
    "handle": { "type": "rail", "position": "bottom" }
}
```

Lift-up door opens upward. Handle at bottom edge.

### tall-oven

```json
{
    "type": "tall-oven",
    "width": 600,
    "ovenHeight": 600,
    "door": "right",
    "shelves": 1,
    "handle": { "type": "rail" }
}
```

| Property     | Type   | Default | Description                    |
| ------------ | ------ | ------- | ------------------------------ |
| `ovenHeight` | number | 600     | Height of the oven cutout (mm) |

The tall-oven has:

- Top section: door with shelves
- Middle section: oven cutout (open)
- Bottom section: door with shelves

### tall-fridge

```json
{
    "type": "tall-fridge",
    "width": 600,
    "fridgeHeight": 1800,
    "door": "right",
    "handle": { "type": "rail" }
}
```

| Property       | Type   | Default | Description                      |
| -------------- | ------ | ------- | -------------------------------- |
| `fridgeHeight` | number | 1800    | Height of the fridge cutout (mm) |

### tall-pantry

```json
{
    "type": "tall-pantry",
    "width": 600,
    "door": "right",
    "shelves": 4,
    "handle": { "type": "rail" }
}
```

### filler

```json
{
    "type": "filler",
    "width": 100
}
```

Filler strip at the end of a run, against a wall. No door, no handle.
The plugin makes it flush with the cabinet fronts.

---

## 7. Handle System

### Handle Types

| Type             | String       | Description                        |
| ---------------- | ------------ | ---------------------------------- |
| Rail (bar)       | `"rail"`     | Horizontal bar, mounted on surface |
| Gola (edge pull) | `"gola"`     | Recessed profile along top edge    |
| Recessed         | `"recessed"` | J-pull or C-pull cut into edge     |
| Knob             | `"knob"`     | Round knob                         |
| Push-to-open     | `"push"`     | No handle, touch to open           |
| None             | `"none"`     | No handle, no mechanism            |

### Handle Object

```json
{
    "handle": {
        "type": "rail",
        "length": 160,
        "projection": 35,
        "position": "auto",
        "offsetX": 0,
        "offsetZ": 0
    }
}
```

| Property     | Type   | Default  | Description                          |
| ------------ | ------ | -------- | ------------------------------------ |
| `type`       | string | `"rail"` | Handle type (see table)              |
| `length`     | number | auto     | Handle bar length in mm (rail only)  |
| `projection` | number | 35       | How far handle sticks out (mm)       |
| `position`   | string | `"auto"` | Placement (see below)                |
| `offsetX`    | number | 0        | Horizontal offset from auto position |
| `offsetZ`    | number | 0        | Vertical offset from auto position   |

### Handle Position

| Position     | Description                                    |
| ------------ | ---------------------------------------------- |
| `"auto"`     | Plugin decides based on cabinet type and level |
| `"centered"` | Center of door/drawer front                    |
| `"top"`      | Top edge (Gola system)                         |
| `"bottom"`   | Bottom edge                                    |
| `"left"`     | Left side                                      |
| `"right"`    | Right side                                     |

**Auto-positioning rules (plugin implements these):**

| Cabinet      | Level | Handle position                           |
| ------------ | ----- | ----------------------------------------- |
| Base door    | floor | 100mm from bottom, hinge-side edge        |
| Base drawer  | floor | centered horizontally, or top edge (Gola) |
| Wall door    | wall  | 100mm from bottom, hinge-side edge        |
| Wall lift-up | wall  | bottom edge of door                       |
| Tall door    | tall  | 1000mm from floor                         |

### Gola System

When `handle.type = "gola"`:

- No visible handle object is created
- A recessed profile is added along the top edge of drawers
- For doors, the profile is on the hinge-side edge
- Profile color: aluminum (material override)

```json
{
    "handle": { "type": "gola" }
}
```

### Push-to-Open

When `handle.type = "push"`:

- No handle object
- No profile
- Clean flat front

```json
{
    "handle": { "type": "push" }
}
```

---

## 8. Gap System

### Two Types of Gap

European frameless kitchens have two distinct gap concepts:

| Setting      | Purpose                     | Typical Value | Example                        |
| ------------ | --------------------------- | ------------- | ------------------------------ |
| `cabinetGap` | Space between carcass boxes | 0mm (flush)   | Carcass-to-carcass spacing     |
| `frontGap`   | Visible gap between fronts  | 2–3mm         | Door-to-door, drawer-to-drawer |

**Why two settings?**

- Carcasses are typically installed flush (0mm gap) for maximum storage
- The visible 2–3mm gap is ONLY between door/drawer fronts for aesthetics
- Countertops sit directly on carcasses (use cabinetGap)
- Plinths are flush with carcass fronts

### Default Settings

```json
"settings": {
    "cabinetGap": 0,
    "frontGap": 2
}
```

### Per-Cabinet Front Gap Override

```json
{
    "type": "base-drawers",
    "width": 600,
    "drawers": 3,
    "frontGap": 3
}
```

### What Uses Which Gap

| Spacing                       | Setting      | Typical |
| ----------------------------- | ------------ | ------- |
| Carcass to carcass            | `cabinetGap` | 0mm     |
| Drawer front to drawer front  | `frontGap`   | 2–3mm   |
| Door to door (double cabinet) | `frontGap`   | 2–3mm   |
| Door to drawer (same cabinet) | `frontGap`   | 2–3mm   |
| Countertop to countertop      | `cabinetGap` | 0mm     |
| Plinth to plinth              | `cabinetGap` | 0mm     |

### Backward Compatibility

Old configs using `"gap": 2` are automatically migrated:

- `"gap"` → `"frontGap": 2`
- `"cabinetGap"` defaults to `0`

### Front Flush Alignment

All cabinet fronts are on the same plane (European frameless).
The plugin handles this automatically — no config needed.

---

## 9. Countertop

Countertop is generated automatically for each `base` run.

### Per-Run Countertop Override

```json
{
  "label": "back wall",
  "countertop": {
    "thickness": 40,
    "overhangFront": 30,
    "overhangEnd": 50,
    "edge": true
  },
  "base": [ ... ]
}
```

| Property        | Type    | Default       | Description            |
| --------------- | ------- | ------------- | ---------------------- |
| `thickness`     | number  | from settings | Countertop thickness   |
| `overhangFront` | number  | from settings | Front overhang         |
| `overhangEnd`   | number  | from settings | Overhang at open ends  |
| `edge`          | boolean | true          | Add visible edge strip |

The countertop spans the full width of the run, including corner cabinets.
Filler strips and corner cabinets are counted in the total.

---

## 10. Layout Examples

### I-Shape (Single Row)

```
  ┌──┬──┬──┬──┬──┐
  │  │  │  │  │  │
  └──┴──┴──┴──┴──┘
  back wall
```

```json
{
    "version": "1.0",
    "units": "mm",
    "name": "I-Shape Kitchen 3.0m",

    "settings": {
        "baseBodyHeight": 720,
        "baseDepth": 560,
        "wallHeight": 720,
        "wallDepth": 300,
        "plinthHeight": 120,
        "counterThickness": 30,
        "counterOverhangFront": 20,
        "cabinetGap": 0,
        "frontGap": 2
    },

    "runs": [
        {
            "label": "back wall",
            "base": [
                { "type": "filler", "width": 50 },
                {
                    "type": "base-drawer-door",
                    "width": 600,
                    "drawerHeight": 150,
                    "door": "right",
                    "handle": { "type": "rail", "length": 160 }
                },
                { "type": "base-sink", "width": 800, "handle": { "type": "rail", "length": 192 } },
                {
                    "type": "base-drawers",
                    "width": 600,
                    "drawers": 3,
                    "handle": { "type": "rail", "length": 160 }
                },
                {
                    "type": "base-door",
                    "width": 600,
                    "door": "right",
                    "handle": { "type": "rail", "length": 160 }
                },
                {
                    "type": "tall-oven",
                    "width": 600,
                    "ovenHeight": 600,
                    "door": "right",
                    "handle": { "type": "rail", "length": 160 }
                },
                { "type": "filler", "width": 50 }
            ],
            "upper": [
                { "type": "filler", "width": 50 },
                {
                    "type": "wall-door",
                    "width": 600,
                    "door": "right",
                    "handle": { "type": "rail", "length": 160 }
                },
                {
                    "type": "wall-lift-up",
                    "width": 800,
                    "handle": { "type": "rail", "length": 192 }
                },
                {
                    "type": "wall-door-double",
                    "width": 600,
                    "handle": { "type": "rail", "length": 128 }
                },
                {
                    "type": "wall-door",
                    "width": 600,
                    "door": "left",
                    "handle": { "type": "rail", "length": 160 }
                },
                { "type": "filler", "width": 50 }
            ]
        }
    ]
}
```

### L-Shape

```
  ┌──┬──┬──┬──┐
  │  │  │  │  │
  ├──┼──┼──┼──┘
  │  │
  │  │
  └──┘
  back wall      left wall
```

```json
{
    "version": "1.0",
    "units": "mm",
    "name": "L-Shape Kitchen",

    "settings": {
        "baseBodyHeight": 720,
        "baseDepth": 560,
        "wallHeight": 600,
        "wallDepth": 300,
        "plinthHeight": 120,
        "counterThickness": 30,
        "counterOverhangFront": 20,
        "cabinetGap": 0,
        "frontGap": 2
    },

    "runs": [
        {
            "label": "back wall",
            "base": [
                { "type": "filler", "width": 50 },
                {
                    "type": "tall-oven",
                    "width": 600,
                    "ovenHeight": 600,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                {
                    "type": "base-drawer-door",
                    "width": 600,
                    "drawerHeight": 150,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                { "type": "base-sink", "width": 800, "handle": { "type": "rail" } },
                {
                    "type": "base-drawers",
                    "width": 600,
                    "drawers": 3,
                    "handle": { "type": "rail" }
                },
                {
                    "type": "corner-blind",
                    "width": 900,
                    "blindDepth": 400,
                    "blindSide": "right",
                    "door": "left",
                    "handle": { "type": "rail" }
                }
            ],
            "upper": [
                { "type": "filler", "width": 50 },
                { "type": "wall-lift-up", "width": 600, "handle": { "type": "rail" } },
                {
                    "type": "wall-door",
                    "width": 600,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                { "type": "wall-lift-up", "width": 800, "handle": { "type": "rail" } },
                { "type": "wall-door-double", "width": 600, "handle": { "type": "rail" } },
                { "type": "wall-glass", "width": 600, "door": "left", "handle": { "type": "rail" } }
            ]
        },
        {
            "label": "left wall",
            "turn": "left",
            "base": [
                {
                    "type": "base-door",
                    "width": 600,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                {
                    "type": "base-drawers",
                    "width": 400,
                    "drawers": [120, 160, 200],
                    "handle": { "type": "gola" }
                },
                { "type": "base-door", "width": 600, "door": "left", "handle": { "type": "rail" } },
                { "type": "filler", "width": 50 }
            ],
            "upper": [
                {
                    "type": "wall-door",
                    "width": 600,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                {
                    "type": "wall-door",
                    "width": 400,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                { "type": "wall-door", "width": 600, "door": "left", "handle": { "type": "rail" } },
                { "type": "filler", "width": 50 }
            ]
        }
    ]
}
```

### U-Shape

```
  ┌──┬──┬──┬──┬──┐
  │  │  │  │  │  │
  │  ├──┼──┼──┤  │
  │  │        │  │
  └──┘        └──┘
  left wall   right wall
       back wall
```

```json
{
    "version": "1.0",
    "units": "mm",
    "name": "U-Shape Kitchen",

    "settings": {
        "baseBodyHeight": 720,
        "baseDepth": 560,
        "wallHeight": 600,
        "wallDepth": 300,
        "plinthHeight": 120,
        "counterThickness": 30,
        "counterOverhangFront": 20,
        "cabinetGap": 0,
        "frontGap": 2
    },

    "runs": [
        {
            "label": "left wall",
            "base": [
                { "type": "filler", "width": 50 },
                {
                    "type": "tall-oven",
                    "width": 600,
                    "ovenHeight": 600,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                {
                    "type": "base-drawer-door",
                    "width": 600,
                    "drawerHeight": 150,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                {
                    "type": "corner-blind",
                    "width": 900,
                    "blindDepth": 400,
                    "blindSide": "right",
                    "door": "left",
                    "handle": { "type": "rail" }
                }
            ],
            "upper": [
                { "type": "filler", "width": 50 },
                { "type": "wall-lift-up", "width": 600, "handle": { "type": "rail" } },
                {
                    "type": "wall-door",
                    "width": 600,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                { "type": "wall-glass", "width": 600, "door": "left", "handle": { "type": "rail" } }
            ]
        },
        {
            "label": "back wall",
            "turn": "right",
            "base": [
                { "type": "base-sink", "width": 800, "handle": { "type": "rail" } },
                {
                    "type": "base-drawers",
                    "width": 600,
                    "drawers": 3,
                    "handle": { "type": "gola" }
                },
                { "type": "base-door-double", "width": 900, "handle": { "type": "rail" } }
            ],
            "upper": [
                { "type": "wall-lift-up", "width": 800, "handle": { "type": "rail" } },
                { "type": "wall-door-double", "width": 600, "handle": { "type": "rail" } },
                { "type": "wall-door-double", "width": 900, "handle": { "type": "rail" } }
            ]
        },
        {
            "label": "right wall",
            "turn": "right",
            "base": [
                {
                    "type": "base-drawers",
                    "width": 600,
                    "drawers": 4,
                    "handle": { "type": "gola" }
                },
                { "type": "base-door", "width": 600, "door": "left", "handle": { "type": "rail" } },
                {
                    "type": "tall-fridge",
                    "width": 600,
                    "fridgeHeight": 1800,
                    "door": "left",
                    "handle": { "type": "rail" }
                },
                { "type": "filler", "width": 50 }
            ],
            "upper": [
                {
                    "type": "wall-door",
                    "width": 600,
                    "door": "right",
                    "handle": { "type": "rail" }
                },
                { "type": "wall-door", "width": 600, "door": "left", "handle": { "type": "rail" } }
            ]
        }
    ]
}
```

---

## 11. Coordinate System

The plugin places cabinets in Blender's coordinate system:

```
  First run direction: +X (east)

  Z (up)
  │
  │   Y (toward viewer)
  │  /
  │ /
  └───────── X (right)

  Wall is at Y=0
  Cabinet fronts face -Y (toward viewer)
  Plinth is below Z=0
```

### Position Calculation

The plugin calculates positions automatically:

1. First cabinet in a run starts at `(0, 0, plinthHeight)` for base
2. Each subsequent cabinet: `x += previous.width + gap` (or `y` if turned)
3. Corner cabinet triggers a turn:
    - Turn left: next run goes in +Y direction
    - Turn right: next run goes in -Y direction
4. Wall cabinets: same X positions, at `Z = wallMountHeight`
5. Tall cabinets: same X positions, at `Z = 0`

---

## 12. Plugin Mapping

How config properties map to existing `CabinetProperties`:

| Config Property         | CabinetProperty         | Notes                              |
| ----------------------- | ----------------------- | ---------------------------------- |
| `width`                 | `sX`                    | Direct mapping (mm → m conversion) |
| `depthOffset`           | `wY`                    |                                    |
| `heightOffset`          | `wZ`                    |                                    |
| `xShift`                | `pX`                    |                                    |
| `yShift`                | `pY`                    |                                    |
| `zShift`                | `pZ`                    |                                    |
| `door: "left"`          | `dType: "2"`            | Single L                           |
| `door: "right"`         | `dType: "1"`            | Single R                           |
| `door: "double"`        | `dType: "8"`            | Double                             |
| `drawers: N`            | `dType: "7"`, `dNum: N` |                                    |
| `shelves`               | `sNum`                  |                                    |
| `glassRatio`            | `gF`                    |                                    |
| `handle.type != "none"` | `hand: true`            |                                    |
| `handle.type == "none"` | `hand: false`           |                                    |
| `blindDepth`            | new property            | Not yet in plugin                  |
| `handle.type`           | new property            | Not yet in plugin                  |

### New Properties Needed in Plugin

```python
# Add to CabinetProperties:
blind_depth: FloatProperty(name='Blind depth', ...)
handle_type: EnumProperty(items=(
    ('1', "Rail", ""),
    ('2', "Gola", ""),
    ('3', "Recessed", ""),
    ('4', "Knob", ""),
    ('5', "Push", ""),
    ('9', "None", ""),
))
handle_length: FloatProperty(name='Handle length', ...)
```

---

## 13. Validation Rules

The plugin should validate the config before generating:

| Rule                 | Description                                         |
| -------------------- | --------------------------------------------------- |
| Corner at end of run | Corner cabinets must be the last in a `base` array  |
| Turn matches corner  | Next run's `turn` must be valid for the corner type |
| Width > 0            | All widths must be positive                         |
| blindDepth < width   | Blind depth must be less than total width           |
| drawers in range     | Drawer count: 1–6, or array length 1–6              |
| Sum of widths        | Total run width should be reasonable (< 10m)        |
| glassRatio range     | 0.05–0.40                                           |
