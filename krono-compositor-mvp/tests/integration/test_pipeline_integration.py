# tests/integration/test_pipeline_integration.py
import os
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


def test_full_pipeline_with_real_files(tmp_path: Path):
    """
    INTEGRATION TEST:
    Generates real files on disk, runs the real OpenCV pipeline,
    and verifies the output file is created correctly.
    """
    # 1. ARRANGE: Generate real files in a temporary directory
    base_path = str(tmp_path / "base.png")
    uv_path = str(tmp_path / "uv.exr")
    mask_path = str(tmp_path / "mask.png")
    tex_path = str(tmp_path / "tex.jpg")
    out_path = str(tmp_path / "out.jpg")

    # Create a 100x100 Base Pass (Gray)
    cv2.imwrite(base_path, np.full((100, 100, 3), 150, dtype=np.uint8))

    # Create a 100x100 UV Pass (EXR)
    os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    uv_map = np.zeros((100, 100, 3), dtype=np.float32)
    uv_map[:, :, 2] = np.linspace(0, 1, 100)  # U (Red)
    uv_map[:, :, 1] = np.linspace(0, 1, 100)  # V (Green)
    cv2.imwrite(uv_path, uv_map)

    # Create a 100x100 ID Mask (Red)
    cv2.imwrite(mask_path, np.full((100, 100, 3), (0, 0, 255), dtype=np.uint8))

    # Create a 50x50 Texture (White)
    cv2.imwrite(tex_path, np.full((50, 50, 3), 255, dtype=np.uint8))

    # 2. ACT: Setup the real engine and run it
    io_handler = OpenCVImageIO()
    compositor = SceneCompositor(
        reader=io_handler,
        writer=io_handler,
        tiler=OpenCVTextureTiler(),
        warper=OpenCVUVWarper(),
        masker=OpenCVMaskExtractor(),
        blender=OpenCVImageBlender()
    )

    compositor.render_zone(
        base_path=base_path,
        uv_path=uv_path,
        mask_path=mask_path,
        tex_path=tex_path,
        target_color=(0, 0, 255),  # Red
        out_path=out_path,
        scale=1.0
    )

    # 3. ASSERT: Verify the real file was created and processed
    assert os.path.exists(out_path), "The output file was not created on disk!"

    # Read the output file to verify it's a valid image
    result_img = cv2.imread(out_path)
    assert result_img is not None, "The output file is corrupted or empty!"
    assert result_img.shape == (100, 100, 3), "The output image has the wrong dimensions!"