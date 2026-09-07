import math
import bpy
import bmesh
import mathutils

body = bpy.data.objects.get('Yu_Nian_An_Body')
bm = bmesh.new()
bm.from_mesh(body.data)
bm.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

s = 1.0
z_crown = 1.645 * s

for r_scale in [1.0, 1.02, 1.05]:
    crown_pts = []
    r_cx = 0.092 * s * r_scale
    r_cy = 0.098 * s * r_scale
    count = 32
    for i in range(count):
        u = i / max(1, count - 1)
        ang = u * 2.0 * math.pi
        x0 = r_cx * math.cos(ang)
        y0 = r_cy * math.sin(ang) * 0.90 + 0.005 * s
        z0 = z_crown - 0.004 * s
        tip_x = x0 * 1.15
        tip_y = y0 * 1.15
        tip_z = z0 - 0.055 * s
        crown_pts.append(mathutils.Vector((x0, y0, z0)))
        crown_pts.append(mathutils.Vector((tip_x, tip_y, tip_z)))

    inside = 0
    total = len(crown_pts)
    for v in crown_pts:
        nearest_co, normal, idx, dist = bvh.find_nearest(v)
        if nearest_co is not None and normal is not None:
            diff = v - nearest_co
            if diff.dot(normal) < 0:
                inside += 1
    pct_outside = (total - inside) / total * 100.0
    print(f"r_scale={r_scale}: Outside: {total - inside}/{total} ({pct_outside:.1f}%)")
