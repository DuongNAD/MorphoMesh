import sys
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\.agents\explorer_m3_1")
import bpy
import bmesh
import mathutils

from morphomesh.human_generator import HumanAnatomyGenerator, HumanAnatomyConfig
from test_sandal_prototype import build_flat_strappy_sandals

print("Starting Blender BVH Sandal Inspection...")

# 1. Generate body mesh
gen = HumanAnatomyGenerator(HumanAnatomyConfig())
res = gen.generate()

body_mesh = bpy.data.meshes.new("Yu_Nian_An_Body_Mesh")
body_mesh.from_pydata(res.mesh.vertices, [], res.mesh.faces)
body_mesh.update()
body_obj = bpy.data.objects.new("Yu_Nian_An_Body", body_mesh)
bpy.context.scene.collection.objects.link(body_obj)

bm = bmesh.new()
bm.from_mesh(body_obj.data)
bm.transform(body_obj.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

# 2. Inspect sandals
sandals = build_flat_strappy_sandals(height=1.65)
for s_name in ["Mesh_Sandal_L", "Mesh_Sandal_R"]:
    m = sandals[s_name]
    s_mesh = bpy.data.meshes.new(f"{s_name}_Mesh")
    s_mesh.from_pydata(m.vertices, [], m.faces)
    s_mesh.update()
    s_obj = bpy.data.objects.new(s_name, s_mesh)
    bpy.context.scene.collection.objects.link(s_obj)

    verts = [s_obj.matrix_world @ v.co for v in s_obj.data.vertices]
    min_dist = float('inf')
    penetrations = 0
    pen_details = []

    close_verts = []
    for idx, v in enumerate(verts):
        loc, norm, f_idx, dist = bvh.find_nearest(v)
        if loc:
            offset = v - loc
            dot = offset.dot(norm)
            s_dist = dist if dot >= 0 else -dist
            if s_dist < min_dist:
                min_dist = s_dist
            if dot < 0:
                penetrations += 1
                pen_details.append((idx, v, loc, norm, s_dist))
            elif s_dist < 0.0015:
                close_verts.append((idx, v, loc, norm, s_dist))

    print(f"{s_name}: min_signed_clearance={min_dist*1000:.2f}mm, penetrations={penetrations}/{len(verts)}")
    for p_i, pv, ploc, pnorm, ps_dist in pen_details:
        print(f"  PENETRATION vert {p_i}: v={pv}, loc={ploc}, norm={pnorm}, signed_dist={ps_dist*1000:.2f}mm")
    for p_i, pv, ploc, pnorm, ps_dist in close_verts[:5]:
        print(f"  Close vert {p_i} (< 1.5mm): v={pv}, loc={ploc}, signed_dist={ps_dist*1000:.2f}mm")

bm.free()
print("Blender BVH Inspection Complete.")
