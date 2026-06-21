📐 Project Overview

Archimesh is a parametric architectural elements generator for Blender. It adds a custom menu under Mesh > Add with  
 two categories: Structural elements and Decoration assets. Each feature generates editable, parameterized 3D mesh  
 objects with optional Cycles materials.

Author: Antonio Vazquez (antonioya) | License: GPL-2.0-or-later | 17 Python files, ~30 classes

────────────────────────────────────────────────────────────────────────────────

🏗️ Architecture Overview (Mermaid Class Diagram)

```mermaid
  classDiagram
      direction TB

      class Archimesh_Plugin {
          <<Blender Addon>>
          Menu: VIEW3D_MT_mesh_custom_menu_add
          Menu: VIEW3D_MT_mesh_decoration_add
          Scene properties: hint colors, font sizes, GL toggles
          register() / unregister()
      }

      class SharedUtils {
          <<achm_tools>>
          Mesh helpers: set_normals, remove_doubles, set_smooth
          Modifiers: subsurf, mirror, array, curve, solidify, boolean
          Materials: diffuse, translucent, glass, transparent, glossy, emission, brick, fabric
          UV: mark_seam, unwrap_mesh
          Parenting & control boxes
      }

      class OpenGL_Hints {
          <<achm_gltools>>
          draw_room_data()
          draw_door_data()
          draw_window_rail_data()
          draw_window_panel_data()
          draw_text / draw_line
          3D math: distance, interpolate3d, rotate_*
      }

      Archimesh_Plugin --> SharedUtils : uses
      Archimesh_Plugin --> OpenGL_Hints : uses
```

────────────────────────────────────────────────────────────────────────────────

🗂️ Feature Map (Mermaid Diagram)

```mermaid
  mindmap
    root((Archimesh Plugin))
      Structural Elements
        Room Maker
          Multi-wall rooms
          Curved walls
          Baseboard auto-gen
          Floor & ceiling
          Wall cover / shell
          Export/Import .dat
          OpenGL measurement hints
        Door Maker
          6 door models
          4 handle models
          Glass panels
          Rotation & open side
          Real-time property panel
        Rail Window
          Rail / leaf variants
          Sill generation
          External blind box
          Handle models
          Real-time update
        Panel Window
          Grid-based panes (8x5)
          PVC / Wood / Plastic materials
          Top types: Flat / Arch / Inclined / Triangle
          Sill with jamb
          Predefined sizes
        Kitchen Cabinets
          Floor & Wall types
          12 door types (Single, Glass, Drawers, Double, Corner)
          8 handle models
          Auto baseboard & countertop
          Rotation between cabinets
          Export inventory .txt
        Shelves
          Full side / 4 Legs / None
          12 shelves with Z-offsets
          Multi-unit support
        Columns
          Circular & rectangular
          Base / top (box & circle)
          Top arch option
          Array modifier
        Stairs
          Rectangular & rounded steps
          Variable width
          Bezier deformation curve
          Close sides option
        Roof
          4 tile models
          Configurable grid & slope
          Tile scale & thickness
      Decoration Assets
        Books
          Random positioning (X/Y/Z)
          Random rotation & color
          Affinity grouping
        Lamps
          4 presets: Sphere / Pear / Vase / Rectangular
          12-ring base profiling
          Pleats on lampshade
          Light intensity & translucency
        Roller Curtains
          Rail & roller mechanism
          Bezier curve fabric
        Japanese Curtains
          Multi-rail panels (2-5 rails)
          Panel sliding positions
        Venetian Blinds
          Adjustable slat angle
          Extension ratio
          String mechanism
      Core Infrastructure
        achm_tools
          30+ utility functions
          9 material types (Cycles nodes)
          Modifier wrappers
        achm_gltools
          Real-time overlay hints
          Room / door / window data draw
          3D viewport annotations
        Main Panel
          Hole operator (boolean cut)
          Pencil operator (dimensions)
          Hint display toggle
        Registration
          28 classes registered
          12 scene properties
          Dynamic menu injection
```

