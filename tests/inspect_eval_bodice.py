import bpy
import bmesh
import mathutils

body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
bodice_obj = bpy.data.objects.get("Mesh_Dress_Bodice")

print("Bodice modifiers:", [(m.name, m.type) for m in bodice_obj.modifiers])

depsgraph = bpy.context.evaluated_depsgraph_get()
eval_bodice = bodice_obj.evaluated_get(depsgraph)
eval_body = body_obj.evaluated_get(depsgraph)

bm_body = bmesh.new()
bm_body.from_mesh(eval_body.to_mesh())
bm_body.transform(eval_body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

m = eval_bodice.to_mesh()
eval_bodice_verts = [eval_bodice.matrix_world @ v.co for v in m.vertices]
eval_bodice.to_mesh_clear()
eval_body.to_mesh_clear()

signed_dists = []
penetrations = []
for idx, v in enumerate(eval_bodice_verts):
    loc, normal, f_idx, dist = bvh.find_nearest(v)
    if loc:
        offset = v - loc
        dot = offset.dot(normal)
        s_dist = dist if dot >= 0 else -dist
        signed_dists.append(s_dist)
        if dot < 0:
            penetrations.append((idx, v, loc, dist, dot))

min_dist = min(signed_dists)
print(f"Evaluated Bodice: total verts={len(eval_bodice_verts)}, min_signed_clearance={min_dist*1000:.2f}mm, penetrations={len(penetrations)}")
if penetrations:
    print(f"Sample penetrations (first 5):")
    for p in penetrations[:5]:
        print(f"  v[{p[0]}]: v={p[1]}, body={p[2]}, dist={p[3]*1000:.2f}mm, dot={p[4]*1000:.2f}")

bm_body.free()