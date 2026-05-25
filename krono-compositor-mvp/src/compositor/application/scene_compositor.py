from compositor.domain.interfaces import (
    ImageReader,
    ImageWriter,
    TextureTiler,
    UVWarper,
    MaskExtractor,
    ImageBlender,
    ColorBGR
)


class SceneCompositor:
    """
    Orchestrates the 2.5D compositing pipeline.
    Relies entirely on injected dependencies (Interfaces) to do the actual work.
    """

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

    def render_zone(
            self,
            base_path: str,
            uv_path: str,
            mask_path: str,
            tex_path: str,
            target_color: ColorBGR,
            out_path: str,
            scale: float = 1.0
    ) -> None:
        """Executes the compositing pipeline for a single zone."""

        # 1. Load Assets
        base_pass = self.reader.read_color(base_path)
        id_mask = self.reader.read_color(mask_path)
        texture = self.reader.read_color(tex_path)
        uv_map = self.reader.read_uv(uv_path)

        # 2. Tile/Scale Texture
        # We pass the base_pass shape so the tiler knows the target resolution
        target_shape = base_pass.shape[:2]
        tiled_tex = self.tiler.tile(texture, target_shape, scale)

        # 3. Warp Texture into 3D perspective
        warped_tex = self.warper.warp(tiled_tex, uv_map)

        # 4. Extract Alpha Mask for the target zone
        zone_mask = self.masker.extract(id_mask, target_color)

        # 5. Blend
        final_image = self.blender.multiply(base_pass, warped_tex, zone_mask)

        # 6. Output
        self.writer.write(out_path, final_image)