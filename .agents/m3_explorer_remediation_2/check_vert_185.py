import bpy
import math
from pathlib import Path
from mathutils import Euler

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm_obj = bpy.data.objects.get("Anime_Armature")
skirt_obj = bpy.data.objects.get("Anime_Skirt")
legs_obj = bpy.data.objects.get("Anime_Legs")
scene = bpy.context.scene

act = bpy.data.actions.get("action_anime_walk_cycle")
arm_obj.animation_data.action = act
scene.frame_set(15)

pb = arm_obj.pose.bones
print("Rest pos of Skirt #185:", skirt_obj.data.vertices[185].co)
print("Skirt #185 groups:", {skirt_obj.vertex_groups[g.group].name: g.weight for g in skirt_obj.data.vertices[185].groups})

for p in [0, 10, 20, 25, 30, 40]:
    pb.get("Skirt_10").rotation_euler = Euler((math.radians(p * 0.5), 0, 0), "XYZ")
    pb.get("Skirt_11").rotation_euler = Euler((math.radians(p * 1.0), 0, 0), "XYZ")
    pb.get("Skirt_12").rotation_euler = Euler((math.radians(p * 0.8), 0, 0), "XYZ")
    pb.get("Skirt_01").rotation_euler = Euler((math.radians(p * 0.35), 0, 0), "XYZ")
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_skirt = skirt_obj.evaluated_get(depsgraph)
    me = eval_skirt.to_mesh()
    co = eval_skirt.matrix_world @ me.vertices[185].co
    eval_skirt.to_mesh_clear()
    print(f"p={p:2d}°: Skirt #185 eval world co = ({co.x:.4f}, {co.y:.4f}, {co.z:.4f})")
