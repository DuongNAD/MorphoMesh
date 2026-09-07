import bpy
import bmesh
import mathutils

body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
bm = bmesh.new()
bm.from_mesh(body_obj.data)
bm.transform(body_obj.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

for s_name in ["Mesh_Sandal_L", "Mesh_Sandal_R"]:
    s_obj = bpy.data.objects.get(s_name)
    if not s_obj:
        print(f"Missing {s_name}")
        continue
    verts = [s_obj.matrix_world @ v.co for v in s_obj.data.vertices]
    min_dist = float('inf')
    penetrations = 0
    for v in verts:
        loc, norm, idx, dist = bvh.find_nearest(v)
        if loc:
            offset = v - loc
            dot = offset.dot(norm)
            s_dist = dist if dot >= 0 else -dist
            if s_dist < min_dist:
                min_dist = s_dist
            if dot < 0:
                penetrations += 1
    print(f"{s_name}: min_signed_clearance={min_dist*1000:.2f}mm, penetrations={penetrations}/{len(verts)}")

bm.free()