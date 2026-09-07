import os
import time
import numpy as np
from PIL import Image

def generate_4k_textures(output_dir="output/yu_nian_an/textures", resolution=4096):
    os.makedirs(output_dir, exist_ok=True)
    H = W = resolution
    print(f"Generating 4K PBR Texture Suite ({W}x{H}) in {output_dir}...")
    start_time = time.time()

    # Coordinate grids normalized to [0, 1]
    y_coords, x_coords = np.mgrid[0:H, 0:W].astype(np.float32)
    u = x_coords / W
    v = y_coords / H

    # --------------------------------------------------------------------------
    # 1. MASK DEFINITIONS FOR ATLAS ZONES
    # --------------------------------------------------------------------------
    # Q1: Head & Face (u < 0.5, v < 0.5)
    mask_q1 = (u < 0.5) & (v < 0.5)
    # Q2: Upper Body & Limbs (u >= 0.5, v < 0.5)
    mask_q2 = (u >= 0.5) & (v < 0.5)
    # Q3: Wardrobe - Silk Dress (u < 0.5, v >= 0.5)
    mask_q3 = (u < 0.5) & (v >= 0.5)
    # Q4: Sash, Sandals, Hardware, Accents (u >= 0.5, v >= 0.5)
    mask_q4 = (u >= 0.5) & (v >= 0.5)

    # Sub-regions in Q1 (Head/Face):
    # Normalized coords within Q1: u1 = u * 2, v1 = v * 2 in [0, 1]
    u1 = u * 2.0
    v1 = v * 2.0

    # Scalp: top of head (v1 < 0.22)
    mask_scalp = mask_q1 & (v1 < 0.22)

    # Eyes:
    # Left eye: center at (u1=0.35, v1=0.45), radius approx 0.08
    d_eye_l = np.sqrt((u1 - 0.35)**2 + (v1 - 0.45)**2)
    # Right eye: center at (u1=0.65, v1=0.45), radius approx 0.08
    d_eye_r = np.sqrt((u1 - 0.65)**2 + (v1 - 0.45)**2)
    mask_eye_l = mask_q1 & (d_eye_l < 0.075)
    mask_eye_r = mask_q1 & (d_eye_r < 0.075)
    mask_eyes = mask_eye_l | mask_eye_r

    # Eyeliner margin (annulus around eyes, thickness 0.015)
    mask_liner_l = mask_q1 & (d_eye_l >= 0.070) & (d_eye_l < 0.088) & (v1 < 0.48)
    mask_liner_r = mask_q1 & (d_eye_r >= 0.070) & (d_eye_r < 0.088) & (v1 < 0.48)
    mask_eyeliner = mask_liner_l | mask_liner_r

    # Nose: center (0.50, 0.55), width 0.08, height 0.09
    d_nose = np.sqrt(((u1 - 0.50)/0.06)**2 + ((v1 - 0.55)/0.08)**2)
    mask_nose = mask_q1 & (d_nose < 1.0)

    # Ears:
    d_ear_l = np.sqrt(((u1 - 0.08)/0.05)**2 + ((v1 - 0.50)/0.12)**2)
    d_ear_r = np.sqrt(((u1 - 0.92)/0.05)**2 + ((v1 - 0.50)/0.12)**2)
    mask_ears = mask_q1 & ((d_ear_l < 1.0) | (d_ear_r < 1.0))

    # Lips: center (0.50, 0.72), width 0.16, height 0.07
    d_lips = np.sqrt(((u1 - 0.50)/0.10)**2 + ((v1 - 0.72)/0.045)**2)
    mask_lips = mask_q1 & (d_lips < 1.0)

    # Sub-regions in Q4 (Sash, Sandals, Metal Hardware):
    # Normalized coords within Q4: u4 = (u - 0.5) * 2, v4 = (v - 0.5) * 2
    u4 = (u - 0.5) * 2.0
    v4 = (v - 0.5) * 2.0

    # Sash: top half of Q4 (v4 < 0.45)
    mask_sash = mask_q4 & (v4 < 0.45)
    # Sandals: bottom half left (v4 >= 0.45, u4 < 0.65)
    mask_sandals = mask_q4 & (v4 >= 0.45) & (u4 < 0.65)
    # Hardware / Aglets / Buckles: (v4 >= 0.45, u4 >= 0.65, v4 < 0.75)
    mask_hardware = mask_q4 & (v4 >= 0.45) & (u4 >= 0.65) & (v4 < 0.75)
    # Alpha accents / hair cards: (v4 >= 0.75, u4 >= 0.65)
    mask_alpha_zone = mask_q4 & (v4 >= 0.75) & (u4 >= 0.65)

    # --------------------------------------------------------------------------
    # 2. BASECOLOR MAP (RGB)
    # --------------------------------------------------------------------------
    print("Synthesizing BaseColor 4K...")
    base_color = np.zeros((H, W, 3), dtype=np.float32)

    # Default porcelain skin tone: RGB (244, 228, 220) / 255.0
    skin_r, skin_g, skin_b = 244.0/255.0, 228.0/255.0, 220.0/255.0
    base_color[:, :, 0] = skin_r
    base_color[:, :, 1] = skin_g
    base_color[:, :, 2] = skin_b

    # Scalp under-tone: (85, 72, 68)
    base_color[mask_scalp] = [85.0/255.0, 72.0/255.0, 68.0/255.0]

    # Nose warm blush: (242, 215, 208)
    base_color[mask_nose] = [242.0/255.0, 215.0/255.0, 208.0/255.0]

    # Ears warm translucency: (238, 200, 195)
    base_color[mask_ears] = [238.0/255.0, 200.0/255.0, 195.0/255.0]

    # Lips: soft rose vermilion (214, 112, 128) with subtle inner gradient
    lip_blend = np.clip(1.0 - d_lips, 0.0, 1.0)[mask_lips, np.newaxis]
    lip_outer = np.array([218.0/255.0, 120.0/255.0, 135.0/255.0], dtype=np.float32)
    lip_inner = np.array([195.0/255.0, 85.0/255.0, 105.0/255.0], dtype=np.float32)
    base_color[mask_lips] = lip_outer * (1.0 - lip_blend) + lip_inner * lip_blend

    # Eyeliner: dark slate / charcoal (26, 24, 30)
    base_color[mask_eyeliner] = [26.0/255.0, 24.0/255.0, 30.0/255.0]

    # Eyes (Sclera & Iris)
    base_color[mask_eyes] = [252.0/255.0, 252.0/255.0, 254.0/255.0]
    mask_iris_l = mask_eye_l & (d_eye_l < 0.045)
    mask_iris_r = mask_eye_r & (d_eye_r < 0.045)
    base_color[mask_iris_l | mask_iris_r] = [38.0/255.0, 46.0/255.0, 62.0/255.0]
    mask_pupil_l = mask_eye_l & (d_eye_l < 0.018)
    mask_pupil_r = mask_eye_r & (d_eye_r < 0.018)
    base_color[mask_pupil_l | mask_pupil_r] = [12.0/255.0, 12.0/255.0, 14.0/255.0]

    # Q2 (Upper Body / Limbs): porcelain skin with delicate warm fingertip blush
    # Add subtle organic skin variation
    body_skin = np.array([245.0/255.0, 229.0/255.0, 222.0/255.0], dtype=np.float32)
    base_color[mask_q2] = body_skin

    # Q3 (Ivory Silk Dress): ivory pure silk (248, 246, 242) with delicate micro pleats
    dress_color = np.array([248.0/255.0, 246.0/255.0, 242.0/255.0], dtype=np.float32)
    pleat_pattern = 0.012 * np.sin(x_coords * (2.0 * np.pi / 64.0))
    base_color[mask_q3] = np.clip(dress_color + pleat_pattern[mask_q3, np.newaxis], 0.0, 1.0)

    # Q4 Sash: pale ice-blue satin (198, 222, 238)
    base_color[mask_sash] = [198.0/255.0, 222.0/255.0, 238.0/255.0]

    # Q4 Sandals: white leather (242, 240, 236)
    base_color[mask_sandals] = [242.0/255.0, 240.0/255.0, 236.0/255.0]

    # Q4 Hardware / Aglets: metallic gold / brass (225, 195, 110)
    base_color[mask_hardware] = [225.0/255.0, 195.0/255.0, 110.0/255.0]

    # Q4 Alpha zone strands: dark hair (20, 20, 22)
    base_color[mask_alpha_zone] = [20.0/255.0, 20.0/255.0, 22.0/255.0]

    base_color_img = Image.fromarray((np.clip(base_color, 0.0, 1.0) * 255.0).astype(np.uint8))
    base_color_path = os.path.join(output_dir, "Yu_Nian_An_BaseColor_4K.png")
    base_color_img.save(base_color_path, format="PNG", optimize=True)
    print(f"Saved BaseColor: {base_color_path} ({os.path.getsize(base_color_path) / 1024 / 1024:.2f} MB)")

    # --------------------------------------------------------------------------
    # 2. NORMAL MAP (Tangent-Space RGB: flat = 128, 128, 255)
    # --------------------------------------------------------------------------
    print("Synthesizing Normal 4K...")
    # Micro-skin pore high frequency generator using multi-frequency sinusoids
    pore_freq = 2.0 * np.pi / 16.0
    pore_noise_x = 0.06 * np.sin(x_coords * pore_freq) * np.cos(y_coords * pore_freq * 1.3)
    pore_noise_y = 0.06 * np.cos(x_coords * pore_freq * 1.1) * np.sin(y_coords * pore_freq)

    # Lip vermilion vertical wrinkle striations
    lip_wrinkle_freq = 2.0 * np.pi / 12.0
    lip_nx = 0.28 * np.sin(x_coords * lip_wrinkle_freq)
    lip_ny = 0.05 * np.cos(y_coords * lip_wrinkle_freq)

    # Fabric weave cross-hatch for dress and sash
    fabric_freq = 2.0 * np.pi / 8.0
    fabric_nx = 0.12 * np.sin(x_coords * fabric_freq)
    fabric_ny = 0.12 * np.sin(y_coords * fabric_freq)

    norm_x = np.zeros((H, W), dtype=np.float32)
    norm_y = np.zeros((H, W), dtype=np.float32)

    # Apply skin pores to face and body
    norm_x[mask_q1 | mask_q2] = pore_noise_x[mask_q1 | mask_q2]
    norm_y[mask_q1 | mask_q2] = pore_noise_y[mask_q1 | mask_q2]

    # Apply lip wrinkles
    norm_x[mask_lips] = lip_nx[mask_lips]
    norm_y[mask_lips] = lip_ny[mask_lips]

    # Apply fabric weave to dress and sash
    norm_x[mask_q3 | mask_sash] = fabric_nx[mask_q3 | mask_sash]
    norm_y[mask_q3 | mask_sash] = fabric_ny[mask_q3 | mask_sash]

    # Smooth Z component: nz = sqrt(1 - nx^2 - ny^2)
    norm_z = np.sqrt(np.clip(1.0 - (norm_x**2 + norm_y**2), 0.001, 1.0))

    # Convert tangent vector [-1, 1] to [0, 255]
    norm_img_array = np.zeros((H, W, 3), dtype=np.uint8)
    norm_img_array[:, :, 0] = np.clip((norm_x + 1.0) * 127.5, 0, 255).astype(np.uint8)
    norm_img_array[:, :, 1] = np.clip((norm_y + 1.0) * 127.5, 0, 255).astype(np.uint8)
    norm_img_array[:, :, 2] = np.clip((norm_z + 1.0) * 127.5, 0, 255).astype(np.uint8)

    normal_img = Image.fromarray(norm_img_array, mode="RGB")
    normal_path = os.path.join(output_dir, "Yu_Nian_An_Normal_4K.png")
    normal_img.save(normal_path, format="PNG", optimize=True)
    print(f"Saved Normal: {normal_path} ({os.path.getsize(normal_path) / 1024 / 1024:.2f} MB)")

    # --------------------------------------------------------------------------
    # 3. ROUGHNESS MAP (Grayscale / L)
    # --------------------------------------------------------------------------
    print("Synthesizing Roughness 4K...")
    # Default body roughness: 0.42
    roughness = np.full((H, W), 0.42, dtype=np.float32)

    # Face skin: 0.38
    roughness[mask_q1] = 0.38
    # Lips: 0.28 (moist specular sheen)
    roughness[mask_lips] = 0.28
    # Scalp: 0.70
    roughness[mask_scalp] = 0.70
    # Dress (ivory silk): 0.45
    roughness[mask_q3] = 0.45
    # Sash (ice-blue satin): 0.22
    roughness[mask_sash] = 0.22
    # Sandals (leather): 0.50
    roughness[mask_sandals] = 0.50
    # Hardware (polished metal): 0.20
    roughness[mask_hardware] = 0.20
    # Eyes (cornea gloss): 0.05
    roughness[mask_eyes] = 0.05
    # Eyeliner: 0.65
    roughness[mask_eyeliner] = 0.65

    # Add micro-variation to roughness (pores slightly rougher)
    roughness = np.clip(roughness + 0.02 * pore_noise_x, 0.0, 1.0)

    roughness_img = Image.fromarray((roughness * 255.0).astype(np.uint8), mode="L")
    roughness_path = os.path.join(output_dir, "Yu_Nian_An_Roughness_4K.png")
    roughness_img.save(roughness_path, format="PNG", optimize=True)
    print(f"Saved Roughness: {roughness_path} ({os.path.getsize(roughness_path) / 1024 / 1024:.2f} MB)")

    # --------------------------------------------------------------------------
    # 4. METALLIC MAP (Grayscale / L)
    # --------------------------------------------------------------------------
    print("Synthesizing Metallic 4K...")
    # Non-metal dielectric (0.0) across all skin, lips, scalp, dress, sash, sandals
    metallic = np.zeros((H, W), dtype=np.float32)
    # Metallic sheen on ribbon aglets, buckles, and hardware
    metallic[mask_hardware] = 1.0

    metallic_img = Image.fromarray((metallic * 255.0).astype(np.uint8), mode="L")
    metallic_path = os.path.join(output_dir, "Yu_Nian_An_Metallic_4K.png")
    metallic_img.save(metallic_path, format="PNG", optimize=True)
    print(f"Saved Metallic: {metallic_path} ({os.path.getsize(metallic_path) / 1024 / 1024:.2f} MB)")

    # --------------------------------------------------------------------------
    # 5. SSS MAP (Subsurface Scattering Mask: Grayscale / L)
    # --------------------------------------------------------------------------
    print("Synthesizing SSS 4K...")
    # Body default SSS: 0.35
    sss = np.zeros((H, W), dtype=np.float32)
    sss[mask_q2] = 0.35

    # Face default SSS: 0.45
    sss[mask_q1] = 0.45

    # High SSS regions:
    # Ears: 0.85
    sss[mask_ears] = 0.85
    # Nose: 0.75
    sss[mask_nose] = 0.75
    # Lips: 0.70
    sss[mask_lips] = 0.70

    # Low SSS regions:
    # Scalp: 0.05
    sss[mask_scalp] = 0.05
    # Dress, sash, sandals, eyes, hardware: 0.0 (dielectric fabric/metal has zero skin SSS)
    sss[mask_q3] = 0.0
    sss[mask_sash] = 0.0
    sss[mask_sandals] = 0.0
    sss[mask_hardware] = 0.0
    sss[mask_eyes] = 0.0

    sss_img = Image.fromarray((sss * 255.0).astype(np.uint8), mode="L")
    sss_path = os.path.join(output_dir, "Yu_Nian_An_SSS_4K.png")
    sss_img.save(sss_path, format="PNG", optimize=True)
    print(f"Saved SSS: {sss_path} ({os.path.getsize(sss_path) / 1024 / 1024:.2f} MB)")

    # --------------------------------------------------------------------------
    # 6. ALPHA MAP (Opacity Mask: Grayscale / L)
    # --------------------------------------------------------------------------
    print("Synthesizing Alpha 4K...")
    # Fully opaque (1.0 / 255) for character mesh surfaces
    alpha = np.ones((H, W), dtype=np.float32)

    # Feathered transparency gradient in the alpha zone (strands/lashes card cutout)
    strand_u = (u4 - 0.65) / 0.35
    strand_v = (v4 - 0.75) / 0.25
    strand_feather = np.clip(1.0 - strand_v, 0.0, 1.0) * (0.5 + 0.5 * np.sin(x_coords * (2.0 * np.pi / 16.0)))
    alpha[mask_alpha_zone] = strand_feather[mask_alpha_zone]

    alpha_img = Image.fromarray((alpha * 255.0).astype(np.uint8), mode="L")
    alpha_path = os.path.join(output_dir, "Yu_Nian_An_Alpha_4K.png")
    alpha_img.save(alpha_path, format="PNG", optimize=True)
    print(f"Saved Alpha: {alpha_path} ({os.path.getsize(alpha_path) / 1024 / 1024:.2f} MB)")

    # --------------------------------------------------------------------------
    # 7. HEIGHT MAP (Displacement / Bump: Grayscale / L)
    # --------------------------------------------------------------------------
    print("Synthesizing Height 4K...")
    # Mid-gray neutral height: 0.50 (128)
    height_map = np.full((H, W), 0.50, dtype=np.float32)

    # Lip fullness: +0.12 (raised vermilion volume)
    height_map[mask_lips] = 0.50 + 0.12 * np.clip(1.0 - d_lips[mask_lips], 0.0, 1.0)

    # Oral slit cavity: -0.25 (depth between upper and lower lips)
    mask_oral_slit = mask_lips & (np.abs(v1 - 0.72) < 0.008)
    height_map[mask_oral_slit] = 0.25

    # Nose protrusion: +0.18
    height_map[mask_nose] = 0.50 + 0.18 * np.clip(1.0 - d_nose[mask_nose], 0.0, 1.0)

    # Eyelid crease: -0.10
    height_map[mask_eyeliner] = 0.40

    # Micro-pore indentations on skin
    height_map[mask_q1 | mask_q2] -= 0.015 * np.sin(x_coords[mask_q1 | mask_q2] * pore_freq) * np.sin(y_coords[mask_q1 | mask_q2] * pore_freq)

    # Sash ribbon knot and layered streamers: +0.22
    height_map[mask_sash] += 0.08 * np.sin(y_coords[mask_sash] * (2.0 * np.pi / 256.0))
    height_map[mask_hardware] = 0.75

    height_img = Image.fromarray((np.clip(height_map, 0.0, 1.0) * 255.0).astype(np.uint8), mode="L")
    height_path = os.path.join(output_dir, "Yu_Nian_An_Height_4K.png")
    height_img.save(height_path, format="PNG", optimize=True)
    print(f"Saved Height: {height_path} ({os.path.getsize(height_path) / 1024 / 1024:.2f} MB)")

    elapsed = time.time() - start_time
    print(f"All 7 4K PBR textures generated successfully in {elapsed:.2f}s!")

    return {
        "BaseColor": base_color_path,
        "Normal": normal_path,
        "Roughness": roughness_path,
        "Metallic": metallic_path,
        "SSS": sss_path,
        "Alpha": alpha_path,
        "Height": height_path,
    }

if __name__ == "__main__":
    generate_4k_textures()
