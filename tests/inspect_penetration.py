import bpy
import bmesh
import mathutils

body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
bodice_obj = bpy.data.objects.get("Mesh_Dress_Bodice")
sash_obj = bpy.data.objects.get("Mesh_Dress_WaistSash")

bm_body = bmesh.new()
bm_body.from_mesh(body_obj.data)
bm_body.transform(body_obj.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

print("=== DETAILED BODICE VERTEX ANALYSIS ===")
bodice_verts = [bodice_obj.matrix_world @ v.co for v in bodice_obj.data.vertices]
penetrations = []
for idx, v in enumerate(bodice_verts):
    loc, normal, f_idx, dist = bvh.find_nearest(v)
    if loc is not None:
        offset = v - loc
        dot = offset.dot(normal)
        if dot < 0:
            penetrations.append((idx, v, loc, normal, dist, dot))

print(f"Total bodice verts: {len(bodice_verts)}, Penetrating verts: {len(penetrations)}")
for p in penetrations[:15]:
    idx, v, loc, normal, dist, dot = p
    print(f"  v[{idx:03d}]: v_pos=({v.x:+.3f}, {v.y:+.3f}, {v.z:+.3f}), body_loc=({loc.x:+.3f}, {loc.y:+.3f}, {loc.z:+.3f}), dist={dist*1000:.1f}mm, norm=({normal.x:+.2f}, {normal.y:+.2f}, {normal.z:+.2f}), dot={dot*1000:.2f}")

print("\n=== DETAILED SASH ANALYSIS ===")
sash_verts = [sash_obj.matrix_world @ v.co for v in sash_obj.data.vertices]
sash_dists = []
for idx, v in enumerate(sash_verts):
    loc, normal, f_idx, dist = bvh.find_nearest(v)
    if loc is not None:
        offset = v - loc
        dot = offset.dot(normal)
        sash_dists.append((idx, v, dist, dot))

sash_dists.sort(key=lambda x: x[2])
print("Closest 5 sash verts to body:")
for idx, v, dist, dot in sash_dists[:5]:
    print(f"  sash v[{idx:03d}]: pos=({v.x:+.3f}, {v.y:+.3f}, {v.z:+.3f}), dist={dist*1000:.2f}mm, dot={dot*1000:.2f}")

bm_body.free()