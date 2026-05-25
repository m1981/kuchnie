# generate_assets.py
import os
import cv2
import numpy as np


def create_checkerboard(size=512, squares=8):
    """Creates a checkerboard texture to easily see scaling and warping."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    sq_size = size // squares
    for i in range(squares):
        for j in range(squares):
            if (i + j) % 2 == 0:
                img[i * sq_size:(i + 1) * sq_size, j * sq_size:(j + 1) * sq_size] = (200, 200, 200)
            else:
                img[i * sq_size:(i + 1) * sq_size, j * sq_size:(j + 1) * sq_size] = (50, 50, 150)
    return img


def generate():
    os.makedirs("assets/textures", exist_ok=True)
    width, height = 800, 600

    # 1. Create Base Pass (A room with a floor and a shadow)
    base = np.full((height, width, 3), 220, dtype=np.uint8)  # Wall
    pts = np.array([[150, 400], [650, 400], [800, 600], [0, 600]], np.int32)  # Floor trapezoid
    cv2.fillPoly(base, [pts], (150, 150, 150))  # Base floor color
    # Add a fake shadow on the floor
    shadow_pts = np.array([[150, 400], [300, 400], [200, 600], [0, 600]], np.int32)
    cv2.fillPoly(base, [shadow_pts], (80, 80, 80))
    cv2.imwrite("assets/base_pass.png", base)

    # 2. Create ID Mask (Red for the floor)
    mask = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], (0, 0, 255))  # Red in BGR
    cv2.imwrite("assets/id_mask.png", mask)

    # 3. Create UV Pass (Perspective warped EXR)
    os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    # Create a flat UV map
    flat_uv = np.zeros((1000, 1000, 3), dtype=np.float32)
    flat_uv[:, :, 2] = np.linspace(0, 1, 1000)  # U (Red)
    flat_uv[:, :, 1] = np.linspace(0, 1, 1000).reshape(-1, 1)  # V (Green)

    # Warp it into the floor trapezoid perspective
    src_pts = np.array([[0, 0], [1000, 0], [1000, 1000], [0, 1000]], dtype=np.float32)
    dst_pts = np.array([[150, 400], [650, 400], [800, 600], [0, 600]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    uv_pass = cv2.warpPerspective(flat_uv, matrix, (width, height), flags=cv2.INTER_LINEAR)
    cv2.imwrite("assets/uv_pass.exr", uv_pass)

    # 4. Create Texture
    tex = create_checkerboard(512, 8)
    cv2.imwrite("assets/textures/krono_oak.jpg", tex)

    print("✅ Synthetic assets generated in the 'assets/' folder!")


if __name__ == "__main__":
    generate()