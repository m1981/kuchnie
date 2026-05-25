import cv2
import numpy as np
import os

def create_solid(color_bgr):
    return np.full((512, 512, 3), color_bgr, dtype=np.uint8)

os.makedirs("assets/textures", exist_ok=True)

# Dąb Szlachetny (Brownish)
cv2.imwrite("assets/textures/dab_szlachetny.jpg", create_solid((104, 139, 168)))
# Zielony Kamienny (Dark Green)
cv2.imwrite("assets/textures/zielony_kamienny.jpg", create_solid((94, 93, 74)))
# Marmur Bianco (Almost White)
cv2.imwrite("assets/textures/marmur_bianco.jpg", create_solid((245, 245, 245)))
# Czarny Strukturalny (Almost Black)
cv2.imwrite("assets/textures/czarny_strukturalny.jpg", create_solid((34, 34, 34)))
# Dąb Casella Jasny (Light Wood)
cv2.imwrite("assets/textures/dab_casella_jasny.jpg", create_solid((149, 184, 212)))
# Alabast (Off-white)
cv2.imwrite("assets/textures/alabast.jpg", create_solid((220, 232, 234)))

print("Missing catalog textures generated!")