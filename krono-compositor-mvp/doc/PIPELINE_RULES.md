# Architectural Rules for 2.5D Image Compositing Pipelines

When building an OpenCV-based 2.5D compositing engine that relies on pre-rendered 3D assets, strict boundaries must be maintained between "Art Passes" and "Math Passes".

## 1. The Dithering & Anti-Aliasing Trap (ID Masks)

- **The Problem:** 3D engines (like Blender/Cycles) default to adding Anti-Aliasing (blurring edges) and Dithering (adding random noise to prevent 8-bit color banding). This destroys mathematical ID masks. OpenCV's `cv2.inRange()` demands exact pixel values. Dithering causes OpenCV to skip pixels, resulting in "sand-like" noise leaking through textures.
- **The Fix (3D Side):** When rendering ID Masks or UV Passes, you MUST disable Anti-Aliasing (`filter_size = 0.0`), disable Dithering (`dither_intensity = 0.0`), and disable AI Denoisers.
- **The Fix (Engine Side):** OpenCV extraction must use a tolerance range (e.g., `+/- 5` RGB values) rather than exact matching to survive sub-pixel variations and future JPG compression.

## 2. The "Black Room" Rule (Reflection Passes)

- **The Problem:** A reflection pass rendered in a white environment will output a noisy, pure-white image. When blended via `Screen` or `Add` in OpenCV, it washes out the entire composite.
- **The Fix:** Reflection passes must be rendered against a pitch-black `(0,0,0)` World Background, illuminated only by specific light sources (Softboxes).

## 3. Base Pass Volume (Multiply Blending)

- **The Problem:** If a Base Pass is flat white, multiplying a texture over it results in a flat texture. 2.5D depth comes entirely from the shadows.
- **The Fix:** The Base Pass must be rendered with Ambient Occlusion (AO) and soft contact shadows. The white areas should be ~90% white to allow textures to pop, while the corners and gaps must fall off into rich grays/blacks.

## 4. Alpha Compositing via Shadow Catchers (Hardware/Handles)

- **The Rule:** Real-time hardware (like handles) cannot just be flat PNGs. They must be rendered using a "Shadow Catcher" workflow so the PNG includes the semi-transparent drop-shadows cast onto the cabinets, allowing OpenCV to naturally darken the underlying textures.
