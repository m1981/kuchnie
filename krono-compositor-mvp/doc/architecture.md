### 1. Architectural Decisions (The "What" and "How")

We built this system using **Clean Architecture** and **Domain-Driven Design (DDD)**. We strictly separated the _rules of the business_ from the _tools of the technology_.

- **The Core Domain (`interfaces.py`):** We strictly followed the **Interface Segregation Principle (ISP)**. We didn't build a monolithic `ImageProcessor`. We defined tiny, single-purpose contracts (`TextureTiler`, `UVWarper`, `MaskExtractor`). This meant our high-level `SceneCompositor` knew _nothing_ about OpenCV or NumPy.
- **The Infrastructure Layer (`opencv_impl.py`):** This is where we implemented the math. Because it was isolated, when we had to add advanced PBR (Screen Blending, Alpha Compositing), we didn't risk breaking the high-level orchestration logic.
- **The Presentation Layer (FastAPI):** We built a **Stateless, In-Memory API**. Instead of writing temp files to the Mac's hard drive (which caused race conditions and I/O bottlenecks), we encoded the final OpenCV NumPy array directly into JPEG bytes in RAM and streamed it to the browser.
- **The Frontend (Alpine.js + Tailwind):** We rejected heavy frameworks like SvelteKit/Next.js for the MVP. By using CDN-based Alpine.js, we achieved a modern, reactive, SPA-like UX (Smart filtering, real-time fetching, CSS zooming) with **Zero Build Steps**.
- **The Asset Generator (Headless Blender):** We abandoned manual 3D GUI work for a **Procedural Text-to-3D Pipeline**. By driving Blender via its Python API (`bpy`) using JSON layouts, we guaranteed mathematically perfect UV exports at infinite scale.

---

### 2. Key Implementation Decisions (The "Why")

1.  **Physical UV Scaling over Simple Resizing:**
    - _Decision:_ We mapped 1.0 UV unit to exactly 1000mm in 3D space, and calculated repetitions using `1000 / texture_width_mm`.
    - _Why:_ In a commercial configurator, a 60cm cabinet and a 120cm cabinet must display the exact same physical wood grain size. Simple image stretching looks cheap; physical UV multiplication looks photorealistic.
2.  **`def` instead of `async def` in FastAPI:**
    - _Decision:_ We used a synchronous route for the rendering endpoint.
    - _Why:_ OpenCV matrix multiplication is heavily **CPU-Bound**. If we used `async`, the OpenCV math would block the entire async event loop, freezing the web server for all other users. FastAPI automatically sends standard `def` routes to a separate worker thread pool.
3.  **Strict 500 Errors over Silent Fallbacks:**
    - _Decision:_ When an asset was missing, we threw a `500 Internal Server Error` instead of falling back to a default wood texture.
    - _Why:_ Silent failures are the enemy of enterprise software. The fallback hid the fact that we were missing real textures, causing a confusing visual bug. Fail fast, fail loudly.

---

### 3. Lessons Learned & Pitfalls (For Future Development)

Bridging 3D (Blender) and 2D Math (OpenCV) is a minefield of conflicting paradigms. We uncovered three major traps that will define how you build assets in the future:

#### Lesson 1: 3D Art defaults will destroy 2D Math.

- **The Trap:** 3D engines use Anti-Aliasing (soft edges) and Dithering (pixel shaking) to make images look natural to the human eye.
- **The Consequence:** OpenCV expects binary, mathematical perfection. Dithered masks created transparent pinholes, resulting in "static TV noise." Anti-aliased edges caused OpenCV to stretch textures across the room.
- **The Fix:** We established a strict pipeline rule. **Art Passes** (Base, Reflections) use Denoisers and Dithering. **Math Passes** (UV, ID Mask) must have Filter Size = 0.0 and Dithering = 0.0.

#### Lesson 2: The "Black Room" Reflection Effect.

- **The Trap:** To get a clean reflection pass, we turned the Blender World Background to pure black.
- **The Consequence:** Flat cabinets act like mirrors. They reflected the black void, making the image far too dark and hiding the glossy highlights.
- **The Fix:** You must use large, bright **Studio Softboxes (Area Lights)** positioned to reflect directly off the cabinet surfaces into the camera lens.

#### Lesson 3: Computer Vision Requires "Tolerance".

- **The Trap:** `cv2.inRange(img, [255,0,0], [255,0,0])` demands a 100.0% match.
- **The Consequence:** If a PNG is ever converted to a JPG, or if an artist accidentally paints `254, 0, 0`, the entire masking engine fails.
- **The Fix:** Always program padding/tolerance into CV color extractors. Using `target +/- 5` safeguarded our entire backend against organic pixel fluctuations.

---
