# tests/application/test_scene_compositor.py
from unittest.mock import MagicMock
import numpy as np

# We will create this class next!
from compositor.application.scene_compositor import SceneCompositor


def test_scene_compositor_pipeline_execution():
    # 1. Arrange: Create Mocks for all our interfaces
    mock_reader = MagicMock()
    mock_writer = MagicMock()
    mock_tiler = MagicMock()
    mock_warper = MagicMock()
    mock_masker = MagicMock()
    mock_blender = MagicMock()

    # Setup dummy return values for the mocks so they pass data down the pipeline
    dummy_base = np.zeros((2, 2, 3))
    dummy_uv = np.zeros((2, 2, 3))
    dummy_id = np.zeros((2, 2, 3))
    dummy_tex = np.zeros((2, 2, 3))

    mock_reader.read_color.side_effect = [dummy_base, dummy_id, dummy_tex]
    mock_reader.read_uv.return_value = dummy_uv

    dummy_tiled = np.ones((2, 2, 3))
    mock_tiler.tile.return_value = dummy_tiled

    dummy_warped = np.ones((2, 2, 3)) * 2
    mock_warper.warp.return_value = dummy_warped

    dummy_mask = np.ones((2, 2, 1))
    mock_masker.extract.return_value = dummy_mask

    dummy_final = np.ones((2, 2, 3)) * 3
    mock_blender.multiply.return_value = dummy_final

    # Inject mocks into the Compositor
    compositor = SceneCompositor(
        reader=mock_reader,
        writer=mock_writer,
        tiler=mock_tiler,
        warper=mock_warper,
        masker=mock_masker,
        blender=mock_blender
    )

    # 2. Act: Run the pipeline
    compositor.render_zone(
        base_path="base.png",
        uv_path="uv.exr",
        mask_path="id.png",
        tex_path="tex.jpg",
        target_color=(0, 0, 255),
        out_path="out.jpg",
        scale=2.0
    )

    # 3. Assert: Verify the pipeline called everything in the correct order
    # Check IO
    assert mock_reader.read_color.call_count == 3
    mock_reader.read_uv.assert_called_once_with("uv.exr")

    # Check Domain Logic
    mock_tiler.tile.assert_called_once_with(dummy_tex, dummy_base.shape[:2], 2.0)
    mock_warper.warp.assert_called_once_with(dummy_tiled, dummy_uv)
    mock_masker.extract.assert_called_once_with(dummy_id, (0, 0, 255))
    mock_blender.multiply.assert_called_once_with(dummy_base, dummy_warped, dummy_mask)

    # Check Output
    mock_writer.write.assert_called_once_with("out.jpg", dummy_final)