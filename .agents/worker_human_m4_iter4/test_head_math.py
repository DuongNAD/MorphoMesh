import math

def test_head_math():
    s = 1.0
    head_height = 1.65 / 7.41
    z_crown = 1.65
    z_chin = z_crown - head_height
    k_head_scale = 1.0

    raw_slices = [
        (1.445, 0.065, 0.075, -0.035, "head"),
        (1.470, 0.075, 0.088, -0.038, "head"),
        (1.500, 0.082, 0.095, -0.030, "head"),
        (1.530, 0.086, 0.095, -0.015, "head"),
        (1.560, 0.088, 0.096, -0.005, "head"),
        (1.600, 0.086, 0.092, 0.005, "head"),
        (1.635, 0.072, 0.078, 0.008, "head"),
        (1.650, 0.020, 0.025, 0.005, "head"),
    ]

    sectors = 24
    for z_can, rx_can, ry_can, yo_can, vg_n in raw_slices:
        u = (z_can - 1.427) / 0.223
        z_slice = z_chin + u * head_height
        rx = rx_can * s * k_head_scale
        ry = ry_can * s * k_head_scale
        yo = yo_can * s * k_head_scale

        print(f"\n--- Slice z={z_slice:.3f} (can {z_can:.3f}) ---")
        for i in range(sectors):
            theta = 2.0 * math.pi * i / sectors
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            rx_mod = rx
            mod_y = ry
            dy_facial = 0.0
            dx_facial = 0.0

            # Facial contour shaping
            if sin_t < -0.2:  # Frontal face hemisphere
                # Midline features (nose, lips, chin) around i=18 (theta=270 deg)
                # Angular distance from midline in radians
                ang_dist = abs(theta - 1.5 * math.pi)

                # 1. Nose bridge & tip at Z in [1.49m, 1.545m]
                if 1.490 <= z_slice <= 1.545:
                    if ang_dist < 0.30:  # Midline nose (i=18)
                        # Protrusion peaks at nose tip (Z ~ 1.505m - 1.515m)
                        z_factor = math.exp(-((z_slice - 1.510) ** 2) / (2 * (0.018 ** 2)))
                        # Nose bridge extension up to Z ~ 1.54m
                        bridge_factor = max(0.0, min(1.0, (1.545 - z_slice) / 0.045))
                        protrusion = (0.0125 * z_factor + 0.007 * bridge_factor) * s
                        dy_facial -= protrusion
                    elif ang_dist < 0.60:  # Alar flanks / nostrils (i=17, 19)
                        z_factor = math.exp(-((z_slice - 1.505) ** 2) / (2 * (0.016 ** 2)))
                        dy_facial -= 0.0055 * z_factor * s
                        dx_facial *= 0.92

                # 2. Orbital sockets (recess around eye spheres at X ~ +/- 0.035m, Z ~ 1.515m - 1.535m)
                if 1.515 <= z_slice <= 1.545:
                    if 0.40 <= ang_dist <= 0.85:  # Orbit zone (i=16, 20)
                        # Subtle recession into skull
                        dy_facial += 0.0045 * s

                # 3. Lips & Philtrum at Z in [1.46m, 1.485m]
                if 1.460 <= z_slice <= 1.485:
                    if ang_dist < 0.20:  # Lip midline
                        # Subtle mouth indentation
                        dy_facial += 0.0020 * s
                    elif 0.20 <= ang_dist <= 0.45:  # Lip fullness (tubercles)
                        dy_facial -= 0.0035 * s
                    elif ang_dist > 0.65:  # Cheilion / mouth corners
                        dy_facial += 0.0030 * s

                # 4. Chin definition at Z in [1.435m, 1.455m]
                if 1.435 <= z_slice <= 1.455:
                    if ang_dist < 0.35:
                        dy_facial -= 0.0040 * s  # Delicate chin protrusion

            px = rx_mod * cos_t + dx_facial
            py = mod_y * sin_t + yo + dy_facial

            if i in (16, 17, 18, 19, 20):
                print(f"  i={i:2d} (x={px:+.4f}, y={py:+.4f})")

test_head_math()
