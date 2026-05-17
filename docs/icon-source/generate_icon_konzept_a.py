#!/usr/bin/env python3
"""
Jarvis 2.0 Icon Generator — Konzept A: The Orb Reborn
Apple HIG compliant: fills entire squircle canvas, depth, Fresnel highlight.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
cx, cy = SIZE // 2, SIZE // 2

Y, X = np.mgrid[0:SIZE, 0:SIZE]
DX = (X - cx).astype(float)
DY = (Y - cy).astype(float)
DIST = np.sqrt(DX**2 + DY**2)

# ─── BACKGROUND ───────────────────────────────────────────────────────────────
# Deep midnight navy — fills entire canvas, subtle radial gradient
bg_t = np.clip(DIST / (SIZE * 0.68), 0, 1) ** 1.4
bg = np.zeros((SIZE, SIZE, 3), dtype=float)
# Center: #0E1B3F → Edge: #060B18
bg[:,:,0] = 14 * (1 - bg_t) + 6 * bg_t
bg[:,:,1] = 27 * (1 - bg_t) + 11 * bg_t
bg[:,:,2] = 63 * (1 - bg_t) + 24 * bg_t

# ─── SOFT AMBIENT GLOW (behind orb, sets the mood) ────────────────────────────
ORB_R = int(SIZE * 0.345)  # radius 354px → diameter 708px (~69% canvas)

glow_t = np.clip(DIST / (ORB_R * 2.2), 0, 1)
glow_strength = (1 - glow_t) ** 2.8
bg[:,:,0] += glow_strength * 18
bg[:,:,1] += glow_strength * 48
bg[:,:,2] += glow_strength * 140

# ─── ORB ──────────────────────────────────────────────────────────────────────
orb_mask = DIST <= ORB_R
orb_norm = np.clip(DIST / ORB_R, 0, 1)

# Core glow — slightly upper-left of center (natural lighting)
CORE_OX, CORE_OY = -0.08, -0.11   # offset as fraction of ORB_R
core_dx = DX - CORE_OX * ORB_R
core_dy = DY - CORE_OY * ORB_R
core_dist_n = np.sqrt(core_dx**2 + core_dy**2) / (ORB_R * 0.70)
core_s = np.maximum(0, 1 - core_dist_n) ** 2.0

# Specular highlight — small sharp spot, upper-left
SPEC_OX, SPEC_OY = -0.30, -0.34
spec_dx = DX - SPEC_OX * ORB_R
spec_dy = DY - SPEC_OY * ORB_R
spec_dist_n = np.sqrt(spec_dx**2 + spec_dy**2) / (ORB_R * 0.28)
spec_s = np.maximum(0, 1 - spec_dist_n) ** 3.5

# Sphere shading: limb darkening (edge) + rim light (subtle blue edge glow)
limb = (1 - orb_norm**1.8) ** 0.35
rim_t = np.clip((orb_norm - 0.80) / 0.20, 0, 1)
rim_s = rim_t ** 0.6 * 0.55

orb = np.zeros((SIZE, SIZE, 3), dtype=float)

# Base sphere — deep blue body
orb[:,:,0][orb_mask] = 10  * limb[orb_mask]
orb[:,:,1][orb_mask] = 32  * limb[orb_mask]
orb[:,:,2][orb_mask] = 112 * limb[orb_mask]

# Core glow — bright electric blue → center near-white
orb[:,:,0][orb_mask] += core_s[orb_mask] * 88
orb[:,:,1][orb_mask] += core_s[orb_mask] * 148
orb[:,:,2][orb_mask] += core_s[orb_mask] * 145

# Rim light — cold blue edge
orb[:,:,0][orb_mask] += rim_s[orb_mask] * 28
orb[:,:,1][orb_mask] += rim_s[orb_mask] * 85
orb[:,:,2][orb_mask] += rim_s[orb_mask] * 200

# Specular — near-white highlight
orb[:,:,0][orb_mask] += spec_s[orb_mask] * 200
orb[:,:,1][orb_mask] += spec_s[orb_mask] * 215
orb[:,:,2][orb_mask] += spec_s[orb_mask] * 255

# Composite orb onto background
canvas = bg.copy()
canvas[:,:,0][orb_mask] = orb[:,:,0][orb_mask]
canvas[:,:,1][orb_mask] = orb[:,:,1][orb_mask]
canvas[:,:,2][orb_mask] = orb[:,:,2][orb_mask]

# ─── CONCENTRIC PULSE RINGS ───────────────────────────────────────────────────
# 2 rings outside orb — subtle activity indicator
rings = [
    (ORB_R * 1.22, ORB_R * 0.055, 0.30),  # inner ring
    (ORB_R * 1.52, ORB_R * 0.075, 0.16),  # outer ring
]
for r_center, r_half_width, opacity in rings:
    ring_dist = np.abs(DIST - r_center)
    ring_s = np.maximum(0, 1 - ring_dist / r_half_width) ** 1.8 * opacity
    canvas[:,:,0] += ring_s * 25
    canvas[:,:,1] += ring_s * 95
    canvas[:,:,2] += ring_s * 255

canvas = np.clip(canvas, 0, 255).astype(np.uint8)

# ─── FINAL BLUR PASS: soften orb edge transition ──────────────────────────────
img = Image.fromarray(canvas, 'RGB')

# Soft glow layer blended on top (gives the "energy" feel)
glow_img = Image.new('RGB', (SIZE, SIZE), (0, 0, 0))
glow_draw = ImageDraw.Draw(glow_img)
glow_draw.ellipse(
    [cx - ORB_R, cy - ORB_R, cx + ORB_R, cy + ORB_R],
    fill=(15, 55, 190)
)
glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=int(ORB_R * 0.18)))

glow_arr = np.array(glow_img).astype(float)
img_arr  = np.array(img).astype(float)
result   = np.clip(img_arr + glow_arr * 0.32, 0, 255).astype(np.uint8)
img = Image.fromarray(result, 'RGB')

out_path = '/tmp/jarvis_icon_1024.png'
img.save(out_path, 'PNG')
print(f"Icon saved: {out_path}")
print(f"Size: {img.size}")
