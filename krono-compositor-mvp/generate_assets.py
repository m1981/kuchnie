# generate_assets.py
import os
import cv2
import numpy as np


def create_checkerboard(size=512, squares=8, color1=(200, 200, 200), color2=(50, 50, 150)):
    img = np.zeros((size, size, 3), dtype=np.uint8)
    sq_size = size // squares
    for i in range(squares):
        for j in range(squares):
            if (i + j) % 2 == 0:
                img[i * sq_size:(i + 1) * sq_size, j * sq_size:(j + 1) * sq_size] = color1
            else:
                img[i * sq_size:(i + 1) * sq_size, j * sq_size:(j + 1) * sq_size] = color2
    return img


def generate():
    os.makedirs("assets/textures", exist_ok=True)
    width, height = 800, 600

    # --- Define our 3 Kitchen Zones (x1, y1, x2, y2) ---
    upper_cab = (150, 50, 650, 250)
    countertop = (100, 350, 700, 380)
    lower_cab = (150, 380, 650, 550)

    # 1. Create Base Pass (Lighting & Shadows)
    base = np.full((height, width, 3), 240, dtype=np.uint8)  # Wall
    cv2.rectangle(base, (upper_cab[0], upper_cab[1]), (upper_cab[2], upper_cab[3]), (200, 200, 200), -1)
    cv2.rectangle(base, (countertop[0], countertop[1]), (countertop[2], countertop[3]), (220, 220, 220), -1)
    cv2.rectangle(base, (lower_cab[0], lower_cab[1]), (lower_cab[2], lower_cab[3]), (180, 180, 180), -1)

    # Add fake Ambient Occlusion (Shadows) under the cabinets
    cv2.rectangle(base, (150, 250), (650, 270), (100, 100, 100), -1)  # Shadow under upper cab
    cv2.rectangle(base, (150, 380), (650, 400), (80, 80, 80), -1)  # Shadow under countertop lip
    cv2.imwrite("assets/base_pass.png", base)

    # 2. Create ID Mask (3 Distinct Colors)
    mask = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.rectangle(mask, (upper_cab[0], upper_cab[1]), (upper_cab[2], upper_cab[3]), (255, 0, 0), -1)  # BLUE = Upper
    cv2.rectangle(mask, (countertop[0], countertop[1]), (countertop[2], countertop[3]), (0, 255, 0), -1)  # GREEN = Top
    cv2.rectangle(mask, (lower_cab[0], lower_cab[1]), (lower_cab[2], lower_cab[3]), (0, 0, 255), -1)  # RED = Lower
    cv2.imwrite("assets/id_mask.png", mask)

    # 3. Create UV Pass
    os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    uv_pass = np.zeros((height, width, 3), dtype=np.float32)

    def apply_flat_uv(zone_rect):
        x1, y1, x2, y2 = zone_rect
        w, h = x2 - x1, y2 - y1
        u = np.tile(np.linspace(0, 1, w, dtype=np.float32), (h, 1))
        v = np.tile(np.linspace(0, 1, h, dtype=np.float32).reshape(-1, 1), (1, w))
        uv_pass[y1:y2, x1:x2, 2] = u  # Red channel
        uv_pass[y1:y2, x1:x2, 1] = v  # Green channel

    apply_flat_uv(upper_cab)
    apply_flat_uv(countertop)
    apply_flat_uv(lower_cab)
    cv2.imwrite("assets/uv_pass.exr", uv_pass)

    # 4. Create Textures
    cv2.imwrite("assets/textures/wood_oak.jpg",
                create_checkerboard(512, 4, (100, 150, 200), (50, 100, 150)))  # Blueish wood
    cv2.imwrite("assets/textures/marble_white.jpg",
                create_checkerboard(512, 16, (250, 250, 250), (220, 220, 220)))  # Tiny white tiles

    print("✅ 3-Zone Kitchen assets generated!")


if __name__ == "__main__":
    generate()