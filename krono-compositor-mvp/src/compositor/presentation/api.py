import os
import tempfile
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List

from compositor.application.scene_compositor import SceneCompositor
from compositor.domain.interfaces import ZoneConfig
from compositor.infrastructure.opencv_impl import (
    OpenCVImageIO, OpenCVTextureTiler, OpenCVUVWarper,
    OpenCVMaskExtractor, OpenCVImageBlender
)
from compositor.presentation.schemas import RenderRequest

# --- Setup Smart Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_logger")

router = APIRouter(prefix="/api/v1", tags=["Render"])


def get_compositor() -> SceneCompositor:
    io_handler = OpenCVImageIO()
    return SceneCompositor(
        reader=io_handler, writer=io_handler, tiler=OpenCVTextureTiler(),
        warper=OpenCVUVWarper(), masker=OpenCVMaskExtractor(), blender=OpenCVImageBlender()
    )


def cleanup_temp_file(path: str):
    """Background task to delete the image after the browser downloads it."""
    try:
        os.remove(path)
        logger.info(f"Cleaned up temp file: {path}")
    except Exception as e:
        logger.error(f"Failed to clean up {path}: {e}")


@router.post("/render", response_class=FileResponse)
def render_image(
        request: RenderRequest,
        background_tasks: BackgroundTasks,  # Added for cleanup
        compositor: SceneCompositor = Depends(get_compositor)
):
    logger.info(f"--- New Render Request: {request.scene_id} ---")

    base_path = "assets/base_pass.png"
    uv_path = "assets/uv_pass.exr"
    mask_path = "assets/id_mask.png"

    domain_zones: List[ZoneConfig] = []
    for zone_req in request.zones:
        tex_path = f"assets/textures/{zone_req.texture_id}.jpg"
        domain_zones.append(
            ZoneConfig(
                mask_color=zone_req.get_bgr_tuple(),
                texture_path=tex_path,
                texture_width_mm=zone_req.texture_width_mm
            )
        )

    # Create temp file in the local project directory to avoid macOS /var/folders permission issues
    temp_dir = os.path.join(os.getcwd(), "assets", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    temp_out = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False, suffix=".jpg")
    temp_out.close()

    logger.info(f"Target output path: {temp_out.name}")

    try:
        # Execute Engine
        compositor.render_scene(
            base_path=base_path,
            uv_path=uv_path,
            mask_path=mask_path,
            zones=domain_zones,
            out_path=temp_out.name,
            uv_scale_mm=request.uv_scale_mm
        )

        # --- SMART DEBUG CHECKS ---
        if not os.path.exists(temp_out.name):
            logger.error("File does not exist after render!")
            raise HTTPException(status_code=500, detail="Engine failed to create file.")

        file_size = os.path.getsize(temp_out.name)
        logger.info(f"Render complete. File size: {file_size} bytes")

        if file_size == 0:
            logger.error("File size is 0 bytes! OpenCV failed to encode the JPEG.")
            raise HTTPException(status_code=500, detail="Engine created an empty file.")

        # Schedule cleanup after response is sent
        background_tasks.add_task(cleanup_temp_file, temp_out.name)

        return FileResponse(
            path=temp_out.name,
            media_type="image/jpeg",
            filename="render.jpg"
        )

    except Exception as e:
        logger.error(f"Render failed with exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))