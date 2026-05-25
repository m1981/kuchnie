import os
import cv2
import numpy as np

# Enable EXR support for saving
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"


def generate_assets():
    width, height = 800, 600
    print("Generating synthetic assets for MVP testing...")

    # 1. Generate Base Pass (Gray background with a fake dark shadow in the middle)
    base_pass = np.ones((height, width, 3), dtype=np.uint8) * 200  # Light gray
    # Add a fake shadow (darker area)
    cv2.circle(base_pass, (width // 2, height // 2), 150, (100, 100, 100), -1)
    # Blur it to look like a soft shadow
    base_pass = cv2.GaussianBlur(base_pass, (99, 99), 0)
    cv2.imwrite("base_pass.png", base_pass)
    print("- Created base_pass.png")

    # 2. Generate UV Pass (32-bit float EXR)
    # U (Red) goes 0.0 to 1.0 left to right. V (Green) goes 0.0 to 1.0 bottom to top.
    u = np.linspace(0, 1, width, dtype=np.float32)
    v = np.linspace(0, 1, height, dtype=np.float32)
    uu, vv = np.meshgrid(u, v)

    # OpenCV uses BGR. Red is index 2, Green is index 1, Blue is index 0.
    uv_pass = np.zeros((height, width, 3), dtype=np.float32)
    uv_pass[:, :, 2] = uu  # U -> Red
    uv_pass[:, :, 1] = vv  # V -> Green (Note: we will invert this in the compositor)

    cv2.imwrite("uv_pass.exr", uv_pass)
    print("- Created uv_pass.exr")

    # 3. Generate ID Mask (Left half is Red, Right half is Blue)
    id_mask = np.zeros((height, width, 3), dtype=np.uint8)
    id_mask[:, :width // 2] = [0, 0, 255]  # Red in BGR (Target Zone)
    id_mask[:, width // 2:] = [255, 0, 0]  # Blue in BGR (Other Zone)
    cv2.imwrite("id_mask.png", id_mask)
    print("- Created id_mask.png")

    # 4. Generate a Dummy Seamless Texture (Checkerboard)
    tex_size = 256
    texture = np.zeros((tex_size, tex_size, 3), dtype=np.uint8)
    texture[0:tex_size // 2, 0:tex_size // 2] = [50, 200, 50]  # Green square
    texture[tex_size // 2:, tex_size // 2:] = [50, 200, 50]  # Green square
    texture[0:tex_size // 2, tex_size // 2:] = [200, 200, 50]  # Yellow square
    texture[tex_size // 2:, 0:tex_size // 2] = [200, 200, 50]  # Yellow square
    cv2.imwrite("seamless_texture.jpg", texture)
    print("- Created seamless_texture.jpg")

    print("Done! You can now run compositor.py")


if __name__ == "__main__":
    generate_assets()