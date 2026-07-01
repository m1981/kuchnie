# Data Flow: Blender → kuchnie_core → Manufacturing

## Current State (Gap Analysis)

### What Blender Plugin KNOWS (geometry_manifest.json)

```json
{
  "settings": {
    "corpusThickness": 18,
    "backThickness": 3,
    "frontThickness": 19,
    "plinthHeight": 120
  },
  "objects": [{
    "name": "run0_base_0_base-door",
    "type": "MESH",
    "classification": "carcass",
    "level": "base",
    "local_dimensions_mm": [600.0, 560.0, 720.0],
    "construction": {
      "corpus_thickness_mm": 18,
      "back_thickness_mm": 3,
      "front_thickness_mm": 19
    },
    "children": [
      {"name": "..._back", "type": "back_panel", "local_dimensions_mm": [564.0, 3.0, 717.0]},
      {"name": "..._bottom", "type": "board", "local_dimensions_mm": [564.0, 560.0, 18.0]}
    ]
  }]
}
```

### What kuchnie_core EXPECTS (CabinetInstance)

```yaml
korpus:
    id: 'K01'
    typ: 'dolna_szufladowa'
    wymiary:
        szerokosc: 800
        wysokosc: 720
        glebokosc: 510
    material:
        korpus: 'swiss_krono.U119_VL'
        plecy: 'HDF_3mm'
        fronty: 'swiss_krono.U119_EM'
    grubosci:
        boki: 18
        plecy: 3
    wnetrze:
        szuflady:
            - id: 'S1'
              typ: 'blum_metabox'
              wysokosc: 150
    fronty:
        - id: 'F1'
          typ: 'szufladowy'
          powiazany: 'S1'
    uchwyty:
        typ: 'relingowy'
        rozstaw: 256
```

### The Gap

| Data | Blender Plugin | kuchnie_core | Gap? |
|------|---------------|--------------|------|
| Cabinet ID | auto-generated name | explicit `id` | ✗ Need mapping |
| Cabinet type | `base-door` | `dolna_szufladowa` | ✗ Different names |
| Dimensions | ✅ 600×560×720 | ✅ 800×720×510 | ✓ Same concept |
| Thicknesses | ✅ corpus=18 | ✅ side=18 | ✓ Same |
| Material codes | ❌ colors only | ✅ `swiss_krono.U119_VL` | ✗ Missing |
| Drawers | ❌ not in manifest | ✅ drawer list | ✗ Missing |
| Shelves | ❌ not in manifest | ✅ shelf list | ✗ Missing |
| Fronts | ❌ not in manifest | ✅ front list | ✗ Missing |
| Handles | ❌ not in manifest | ✅ handle spec | ✗ Missing |

---

## Two Possible Flows

### Flow A: Blender → kuchnie_core (with bridge)

```
┌─────────────────────────────────────────────────────────────────┐
│ BLENDER PLUGIN                                                  │
│                                                                 │
│  User draws kitchen in GUI                                      │
│  │                                                              │
│  ▼                                                              │
│  config.json ──────────────────────────────────────┐            │
│  (cabinet types + widths + materials)              │            │
│                                                    │            │
│  Blender builds 3D geometry                        │            │
│  │                                                │            │
│  ▼                                                │            │
│  geometry_manifest.json                            │            │
│  (dimensions + construction params)                │            │
└────────────────────────────────────────────────────┼────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ BRIDGE MODULE (to be built)                                     │
│                                                                 │
│  Input: config.json + geometry_manifest.json                    │
│  Output: kitchen.yaml (kuchnie_core format)                     │
│                                                                 │
│  Mapping:                                                       │
│    base-door      → dolna_drzwiowa                              │
│    base-drawers   → dolna_szufladowa                            │
│    wall-door      → gorna_drzwiowa                              │
│    corner-blind   → narożna_ślepa                               │
│                                                                 │
│  Adds:                                                          │
│    - Material codes from config/materials                       │
│    - Drawer specs from config/drawers                           │
│    - Handle specs from config/handles                           │
│    - Shelf counts from config/shelves                           │
└────────────────────────────────────────────────────┬────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ kuchnie_core                                                    │
│                                                                 │
│  load_kitchen("kitchen.yaml")                                   │
│  │                                                              │
│  ▼                                                              │
│  Kitchen → decompose_kitchen() → DecompositionResult[]          │
│  │                                                              │
│  ▼                                                              │
│  export_cutlist_csv() → CSV                                     │
│  kitchen_bom() → BOM                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Flow B: Config-first (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│ CONFIG FILE (kitchen.yaml)                                      │
│                                                                 │
│  Contains ALL design decisions:                                 │
│    - Cabinet types + dimensions                                 │
│    - Material codes                                             │
│    - Drawer configurations                                      │
│    - Handle specs                                               │
│    - Shelf counts                                               │
│    - Worktop specs                                              │
│                                                                 │
│  This is the SOURCE OF TRUTH                                    │
└──────────────┬──────────────────────────────────┬───────────────┘
               │                                  │
               ▼                                  ▼
┌──────────────────────────┐      ┌──────────────────────────────┐
│ kuchnie_core             │      │ Blender Plugin               │
│                          │      │                              │
│  load_kitchen(config)    │      │  load_config(config)         │
│  decompose_kitchen()     │      │  build_kitchen_from_layout() │
│  export_cutlist_csv()    │      │  export_manifest()           │
│                          │      │                              │
│  OUTPUT:                 │      │  OUTPUT:                     │
│  - Cut list CSV          │      │  - 3D renders                │
│  - Hardware BOM          │      │  - Elevation views           │
│  - DXF drilling          │      │  - Plan views                │
└──────────────────────────┘      └──────────────────────────────┘
```

---

## Recommended Approach: Config-First

### Why?

