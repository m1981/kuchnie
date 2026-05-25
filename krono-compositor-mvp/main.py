import time
from compositor.infrastructure.opencv_impl import (
    OpenCVImageIO, OpenCVTextureTiler, OpenCVUVWarper,
    OpenCVMaskExtractor, OpenCVImageBlender
)
from compositor.application.scene_compositor import SceneCompositor
from compositor.domain.interfaces import ZoneConfig


def main():
    print("Initializing 2.5D Compositing Engine...")

    io_handler = OpenCVImageIO()
    compositor = SceneCompositor(
        reader=io_handler, writer=io_handler, tiler=OpenCVTextureTiler(),
        warper=OpenCVUVWarper(), masker=OpenCVMaskExtractor(), blender=OpenCVImageBlender()
    )

    # Configure our 3 Kitchen Zones!
    kitchen_configuration = [
        ZoneConfig(
            mask_color=(0, 0, 255),  # RED mask = Lower Cabinets
            texture_path="assets/textures/wood_oak.jpg",
            texture_width_mm=1200.0
        ),
        ZoneConfig(
            mask_color=(255, 0, 0),  # BLUE mask = Upper Cabinets
            texture_path="assets/textures/wood_oak.jpg",
            texture_width_mm=600.0  # Same wood, but scaled smaller!
        ),
        ZoneConfig(
            mask_color=(0, 255, 0),  # GREEN mask = Countertop
            texture_path="assets/textures/marble_white.jpg",
            texture_width_mm=2000.0  # Large marble slab
        )
    ]

    start_time = time.perf_counter()

    try:
        compositor.render_scene(
            base_path="assets/base_pass.png",
            uv_path="assets/uv_pass.exr",
            mask_path="assets/id_mask.png",
            zones=kitchen_configuration,
            out_path="assets/final_render.jpg",
            uv_scale_mm=1000.0
        )

        end_time = time.perf_counter()
        print(f"Success! 3-Zone Kitchen rendered.")
        print(f"Execution time: {(end_time - start_time) * 1000:.2f} ms")

    except FileNotFoundError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()