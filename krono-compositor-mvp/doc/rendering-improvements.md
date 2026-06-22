# Rendering Quality Improvement Plan

## Problem Statement

The current 2.5D compositing output looks flat and unrealistic. The root cause is poor input assets from Blender, not the OpenCV pipeline.

**Current state:**

- Base pass is almost pure white — no AO, no contact shadows, no depth
- Reflection pass is black — nothing to reflect, no HDRI environment
- Cabinets are perfect sharp cubes — no bevels, no edge highlights
- Single flat light source — no dimensionality

**Target state:**

- Base pass has rich ambient occlusion gradients in corners and gaps
- Reflection pass shows meaningful specular highlights on surfaces
- Cabinet edges catch light and cast micro-shadows
- 3-point lighting creates depth and dimension
- Output approaches IKEA/interior design catalog quality (~85-90% photorealistic for fixed camera)

---

## Phase 1: Blender Asset Improvements

### Step 1.1 — Enable Ambient Occlusion ✅ DONE

**What:** Add AO to the base pass render so corners, gaps, and contact areas are visibly darker.

**Changes in `gen_kitchen.py`:**

- Enable `scene.cycles.use_ambient_occlusion = True` (or use compositor AO node)
- Set AO distance to ~0.3m (covers cabinet gaps and countertop overhang)
- Increase base pass samples from 64 to 128 for cleaner AO

**Acceptance criteria:**

- [ ] Dark gradients visible where tall cabinet meets base cabinets
- [ ] Shadow gradient under countertop overhang
- [ ] Cabinet gap lines (4mm) are clearly defined dark lines
- [ ] No noise/grain in AO (clean render)

**Verification:** Render base_pass.png, visually inspect for AO gradients in corners and gaps.

---

### Step 1.2 — 3-Point Lighting Setup ✅ DONE

**What:** Replace single softbox with a professional 3-point studio lighting setup.

**Changes in `gen_kitchen.py`:**

- **Key light:** Area lamp at 45° top-right, energy 800W, warm tone (1.0, 0.95, 0.9), size 3×2m
- **Fill light:** Area lamp at left side, energy 250W, cool tone (0.9, 0.95, 1.0), size 4×3m
- **Rim light:** Area lamp behind camera, energy 400W, neutral tone, size width×0.5m
- World background: blue tint (0.8, 0.85, 0.9) at strength 0.05

**Acceptance criteria:**

- [ ] Cabinet faces show visible light gradient (brighter top, darker bottom)
- [ ] Left side of tall cabinet is slightly cooler/darker than right side
- [ ] Rim light creates subtle highlight strip on top edges of base cabinets
- [ ] No blown-out pure white areas on any surface
- [ ] Shadows have soft falloff, not hard edges

**Verification:** Render base_pass.png, check for directional lighting and gradient across surfaces.

---

### Step 1.3 — Add Bevels to Cabinet Geometry ✅ DONE

**What:** Add small bevels (1-2mm) to all cabinet edges so they catch highlights and cast micro-shadows.

**Changes in `gen_kitchen.py`:**

- After creating each front mesh, apply Bevel modifier:
    - `modifier = obj.modifiers.new(name='Bevel', type='BEVEL')`
    - `modifier.width = 0.001` (1mm)
    - `modifier.segments = 2`
    - Apply modifier before UV unwrap
- Same for carcass objects (optional, less visible)

**Acceptance criteria:**

- [ ] Thin highlight line visible along top edge of base cabinets
- [ ] Edge between front and countertop has subtle shadow/highlight contrast
- [ ] No visible faceting or shading artifacts on flat surfaces
- [ ] UV map still correct after bevel (no texture stretching on edges)

**Verification:** Render base_pass.png, zoom into cabinet edges to confirm edge highlights.

---

### Step 1.4 — Add Floor Plane ✅ DONE

**What:** Add a ground plane beneath the cabinets to catch contact shadows and ground the scene.

**Changes in `gen_kitchen.py`:**

- After countertop generation, create a large plane:
    - Position at Z=0, extending 1m beyond cabinet boundaries in all directions
    - Material: neutral grey (0.3, 0.3, 0.3), low roughness (0.8)
- Do NOT include floor in `fronts_collection` (should not get texture compositing)
- Floor should cast/receive shadows but not appear in ID mask

**Acceptance criteria:**

- [ ] Soft contact shadow visible under base cabinets
- [ ] Shadow gradient radiates outward from cabinet base
- [ ] Floor does NOT appear in id_mask.png (no yellow/red/green/blue on floor)
- [ ] Floor does NOT appear in base pass as a configurable zone
- [ ] Scene feels "grounded" — no floating cabinet illusion

