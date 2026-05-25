# tests/application/test_scene_compositor.py
from unittest.mock import MagicMock, call
import numpy as np

from compositor.application.scene_compositor import SceneCompositor
from compositor.domain.interfaces import ZoneConfig


def test_scene_compositor_multi_zone_pipeline():
    # 1. Arrange: Create Mocks
    mock_reader = MagicMock()
    mock_writer = MagicMock()
    mock_tiler = MagicMock()
    mock_warper = MagicMock()
    mock_masker = MagicMock()
    mock_blender = MagicMock()

    # Dummy arrays
    dummy_base = np.zeros((2, 2, 3))
    dummy_uv = np.zeros((2, 2, 3))
    dummy_id = np.zeros((2, 2, 3))
    dummy_tex_1 = np.ones((2, 2, 3)) * 10
    dummy_tex_2 = np.ones((2, 2, 3)) * 20

    # Reader returns Base, then ID Mask, then Texture 1, then Texture 2
    mock_reader.read_color.side_effect = [dummy_base, dummy_id, dummy_tex_1, dummy_tex_2]
    mock_reader.read_uv.return_value = dummy_uv

    # Blender returns a new image each time it's called
    dummy_blend_1 = np.ones((2, 2, 3)) * 100
    dummy_blend_2 = np.ones((2, 2, 3)) * 200
    mock_blender.multiply.side_effect = [dummy_blend_1, dummy_blend_2]

    compositor = SceneCompositor(
        reader=mock_reader, writer=mock_writer, tiler=mock_tiler,
        warper=mock_warper, masker=mock_masker, blender=mock_blender
    )

    # Create two zones to render
    zones = [
        ZoneConfig(mask_color=(0, 0, 255), texture_path="tex1.jpg", scale=1.0),
        ZoneConfig(mask_color=(0, 255, 0), texture_path="tex2.jpg", scale=2.0)
    ]

    # 2. Act
    compositor.render_scene(
        base_path="base.png",
        uv_path="uv.exr",
        mask_path="id.png",
        zones=zones,
        out_path="out.jpg"
    )

    # 3. Assert
    # Base and ID mask read once, plus 2 textures = 4 color reads total
    assert mock_reader.read_color.call_count == 4
    mock_reader.read_uv.assert_called_once_with("uv.exr")

    # Domain logic should be called twice (once per zone)
    assert mock_tiler.tile.call_count == 2
    assert mock_warper.warp.call_count == 2
    assert mock_masker.extract.call_count == 2
    assert mock_blender.multiply.call_count == 2

    # The final write should be called exactly once with the output of the SECOND blend
    mock_writer.write.assert_called_once_with("out.jpg", dummy_blend_2)