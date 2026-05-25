# tests/conftest.py
import pytest
import numpy as np

@pytest.fixture
def dummy_base_image() -> np.ndarray:
    """A 4x4 solid gray image (BGR: 100, 100, 100)."""
    return np.full((4, 4, 3), 100, dtype=np.uint8)

@pytest.fixture
def dummy_texture() -> np.ndarray:
    """A 2x2 solid white texture (BGR: 255, 255, 255)."""
    return np.full((2, 2, 3), 255, dtype=np.uint8)

@pytest.fixture
def dummy_id_mask() -> np.ndarray:
    """
    A 4x4 ID mask.
    Left half is Red (0, 0, 255). Right half is Blue (255, 0, 0).
    """
    mask = np.zeros((4, 4, 3), dtype=np.uint8)
    mask[:, :2] = [0, 0, 255]  # Red
    mask[:, 2:] = [255, 0, 0]  # Blue
    return mask

@pytest.fixture
def dummy_mask_float() -> np.ndarray:
    """
    A 4x4x1 float32 mask.
    Left half is 1.0 (fully opaque), Right half is 0.0 (fully transparent).
    """
    mask = np.zeros((4, 4, 1), dtype=np.float32)
    mask[:, :2] = 1.0
    return mask