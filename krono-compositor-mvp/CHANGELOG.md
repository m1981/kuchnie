# Changelog

## Rendering Quality Improvements

- **Enabled Ambient Occlusion** — Fast GI with 4 AO bounces; corners, gaps, and contact areas now show dark gradients.
- **3-Point Studio Lighting** — Key (800W warm), Fill (250W cool), Rim (400W neutral) area lights replace single softbox.
- **Bevels on Cabinet Geometry** — 1mm bevels with 2 segments add edge highlights and micro-shadows.
- **Floor Plane** — Neutral grey ground plane catches contact shadows; excluded from ID mask and UV passes.
- **Camera 3/4 Angle** — Shifted right by 15% width, raised 10%, for better depth perception.

## Architecture

- **Clean Architecture + DDD** — Domain interfaces, infrastructure implementations, application orchestration, presentation layer.
- **Physical UV Scaling** — 1.0 UV unit = 1000mm; textures repeat at real-world dimensions.
- **Stateless In-Memory API** — NumPy → JPEG bytes in RAM, streamed directly to browser.
- **Procedural Blender Pipeline** — Headless `bpy` script generates 5 render passes from JSON layout.
