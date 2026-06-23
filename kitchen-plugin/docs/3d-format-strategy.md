# 3D Format Strategy for Inspection & Validation Pipeline

Choosing the right 3D format is the single highest-leverage decision for a
validation pipeline. OBJ and glTF were designed for **rendering**, not
**inspection**. Continuing to build tooling on formats that don't carry the
information you need means every tool becomes a fragile heuristic.

This document explains the trade-offs and recommends a concrete strategy.

---

## 1. What a Validation / LLM-Inspection Pipeline Actually Needs

| Capability                  | Why it matters                                          |
| --------------------------- | ------------------------------------------------------- |
| **Explicit units**          | No guessing whether values are meters or millimeters    |
| **Coordinate system spec**  | No heuristic detection of Y-up vs Z-up                  |
| **Topology data**           | Manifoldness, edge sharing, Euler characteristic checks |
| **Semantic naming**         | Agent needs to know "this mesh is a door, not a shelf"  |
| **Hierarchical structure**  | Cabinets → components → panels, with transforms         |
| **Material / metadata**     | Material type, thickness, production parameters         |
| **Python-parseable**        | No proprietary SDKs, no Blender dependency              |
| **Per-object vertex pools** | No global-index remapping bugs                          |

---

## 2. Format-by-Format Comparison

| Capability             | OBJ             | glTF           | **STEP**         | **IFC**           | **3MF**        |
| ---------------------- | --------------- | -------------- | ---------------- | ----------------- | -------------- |
| Units in file          | ❌ undefined    | ⚠️ no spec     | ✅ explicit      | ✅ explicit       | ✅ explicit    |
| Topology (manifold)    | ❌ none         | ❌ none        | ✅ full B-Rep    | ✅ full B-Rep     | ✅ meshes      |
| Semantic naming        | ⚠️ `o` lines    | ✅ node names  | ✅ product tree  | ✅ rich IFC types | ✅ components  |
| Material / metadata    | ❌ .mtl sidecar | ✅ embedded    | ✅ embedded      | ✅ embedded       | ✅ embedded    |
| Python parsing ease    | ✅ trivial      | ✅ JSON        | ⚠️ pythonocc     | ⚠️ IfcOpenShell   | ✅ XML / ZIP   |
| Coordinate system      | ❌ unspecified  | ✅ Y-up spec   | ✅ right-hand    | ✅ explicit       | ✅ Z-up spec   |
| Hierarchical structure | ❌ flat         | ✅ scene graph | ✅ assembly tree | ✅ spatial tree   | ✅ build items |
| CNC / manufacturing    | ⚠️ mesh only    | ❌ no          | ✅ native        | ⚠️ via export     | ✅ print-ready |

### Rating Summary

```
  Rendering fidelity:     glTF > OBJ > 3MF > STEP > IFC
  Inspection fidelity:    STEP > IFC > 3MF > glTF > OBJ
  Ease of parsing:        OBJ > glTF > 3MF > IFC > STEP
  Manufacturing readiness: STEP > 3MF > IFC > OBJ > glTF
```

---

## 3. Why OBJ and glTF Fail for Validation

### 3.1 OBJ — The Problems

```c
// OBJ declares nothing about units or coordinate system.
// Vertices are raw floats — could be meters, inches, or mm.
v 0.600 0.560 0.720    // Is this 600mm or 0.6mm?
v 0.000 0.000 0.000
```

| Problem                         | Impact                                           |
| ------------------------------- | ------------------------------------------------ |
| No unit declaration             | Every parser must guess or hardcode `*1000`      |
| No coordinate system spec       | Heuristic detection (Z-range > Y-range → Z-up?)  |
| Global vertex index space       | Multi-object files require index remapping       |
| No topology data                | Cannot check manifoldness                        |
| No transform hierarchy          | Objects are flat — no parent/child relationships |
| Material in sidecar `.mtl` file | Easy to lose, hard to keep in sync               |

### 3.2 glTF — Better, But Still Wrong Tool

glTF is excellent for **rendering** — it carries PBR materials, animation,
scene graph, and GPU-ready buffers. But for inspection:

| Problem                             | Impact                                                               |
| ----------------------------------- | -------------------------------------------------------------------- |
| No unit declaration                 | Spec says "units are abstract" — still guessing                      |
| Y-up only (spec) but exporters vary | Many tools output Z-up glTF anyway                                   |
| No topology metadata                | It's triangles — no B-Rep, no edge data                              |
| Binary buffer parsing               | Must unpack base64 + struct offsets manually                         |
| Scene graph is rendering-focused    | Node transforms encode camera/light logic, not engineering semantics |

