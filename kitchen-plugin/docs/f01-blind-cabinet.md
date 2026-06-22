# F01 — Blind Corner Cabinet

Status: **Implemented** · Part of standalone kitchen generator

---

## Problem

The kitchen maker needed a **blind corner** cabinet — a rectangular cabinet
where a portion extends behind the adjacent cabinet run, with the door
only on the visible section.

Blind corners are one of the most common cabinet types in real kitchens
and are essential for realistic kitchen layouts.

---

## Geometry

```
        ┌─────────────────────── width ──────────────────────┐
        │                                                     │
        │  ┌── blind zone ──┐     ┌── visible zone ──┐       │
        │  │                │     │                   │       │
        │  │  (hidden behind│     │  Door here        │       │
  blind │  │  adjacent cab) │     │                   │       │
  depth │  │                │     │                   │       │
        │  └────────────────┘     └───────────────────┘       │
        │                                                     │
        └─────────────────────────────────────────────────────┘
```

**Key dimensions:**

- `width` — full cabinet width (including blind zone)
- `blindDepth` — how far the hidden section extends
- `blindSide` — which side the blind section is on (`"left"` or `"right"`)

**Door width** = `width - blindDepth - 0.001` (small offset for clearance)

---

## Implementation

### Config Format

```json
{
    "type": "corner-blind",
    "width": 900,
    "blindDepth": 400,
    "blindSide": "right",
    "door": "left",
    "shelves": 1,
    "handle": { "type": "rail", "length": 160 }
}
```

| Property     | Type   | Default   | Description                        |
| ------------ | ------ | --------- | ---------------------------------- |
| `width`      | number | required  | Full cabinet width (mm)            |
| `blindDepth` | number | 300       | Depth of hidden section (mm)       |
| `blindSide`  | string | `"left"`  | Which side the blind section is on |
| `door`       | string | `"right"` | Door opening direction             |
| `shelves`    | number | 1         | Shelf count                        |

### Config Parser (`config_parser.py`)

```python
# Cabinet type registration
CABINET_LEVELS = {
    ...
    "corner-blind": "base",
    ...
}

# Validation
if cab_type == "corner-blind":
    bd = cab.get("blindDepth", 300)
    if bd >= cab["width"]:
        raise ValueError(
            f"blindDepth ({bd}) must be < width ({cab['width']})"
        )
```

### Geometry Builder (`geometry_builder.py`)

```python
elif cab_type == "corner-blind":
    blind_depth = mm_to_m(cab.get("blindDepth", 300))
    door_w = w - blind_depth - 0.001
    _add_door_front(obj, door_w, h, front_thickness, cab, level,
                    x_offset=blind_depth + 0.001)
```

---

## Placement Rules

1. Corner cabinets must be **first or last** in a `base` array
2. The next run must specify a `turn` direction
3. The `blindSide` determines which end is hidden:
    - `"left"` — blind zone on left, door on right
    - `"right"` — blind zone on right, door on left

### Example: L-Shape with Blind Corner

```json
{
    "runs": [
        {
            "label": "back wall",
            "base": [
                { "type": "base-door", "width": 600 },
                {
                    "type": "corner-blind",
                    "width": 900,
                    "blindDepth": 400,
                    "blindSide": "right",
                    "door": "left"
                }
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

## Validation

The validator checks:

1. `blindDepth < width` — blind zone must be smaller than total width
2. Corner cabinet is first or last in run
3. Next run has `turn` direction specified

---

## Testing

```bash
# Run corner-related tests
.venv/bin/python -m pytest tests/test_l_shape.py tests/test_u_shape.py -v
```

Tests verify:

- Corner cabinet is last in run (L-shape)
- Corner cabinet is first in run (U-shape connecting run)
- Turn direction is present after corner
- blindDepth validation works correctly
