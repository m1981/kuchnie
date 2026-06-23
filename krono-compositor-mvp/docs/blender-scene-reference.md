# Blender Scene Configuration Reference

The headless Blender script (`gen_kitchen.py`) generates 5 render passes from a JSON layout. This document records the exact scene parameters.

## Camera

- **Type:** Perspective, 50° FOV
- **Position:** 3/4 angle — shifted right by 35% of kitchen width, raised to 50% of distance
- **Target:** Centered on kitchen, slightly above midpoint (Z=0.85)
- **Constraint:** TRACK_TO constraint keeps camera locked on target

## 3-Point Studio Lighting

| Light    | Type | Energy | Color                 | Size       | Position       | Purpose                                    |
| -------- | ---- | ------ | --------------------- | ---------- | -------------- | ------------------------------------------ |
| **Key**  | Area | 800W   | Warm (1.0, 0.95, 0.9) | 3×2m       | Top-right, 45° | Main illumination, creates primary shadows |
| **Fill** | Area | 250W   | Cool (0.9, 0.95, 1.0) | 4×3m       | Left side      | Softens harsh shadows from key light       |
| **Rim**  | Area | 400W   | Neutral               | Width×0.5m | Behind camera  | Edge highlights on cabinet tops            |

## World Background

- **Color:** Slight blue tint (0.8, 0.85, 0.9)
- **Strength:** 0.05 (very low — lets lights do the work)
- **Purpose:** Provides minimal ambient fill without washing out shadows

## Ambient Occlusion

- **Method:** Fast GI (`use_fast_gi = True`, `fast_gi_method = 'REPLACE'`)
- **AO Bounces:** 4 (render quality)
- **Max Bounces:** 8 (indirect lighting quality)
- **Effect:** Darkens corners, gaps, and contact areas automatically

## Render Settings per Pass

| Pass       | Samples | Denoising | Filter Size | Dithering | Film Transparent |
| ---------- | ------- | --------- | ----------- | --------- | ---------------- |
| Base       | 128     | Yes       | 1.5         | 1.0       | No               |
| UV         | 1       | No        | 0.0         | 0.0       | Yes              |
| ID Mask    | 1       | No        | 0.0         | 0.0       | Yes              |
| Reflection | 128     | Yes       | 1.5         | 1.0       | Yes              |
| Handle     | 128     | Yes       | 1.5         | 1.0       | Yes              |

**Rule:** Art passes (Base, Reflection, Handle) use denoising and dithering. Math passes (UV, ID Mask) disable all post-processing to preserve pixel-perfect values.

## Geometry

- **Cabinets:** Cube primitives with 4mm gaps between doors
- **Fronts:** 18mm thick doors with 1mm bevels (2 segments) for edge highlights
- **Carcasses:** Dark boxes (0.02, 0.02, 0.02) behind fronts
- **Countertop:** Spans all base cabinets with 20mm overhang, 40mm thickness
- **Floor:** Neutral grey plane (0.35, 0.35, 0.35) for contact shadows
- **Handles:** Edge pull style — horizontal lip + vertical drop, metallic material

## Collections (Visibility Control)

| Collection | Base | UV  | ID Mask | Reflection | Handle |
| ---------- | ---- | --- | ------- | ---------- | ------ |
| Fronts     | ✅   | ✅  | ✅      | ✅         | ✅     |
| Carcasses  | ✅   | ✅  | ✅      | ✅         | ✅     |
| Handles    | ❌   | ❌  | ❌      | ❌         | ✅     |
| Floor      | ✅   | ❌  | ❌      | ✅         | ✅     |
