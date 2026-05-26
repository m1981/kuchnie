import cv2
import numpy as np

# Load the base pass (RGB) and handle pass (RGBA)
base = cv2.imread('assets/base_pass.png', cv2.IMREAD_COLOR)
handle = cv2.imread('assets/handle_pass.png', cv2.IMREAD_UNCHANGED)

# Extract the Alpha channel and convert to float [0.0, 1.0]
alpha = handle[:, :, 3].astype(np.float32) / 255.0
alpha = alpha[:, :, np.newaxis] # Reshape for math

# Extract the BGR channels
handle_bgr = handle[:, :, :3].astype(np.float32)
base_f = base.astype(np.float32)

# Perform the Alpha Blend!
blended = (handle_bgr * alpha) + (base_f * (1.0 - alpha))

# Save the result
cv2.imwrite('assets/PROOF_IT_WORKS.png', blended.astype(np.uint8))
print("Check assets/PROOF_IT_WORKS.png!")