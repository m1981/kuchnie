# src/compositor/presentation/schemas.py
from pydantic import BaseModel, Field
from typing import List, Tuple
from enum import Enum

class ZoneType(str, Enum):
    FRONT = "FRONT"
    COUNTERTOP = "COUNTERTOP"

class AllowedZone(str, Enum):
    ANY = "ANY"
    FRONT_ONLY = "FRONT_ONLY"
    COUNTERTOP_ONLY = "COUNTERTOP_ONLY"

class ZoneRequest(BaseModel):
    mask_color_hex: str = Field(..., description="Hex color code, e.g., #FF0000")
    texture_id: str = Field(..., description="ID of the texture from the catalog")
    zone_type: ZoneType = Field(..., description="Is this a FRONT or COUNTERTOP?")

    def get_bgr_tuple(self) -> Tuple[int, int, int]:
        hex_color = self.mask_color_hex.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (rgb[2], rgb[1], rgb[0])

class RenderRequest(BaseModel):
    scene_id: str = Field(..., description="ID of the scene")
    angle_id: str = Field(..., description="ID of the camera angle")
    uv_scale_mm: float = Field(1000.0, gt=0)
    handle_id: str = Field(None, description="ID of the handle style (e.g., 'black_matte')") # NEW
    zones: List[ZoneRequest]