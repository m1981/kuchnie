# tests/application/test_scene_compositor.py
from unittest.mock import MagicMock
import numpy as np

from compositor.application.scene_compositor import SceneCompositor
from compositor.domain.interfaces import ZoneConfig


def test_scene_compositor_calculates_physical_scale():
    # 1. Arrange
    mock_reader = MagicMock()
    mock_writer = MagicMock()
    mock_tiler = MagicMock()
    mock_warper = MagicMock()
    mock_masker = MagicMock()
    mock_blender = MagicMock()

    dummy_base = np.zeros((2, 2, 3))
    mock_reader.read_color.return_value = dummy_base
    mock_reader.read_uv.return_value = np.zeros((2, 2, 3))
    mock_blender.multiply.return_value = dummy_base

    compositor = SceneCompositor(
        reader=mock_reader, writer=mock_writer, tiler=mock_tiler,
        warper=mock_warper, masker=mock_masker, blender=mock_blender
    )

    # Scene UV Scale: 1.0 UV unit = 1000mm
    scene_uv_scale_mm = 1000.0

    # Zone 1: Texture is 2000mm wide (should result in scale = 2.0)
    # Zone 2: Texture is 500mm wide (should result in scale = 0.5)
    zones = [
        ZoneConfig(mask_color=(0, 0, 255), texture_path="tex1.jpg", texture_width_mm=2000.0),
        ZoneConfig(mask_color=(0, 255, 0), texture_path="tex2.jpg", texture_width_mm=500.0)
    ]

    # 2. Act
    compositor.render_scene(
        base_path="base.png",
        uv_path="uv.exr",
        mask_path="id.png",
        zones=zones,
        out_path="out.jpg",
        uv_scale_mm=scene_uv_scale_mm  # NEW PARAMETER
    )

    # 3. Assert
    # Verify the tiler was called with the CORRECTLY CALCULATED scales
    assert mock_tiler.tile.call_count == 2

    # Call 1: 2000 / 1000 = 2.0
    call_1_args = mock_tiler.tile.call_args_list[0]
    assert call_1_args[0][2] == 2.0  # The 3rd argument is 'scale'

    # Call 2: 500 / 1000 = 0.5
    call_2_args = mock_tiler.tile.call_args_list[1]
    assert call_2_args[0][2] == 0.5