1. **Single source of truth** — config file contains ALL decisions
2. **No bridge needed** — both systems read same config
3. **Reproducible** — regenerate renders or cut list from same config
4. **Versionable** — config file in git, track design changes

### Config Format (Proposed)

```yaml
# kitchen.yaml — SOURCE OF TRUTH
version: "2.0"
project_name: "Kuchnia Jan Kowalski"

settings:
  base_height: 720
  base_depth: 560
  wall_height: 720
  wall_depth: 300
  plinth_height: 120
  corpus_thickness: 18
  back_thickness: 3
  front_thickness: 19

materials:
  body: "swiss_krono.U119_VL"      # Beż Jasny Mat
  back: "HDF_3mm"
  front: "swiss_krono.U119_EM"     # Beż Jasny Velvet
  worktop: "kronospan.8685_BS_PD"  # Dąb Naturalny

rows:
  - label: "Ściana północna"
    wall_width_mm: 3600
    cabinets:
      - id: "K01"
        type: "dolna_szufladowa"
        width_mm: 800
        height_mm: 720
        depth_mm: 510
        drawers:
          - id: "S1"
            height_mm: 150
            system: "tandembox_antaro"
            height_code: "N"
            nl: 500
          - id: "S2"
            height_mm: 300
            system: "tandembox_antaro"
            height_code: "M"
            nl: 500
        fronts:
          - id: "F1"
            type: "drawer"
            linked_to: "S1"
            margins: {left: 3, right: 3, top: 3, bottom: 3}
          - id: "F2"
            type: "drawer"
            linked_to: "S2"
            margins: {left: 3, right: 3, top: 3, bottom: 3}
        handles:
          type: "rail"
          spacing_mm: 256

      - id: "K02"
        type: "dolna_drzwiowa"
        width_mm: 600
        height_mm: 720
        depth_mm: 510
        shelves: 1
        fronts:
          - id: "F1"
            type: "door"
            side: "right"
            hinges: "blum_cliptop_110"
            hinge_count: 2
        handles:
          type: "rail"
          spacing_mm: 192

worktops:
  - row_label: "Ściana północna"
    material: "kronospan.8685_BS_PD"
    thickness_mm: 40
    depth_mm: 600
    overhang_front_mm: 20
    overhang_ends_mm: 30
```

### Execution Flow

```
Step 1: Designer creates kitchen.yaml (by hand or via UI)
           │
           ├──► kuchnie_core.load_kitchen("kitchen.yaml")
           │        │
           │        ▼
           │    Kitchen → decompose_kitchen() → cut list + BOM
           │
           └──► kitchen-plugin.load_config("kitchen.yaml")
                    │
                    ▼
                Blender builds 3D → renders for client approval
```

---

## Current Gaps to Fill

### Gap 1: Config format doesn't exist yet

**Status:** No unified config format

**Action:** Define `kitchen.yaml` schema (above)

### Gap 2: Blender plugin doesn't read our config

**Status:** Plugin reads its own JSON format

**Action:** Write adapter: `kitchen.yaml` → plugin's `config.json`

### Gap 3: kuchnie_core doesn't read drawer specs from config

**Status:** `CabinetInstance.drawers` is `list[dict]` — no schema

**Action:** Define drawer spec schema with Blum system + height code + NL

### Gap 4: Material codes not in Blender config

**Status:** Plugin uses colors, not catalog codes

**Action:** Add `materials` section to config, pass colors + codes

---

## Minimal Bridge (If Config-First Too Complex)

If config-first is too much work, a minimal bridge:

```python
# bridge.py — converts Blender manifest → kuchnie_core format

def manifest_to_kitchen(manifest: dict) -> Kitchen:
    """Convert geometry manifest to kuchnie_core Kitchen."""
    kitchen = Kitchen(
        project_name=manifest.get("source_config", ""),
        version="1.0",
    )
    
    settings = manifest["settings"]
    
    for run in manifest["layout"]["runs"]:
        row = Row(
            id=run["label"],
            label=run["label"],
            wall_width_mm=int(run["total_width_mm"]),
            wall_height_mm=int(settings["baseBodyHeight"]),
        )
        
        for obj_name in run["cabinets"]:
            obj = _find_object(manifest, obj_name)
            if obj:
                cab = _object_to_cabinet(obj, settings)
                row.cabinets.append(cab)
        
        kitchen.rows.append(row)
    
    return kitchen

def _object_to_cabinet(obj: dict, settings: dict) -> CabinetInstance:
    """Convert manifest object to CabinetInstance."""
    dims = obj["local_dimensions_mm"]
    level = obj.get("level", "base")
    
    # Map type
    type_map = {
        ("base", "base-door"): "dolna_drzwiowa",
        ("base", "base-drawers"): "dolna_szufladowa",
        ("upper", "wall-door"): "gorna_drzwiowa",
    }
    
    cab_type = type_map.get((level, obj.get("type", "")), "dolna_drzwiowa")
    
    return CabinetInstance(
        id=obj["name"],
        type=cab_type,
        description=f"From Blender: {obj['name']}",
        width_mm=int(dims[0]),
        height_mm=int(dims[2]),
        depth_mm=int(dims[1]),
        body_material="UNKNOWN",  # Not in manifest
        back_material="HDF_3mm",
        front_material="UNKNOWN",
        thickness_side_mm=int(settings["corpusThickness"]),
        thickness_back_mm=int(settings["backThickness"]),
    )
```

---

## Recommendation

**Start with Config-First approach:**

1. Define `kitchen.yaml` schema
2. Implement `load_kitchen()` in kuchnie_core (already exists)
3. Write adapter: `kitchen.yaml` → Blender's `config.json`
4. Both systems read same config

**This eliminates the bridge entirely.**

Want me to proceed with implementing the config-first approach?
