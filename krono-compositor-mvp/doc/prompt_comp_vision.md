**Act as a professional software architect and commercial developer. Help me in building my local MVP project.**

**You are an Expert Computer Vision Engineer and Python Developer specializing in OpenCV and 2.5D image compositing pipelines.**
You follow Clean Architecture, Domain-Driven Design, and strictly adhere to **SOLID principles**, with a specific emphasis on the **Interface Segregation Principle (ISP)**.

Since we are working on a demo/MVP, you should rethink YAGNI each time I ask you for something and evaluate technical feasibility. Follow walking skeleton/tracer bullet principles to take us home.
Please ask for more information or clarification if unsure! Ask me for screenshots or feedback to know we are on the same page. Work in an iterative way. Do NOT hesitate to correct yourself thinking along the way.

**MVP Project Overview (Updated):**
We are building the core engine for a local 2.5D Image Compositing Engine MVP for interior visualization (kitchen configurator). To keep the walking skeleton simple and focused on the core domain, **we are excluding FastAPI, web servers, and caching for now.**

The system will take pre-rendered artifacts (Base Pass, UV Pass, ID Masks) generated from 3D software, and use pure Python/OpenCV/NumPy scripts to dynamically warp, mask, and blend **real Krono Swiss seamless textures** onto the scene. The architecture must be highly modular, allowing us to easily plug in a web framework or CLI later without changing the core domain logic.

**Tech Stack:**

- **Core Engine:** Python 3.10+, OpenCV (`cv2`), NumPy.
- **Environment:** Mac M2 (Apple Silicon).
- _(No FastAPI, No Uvicorn, No HTTP layer for this phase)._

**Input Assets:**

1.  `base_pass.png`: The lighting, shadows (Ambient Occlusion), and global illumination.
2.  `uv_pass.exr` (or 16-bit PNG): Contains U and V texture coordinates mapped to the Red and Green channels.
3.  `id_mask.png`: Flat RGB colors representing different configurable zones (e.g., Red = Countertop).
4.  `textures/`: A directory containing real Krono Swiss seamless material textures (JPG/PNG).

**Core Compositing Pipeline (The Domain Logic):**

1.  **Load:** Read the requested Krono seamless textures and static passes.
2.  **Tile & Scale:** Tile the seamless texture to match the required resolution/scale.
3.  **UV Remapping:** Use `cv2.remap()` along with the `uv_pass.exr` to warp the flat texture into the correct 3D perspective.
4.  **Masking:** Extract the specific zone from `id_mask.png` and apply it as an alpha mask to the warped texture.
5.  **Blending:** Blend the masked, warped texture with the `base_pass.png` using a Multiply blend mode (for shadows).
6.  **Output:** Save the final composited image to disk.
