import bpy
import math
from pathlib import Path
from mathutils import Euler, Vector

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm = bpy.data.objects.get("Anime_Armature")
skirt_obj = bpy.data.objects.get("Anime_Skirt")
scene = bpy.context.scene

print("=== CHECK SKIRT BONE ROTATIONS AND REST TAILS ===")
# Set rest pose / frame 1
scene.frame_set(1)
bpy.context.view_layer.update()

for i in range(1, 13):
    bname = f"Skirt_{i:02d}"
    pb = arm.pose.bones[bname]
    # Set rotation to 0
    pb.rotation_euler = Euler((0, 0, 0), "XYZ")

bpy.context.view_layer.update()

for i in range(1, 13):
    bname = f"Skirt_{i:02d}"
    pb = arm.pose.bones[bname]
    head_rest = arm.matrix_world @ pb.head
    tail_rest = arm.matrix_world @ pb.tail
    
    # Now set rotation_euler.x = +30 deg
    pb.rotation_euler = Euler((math.radians(30.0), 0, 0), "XYZ")
    bpy.context.view_layer.update()
    tail_rot = arm.matrix_world @ pb.tail

    delta = tail_rot - tail_rest
    # Radius from character center (0, 0, Z)
    r_rest = math.hypot(tail_rest.x, tail_rest.y)
    r_rot = math.hypot(tail_rot.x, tail_rot.y)
    
    print(f"{bname:8s}: rest_tail=({tail_rest.x:.3f}, {tail_rest.y:.3f}, {tail_rest.z:.3f}) | "
          f"rot_tail=({tail_rot.x:.3f}, {tail_rot.y:.3f}, {tail_rot.z:.3f}) | "
          f"delta=({delta.x:.3f}, {delta.y:.3f}, {delta.z:.3f}) | "
          f"r_rest={r_rest:.3f} -> r_rot={r_rot:.3f} (delta_r={r_rot - r_rest:+.3f}m)")

    # Reset
    pb.rotation_euler = Euler((0, 0, 0), "XYZ")
