# src/compositor/presentation/api.py
import os
import cv2
import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List

from compositor.application.scene_compositor import SceneCompositor
from compositor.domain.interfaces import ZoneConfig
from compositor.infrastructure.opencv_impl import (
    OpenCVImageIO, OpenCVTextureTiler, OpenCVUVWarper,
    OpenCVMaskExtractor, OpenCVImageBlender
)
from compositor.presentation.schemas import RenderRequest, ZoneType, AllowedZone
from compositor.presentation.catalog_db import CATALOG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_logger")

router = APIRouter(prefix="/api/v1", tags=["Render"])


def get_compositor() -> SceneCompositor:
    io_handler = OpenCVImageIO()
    return SceneCompositor(
        reader=io_handler, writer=io_handler, tiler=OpenCVTextureTiler(),
        warper=OpenCVUVWarper(), masker=OpenCVMaskExtractor(), blender=OpenCVImageBlender()
    )


@router.get("/catalog")
def get_catalog():
    """Returns the full catalog of materials, price groups, and scenes."""
    return CATALOG


@router.post("/render")
def render_image(request: RenderRequest, compositor: SceneCompositor = Depends(get_compositor)):
    logger.info(f"--- Render Request: {request.scene_id} | Angle: {request.angle_id} ---")

    # 1. Dynamic Path Resolution
    scene_dir = f"assets/scenes/{request.scene_id}/{request.angle_id}"
    base_path = f"{scene_dir}/base_pass.png"
    uv_path = f"{scene_dir}/uv_pass.exr"
    mask_path = f"{scene_dir}/id_mask.png"

    if not os.path.exists(base_path):
        raise HTTPException(status_code=404, detail=f"Scene assets not found at {scene_dir}")

    # 2. Business Logic Validation & Domain Mapping
    domain_zones: List[ZoneConfig] = []

    for zone_req in request.zones:
        # Find material in catalog
        material = next((m for m in CATALOG["materials"] if m["id"] == zone_req.texture_id), None)
        if not material:
            raise HTTPException(status_code=404, detail=f"Material '{zone_req.texture_id}' not found in catalog.")

        # Validate Constraints ("dostępny tylko jako front")
        if material["allowed_zone"] == AllowedZone.FRONT_ONLY and zone_req.zone_type != ZoneType.FRONT:
            raise HTTPException(status_code=400, detail=f"Material '{material['name']}' is only available for Fronts.")
        if material["allowed_zone"] == AllowedZone.COUNTERTOP_ONLY and zone_req.zone_type != ZoneType.COUNTERTOP:
            raise HTTPException(status_code=400,
                                detail=f"Material '{material['name']}' is only available for Countertops.")

        # Resolve texture path
        tex_path = f"assets/textures/{zone_req.texture_id}.jpg"

        # THE FIX: Remove the silent fallback and raise a 500 error
        if not os.path.exists(tex_path):
            logger.error(f"Missing asset on disk: {tex_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Server configuration error: Texture file for '{material['name']}' is missing."
            )

        domain_zones.append(
            ZoneConfig(
                mask_color=zone_req.get_bgr_tuple(),
                texture_path=tex_path,
                texture_width_mm=material["texture_width_mm"]  # Backend is now the source of truth for physical size!
            )
        )

    try:
        final_image_array = compositor.render_scene(
            base_path=base_path, uv_path=uv_path, mask_path=mask_path,
            zones=domain_zones, out_path=None, uv_scale_mm=request.uv_scale_mm
        )

        success, encoded_image = cv2.imencode('.jpg', final_image_array)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to encode image.")

        return Response(content=encoded_image.tobytes(), media_type="image/jpeg")

    except Exception as e:
        logger.error(f"Render failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))