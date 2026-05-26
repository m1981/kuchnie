import numpy as np
from typing import Protocol, Tuple
from dataclasses import dataclass

# --- Domain Type Aliases for clarity ---
Image = np.ndarray      # Standard 8-bit BGR image
UVMap = np.ndarray      # 32-bit float image (EXR)
Mask = np.ndarray       # 1-channel float or boolean mask
ColorBGR = Tuple[int, int, int]

# --- Interface Segregation Principle (ISP) ---
# We break down the IO into Reader and Writer so classes only depend on what they need.

class ImageReader(Protocol):
    def read_color(self, path: str) -> Image:
        """Reads a standard 8-bit image (e.g., PNG, JPG) in BGR format."""
        ...
    def read_rgba(self, path: str) -> Image:
        """Reads an image keeping the Alpha channel (4 channels)."""
        ...
    def read_uv(self, path: str) -> UVMap:
        """Reads a high bit-depth UV map (e.g., EXR) in float32 format."""
        ...

class ImageWriter(Protocol):
    def write(self, path: str, image: Image) -> None:
        """Writes an image to disk."""
        ...

# --- Core Compositing Interfaces ---

class TextureTiler(Protocol):
    def tile(self, texture: Image, target_shape: Tuple[int, int], scale: float) -> Image:
        """
        Repeats and scales a seamless texture to match a target resolution.
        target_shape is (height, width).
        """
        ...

class UVWarper(Protocol):
    def warp(self, texture: Image, uv_map: UVMap) -> Image:
        """
        Warps a flat 2D texture into 3D perspective using a UV map.
        """
        ...

class MaskExtractor(Protocol):
    def extract(self, id_mask: Image, target_color: ColorBGR) -> Mask:
        """
        Isolates a specific color from an ID mask and returns a 1-channel alpha mask [0.0, 1.0].
        """
        ...

class ImageBlender(Protocol):
    def multiply(self, base: Image, layer: Image, mask: Mask) -> Image:
        ...

    def screen(self, base: Image, layer: Image) -> Image:
        """Blends a reflection/specular layer over the base."""
        ...

    def alpha_composite(self, base: Image, rgba_layer: Image) -> Image:
        """Overlays an RGBA image (with transparency) onto an RGB base."""
        ...

@dataclass(frozen=True)
class ZoneConfig:
    """Represents the configuration for a single configurable zone in the scene."""
    mask_color: ColorBGR
    texture_path: str
    texture_width_mm: float  # NEW: Physical width of the texture
    # We remove the old 'scale' property

