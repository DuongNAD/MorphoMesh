import bpy
import bmesh
import mathutils

body = bpy.data.objects.get('Yu_Nian_An_Body')
cam = bpy.data.objects.get("Camera_Front") or bpy.data.objects.get("Camera_Portrait_85mm")

bm = bmesh.new()
bm.from_mesh(body.data)
bm.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

s = 1.0
ipd = 0.062 * s

for test_z in [1.515, 1.520, 1.525, 1.530, 1.543]:
    for test_y in [-0.118, -0.120, -0.122]:
        left_eye_pos = mathutils.Vector((ipd / 2.0, test_y * s, test_z * s))
        cam_pos = cam.matrix_world.translation
        ray_dir = (left_eye_pos - cam_pos).normalized()
        ray_len = (left_eye_pos - cam_pos).length
        hit_loc, hit_norm, hit_idx, hit_dist = bvh.ray_cast(cam_pos, ray_dir, ray_len - 0.002)
        status = f"OCCLUDED at {hit_loc}" if hit_loc else "CLEAN"
        print(f"z={test_z:.3f}, y={test_y:.3f} -> {status}")