### 3.3 The Core Issue

Both formats answer: **"How do I draw this on screen?"**

They do not answer: **"What is this object, what are its exact dimensions,
is it a valid solid, and does it meet manufacturing tolerances?"**

---

## 4. Recommended Formats

### 4.1 3MF — Primary Inspection Format

**3MF** (3D Manufacturing Format) solves almost every problem:

```xml
<!-- 3MF explicitly declares units — no guessing -->
<model unit="millimeter" xml:lang="en-US">
  <resources>
    <object id="1" name="base_cabinet_600" type="model">
      <mesh>
        <vertices>
          <vertex x="0" y="0" z="0"/>
          <vertex x="600" y="0" z="0"/>
          <!-- coordinates are in the declared unit -->
        </vertices>
        <triangles>
          <!-- indices are LOCAL to this object — no global remapping -->
          <triangle v1="0" v2="1" v3="2"/>
        </triangles>
      </mesh>
    </object>
  </resources>
  <build>
    <!-- explicit placement transforms -->
    <item objectid="1" transform="1 0 0 0 1 0 0 0 1 100 0 0"/>
  </build>
</model>
```

**What 3MF gives you for free:**

| Problem with OBJ/glTF                 | 3MF solution                                                 |
| ------------------------------------- | ------------------------------------------------------------ |
| Unit guessing (`*1000` heuristic)     | `<model unit="millimeter">` — explicit, declarative          |
| Coordinate system detection heuristic | Spec-defined coordinate system                               |
| Multi-object index remapping bug      | Each `<object>` has its own vertex pool                      |
| No manifold validation                | Spec requires watertight meshes                              |
| Hardcoded expected dims in scripts    | Metadata extensions: `<metadata name="width">600</metadata>` |
| No material info                      | Embedded materials + textures                                |
| No production metadata                | Production extensions (slice, print, ticket)                 |

**Python parsing** — 3MF is a ZIP containing XML. No exotic libraries:

```python
import zipfile
import xml.etree.ElementTree as ET

def parse_3mf(path: str) -> dict:
    """Parse 3MF file. Units, names, transforms — all declarative."""
    with zipfile.ZipFile(path) as zf:
        model = ET.parse(zf.open("3D/3dmodel.model"))
        root = model.getroot()
        ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}

        result = {
            "unit": root.get("unit", "millimeter"),  # ← instant, no guessing
            "objects": [],
        }

        for obj in root.findall(".//m:object", ns):
            name = obj.get("name", "unnamed")
            vertices = []
            for v in obj.findall(".//m:vertex", ns):
                vertices.append((
                    float(v.get("x")),
                    float(v.get("y")),
                    float(v.get("z")),
                ))
            triangles = []
            for tri in obj.findall(".//m:triangle", ns):
                triangles.append((
                    int(tri.get("v1")),
                    int(tri.get("v2")),
                    int(tri.get("v3")),
                ))

            result["objects"].append({
                "name": name,
                "vertices": vertices,
                "triangles": triangles,
            })

        return result
```

### 4.2 STEP — Secondary Format for Topology Validation

When you need to validate **B-Rep topology** (not just mesh bounding boxes),
STEP is the only format that carries the full structural information:

```
STEP data model:
  Body → Shell → Face → Loop → Coedge → Edge → Vertex

  Each with:
  ├── Parametric surface / curve definitions
  ├── Tolerance metadata
  └── Manifold guarantees
```

```python
# Using pythonocc-core (OpenCASCADE wrapper)
from OCP.STEPControl import STEPControl_Reader

reader = STEPControl_Reader()
reader.ReadFile("cabinet.stp")
reader.TransferRoots()

shape = reader.OneShape()

# What you can check with STEP that you CANNOT with OBJ/glTF:
# - Is this a valid solid? (TopAbs_SOLID)
# - How many edges? How many faces? (TopExp_Explorer)
# - Euler characteristic: V - E + F = 2(S - H) + R
# - Are all faces planar? Are edges tangent-continuous?
# - What are the exact parametric dimensions (not bounding box)?
```

**Tradeoff:** `pythonocc-core` is ~500MB. Acceptable for a CI pipeline,
not for a browser-based tool.

### 4.3 IFC — Semantic Layer (When Needed)

IFC adds **architectural meaning** on top of geometry:

