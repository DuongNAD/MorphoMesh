
import bpy
import bmesh
import mathutils
import os

print("[3/4] Opening master blend file for audit and rendering...")
bpy.ops.wm.open_mainfile(filepath=r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend")

body = bpy.data.objects.get('Yu_Nian_An_Body')
assert body is not None, "Yu_Nian_An_Body not found!"

bm = bmesh.new()
bm.from_mesh(body.data)
bm.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

print("\n=== HAIR OCCLUSION & NORMAL-DOT CONTAINMENT AUDIT ===")
hair_layers = ['Hair_Hime_Bangs', 'Hair_Eyebrows', 'Hair_Eyelashes', 'Hair_Scalp_Crown', 'Hair_Hime_Sidelocks', 'Hair_Back_Cascade']
for h in hair_layers:
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
    pct_outside = ((total - inside) / total * 100.0) if total > 0 else 0.0
    print(f"{h}: Total: {total} | Inside: {inside} | OUTSIDE: {total - inside} ({pct_outside:.1f}%)")

bm.free()

# 4. Render beauty images
print("\n[4/4] Rendering beauty verification images...")
scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.device = 'CPU'

# Portrait
cam_portrait = bpy.data.objects.get('Camera_Portrait_85mm')
assert cam_portrait is not None, "Camera_Portrait_85mm not found!"
scene.camera = cam_portrait
portrait_path = os.path.abspath("output/yu_nian_an/master_portrait_clean.png")
scene.render.filepath = portrait_path
print("Rendering portrait to:", portrait_path)
bpy.ops.render.render(write_still=True)
print("Portrait render complete! File size:", os.path.getsize(portrait_path))

# Full-Body
cam_fullbody = bpy.data.objects.get('Camera_FullBody')
assert cam_fullbody is not None, "Camera_FullBody not found!"
scene.camera = cam_fullbody
fullbody_path = os.path.abspath("output/yu_nian_an/master_fullbody_clean.png")
scene.render.filepath = fullbody_path
print("Rendering fullbody to:", fullbody_path)
bpy.ops.render.render(write_still=True)
print("Fullbody render complete! File size:", os.path.getsize(fullbody_path))

print("\nALL DELIVERABLES REGENERATED CLEANLY.")
