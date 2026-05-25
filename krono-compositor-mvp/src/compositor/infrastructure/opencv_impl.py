import os
import cv2
import numpy as np
from typing import Tuple

# Import our domain types (this does not violate DIP because interfaces.py has no logic)
from compositor.domain.interfaces import Image, UVMap, Mask, ColorBGR

# Enable EXR support in OpenCV globally for this module
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"


class OpenCVImageIO:
    """Handles reading and writing images from/to disk using OpenCV."""

    def read_color(self, path: str) -> Image:
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"Failed to load color image at: {path}")
        return img

    def read_uv(self, path: str) -> UVMap:
        # IMREAD_ANYCOLOR | IMREAD_ANYDEPTH ensures we get the 32-bit float data from EXRs
        img = cv2.imread(path, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        if img is None:
            raise FileNotFoundError(f"Failed to load UV map at: {path}")
        return img

    def write(self, path: str, image: Image) -> None:
        success = cv2.imwrite(path, image)
        if not success:
            raise IOError(f"Failed to write image to: {path}")


class OpenCVTextureTiler:
    """
    Handles scaling the texture.
    Note: We don't actually 'tile' (repeat) the image array in memory here.
    We just scale it. The actual repeating is handled by the UVWarper's BORDER_WRAP.
    This is a massive performance optimization.
    """

    def tile(self, texture: Image, target_shape: Tuple[int, int], scale: float) -> Image:
        if scale == 1.0:
            return texture

        h, w = texture.shape[:2]
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        # INTER_AREA is best for shrinking, INTER_CUBIC for enlarging
        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
        return cv2.resize(texture, (new_w, new_h), interpolation=interpolation)


class OpenCVUVWarper:
    """Warps a 2D texture into 3D perspective using a UV Map."""

    def warp(self, texture: Image, uv_map: UVMap) -> Image:
        tex_h, tex_w = texture.shape[:2]

        # OpenCV loads EXR as BGR.
        # Standard Blender UVs: U -> Red (index 2), V -> Green (index 1)
        u_channel = uv_map[:, :, 2]
        v_channel = uv_map[:, :, 1]

        # Invert V channel (Blender origin is bottom-left, OpenCV is top-left)
        v_channel = 1.0 - v_channel

        # Convert normalized UVs [0.0, 1.0] to absolute texture pixel coordinates
        map_x = (u_channel * tex_w).astype(np.float32)
        map_y = (v_channel * tex_h).astype(np.float32)

        # cv2.BORDER_WRAP is the magic here: if UVs go beyond 1.0, it loops the texture seamlessly!
        warped = cv2.remap(
            texture,
            map_x,
            map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_WRAP
        )
        return warped


class OpenCVMaskExtractor:
    """Isolates a specific color zone from an ID mask."""

    def extract(self, id_mask: Image, target_color: ColorBGR) -> Mask:
        # Create a boolean mask where pixels exactly match the target color
        # Note: ID masks from 3D software should be rendered WITHOUT anti-aliasing for this to work perfectly.
        binary_mask = cv2.inRange(id_mask, target_color, target_color)

        # Convert to float32 [0.0, 1.0] and add channel dimension (H, W) -> (H, W, 1)
        # This shape is required for NumPy broadcasting during the blending phase.
        float_mask = (binary_mask.astype(np.float32) / 255.0)[..., np.newaxis]
        return float_mask


class OpenCVImageBlender:
    """Blends images using math operations."""

    def multiply(self, base: Image, layer: Image, mask: Mask) -> Image:
        # Convert to float32 [0.0, 1.0] for accurate math
        base_f = base.astype(np.float32) / 255.0
        layer_f = layer.astype(np.float32) / 255.0

        # Multiply blend mode: Base * Layer
        # This keeps shadows dark and highlights colored
        blended_f = base_f * layer_f

        # Composite using the alpha mask
        # Where mask is 1.0, use blended. Where mask is 0.0, use original base.
        final_f = (blended_f * mask) + (base_f * (1.0 - mask))

        # Convert back to 8-bit integer [0, 255]
        final_img = (final_f * 255.0).clip(0, 255).astype(np.uint8)
        return final_img