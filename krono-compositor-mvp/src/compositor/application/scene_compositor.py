from typing import List
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
            out_path: str,
            uv_scale_mm: float = 1000.0  # NEW: 1.0 UV unit = 1000mm by default
    ) -> None:
        """Executes the compositing pipeline for multiple zones in a single pass."""

        base_pass = self.reader.read_color(base_path)
        id_mask = self.reader.read_color(mask_path)
        uv_map = self.reader.read_uv(uv_path)

        target_shape = base_pass.shape[:2]
        current_composite = base_pass

        for zone in zones:
            texture = self.reader.read_color(zone.texture_path)

            # NEW: Calculate the physical scale dynamically
            calculated_scale = zone.texture_width_mm / uv_scale_mm

            tiled_tex = self.tiler.tile(texture, target_shape, calculated_scale)
            warped_tex = self.warper.warp(tiled_tex, uv_map)
            zone_mask = self.masker.extract(id_mask, zone.mask_color)
            current_composite = self.blender.multiply(current_composite, warped_tex, zone_mask)

        self.writer.write(out_path, current_composite)