import math
import bpy
import bmesh
import mathutils

def audit_simulated_hair_and_face():
    # 1. Test generate_hime_cut_splines with proposed anterior offsets
    s = 1.0
    z_crown = 1.645 * s
    z_brow = 1.540 * s
    z_clavicle = 1.320 * s
    z_hip = 0.720 * s

    # Forehead Bangs
    count_bangs = 20
    bangs_splines = []
    for i in range(count_bangs):
        u = i / max(1, count_bangs - 1)
        x0 = (-0.055 + 0.110 * u) * s
        # Root starts on anterior scalp
        y_root = (-0.088 - 0.012 * math.cos((u - 0.5) * math.pi)) * s
        z0 = (z_crown - 0.025 - 0.008 * abs(u - 0.5)) * s
        target_z = (z_brow - 0.008) * s
        y_tip = (-0.126 - 0.010 * math.cos((u - 0.5) * math.pi)) * s

        curve_pts = []
        pts_per_curve = 10
        for p in range(pts_per_curve):
            t = p / max(1, pts_per_curve - 1)
            # Gentle forward drape over forehead
            drape_y = -0.012 * math.sin(t * math.pi) * s
            curv_y = y_root + t * (y_tip - y_root) + drape_y
            curv_z = z0 + t * (target_z - z0)
            curv_x = x0 + 0.004 * (u - 0.5) * t * s
            curve_pts.append((curv_x, curv_y, curv_z))
        bangs_splines.append(curve_pts)

    # Eyebrows
    count_brows = 10
    brow_splines = []
    for i in range(count_brows):
        side = 1.0 if i % 2 == 0 else -1.0
        sub_u = (i // 2) / max(1, (count_brows // 2) - 1)
        x0 = side * (0.018 + 0.032 * sub_u) * s
        y0 = (-0.126 - 0.003 * math.sin(sub_u * math.pi)) * s
        z0 = (1.536 + 0.008 * math.sin(sub_u * math.pi)) * s
        tip_x = x0 + side * 0.004 * s
        tip_y = y0 - 0.003 * s
        tip_z = z0 - 0.003 * s
        brow_splines.append([(x0, y0, z0), (tip_x, tip_y, tip_z)])

    # Eyelashes
    count_lashes = 10
    lash_splines = []
    for i in range(count_lashes):
        side = 1.0 if i % 2 == 0 else -1.0
        sub_u = (i // 2) / max(1, (count_lashes // 2) - 1)
        x0 = side * (0.019 + 0.026 * sub_u) * s
        y0 = (-0.128 - 0.003 * math.sin(sub_u * math.pi)) * s
        z0 = (1.520 + 0.002 * math.sin(sub_u * math.pi)) * s
        tip_x = x0 + side * 0.003 * s
        tip_y = y0 - 0.004 * s
        tip_z = z0 + 0.002 * s
        lash_splines.append([(x0, y0, z0), (tip_x, tip_y, tip_z)])

    # Sidelocks
    count_side = 12
    half = count_side // 2
    sidelock_splines = []
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        for i in range(half):
            u = i / max(1, half - 1)
            x0 = sign * (0.078 + 0.006 * u) * s
            y0 = (-0.082 - 0.024 * u) * s
            z0 = (z_crown - 0.050 - 0.015 * u) * s
            target_z = z_clavicle + 0.030 * s
            curve_pts = []
            pts_per_curve = 12
            for p in range(pts_per_curve):
                t = p / max(1, pts_per_curve - 1)
                curv_x = x0 + sign * 0.003 * math.sin(t * math.pi) * s
                curv_y = y0 - 0.018 * t * s - 0.006 * math.sin(t * math.pi) * s
                curv_z = z0 + t * (target_z - z0)
                curve_pts.append((curv_x, curv_y, curv_z))
            sidelock_splines.append(curve_pts)

    # Crown
    count_crown = 16
    crown_splines = []
    r_cx = 0.090 * s
    r_cy = 0.096 * s
    for i in range(count_crown):
        u = i / max(1, count_crown - 1)
        ang = u * 2.0 * math.pi
        x0 = r_cx * math.cos(ang)
        y0 = r_cy * math.sin(ang) * 0.85
        z0 = z_crown - 0.005 * s
        curve_pts = [(x0, y0, z0), (x0 * 1.12, y0 * 1.12, z0 - 0.065 * s)]
        crown_splines.append(curve_pts)

    print("Splines generated successfully.")

audit_simulated_hair_and_face()
