### The Conflicting Paradigms (Art vs. Math)

The friction we experienced (the noisy renders, the blown-out pixels, the transparent pinholes) happened because 3D rendering engines and Computer Vision libraries view the world through fundamentally opposed paradigms.

#### Paradigm A: Blender (Psycho-Visual Approximation)

Blender’s primary goal is to **trick the human eye**.
To make a digital image look "real," 3D engines rely on organic imperfection.

- **Anti-Aliasing:** If a red cabinet overlaps a green wall, Blender blends the edge pixels into a brownish-yellow so the human eye doesn't see a jagged staircase effect.
- **Dithering:** Blender randomly shakes pixel color values by 1 or 2 points to prevent visible "banding" in gradients.
- **The Paradigm:** _"Close enough is perfect, as long as it looks smooth."_

#### Paradigm B: OpenCV (Deterministic Matrix Mathematics)

OpenCV’s primary goal is to **process exact numerical data**.
To OpenCV, an image is not a picture; it is a multi-dimensional NumPy array.

- **Binary Logic:** If we ask OpenCV to find Red `[255, 0, 0]`, it looks for exactly that. A dithered pixel of `[254, 0, 0]` is mathematically rejected.
- **Coordinate Mapping:** If OpenCV reads a UV map, it expects exact float values. If Blender "anti-aliases" a UV edge, it averages the coordinate `0.9` with the background coordinate `0.0`, resulting in `0.45`. OpenCV will mathematically warp your texture to the center of the room instead of the edge of the cabinet.
- **The Paradigm:** _"Precision is absolute. Approximations cause mathematical crashes."_

---

### Part 2: How We Achieved Separation of Concerns (SoC)

To stop these paradigms from fighting, we had to draw a hard architectural boundary. We decided that **Blender is the Offline Geometry Engine**, and **OpenCV is the Real-Time Texture Engine**.

They never talk to each other directly. They only communicate through a strict "Data Contract" (the exported files).

Here is how we separated their concerns:

#### 1. Blender’s Concern: The "Heavy" Physics & Geometry

We restricted Blender to doing what it does best: calculating complex 3D space, perspective, and light bounces.

- Blender calculates the camera angle.
- Blender calculates where the shadows fall.
- Blender calculates the physical UV unwrapping.
- **Crucially:** Blender does _not_ apply the Krono textures. If Blender applied the textures, we would have to run a 10-second 3D render every time the user clicked a button.

#### 2. OpenCV’s Concern: The "Light" Real-Time Math

We restricted OpenCV to doing what it does best: lightning-fast matrix multiplication.

- OpenCV does _not_ know what a "cabinet" or a "camera" is.
- It only knows: _"Take this 2D array of wood pixels, warp it according to this 32-bit float array, and multiply it by this shadow array."_
- Because OpenCV is only doing 2D math, it can swap a texture in 50 milliseconds.

#### 3. The Data Contract (The Bridge)

To safely pass data across the boundary, we had to choose the right file formats to protect the math:

- **The Art Contract (`base_pass.png`, `reflection_pass.png`):** We used standard 8-bit PNGs. We _allowed_ Blender to use its Art Paradigm (Dithering, Denoisers, Anti-aliasing) here because OpenCV is just visually overlaying these files.
- **The Math Contract (`uv_pass.exr`):** We used **32-bit OpenEXR**. Standard 8-bit images only hold 256 values, which is not enough precision for 3D coordinates. EXR holds millions of decimal points, allowing OpenCV to map textures with sub-pixel accuracy.

---

### The Ultimate Architectural Solution

The defining moment of our Separation of Concerns was when we wrote this specific code in the Headless Blender script:

```python
def configure_engine_for_art():
    scene.cycles.use_denoising = True
    scene.render.filter_size = 1.5
    scene.render.dither_intensity = 1.0

def configure_engine_for_math():
    scene.cycles.use_denoising = False
    scene.render.filter_size = 0.0
    scene.render.dither_intensity = 0.0
```
