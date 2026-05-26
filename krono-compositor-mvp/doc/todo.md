Act as an Expert 3D Technical Artist and Full-Stack Developer (FastAPI + Alpine.js).

I have a working 2.5D Compositing Engine. The backend (FastAPI/OpenCV) correctly extracts ID masks, warps UVs, and applies Multiply/Screen/Alpha compositing. However, the current output looks "flat and dodgy", and I cannot select handles ("okucia") from my UI yet.

I need your help with 3 distinct tasks to make this pipeline photorealistic:

**Task 1: Improve the Headless Blender Script (Lighting & AO)**
My current `gen_kitchen.py` script produces a Base Pass that is too bright/flat. I need you to update the Blender Python script to:

- Enable and boost Ambient Occlusion (AO) so corners and gaps between cabinets are dark.
- Adjust the Area Light (Softbox) so it creates a nice gradient on the cabinets rather than blowing them out to pure white.
- Ensure the Handle Pass ("Shadow Catcher") is generating correctly and visibly casting shadows.

**Task 2: Real Textures**
Provide me a quick Python script to download (or generate via noise) 3 photorealistic seamless textures (Oak Wood, White Marble, Dark Matte) and save them into my `assets/textures/` folder, replacing my current solid-color dummy JPEGs.

**Task 3: Update the Alpine.js Frontend (Handle Selection)**
My backend Pydantic schema expects an optional `"handle_id": "edge_pull"` in the JSON payload, but my Alpine.js frontend currently doesn't send it.
Please update my `index.html` (Alpine.js/Tailwind) to include a new UI section where the user can select a Handle style (e.g., "Brak" (None) or "Uchwyt Krawędziowy" (Edge Pull)), and ensure this selection is passed into the `renderKitchen()` fetch payload.

Let's start with Task 1. How do we tweak the `bpy` script to get massive, beautiful Ambient Occlusion and contact shadows?
