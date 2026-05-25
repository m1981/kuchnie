from pydantic import BaseModel, Field
from typing import List, Tuple

class ZoneRequest(BaseModel):
    mask_color_hex: str = Field(..., description="Hex color code, e.g., #FF0000 for Red")
    texture_id: str = Field(..., description="ID of the texture, e.g., wood_oak")
    texture_width_mm: float = Field(..., gt=0, description="Physical width of the texture in mm")

    def get_bgr_tuple(self) -> Tuple[int, int, int]:
        """Translates Frontend HEX to OpenCV BGR."""
        hex_color = self.mask_color_hex.lstrip('#')
        # Parse to RGB
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # Return as BGR
        return (rgb[2], rgb[1], rgb[0])

class RenderRequest(BaseModel):
    scene_id: str = Field(..., description="ID of the scene, e.g., kitchen_01")
    uv_scale_mm: float = Field(1000.0, gt=0, description="Physical scale of 1.0 UV unit")
    zones: List[ZoneRequest]