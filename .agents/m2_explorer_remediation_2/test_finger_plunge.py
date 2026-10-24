"""
Detailed check of out-of-plane plunge and lateral deflection during finger flexion.
"""
import math
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector

blend_path = Path("E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_rigged.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm_obj = bpy.data.objects.get("Anime_Armature")
pb = arm_obj.pose.bones
arms_obj = bpy.data.objects.get("Anime_Arms")

# Apply transform synchronization
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.parent = arm_obj
        obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()

bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
depsgraph.update()

palm_L = Vector((0.43550, -0.18575, 1.01439))
palm_R = Vector((-0.43550, -0.18575, 1.01439))
finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]

print("================================================================================")
print("FINGERTIP TRAJECTORY & OUT-OF-PLANE LATERAL DEFLECTION AUDIT")
print("================================================================================")

for side in ["L", "R"]:
    palm = palm_L if side == "L" else palm_R
    print(f"\n--- Side {side} (Palm Centroid: {palm}) ---")
    for f in finger_names:
        p_distal = pb[f"{f}.03.{side}"]
        p_distal.rotation_mode = 'QUATERNION'

        # Rest
        p_distal.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        bpy.context.view_layer.update()
        t0 = (arm_obj.matrix_world @ p_distal.tail).copy()
        d0 = (t0 - palm).length

        # 45 deg
        p_distal.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(45.0))
        bpy.context.view_layer.update()
        t45 = (arm_obj.matrix_world @ p_distal.tail).copy()
        d45 = (t45 - palm).length

        # 90 deg
        p_distal.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(90.0))
        bpy.context.view_layer.update()
        t90 = (arm_obj.matrix_world @ p_distal.tail).copy()
        d90 = (t90 - palm).length

        # Reset
        p_distal.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        bpy.context.view_layer.update()

        # Bone local coordinate frame
        # In bone local space, flexion is around local X.
        # Check lateral deviation along bone's local X axis in world space:
        local_x = (arm_obj.matrix_world.to_3x3() @ p_distal.matrix.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
        lat_dev_45 = abs((t45 - t0).dot(local_x))
        lat_dev_90 = abs((t90 - t0).dot(local_x))

        print(f"{f}.03.{side}:")
        print(f"  Rest pos:  {t0}")
        print(f"  45°  pos:  {t45} | dist_to_palm={d45:.4f}m (curl={d45 < d0}) | lat_dev={lat_dev_45*1000:.3f}mm")
        print(f"  90°  pos:  {t90} | dist_to_palm={d90:.4f}m (curl={d90 < d45}) | lat_dev={lat_dev_90*1000:.3f}mm")
        print(f"  Strict monotonic curl: {d90 < d45 < d0} | Zero out-of-plane lateral plunge: {lat_dev_90 < 1e-4}")
