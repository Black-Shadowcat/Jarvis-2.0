#!/usr/bin/env python3
"""
Jarvis Manager Icon - Hintergrund Blau -> Rot, Orb/Waveform/Text unveraendert.
Basis: JARVIS_source_1254x1254.png (echtes Icon)
"""

import numpy as np
from PIL import Image
import os

src = os.path.join(os.path.dirname(__file__), 'JARVIS_source_1254x1254.png')
img = Image.open(src).convert('RGB')
img = img.resize((1024, 1024), Image.LANCZOS)
arr = np.array(img).astype(float)

r = arr[:,:,0]
g = arr[:,:,1]
b = arr[:,:,2]

brightness = (r + g + b) / 3 / 255  # 0..1

# Hintergrund-Erkennung:
# - Blau dominiert Rot (einfache, direkte Metrik)
# - Dunkel (helle Cyan-Pixel des Orb-Glows werden durch brightness geschuetzt)
bg_blue_dom = np.clip((b - r) / 60.0, 0, 1)
bg_dark     = np.clip(1 - brightness * 2.2, 0, 1)

# bg_weight: 1 = reiner Hintergrund, 0 = Orb-Glow/Waveform/Text
bg_weight = bg_blue_dom * bg_dark

# Transformation: Blau-Energie komplett auf Rot umlegen
r_new = b * 0.90 + r * 0.10   # Rot bekommt fast alle Blau-Energie
g_new = g * 0.30               # Gruen stark reduziert
b_new = b * 0.08 + r * 0.05   # Blau fast eliminiert

# Gewichtetes Mischen: bg_weight entscheidet wie stark die Transformation greift
result = np.zeros_like(arr)
result[:,:,0] = r * (1 - bg_weight) + r_new * bg_weight
result[:,:,1] = g * (1 - bg_weight) + g_new * bg_weight
result[:,:,2] = b * (1 - bg_weight) + b_new * bg_weight

result = np.clip(result, 0, 255).astype(np.uint8)
out_img = Image.fromarray(result, 'RGB')

out_path = os.path.join(os.path.dirname(__file__), 'jarvis_manager_1024.png')
out_img.save(out_path, 'PNG')
print(f"Icon gespeichert: {out_path}")
