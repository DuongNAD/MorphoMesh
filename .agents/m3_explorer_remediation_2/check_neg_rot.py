import bpy
import math
from pathlib import Path
from mathutils import Euler

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm = bpy.data.objects.get("Anime_Armature")
scene = bpy.context.scene
scene.frame_set(1)

pb11 = arm.pose.bones["Skirt_11"]
tail_rest = arm.matrix_world @ pb11.tail

for rot in [-30, -20, -10, 0, 10, 20, 30]:
    pb11.rotation_euler = Euler((math.radians(rot), 0, 0), "XYZ")
    bpy.context.view_layer.update()
    tail_rot = arm.matrix_world @ pb11.tail
    delta = tail_rot - tail_rest
    print(f"Skirt_11 rot_x={rot:+3d}°: tail=({tail_rot.x:.3f}, {tail_rot.y:.3f}, {tail_rot.z:.3f}), delta=({delta.x:+.3f}, {delta.y:+.3f}, {delta.z:+.3f})")
