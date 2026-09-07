import math

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
]

sectors = 24
for z_can, rx_can, ry_can, yo_can, vg_n in raw_slices:
    u = (z_can - 1.427) / 0.223
    z_slice = z_chin + u * head_height
    rx = rx_can * s * k_head_scale
    ry = ry_can * s * k_head_scale
    yo = yo_can * s * k_head_scale

    print(f"\n--- Slice z={z_slice:.3f} ---")
    for i in (16, 17, 18, 19, 20):
        theta = 2.0 * math.pi * i / sectors
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        mod_y = ry
        rx_mod = rx
        dx_facial = 0.0
        dy_facial = 0.0

        if sin_t < -0.2:
            ang_dist = abs(theta - 1.5 * math.pi)

            # 1. Nose bridge & tip: Z in [1.49m, 1.545m]
            if 1.490 * s <= z_slice <= 1.545 * s:
                if ang_dist < 0.30:  # Midline nose (i=18)
                    z_tip_factor = math.exp(-((z_slice - 1.505 * s) ** 2) / (2 * ((0.016 * s) ** 2)))
                    bridge_factor = max(0.0, min(1.0, (1.545 * s - z_slice) / (0.045 * s)))
                    dy_facial -= (0.0135 * z_tip_factor + 0.0080 * bridge_factor) * s
                elif ang_dist < 0.60:  # Alar flanks (i=17, 19)
                    z_flank_factor = math.exp(-((z_slice - 1.505 * s) ** 2) / (2 * ((0.016 * s) ** 2)))
                    dy_facial -= 0.0065 * z_flank_factor * s
                    dx_facial = -0.10 * (rx * cos_t)

            # 2. Orbital sockets: slight recess at X ~ +/- 0.035m, Z ~ 1.515m - 1.540m (i=16, 20)
            if 1.515 * s <= z_slice <= 1.540 * s:
                if 0.40 <= ang_dist <= 0.85:
                    dy_facial += 0.0045 * s

            # 3. Mouth & lips: Z in [1.46m, 1.485m] (Slice 16)
            if 1.460 * s <= z_slice <= 1.485 * s:
                if ang_dist < 0.20:
                    dy_facial += 0.0020 * s
                elif 0.20 <= ang_dist <= 0.45:
                    dy_facial -= 0.0035 * s
                elif ang_dist > 0.65:
                    dy_facial += 0.0030 * s

            # 4. Feminine chin contour: Z in [1.435m, 1.455m] (Slice 15)
            if 1.435 * s <= z_slice <= 1.455 * s:
                if ang_dist < 0.35:
                    dy_facial -= 0.0045 * s

        px = rx_mod * cos_t + dx_facial
        py = mod_y * sin_t + yo + dy_facial
        print(f"  i={i:2d} (x={px:+.4f}, y={py:+.4f})")