```
IfcProject
  → IfcSite
    → IfcBuilding
      → IfcBuildingStorey
        → IfcCabinet           ← semantic type
          → IfcPropertySet     ← { width: 600, depth: 560, ... }
          → IfcExtrudedAreaSolid ← parametric geometry
```

Use IFC when you're integrating with BIM software or need to reason about
building context (wall placement, clearances between rooms, etc.).

**Tradeoff:** Complex spec, heavy parser (IfcOpenShell), overkill for
pure cabinet geometry validation.

---

## 5. The Unit Problem — In Depth

This is the single most common source of silent bugs in CAD pipelines:

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  What the exporter thinks        What the importer assumes      │
  │  ─────────────────────────       ──────────────────────────     │
  │  600.0 (it's millimeters!)       600.0 (it's meters!)          │
  │                                                                  │
  │  Result: cabinet appears as 600 meters wide in the scene        │
  │          OR: 0.6mm wide if the reverse mistake is made          │
  │                                                                  │
  │  Neither tool reports an error. Both "parse successfully."      │
  └─────────────────────────────────────────────────────────────────┘
```

**Format responses to this problem:**

| Format | What happens                      | Can you detect the mistake? |
| ------ | --------------------------------- | --------------------------- |
| OBJ    | No unit info. You guess.          | ❌ No                       |
| glTF   | "Units are abstract." You guess.  | ❌ No                       |
| STEP   | `LENGTH_MEASURE(600.0)` with unit | ✅ Yes                      |
| IFC    | `IfcSIUnit(MILLI.., METRE)`       | ✅ Yes                      |
| 3MF    | `<model unit="millimeter">`       | ✅ Yes                      |

**Recommendation:** Never trust a format that doesn't declare units.
At minimum, validate against expected bounding box (e.g., "a cabinet should
be between 300mm and 2000mm on any axis — if I get 0.6 or 600000, units are wrong").

---

## 6. Recommended Pipeline Architecture

```
                  ┌──────────────────────────────────────┐
                  │   External app generates cabinets     │
                  └───────────────┬──────────────────────┘
                                  │
                  ┌───────────────▼──────────────────────┐
                  │   Export: 3MF + STEP (dual output)    │
                  └───────────────┬──────────────────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           ▼                      ▼                      ▼
  ┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐
  │ parse_3mf.py    │   │ parse_step.py    │   │ validate.py     │
  │                 │   │                  │   │                 │
  │ • Units ✅      │   │ • Manifold ✅    │   │ • Dimensions    │
  │ • Dimensions ✅ │   │ • Edge count     │   │ • Overlaps      │
  │ • Naming ✅     │   │ • Euler check    │   │ • Clearances    │
  │ • Transforms ✅ │   │ • Tolerances     │   │ • Standards     │
  └────────┬────────┘   └────────┬─────────┘   └────────┬────────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  ▼
                  ┌──────────────────────────────────────┐
                  │   Structured JSON report              │
                  │   → LLM agent reads & decides         │
                  └──────────────────────────────────────┘
```

### Validation Levels (Same Concept, Better Data)

```
  Level 1: SYNTAX (3MF XML schema / STEP file integrity)
    → "Is this a valid file with all required structures?"

  Level 2: SEMANTIC (from 3MF metadata + object names)
    → "Is this object a cabinet? Does it have standard width?"
    → "Do cabinets overlap? Is clearance ≥ 900mm?"

  Level 3: GEOMETRIC (from STEP B-Rep / 3MF mesh checks)
    → "Is the mesh manifold? Are dimensions within tolerance?"
    → "Does Euler characteristic hold?"
