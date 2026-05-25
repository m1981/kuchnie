# tests/performance/test_performance.py
import os
import time
import cv2
import numpy as np
from pathlib import Path

from compositor.infrastructure.opencv_impl import (
    OpenCVImageIO,
    OpenCVTextureTiler,
    OpenCVUVWarper,
    OpenCVMaskExtractor,
    OpenCVImageBlender
)
from compositor.application.scene_compositor import SceneCompositor


def generate_4k_assets(tmp_path: Path):
    """Generates 4K (3840x2160) assets for stress testing."""
    width, height = 3840, 2160

    base_path = str(tmp_path / "base_4k.png")
    uv_path = str(tmp_path / "uv_4k.exr")
    mask_path = str(tmp_path / "mask_4k.png")
    tex_path = str(tmp_path / "tex_2k.jpg")
    out_path = str(tmp_path / "out_4k.jpg")

    # 1. 4K Base Pass
    cv2.imwrite(base_path, np.full((height, width, 3), 150, dtype=np.uint8))

    # 2. 4K UV Pass (EXR)
    os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    uv_map = np.zeros((height, width, 3), dtype=np.float32)
    # Fill with dummy UV data
    uv_map[:, :, 2] = np.linspace(0, 1, width, dtype=np.float32)
    uv_map[:, :, 1] = np.linspace(0, 1, height, dtype=np.float32).reshape(-1, 1)
    cv2.imwrite(uv_path, uv_map)

    # 3. 4K ID Mask
    cv2.imwrite(mask_path, np.full((height, width, 3), (0, 0, 255), dtype=np.uint8))

    # 4. 2K Texture (2048x2048 is standard for seamless materials)
    cv2.imwrite(tex_path, np.full((2048, 2048, 3), 255, dtype=np.uint8))

    return base_path, uv_path, mask_path, tex_path, out_path


def test_4k_rendering_performance(tmp_path: Path):
    print("\nGenerating 4K assets... (this might take a second)")
    base_path, uv_path, mask_path, tex_path, out_path = generate_4k_assets(tmp_path)

    io_handler = OpenCVImageIO()
    compositor = SceneCompositor(
        reader=io_handler,
        writer=io_handler,
        tiler=OpenCVTextureTiler(),
        warper=OpenCVUVWarper(),
        masker=OpenCVMaskExtractor(),
        blender=OpenCVImageBlender()
    )

    # 1. Warm-up run (loads libraries into memory, caches files in OS)
    compositor.render_zone(base_path, uv_path, mask_path, tex_path, (0, 0, 255), out_path)

    # 2. Benchmark run
    iterations = 5
    total_time = 0.0

    print(f"\nRunning {iterations} iterations of 4K compositing...")
    for i in range(iterations):
        start_time = time.perf_counter()

        compositor.render_zone(base_path, uv_path, mask_path, tex_path, (0, 0, 255), out_path)

        end_time = time.perf_counter()
        iteration_time = (end_time - start_time) * 1000  # Convert to ms
        total_time += iteration_time
        print(f"  Iteration {i + 1}: {iteration_time:.2f} ms")

    avg_time = total_time / iterations
    print(f"\nAverage 4K Execution Time: {avg_time:.2f} ms")

    # 3. Assert Performance (Adjust this threshold based on your M2's actual output)
    # Note: Reading/Writing 4K files to disk takes time. The pure math is much faster.
    # We set a generous threshold of 500ms for full Disk I/O + 4K Math.
    assert avg_time < 500.0, f"Performance too slow! Averaged {avg_time:.2f} ms"