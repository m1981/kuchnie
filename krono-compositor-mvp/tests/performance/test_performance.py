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
from compositor.domain.interfaces import ZoneConfig


def test_full_pipeline_with_real_files(tmp_path: Path):
    # 1. ARRANGE
    base_path = str(tmp_path / "base.png")
    uv_path = str(tmp_path / "uv.exr")
    mask_path = str(tmp_path / "mask.png")
    tex_path = str(tmp_path / "tex.jpg")
    out_path = str(tmp_path / "out.jpg")

    cv2.imwrite(base_path, np.full((100, 100, 3), 150, dtype=np.uint8))

    os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    uv_map = np.zeros((100, 100, 3), dtype=np.float32)
    uv_map[:, :, 2] = np.linspace(0, 1, 100)
    uv_map[:, :, 1] = np.linspace(0, 1, 100)
    cv2.imwrite(uv_path, uv_map)

    cv2.imwrite(mask_path, np.full((100, 100, 3), (0, 0, 255), dtype=np.uint8))
    cv2.imwrite(tex_path, np.full((50, 50, 3), 255, dtype=np.uint8))

    # 2. ACT
    io_handler = OpenCVImageIO()
    compositor = SceneCompositor(
        reader=io_handler,
        writer=io_handler,
        tiler=OpenCVTextureTiler(),
        warper=OpenCVUVWarper(),
        masker=OpenCVMaskExtractor(),
        blender=OpenCVImageBlender()
    )

    zones = [ZoneConfig(mask_color=(0, 0, 255), texture_path=tex_path, scale=1.0)]

    compositor.render_scene(
        base_path=base_path,
        uv_path=uv_path,
        mask_path=mask_path,
        zones=zones,
        out_path=out_path
    )

    # 3. ASSERT
    assert os.path.exists(out_path), "The output file was not created on disk!"
    result_img = cv2.imread(out_path)
    assert result_img is not None, "The output file is corrupted or empty!"
    assert result_img.shape == (100, 100, 3), "The output image has the wrong dimensions!"