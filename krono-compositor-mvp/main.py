import time
from compositor.infrastructure.opencv_impl import (
    OpenCVImageIO,
    OpenCVTextureTiler,
    OpenCVUVWarper,
    OpenCVMaskExtractor,
    OpenCVImageBlender
)
from compositor.application.scene_compositor import SceneCompositor


def main():
    print("Initializing 2.5D Compositing Engine...")

    # 1. Instantiate the concrete OpenCV implementations
    io_handler = OpenCVImageIO()
    tiler = OpenCVTextureTiler()
    warper = OpenCVUVWarper()
    masker = OpenCVMaskExtractor()
    blender = OpenCVImageBlender()

    # 2. Inject them into the Compositor
    compositor = SceneCompositor(
        reader=io_handler,
        writer=io_handler,  # OpenCVImageIO implements both Reader and Writer
        tiler=tiler,
        warper=warper,
        masker=masker,
        blender=blender
    )

    # 3. Define our asset paths
    # Make sure these files exist in your 'assets' folder!
    base_pass_path = "assets/base_pass.png"
    uv_pass_path = "assets/uv_pass.exr"
    id_mask_path = "assets/id_mask.png"
    texture_path = "assets/textures/krono_oak.jpg"
    output_path = "assets/final_render.jpg"

    # Assuming Red (0, 0, 255 in BGR) is the target zone in your ID mask
    TARGET_COLOR_BGR = (0, 0, 255)
    TEXTURE_SCALE = 2.0  # Adjust this to make the wood grain larger/smaller

    print(f"Rendering zone with texture: {texture_path}")

    start_time = time.perf_counter()

    try:
        # 4. Execute the pipeline
        compositor.render_zone(
            base_path=base_pass_path,
            uv_path=uv_pass_path,
            mask_path=id_mask_path,
            tex_path=texture_path,
            target_color=TARGET_COLOR_BGR,
            out_path=output_path,
            scale=TEXTURE_SCALE
        )

        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000

        print(f"Success! Image saved to {output_path}")
        print(f"Execution time: {execution_time_ms:.2f} ms")

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please ensure you have placed the dummy/real assets in the 'assets/' folder.")


if __name__ == "__main__":
    main()