# F01 — Blind Corner Cabinet

Status: **Design** · Target: `achm_kitchen_maker.py`

---

## Problem

The kitchen maker supports diagonal corner cabinets (`Corner L` type 9,
`Corner R` type 10) but lacks a **blind corner** — a rectangular cabinet
where a portion extends behind the adjacent cabinet run, with the door
only on the visible section.

Blind corners are one of the most common cabinet types in real kitchens
and are essential for realistic kitchen layouts.

---

## Geometry

```
        ┌─────────────────────── sx (width) ──────────────────────┐
        │                                                          │
        │  ┌── blind zone ──┐     ┌── visible zone ──┐            │
        │  │                │     │                   │            │
        │  │  (hidden behind│     │  Door here        │            │
  blind │  │  adjacent cab) │     │                   │            │
  depth │  │                │     │                   │            │
        │  └────────────────┘     └───────────────────┘            │
        │                                                          │
        └──────────────────────────────────────────────────────────┘
                                    sy (depth)
```

**Key dimensions:**

- `sx` — full cabinet width (including blind zone)
- `sy` — cabinet depth (same as adjacent cabinets)
- `blind_depth` — how far the hidden section extends

**Door width** = `sx - blind_depth - thickness - gap`

Two orientations:

- **Blind R** — door on the right, blind zone on the left
- **Blind L** — door on the left, blind zone on the right

---

## Comparison with Existing Corner Types

| Aspect      | Corner L/R (9/10)         | Blind Corner (12/13)                |
| ----------- | ------------------------- | ----------------------------------- |
| Box shape   | Rectangular               | Rectangular                         |
| Door style  | Diagonal, narrower        | Straight, offset                    |
| Door width  | `sx - depth - thickness`  | `sx - blind_depth - thickness`      |
| Hidden area | Door angled across corner | Box extends behind adjacent cabinet |
| New param   | —                         | `blind_depth`                       |

---

## Changes

### 1. `CabinetProperties` — New enum values + property

```python
# dType EnumProperty — add two new items:
('12', "Blind Corner R", "Blind corner, door on right"),
('13', "Blind Corner L", "Blind corner, door on left"),

# New property:
blind_depth: FloatProperty(
    name='Blind depth',
    min=0.001, max=10, default=0.30, precision=3,
    description='Depth of the hidden section behind adjacent cabinet',
)
```

### 2. `create_box()` — Door section

Add a new branch for `doortype == "12"` / `"13"` in the Doors section
(~line 960). Reuses existing `create_door()` with offset positioning:

```python
if doortype == "12" or doortype == "13":
    visible_width = sx - blind_depth - thickness - 0.001

    if doortype == "12":  # Blind R
        mydoor = create_door(type_cabinet, objname + "_Door", thickness,
                             visible_width, sz, "1", gf, mat, handle,
                             handle_model, handle_x, handle_z, 0.001)
        mydoor.location[0] = blind_depth + thickness
    else:  # Blind L
        mydoor = create_door(type_cabinet, objname + "_Door", thickness,
                             visible_width, sz, "2", gf, mat, handle,
                             handle_model, handle_x, handle_z, 0.001)
        mydoor.location[0] = 0

    mydoor.location[1] = -sy - 0.001
    mydoor.parent = myobject
    remove_doubles(mydoor)
    set_normals(mydoor)
```

### 3. `generate_cabinets()` — Pass `blind_depth`

Update the `create_box()` call (~line 660) to forward `blind_depth`:

```python
self.cabinets[i].blind_depth  # new argument
```

### 4. `create_baseboard()` — Handle blind corner

Add baseboard handling for types 12/13, extending the baseboard
into the blind zone when `bL` or `bR` flags are set.

### 5. `createunitsku()` — SKU generation

```python
# Front type:
elif cabinet.dType == "12" or cabinet.dType == "13":
    p2 = "B"  # blind corner

# Door number:
elif cabinet.dType == "12" or cabinet.dType == "13":
    p3 = "01"

# Door size:
elif cabinet.dType == "12" or cabinet.dType == "13":
    dwidth = cabinet.sX - cabinet.blind_depth - self.thickness - 0.001
    p7 = "%06.3f" % dwidth
```

### 6. `add_cabinet()` — UI panel

Show `blind_depth` only for blind corner types:

```python
if doortype == "12" or doortype == "13":
    row.prop(cabinet, 'blind_depth')
```

---

## Scope

| Metric           | Value                                        |
| ---------------- | -------------------------------------------- |
| Files modified   | 1 (`achm_kitchen_maker.py`)                  |
| New lines (est.) | 40–60                                        |
| New dependencies | None (reuses `create_door`, `create_handle`) |
| Blender version  | 3.x / 4.x                                    |

---

## Testing

- [ ] `Blind Corner R`: door on right, blind zone left, full box width
- [ ] `Blind Corner L`: door on left, blind zone right
- [ ] Rotate 90° CW → position chains correctly with next cabinet
- [ ] Rotate 180° → layout mirrored correctly
- [ ] Baseboard extends into blind zone
- [ ] Countertop covers full width including blind zone
- [ ] SKU format: `FB1211...` (F=floor, B=blind, 12=type, 1=door, 1=handle)
- [ ] Wall cabinet variant (`type_cabinet="2"`) works
- [ ] Handle appears on correct side
- [ ] Shelf count renders inside the full box

---

## Design Decisions

### Why new types 12/13 instead of a boolean on existing 9/10?

- Keeps `dType` enum self-documenting — each value is a distinct geometry
- Avoids adding conditional branches inside already-complex corner logic
- Existing corner types (9/10) are diagonal and serve a different purpose
- New types are easier to test in isolation
