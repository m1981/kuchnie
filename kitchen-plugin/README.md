# Archimesh — Blender Parametric Architecture Plugin

A parametric architectural elements generator for Blender. Adds customizable
rooms, doors, windows, kitchen cabinets, shelves, columns, stairs, roofs,
and decoration assets — all driven by editable properties.

**Author:** Antonio Vazquez (antonioya) · **License:** GPL-2.0-or-later

---

## Features

| Category           | Element                                     | File                     |
| ------------------ | ------------------------------------------- | ------------------------ |
| **Structural**     | Room (multi-wall, curved, import/export)    | `achm_room_maker.py`     |
|                    | Door (6 models, 4 handles)                  | `achm_door_maker.py`     |
|                    | Rail Window (leaf, sill, blind)             | `achm_window_maker.py`   |
|                    | Panel Window (grid-based panes)             | `achm_window_panel.py`   |
|                    | Kitchen Cabinets (12 door types, 8 handles) | `achm_kitchen_maker.py`  |
|                    | Shelves (full side / 4 legs / none)         | `achm_shelves_maker.py`  |
|                    | Columns (circular, rectangular, arch)       | `achm_column_maker.py`   |
|                    | Stairs (rectangular, rounded, bezier)       | `achm_stairs_maker.py`   |
|                    | Roof (4 tile models)                        | `achm_roof_maker.py`     |
| **Decoration**     | Books (randomized)                          | `achm_books_maker.py`    |
|                    | Lamps (4 presets, pleats)                   | `achm_lamp_maker.py`     |
|                    | Roller Curtains                             | `achm_curtain_maker.py`  |
|                    | Japanese Curtains                           | `achm_curtain_maker.py`  |
|                    | Venetian Blinds                             | `achm_venetian_maker.py` |
| **Infrastructure** | Mesh/material/modifier utilities            | `achm_tools.py`          |
|                    | OpenGL viewport hints                       | `achm_gltools.py`        |
|                    | Main UI panel, Hole, Pencil                 | `achm_main_panel.py`     |

---

## Project Structure

```
kitchen-plugin/
├── README.md
├── docs/
│   └── f01-blind-cabinet.md        # Blind corner cabinet design
└── archimesh/
    └── source/
        ├── __init__.py              # Registration & menus (28 classes)
        ├── achm_tools.py            # 30+ mesh/material/modifier utilities
        ├── achm_gltools.py          # OpenGL overlay drawing functions
        ├── achm_main_panel.py       # Main UI panel, Hole, Pencil, Hints
        ├── achm_room_maker.py       # Room generator (1600+ lines)
        ├── achm_door_maker.py       # Door generator (2000+ lines)
        ├── achm_window_maker.py     # Rail/Leaf window (2300+ lines)
        ├── achm_window_panel.py     # Panel window (1900+ lines)
        ├── achm_kitchen_maker.py    # Kitchen cabinets (2600+ lines)
        ├── achm_shelves_maker.py    # Shelf units
        ├── achm_column_maker.py     # Columns + arches
        ├── achm_stairs_maker.py     # Staircase generator
        ├── achm_roof_maker.py       # Roof tiles
        ├── achm_books_maker.py      # Decorative books
        ├── achm_lamp_maker.py       # Parametric lamps
        ├── achm_curtain_maker.py    # Roller + Japanese curtains
        └── achm_venetian_maker.py   # Venetian blinds
```

---

## Development Setup (macOS)

### 1. Find your Blender addons directory

```bash
# Check which Blender versions you have installed
ls ~/Library/Application\ Support/Blender/
# e.g. → 4.2
```

### 2. Symlink the project into Blender (one-time)

Replace `4.2` with your actual Blender version:

```bash
ln -sf \
  /Users/michal/PycharmProjects/kuchnie/kitchen-plugin/archimesh \
  ~/Library/Application\ Support/Blender/4.2/scripts/addons/archimesh
```

### 3. Enable the addon in Blender

`Edit → Preferences → Add-ons → Search "archimesh" → Enable`

---

## Development Workflow

### Edit → Reload → Test loop

```
1. Edit code in PyCharm        →  Save (⌘S)
2. In Blender:                  →  Edit → Preferences → Add-ons → Reload 🔄
3. Test:                        →  Shift+A → Mesh → Archimesh → <element>
```

No restart needed for most changes (UI, properties, operators).

### When to restart Blender

Only required if you changed `register()` / `unregister()` logic or
class registration order in `__init__.py`.

### Reloading individual modules (Blender Python console)

```python
import importlib
import achm_kitchen_maker
importlib.reload(achm_kitchen_maker)
```

---

## Debugging

### Console output

Launch Blender from terminal to see `print()` output:

```bash
/Applications/Blender.app/Contents/MacOS/Blender
```

### In-app debug popup

```python
def draw(self, context):
    self.layout.label(text="Debug: " + str(my_var))
bpy.context.window_manager.popup_menu(draw, title="Debug", icon='INFO')
```

### Useful Python console commands

```python
# List registered operators containing "archimesh"
[b for b in dir(bpy.ops.mesh) if 'archimesh' in b]

# Check properties on active object
bpy.context.active_object.data

# Inspect addon classes
bpy.types.Operator.__subclasses__()
```

---

## Feature Documentation

Design documents for planned or implemented features live in `docs/`:

- [f01-blind-cabinet.md](docs/f01-blind-cabinet.md) — Blind corner cabinet design
