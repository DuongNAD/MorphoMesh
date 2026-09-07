import math
import bpy
import bmesh
import mathutils

body = bpy.data.objects.get('Yu_Nian_An_Body')
if not body:
    print("Yu_Nian_An_Body not found!")
    exit(1)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

s = 1.0
z_crown = 1.645 * s
z_brow = 1.540 * s
z_clavicle = 1.320 * s
z_hip = 0.720 * s

# Test layers
tests = {}

# 1. Bangs
count = 20
bangs_pts = []
for i in range(count):
    u = i / max(1, count - 1)
    x0 = (-0.055 + 0.110 * u) * s
    y_root = (-0.088 - 0.012 * math.cos((u - 0.5) * math.pi)) * s
    z0 = (z_crown - 0.025 - 0.008 * abs(u - 0.5)) * s
    target_z = (z_brow - 0.008) * s
    y_tip = (-0.126 - 0.010 * math.cos((u - 0.5) * math.pi)) * s

    pts_per_curve = 10
    for p in range(pts_per_curve):
        t = p / max(1, pts_per_curve - 1)
        drape_y = -0.012 * math.sin(t * math.pi) * s
        curv_y = y_root + t * (y_tip - y_root) + drape_y
        curv_z = z0 + t * (target_z - z0)
        curv_x = x0 + 0.004 * (u - 0.5) * t * s
        bangs_pts.append(mathutils.Vector((curv_x, curv_y, curv_z)))
tests['Bangs'] = bangs_pts

# 2. Eyebrows
count = 10
brow_pts = []
for i in range(count):
    side = 1.0 if i % 2 == 0 else -1.0
    sub_u = (i // 2) / max(1, (count // 2) - 1)
    x0 = side * (0.018 + 0.032 * sub_u) * s
    y0 = (-0.126 - 0.003 * math.sin(sub_u * math.pi)) * s
    z0 = (1.536 + 0.008 * math.sin(sub_u * math.pi)) * s
    tip_x = x0 + side * 0.004 * s
    tip_y = y0 - 0.003 * s
    tip_z = z0 - 0.003 * s
    brow_pts.append(mathutils.Vector((x0, y0, z0)))
    brow_pts.append(mathutils.Vector((tip_x, tip_y, tip_z)))
tests['Eyebrows'] = brow_pts

# 3. Eyelashes
count = 10
lash_pts = []
for i in range(count):
    side = 1.0 if i % 2 == 0 else -1.0
    sub_u = (i // 2) / max(1, (count // 2) - 1)
    x0 = side * (0.019 + 0.026 * sub_u) * s
    y0 = (-0.128 - 0.003 * math.sin(sub_u * math.pi)) * s
    z0 = (1.520 + 0.002 * math.sin(sub_u * math.pi)) * s
    tip_x = x0 + side * 0.003 * s
    tip_y = y0 - 0.004 * s
    tip_z = z0 + 0.002 * s
    lash_pts.append(mathutils.Vector((x0, y0, z0)))
    lash_pts.append(mathutils.Vector((tip_x, tip_y, tip_z)))
tests['Eyelashes'] = lash_pts

# 4. Sidelocks
count = 12
half = count // 2
sidelock_pts = []
for side, sign in [("L", 1.0), ("R", -1.0)]:
    for i in range(half):
        u = i / max(1, half - 1)
        x0 = sign * (0.078 + 0.006 * u) * s
        y0 = (-0.082 - 0.024 * u) * s
        z0 = (z_crown - 0.050 - 0.015 * u) * s
        target_z = z_clavicle + 0.030 * s
        pts_per_curve = 12
        for p in range(pts_per_curve):
            t = p / max(1, pts_per_curve - 1)
            curv_x = x0 + sign * 0.003 * math.sin(t * math.pi) * s
            curv_y = y0 - 0.018 * t * s - 0.006 * math.sin(t * math.pi) * s
            curv_z = z0 + t * (target_z - z0)
            sidelock_pts.append(mathutils.Vector((curv_x, curv_y, curv_z)))
tests['Sidelocks'] = sidelock_pts

# 5. Crown
count = 16
crown_pts = []
r_cx = 0.090 * s
r_cy = 0.096 * s
for i in range(count):
    u = i / max(1, count - 1)
    ang = u * 2.0 * math.pi
    x0 = r_cx * math.cos(ang)
    y0 = r_cy * math.sin(ang) * 0.85
    z0 = z_crown - 0.005 * s
    tip_x = x0 * 1.12
    tip_y = y0 * 1.12
    tip_z = z0 - 0.065 * s
    crown_pts.append(mathutils.Vector((x0, y0, z0)))
    crown_pts.append(mathutils.Vector((tip_x, tip_y, tip_z)))
tests['Crown'] = crown_pts

for name, pts in tests.items():
    inside = 0
    total = len(pts)
    for v in pts:
        nearest_co, normal, idx, dist = bvh.find_nearest(v)
        if nearest_co is not None and normal is not None:
            diff = v - nearest_co
            if diff.dot(normal) < 0:
                inside += 1
    pct_inside = (inside / total * 100.0) if total > 0 else 0.0
    pct_outside = 100.0 - pct_inside
    print(f"Proposed {name}: Total: {total} | Inside: {inside} ({pct_inside:.1f}%) | OUTSIDE: {total - inside} ({pct_outside:.1f}%)")
