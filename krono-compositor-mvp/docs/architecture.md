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

> **See also:** [Blender Scene Configuration](blender-scene-reference.md) for detailed camera, lighting, geometry, and render pass settings.
> **See also:** [Conflicting Paradigms](conflicting_paradigms.md) and [Pipeline Rules](PIPELINE_RULES.md) for lessons learned bridging 3D rendering and 2D math.
