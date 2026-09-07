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

layers = ['Hair_Hime_Bangs', 'Hair_Eyebrows', 'Hair_Eyelashes', 'Hair_Scalp_Crown', 'Hair_Hime_Sidelocks', 'Hair_Back_Cascade']

for h in layers:
    obj = bpy.data.objects.get(h)
    if not obj or not obj.data or not hasattr(obj.data, "vertices"):
        print(f"{h}: Not found or no vertices")
        continue
    verts = obj.data.vertices
    inside = 0
    total = len(verts)
    for v in verts:
        world_co = obj.matrix_world @ v.co
        nearest_co, normal, idx, dist = bvh.find_nearest(world_co)
        if nearest_co is not None and normal is not None:
            diff = world_co - nearest_co
            if diff.dot(normal) < 0:
                inside += 1
    pct = (inside / total * 100.0) if total > 0 else 0.0
    print(f"{h}: Total verts: {total} | Inside: {inside}/{total} ({pct:.1f}%) | Outside: {total - inside}/{total} ({100.0 - pct:.1f}%)")
