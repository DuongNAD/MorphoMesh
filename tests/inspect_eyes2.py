import bpy
import bmesh
import mathutils

body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
eye_objs = [
    "Mesh_Eye_Left_CorneaSclera", "Mesh_Eye_Left_IrisPupil",
    "Mesh_Eye_Right_CorneaSclera", "Mesh_Eye_Right_IrisPupil"
]

print("=== EYE MESH EMPIRICAL ANTERIOR AUDIT ===")
for e_name in eye_objs:
    e_obj = bpy.data.objects.get(e_name)
    if not e_obj:
        print(f"MISSING: {e_name}")
        continue
    # Evaluate world vertices
    eval_obj = e_obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = eval_obj.to_mesh()
    world_verts = [eval_obj.matrix_world @ v.co for v in m.vertices]
    eval_obj.to_mesh_clear()
    
    min_y = min(v.y for v in world_verts)
    max_y = max(v.y for v in world_verts)
    center_y = sum(v.y for v in world_verts) / len(world_verts)
    center_z = sum(v.z for v in world_verts) / len(world_verts)
    center_x = sum(v.x for v in world_verts) / len(world_verts)
    print(f"{e_name}: min_y={min_y:.5f}m, max_y={max_y:.5f}m, center=({center_x:+.4f}, {center_y:+.4f}, {center_z:+.4f})")
    is_valid = min_y >= -0.135
    print(f"  -> min_y >= -0.135m: {is_valid} (margin = {(min_y - (-0.135))*1000:.2f}mm)")

# Camera visibility
cam = bpy.data.objects.get("Camera_Front") or bpy.data.objects.get("Camera_Portrait_85mm")
print(f"\nCamera: {cam.name} at {cam.matrix_world.translation}")

bm = bmesh.new()
bm.from_mesh(body_obj.data)
bm.transform(body_obj.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

for c_name in ["Mesh_Eye_Left_CorneaSclera", "Mesh_Eye_Right_CorneaSclera"]:
    c = bpy.data.objects.get(c_name)
    c_pos = c.matrix_world.translation
    cam_pos = cam.matrix_world.translation
    ray_dir = (c_pos - cam_pos).normalized()
    ray_len = (c_pos - cam_pos).length
    hit_loc, hit_norm, hit_idx, hit_dist = bvh.ray_cast(cam_pos, ray_dir, ray_len - 0.002)
    print(f"Raycast to {c_name} center {c_pos}:")
    if hit_loc:
        diff_mm = (ray_len - hit_dist) * 1000
        print(f"  OCCLUSION HIT on body at {hit_loc}, dist diff from eye: {diff_mm:.2f}mm")
        if diff_mm > 15.0:
            print("  -> OCCLUDED by cranium/face surface!")
        else:
            print("  -> Close to eye boundary / socket rim.")
    else:
        print(f"  CLEAN LINE OF SIGHT! No body occlusion.")

bm.free()