```

---

## 7. Migration Effort Estimate

| Step                                 | Effort   | Impact                                                   |
| ------------------------------------ | -------- | -------------------------------------------------------- |
| Write `parse_3mf.py`                 | 1–2 days | Replaces `analyze_gltf_v2.py` + `convert_obj_to_gltf.py` |
| Request 3MF export from other app    | Varies   | Eliminates unit guessing + index bugs                    |
| Keep OBJ parser as fallback          | 0 days   | Backwards compatibility                                  |
| Write `parse_step.py` (optional)     | 1 week   | Real topology validation                                 |
| Add unit-sanity check to validate.py | 1 hour   | Catches 90% of unit mistakes                             |

---

## 8. Decision Matrix — When to Use What

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                     USE 3MF WHEN:                                │
  │  • You need mesh inspection (dimensions, bounds, vertex count)   │
  │  • You need explicit units without guessing                      │
  │  • You want simple Python parsing (ZIP + XML)                    │
  │  • You want metadata (object names, properties)                  │
  │  • The target is manufacturing / CNC / 3D printing               │
  ├──────────────────────────────────────────────────────────────────┤
  │                     USE STEP WHEN:                               │
  │  • You need to verify topology (manifold, Euler, edge sharing)   │
  │  • You need exact parametric dimensions (not bounding box)       │
  │  • You're doing boolean operations or feature recognition        │
  │  • You need tolerance-aware geometry                             │
  ├──────────────────────────────────────────────────────────────────┤
  │                     USE IFC WHEN:                                │
  │  • You're integrating with BIM / architectural software          │
  │  • You need semantic building context (walls, rooms, storeys)    │
  │  • You need property sets (fire rating, material spec, cost)     │
  ├──────────────────────────────────────────────────────────────────┤
  │                     USE glTF WHEN:                               │
  │  • You're rendering in a browser or game engine                  │
  │  • You need PBR materials, animations, scene graph               │
  │  • Visual inspection only (not dimensional validation)           │
  ├──────────────────────────────────────────────────────────────────┤
  │                     USE OBJ WHEN:                                │
  │  • Quick interoperability with legacy tools                      │
  │  • You're already inside Blender and it's just a temp exchange   │
  │  • Never for validation pipelines                                │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 9. Golden Rules

1. **Never trust a format that doesn't declare units.** OBJ and glTF don't.
   You will get unit bugs. They will be silent.

2. **Coordinate system detection heuristics are inherently fragile.**
   A 1200mm-wide, 720mm-tall cabinet has X > Z — Z-up detection fails.
   Use formats that declare their coordinate system.

3. **Global vertex indices are a bug factory.** OBJ's global index space
   breaks when you split into per-object buffers. Use formats with
   per-object vertex pools (3MF, glTF with proper node separation).

4. **Bounding box ≠ geometry.** Matching width/depth/height does not prove
   the mesh is correct. If topology matters, use STEP.

5. **Validation tools must be format-aware, not format-agnostic.**
   A "universal" parser that handles OBJ + glTF + STL will always be
   lossy. Better to have a thin, correct parser per format.

6. **The LLM agent needs structured data, not raw vertices.**
   Output JSON reports with object names, dimensions, units, and pass/fail
   flags — not dumps of vertex arrays.

---

## 10. References

| Resource                                                           | What it covers                     |
| ------------------------------------------------------------------ | ---------------------------------- |
| [3MF Core Specification](https://3mf.io/specs/)                    | File format, units, mesh structure |
| [ISO 10303 (STEP)](https://www.iso.org/standard/74878.html)        | B-Rep exchange standard            |
| [IFC Standard](https://technical.buildingsmart.org/standards/ifc/) | BIM data model                     |
| [pythonocc-core](https://github.com/tpaviot/pythonocc-core)        | OpenCASCADE Python bindings        |
| [IfcOpenShell](https://ifcopenshell.org/)                          | IFC parsing library                |
| [lib3mf](https://github.com/3MFConsortium/lib3mf)                  | Official 3MF C++ / Python library  |
| [OpenCASCADE (OCCT)](https://dev.opencascade.org/)                 | Reference B-Rep kernel             |

---

## Appendix: What the Current Pipeline Gets Wrong

For reference, here are the specific bugs in the existing OBJ/glTF pipeline
that this strategy eliminates:

| #   | Bug                                    | Root cause                        | 3MF/STEP fix                               |
| --- | -------------------------------------- | --------------------------------- | ------------------------------------------ |
| 1   | `*1000` assumes meters                 | OBJ has no unit declaration       | `<model unit="millimeter">`                |
| 2   | Z-up detection fails for wide cabinets | Heuristic on axis ranges          | Format declares coordinate system          |
| 3   | Multi-object index mismatch            | OBJ global vertex indices         | Per-object vertex pools                    |
| 4   | No manifold / Euler check              | glTF has no topology data         | STEP B-Rep + 3MF spec requirement          |
| 5   | Normals silently dropped in OBJ→glTF   | Converter skips `vn` lines        | 3MF carries normals; STEP has surface defs |
| 6   | Fan triangulation breaks concave faces | Single algorithm for all polygons | 3MF triangulation spec                     |
| 7   | glTF `matrix`/`rotation` not handled   | Only `translation` parsed         | 3MF uses explicit 4×4 transforms           |
| 8   | Expected dims hardcoded in Python      | Not data-driven                   | `<metadata>` in 3MF or config JSON         |
