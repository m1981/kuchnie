from typing import List
import cv2
from compositor.domain.interfaces import (
    ImageReader,
    ImageWriter,
    TextureTiler,
    UVWarper,
    MaskExtractor,
    ImageBlender,
    ZoneConfig
)


class SceneCompositor:
    def __init__(
            self,
            reader: ImageReader,
            writer: ImageWriter,
            tiler: TextureTiler,
            warper: UVWarper,
            masker: MaskExtractor,
            blender: ImageBlender
    ):
        self.reader = reader
        self.writer = writer
        self.tiler = tiler
        self.warper = warper
        self.masker = masker
        self.blender = blender

    def render_scene(
            self,
            base_path: str,
            uv_path: str,
            mask_path: str,
            zones: List[ZoneConfig],
            out_path: str = None,
            uv_scale_mm: float = 1000.0,
            reflection_path: str = None,  # NEW
            handle_path: str = None  # NEW
    ):
        base_pass = self.reader.read_color(base_path)
        id_mask = self.reader.read_color(mask_path)
        uv_map = self.reader.read_uv(uv_path)

        target_shape = base_pass.shape[:2]
        current_composite = base_pass

        # 1. Process all Krono/Egger Textures
        for zone in zones:
            texture = self.reader.read_color(zone.texture_path)
            repetition_factor = uv_scale_mm / zone.texture_width_mm
            tiled_tex = self.tiler.tile(texture, target_shape, scale=1.0)
            warped_tex = self.warper.warp(tiled_tex, uv_map, repetition_factor)
            zone_mask = self.masker.extract(id_mask, zone.mask_color)
            current_composite = self.blender.multiply(current_composite, warped_tex, zone_mask)

        # 2. Apply Photorealistic Reflections (If provided)
        if reflection_path:
            try:
                reflection_pass = self.reader.read_color(reflection_path)
                current_composite = self.blender.screen(current_composite, reflection_pass)
            except FileNotFoundError:
                pass  # Fail gracefully if scene doesn't have reflections

        # 3. Apply Handles and Shadows (If provided)
        if handle_path:
            try:
                # MUST use read_rgba to keep the transparent shadows!
                handle_pass = self.reader.read_rgba(handle_path)
                current_composite = self.blender.alpha_composite(current_composite, handle_pass)
            except FileNotFoundError:
                pass

        # ==========================================
        # THE FIX: SUPER-SAMPLING ANTI-ALIASING (SSAA)
        # ==========================================
        # Shrink the image by 50% using INTER_AREA.
        # This averages 4 pixels into 1, creating perfect, smooth edges.
        h, w = current_composite.shape[:2]
        final_composite = cv2.resize(current_composite, (w // 2, h // 2), interpolation=cv2.INTER_AREA)

        if out_path:
            self.writer.write(out_path, final_composite)

        return final_composite # Return the smooth, downscaled image!