────────────────────────────────────────────────────────────────────────────────

🔗 Module Dependency Graph

```mermaid
  graph LR
      subgraph Core["🧱 Core Infrastructure"]
          tools["achm_tools<br/>30+ utility functions<br/>9 material types"]
          gltools["achm_gltools<br/>OpenGL overlays"]
          init["__init__<br/>Menu registration"]
      end

      subgraph Structural["🏛️ Structural Elements"]
          room["achm_room_maker<br/>RoomProperties + WallProperties<br/>Export/Import .dat"]
          door["achm_door_maker<br/>ObjectProperties<br/>6 models, 4 handles"]
          win["achm_window_maker<br/>ObjectProperties<br/>Rail + Leaf windows"]
          wpanel["achm_window_panel<br/>GeneralPanelProperties<br/>Grid-based panels"]
          kitchen["achm_kitchen_maker<br/>CabinetProperties<br/>12 door types, 8 handles"]
          shelves["achm_shelves_maker<br/>ShelvesProperties<br/>3 side types"]
          column["achm_column_maker<br/>Circular + Rectangular<br/>Arch + Array"]
          stairs["achm_stairs_maker<br/>Rect + Rounded steps<br/>Bezier curve"]
          roof["achm_roof_maker<br/>4 tile models"]
      end

      subgraph Decoration["🎨 Decoration Assets"]
          books["achm_books_maker<br/>Randomized books"]
          lamp["achm_lamp_maker<br/>4 presets<br/>12-ring profiling"]
          curtain["achm_curtain_maker<br/>Roller + Japanese"]
          venetian["achm_venetian_maker<br/>Adjustable slats"]
      end

      subgraph Panel["🖥️ UI Panel"]
          main["achm_main_panel<br/>Hole / Pencil / Hints"]
      end

      %% Dependencies
      init --> Structural
      init --> Decoration
      init --> Panel

      room & door & win & wpanel & kitchen & shelves & column & stairs & roof --> tools
      books & lamp & curtain & venetian --> tools
      main --> tools
      main --> gltools

      room & door & win & wpanel -.-> gltools
```

────────────────────────────────────────────────────────────────────────────────

📊 Feature Property Summary Table

```mermaid
  ---
  config:
    theme: base
    themeVariables:
      primaryColor: "#e8f4fd"
  ---
  graph TD
      subgraph Features["Feature Property Counts"]
          direction LR
          A["🏠 Room Maker<br/>━━━━━━━━━━<br/>• 15+ wall params<br/>• 5 room-level params<br/>• Curved wall
support<br/>• Import/Export .dat"]
          B["🚪 Door Maker<br/>━━━━━━━━━━<br/>• 14 frame params<br/>• 6 door models<br/>• 4 handle models<br/>•
OpenGL points"]
          C["🪟 Window Maker<br/>━━━━━━━━━━<br/>• 16 frame params<br/>• 4 open types<br/>• Sill + Blind<br/>• OpenGL
points"]
          D["🍳 Kitchen<br/>━━━━━━━━━━<br/>• 14 global params<br/>• 15 cabinet params<br/>• 12 door types<br/>• 8
handle models"]
          E["🪜 Stairs<br/>━━━━━━━━━━<br/>• 12 step params<br/>• 2 step models<br/>• Bezier curve<br/>• Variable
width"]
          F["📚 Books<br/>━━━━━━━━━━<br/>• 3 dimensions<br/>• 3 randomness axes<br/>• Rotation + Affinity<br/>• Color
random"]
          G["💡 Lamp<br/>━━━━━━━━━━<br/>• 12 ring radii<br/>• 12 Z-shift factors<br/>• 4 presets<br/>• Pleats
option"]
          H["🪟 Venetian<br/>━━━━━━━━━━<br/>• 7 slat params<br/>• Angle 0-85°<br/>• Extension %<br/>• Color picker"]
      end
```

────────────────────────────────────────────────────────────────────────────────

📁 File Structure

```
  kitchen-plugin/
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
