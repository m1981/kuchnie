**Act as an Expert Blender Python (`bpy`) Developer and Technical 3D Artist.**

I am building a procedural "Text-to-2.5D" pipeline. I need a standalone Python script that runs in Headless Blender (`blender -b -P generate_kitchen.py`).

The script must read a JSON configuration file defining a linear kitchen layout, procedurally generate simple box geometry for the cabinets side-by-side, calculate perfect physical UVs, and export three specific render passes for a downstream OpenCV compositing engine.

**1. The Input Format (JSON)**
The script should read a file named `layout.json` with this structure:

```json
{
    "scene_name": "linear_kitchen_01",
    "cabinets": [
        {
            "type": "tall",
            "width_mm": 600,
            "height_mm": 2000,
            "depth_mm": 600,
            "id_hex": "#FF0000"
        },
        { "type": "base", "width_mm": 800, "height_mm": 820, "depth_mm": 600, "id_hex": "#00FF00" },
        { "type": "base", "width_mm": 600, "height_mm": 820, "depth_mm": 600, "id_hex": "#0000FF" }
    ],
    "countertop": {
        "thickness_mm": 40,
        "overhang_mm": 20,
        "id_hex": "#FFFF00"
    }
}
```

**2. Geometry Generation Requirements**

- Clear the default Blender scene.
- Iterate through the `cabinets` array. For each item, generate a simple Cube mesh matching the exact dimensions (convert mm to meters).
- Place them side-by-side along the X-axis, starting at X=0.
- Generate a single countertop box that spans across all "base" cabinets.

**3. UV Mapping Requirements (CRITICAL)**

- The downstream OpenCV engine relies on physical scale.
- You must unwrap every generated mesh using Cube Projection.
- **The Scale Rule:** Exactly 1.0 Blender Unit (1 meter) must equal 1.0 UV space. (e.g., A cabinet that is 0.6m wide should take up exactly 0.6 of the UV grid).

**4. Render Passes & Shaders**
The script must configure the Blender Compositor to output three distinct images into an `assets/` folder:

1.  **`base_pass.png` (8-bit RGB):** A standard render (Cycles or Eevee) with a simple white diffuse material and a basic lighting setup (e.g., a Sun light or Area light) so the cabinets have basic shadows and ambient occlusion.
2.  **`uv_pass.exr` (32-bit Float EXR):** A render where the material outputs the raw UV coordinates. U maps to the Red channel, V maps to the Green channel. _Must be saved as OpenEXR._
3.  **`id_mask.png` (8-bit RGB):** A flat, shadeless render using the `id_hex` colors from the JSON. **CRITICAL:** This pass must have Anti-Aliasing completely DISABLED (Filter Size = 0.0), otherwise the downstream OpenCV color-picking math will fail on the edges.

**5. Camera Setup**

- Create a camera, point it at the generated kitchen, and automatically frame it so the entire kitchen fits within an 800x600 resolution render.

**Deliverable:**
Provide the complete, single-file `generate_kitchen.py` script. Ensure it is heavily commented, handles the JSON parsing, builds the node trees for the compositor, and triggers the render automatically. Do not rely on any external `.blend` files; generate the simple box meshes procedurally.
