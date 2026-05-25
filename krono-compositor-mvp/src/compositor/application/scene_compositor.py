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
            out_path: str
    ) -> None:
        """Executes the compositing pipeline for multiple zones in a single pass."""

        # 1. Load Static Assets ONCE
        base_pass = self.reader.read_color(base_path)
        id_mask = self.reader.read_color(mask_path)
        uv_map = self.reader.read_uv(uv_path)

        target_shape = base_pass.shape[:2]

        # This variable will accumulate our layers. It starts as the base pass.
        current_composite = base_pass

        # 2. Process each zone sequentially
        for zone in zones:
            # Load specific texture
            texture = self.reader.read_color(zone.texture_path)

            # Tile & Warp
            tiled_tex = self.tiler.tile(texture, target_shape, zone.scale)
            warped_tex = self.warper.warp(tiled_tex, uv_map)

            # Extract Mask
            zone_mask = self.masker.extract(id_mask, zone.mask_color)

            # Blend over the CURRENT composite (not the original base pass)
            current_composite = self.blender.multiply(current_composite, warped_tex, zone_mask)

        # 3. Output the final accumulated image ONCE
        self.writer.write(out_path, current_composite)