**Verification:** Render all passes. Check id_mask has no floor color. Check base_pass has floor shadow.

---

### Step 1.5 — HDRI Environment for Reflections

**What:** Replace black world background with an HDRI studio environment for meaningful reflections.

**Changes in `gen_kitchen.py`:**

- For reflection pass: use a neutral studio HDRI instead of pure black
- Option A: Download a free HDRI (e.g., "studio_small_09" from polyhaven.com) and load it
- Option B: Create a procedural gradient environment in Blender nodes (no external file):
    - Warm gradient top (slightly bright), cool gradient bottom (darker)
    - This gives the glossy surfaces something to reflect
- Set world strength to 0.3 for reflections (subtle, not dominant)

**Acceptance criteria:**

- [ ] reflection_pass.png is NOT mostly black — shows visible gradient/highlights
- [ ] Glossy cabinet fronts show subtle environment reflection
- [ ] Countertop (marble) shows clear specular highlight from key light
- [ ] Reflections are physically plausible (not stretched, not inverted)

**Verification:** Render reflection_pass.png, confirm visible content (not black). Screen-blend over base should add visible sheen.

---

### Step 1.6 — Camera Angle Adjustment ✅ DONE

**What:** Shift camera from dead-frontal to a slight 3/4 view for better depth perception.

**Changes in `gen_kitchen.py`:**

- Current: `cam_obj.location = (center_x, -distance, distance * 0.3)` — frontal
- New: Shift X by +15% of total width, raise Z by 10%, move Y back by 10%
    - `cam_obj.location = (center_x + total_width * 0.15, -distance * 1.1, distance * 0.4)`
- Adjust empty_target to compensate: `empty_target.location = (center_x, 0, 0.9)`
- Keep TRACK_TO constraint

**Acceptance criteria:**

- [ ] Right side of base cabinets is slightly visible (not flat frontal)
- [ ] Perspective lines converge naturally (not extreme wide-angle distortion)
- [ ] All 4 zones still clearly identifiable in id_mask.png
- [ ] Camera frames entire kitchen with small margin (not cropped)

**Verification:** Render all passes. Confirm 3/4 angle. Check id_mask zones are clean and complete.

---

## Phase 2: OpenCV Post-Processing (Optional Enhancements)

### Step 2.1 — Base Pass Contrast Enhancement

**What:** Apply contrast curve to base pass before multiplying textures, to deepen shadows and preserve highlights.

**Changes in `src/compositor/application/scene_compositor.py`:**

- After loading base_pass, apply:
    - Gamma correction: `base_f = np.power(base_f, 0.85)` (darkens midtones)
    - Optional: S-curve contrast adjustment
- This deepens AO gradients without touching Blender

**Acceptance criteria:**

- [ ] Composited output has visibly deeper shadows than current
- [ ] Bright areas (countertop) are not blown out
- [ ] Wood grain texture shows shadow detail in gap areas
- [ ] No banding or posterization artifacts

**Verification:** Compare composited output before/after. Check shadow areas specifically.

---

### Step 2.2 — Synthetic Edge AO

**What:** Generate artificial contact shadows along cabinet gaps using edge detection on ID mask.

**Changes in `src/compositor/infrastructure/opencv_impl.py`:**

- New method `generate_edge_ao(id_mask, gap_width=3)`:
    - Convert ID mask to grayscale
    - Apply Canny edge detection
    - Dilate edges with gaussian kernel
    - Invert and normalize to [0.5, 1.0] range (subtle darkening only)
- Apply as multiply layer before texture compositing

**Acceptance criteria:**

- [ ] 2-3px dark gradient visible along cabinet gap lines
- [ ] Effect is subtle — not thick black lines
- [ ] Works for all zone boundaries, not just specific colors
- [ ] No artifacts on smooth surfaces (only affects edges)

**Verification:** Compare output with/without edge AO. Zoom into gap areas.

---

## Execution Order

1. Step 1.1 (AO) — highest impact, immediate visual improvement
2. Step 1.2 (Lighting) — transforms the base pass quality
3. Step 1.3 (Bevels) — adds edge definition
4. Step 1.4 (Floor) — grounds the scene
5. Step 1.5 (HDRI) — makes reflections meaningful
6. Step 1.6 (Camera) — final composition polish
7. Step 2.1 (Contrast) — fine-tune compositing output
8. Step 2.2 (Edge AO) — synthetic depth enhancement

Each step is committed separately after visual verification of improvement.
