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

    # Real-world physical configuration!
    kitchen_configuration = [
        ZoneConfig(
            mask_color=(0, 0, 255),
            texture_path="assets/textures/krono_oak.jpg",
            texture_width_mm=1200.0  # This Krono texture represents 1.2 meters of wood
        ),
        ZoneConfig(
            mask_color=(0, 255, 0),
            texture_path="assets/textures/krono_oak.jpg",
            texture_width_mm=600.0  # Same texture, but scaled to represent 60cm
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
            uv_scale_mm=1000.0  # The 3D scene was exported where 1 UV unit = 1 meter
        )

        end_time = time.perf_counter()
        print(f"Success! Physically scaled multi-zone image saved.")
        print(f"Execution time: {(end_time - start_time) * 1000:.2f} ms")

    except FileNotFoundError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()