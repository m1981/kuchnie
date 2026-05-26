# tests/infrastructure/test_opencv_impl.py
import numpy as np
from compositor.infrastructure.opencv_impl import (
    OpenCVMaskExtractor,
    OpenCVImageBlender,
    OpenCVTextureTiler
)


class TestOpenCVMaskExtractor:
    def test_extract_target_color_creates_correct_float_mask(self, dummy_id_mask):
        # Arrange
        extractor = OpenCVMaskExtractor()
        target_color_red = (0, 0, 255)  # BGR

        # Act
        result_mask = extractor.extract(dummy_id_mask, target_color_red)

        # Assert
        assert result_mask.dtype == np.float32
        assert result_mask.shape == (4, 4, 1)  # Must have the channel dimension for broadcasting

        # Left half should be 1.0 (Red matched)
        np.testing.assert_array_equal(result_mask[:, :2], 1.0)
        # Right half should be 0.0 (Blue did not match)
        np.testing.assert_array_equal(result_mask[:, 2:], 0.0)


class TestOpenCVImageBlender:
    def test_multiply_blend_math_is_correct(self, dummy_base_image, dummy_mask_float):
        # Arrange
        blender = OpenCVImageBlender()

        # Create a layer that is solid dark gray (BGR: 50, 50, 50)
        layer = np.full((4, 4, 3), 50, dtype=np.uint8)

        # Act
        # Blend layer over base using the half-and-half mask
        result = blender.multiply(dummy_base_image, layer, dummy_mask_float)

        # Assert
        assert result.dtype == np.uint8
        assert result.shape == (4, 4, 3)

        # Math check for the LEFT half (Mask = 1.0):
        # Base(100/255) * Layer(50/255) = 0.0769
        # 0.0769 * 255 = 19.6 -> truncated to 19 by astype(np.uint8)
        expected_blended_value = 19
        np.testing.assert_array_equal(result[:, :2], expected_blended_value)
        np.testing.assert_array_equal(result[:, :2], expected_blended_value)

        # Math check for the RIGHT half (Mask = 0.0):
        # Should remain exactly the base image (100)
        np.testing.assert_array_equal(result[:, 2:], 100)

    def test_screen_blend_math_is_correct(self, dummy_base_image):
        # Arrange
        blender = OpenCVImageBlender()
        # Base is 100 (from fixture). 100/255 = 0.392

        # Create a reflection layer that is dark gray (50)
        # 50/255 = 0.196
        reflection = np.full((4, 4, 3), 50, dtype=np.uint8)

        # Act
        result = blender.screen(dummy_base_image, reflection)

        # Assert
        assert result.dtype == np.uint8
        assert result.shape == (4, 4, 3)

        # Screen Math: 1.0 - (1.0 - Base) * (1.0 - Layer)
        # 1.0 - (1.0 - 0.392) * (1.0 - 0.196)
        # 1.0 - (0.608 * 0.804) = 1.0 - 0.4888 = 0.5112
        # 0.5112 * 255 = 130.3 -> truncated to 130
        expected_value = 130
        np.testing.assert_array_equal(result, expected_value)

    def test_alpha_composite_math_is_correct(self, dummy_base_image):
        # Arrange
        blender = OpenCVImageBlender()
        # Base is 100 (RGB)

        # Create an RGBA layer (e.g., a Handle)
        # RGB = 200, Alpha = 128 (~50% opacity)
        rgba_layer = np.full((4, 4, 4), 200, dtype=np.uint8)
        rgba_layer[:, :, 3] = 128

        # Act
        result = blender.alpha_composite(dummy_base_image, rgba_layer)

        # Assert
        assert result.dtype == np.uint8
        assert result.shape == (4, 4, 3)  # Output must be RGB, not RGBA!

        # Alpha Math: Foreground * Alpha + Background * (1 - Alpha)
        # Alpha float = 128 / 255.0 = 0.5019
        # (200 * 0.5019) + (100 * (1.0 - 0.5019))
        # 100.38 + 49.81 = 150.19 -> truncated to 150
        expected_value = 150
        np.testing.assert_array_equal(result, expected_value)

class TestOpenCVTextureTiler:
    def test_tile_scales_image_correctly(self, dummy_texture):
        # Arrange
        tiler = OpenCVTextureTiler()
        target_shape = (100, 100)  # Note: Our current impl ignores this and relies on scale

        # Act
        # Scale a 2x2 image by 2.0
        result = tiler.tile(dummy_texture, target_shape, scale=2.0)

        # Assert
        assert result.shape == (4, 4, 3)  # 2x2 scaled by 2.0 becomes 4x4

    def test_tile_returns_original_if_scale_is_one(self, dummy_texture):
        # Arrange
        tiler = OpenCVTextureTiler()

        # Act
        result = tiler.tile(dummy_texture, (100, 100), scale=1.0)

        # Assert
        # Should return the exact same object in memory (optimization)
        assert result is dummy_texture