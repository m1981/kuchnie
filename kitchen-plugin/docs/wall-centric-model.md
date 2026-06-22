# Wall-Centric Positioning Model

Industry standard approach for kitchen cabinet positioning.

---

## Overview

Instead of absolute coordinates, cabinets are positioned **relative to walls**:

- Each wall defines a local coordinate system
- Cabinets reference a wall and an offset along that wall
- Corner cabinets reference two walls (primary + secondary)

This approach is used by professional kitchen design software:

- IKEA Home Planner
- 2020 Design
- Chief Architect
- SketchUp kitchen plugins

---

## Coordinate System

### Wall-Local Coordinates

```
                    Wall Normal (into room)
                           ↑
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    │   Wall Start ────────┼──────── Wall End     │
    │         (0,0)        │           (L,0)      │
    │                      │                      │
    └──────────────────────┼──────────────────────┘
                           │
                           ↓
                    Wall Direction (+X)
```

- **X axis**: along wall (from start to end)
- **Y axis**: into room (wall normal)
- **Z axis**: up (floor to ceiling)

### Cabinet Origin

**Back-left-bottom** (at wall face):

```
         ┌─────────────────┐
        /│                /│
       / │    FRONT     /  │  ← Y = depth (into room)
      /  │   (face)    /   │
     ┌─────────────────┐   │
     │   │             │   │
     │   └─────────────│───┘
     │  /   BACK       │  /
     │ /    (wall)     │ /   ← Y = 0 (wall face)
     │/                │/
     └─────────────────┘
     ↑                 ↑
     X=0              X=width
```

---

## Key Classes

### Wall

```python
@dataclass
class Wall:
    id: str                              # "back_wall", "left_wall"
    start: Tuple[float, float]           # (x, y) start point
    end: Tuple[float, float]             # (x, y) end point

    @property
    def length(self) -> float            # Wall length in mm
    @property
    def direction(self) -> Tuple[float, float]  # Normalized direction
    @property
    def normal(self) -> Tuple[float, float]     # Points into room

    def point_at_offset(self, offset: float) -> Tuple[float, float]
    def point_at_depth(self, offset: float, depth: float) -> Tuple[float, float]
```

### Room

```python
@dataclass
class Room:
    walls: List[Wall]

    def get_wall(self, wall_id: str) -> Optional[Wall]
    @property
    def corners(self) -> List[Tuple[float, float]]
```

### WallCabinet

```python
@dataclass
class WallCabinet:
    wall_id: str      # Reference to wall
    offset: float     # Distance from wall start
    width: float      # Cabinet width (along wall)
    depth: float      # Cabinet depth (into room)
    height: float     # Cabinet height (up)

    def world_position(self, wall: Wall) -> Tuple[float, float]
    def front_position(self, wall: Wall) -> Tuple[float, float]
    def center_position(self, wall: Wall) -> Tuple[float, float]
```

### CornerCabinet

```python
@dataclass
class CornerCabinet:
    primary_wall: str     # Main wall
    secondary_wall: str   # Adjacent wall
    width: float          # Total width
    blind_depth: float    # Extends into secondary wall
    blind_side: str       # "left" or "right"

    @property
    def space_consumed_on_secondary(self) -> float
```

---

## Wall Ordering Convention

Walls should be ordered **counterclockwise** around the room:

```
        Back Wall (east →)
    ┌─────────────────────────┐
    │                         │
    │         ROOM            │
Left Wall                     Right Wall
(north ↑)                     (south ↓)
    │                         │
    └─────────────────────────┘
        Front Wall (west ←)
```

This ensures wall normals always point **into the room**.

---

## Example: U-Shape Kitchen

```python
from src.wall_model import Wall, Room, WallCabinet, CornerCabinet

# Define room walls (counterclockwise)
room = Room(walls=[
    Wall(id="left",  start=(0, 0),    end=(0, 2400)),
    Wall(id="back",  start=(0, 2400), end=(3000, 2400)),
    Wall(id="right", start=(3000, 2400), end=(3000, 0)),
])

# Cabinets on back wall
back_cabinets = [
    WallCabinet(wall_id="back", offset=0, width=600, depth=560, height=720),
    WallCabinet(wall_id="back", offset=600, width=800, depth=560, height=720),
]

# Corner at back-right junction
corner = CornerCabinet(
    primary_wall="back",
    secondary_wall="right",
    width=900,
    blind_depth=400,
    blind_side="right",
)

# Right wall starts after corner blind depth
right_cabinets = [
    WallCabinet(wall_id="right", offset=400, width=600, depth=560, height=720),
]
```

---

## Advantages Over Absolute Positioning

| Aspect                | Absolute Positioning    | Wall-Centric                |
| --------------------- | ----------------------- | --------------------------- |
| **Wall alignment**    | Manual calculation      | Automatic (wall reference)  |
| **Corner handling**   | Complex rotation math   | Simple wall-pair reference  |
| **Wall changes**      | Reposition all cabinets | Just update wall definition |
| **Validation**        | Check absolute bounds   | Check wall offset bounds    |
| **Industry standard** | ❌                      | ✅                          |

---

## Migration from Current Implementation

The current implementation uses:

- Run-based positioning (similar but not identical)
- Direction vectors (east, north, west, south)
- Front-face origin (Y=0 at front)

The new model:

- Wall-based positioning (more general)
- Wall normal (always points into room)
- Back-face origin (Y=0 at wall face)

Both can coexist during migration.
