import bpy
import math
from pathlib import Path
from mathutils import Euler
from mathutils.kdtree import KDTree

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm_obj = bpy.data.objects.get("Anime_Armature")
skirt_obj = bpy.data.objects.get("Anime_Skirt")
legs_obj = bpy.data.objects.get("Anime_Legs")
scene = bpy.context.scene

thigh_vgroups = {g.index: g.name for g in legs_obj.vertex_groups if "Thigh" in g.name}
thigh_vert_indices = [
    v.index for v in legs_obj.data.vertices
    for g in v.groups if g.group in thigh_vgroups and g.weight > 0.05
]
skirt_rest_z_min = min(v.co.z for v in skirt_obj.data.vertices)
skirt_rest_z_max = max(v.co.z for v in skirt_obj.data.vertices)

def eval_frame_clearance():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_skirt = skirt_obj.evaluated_get(depsgraph)
    eval_legs = legs_obj.evaluated_get(depsgraph)
    me_skirt = eval_skirt.to_mesh()
    me_legs = eval_legs.to_mesh()
    mw_skirt = eval_skirt.matrix_world
    mw_legs = eval_legs.matrix_world

    skirt_cos = [mw_skirt @ v.co for v in me_skirt.vertices]
    thigh_cos = [mw_legs @ me_legs.vertices[i].co for i in thigh_vert_indices]

    kd = KDTree(len(skirt_cos))
    for i, co in enumerate(skirt_cos): kd.insert(co, i)
    kd.balance()

    min_dist = 999.0
    for tc in thigh_cos:
        if (skirt_rest_z_min - 0.05) <= tc.z <= (skirt_rest_z_max + 0.05):
            _, _, dist = kd.find(tc)
            if dist < min_dist:
                min_dist = dist

    eval_skirt.to_mesh_clear()
    eval_legs.to_mesh_clear()
    return min_dist * 1000.0

print("=== SENSITIVITY TEST: Jump Cheer Frame 27 ===")
act = bpy.data.actions.get("action_anime_jump_cheer")
arm_obj.animation_data.action = act
scene.frame_set(27)

pb = arm_obj.pose.bones
for test_pitch_deg in [0, 15, 25, 35, 45, 55, 65]:
    for bname in ["Skirt_08", "Skirt_09", "Skirt_10", "Skirt_11", "Skirt_12", "Skirt_01"]:
        pb.get(bname).rotation_euler = Euler((math.radians(test_pitch_deg), 0, 0), "XYZ")
    bpy.context.view_layer.update()
    c = eval_frame_clearance()
    print(f"Front pitch = {test_pitch_deg:2d}° -> clearance = {c:6.2f} mm")

print("\n=== SENSITIVITY TEST: Jump Cheer Frame 54 ===")
scene.frame_set(54)
for test_pitch_deg in [0, 15, 25, 35, 45, 55, 65]:
    for bname in ["Skirt_08", "Skirt_09", "Skirt_10", "Skirt_11", "Skirt_12", "Skirt_01"]:
        pb.get(bname).rotation_euler = Euler((math.radians(test_pitch_deg), 0, 0), "XYZ")
    bpy.context.view_layer.update()
    c = eval_frame_clearance()
    print(f"Front pitch = {test_pitch_deg:2d}° -> clearance = {c:6.2f} mm")

print("\n=== SENSITIVITY TEST: Walk Cycle Frame 32 ===")
act_walk = bpy.data.actions.get("action_anime_walk_cycle")
arm_obj.animation_data.action = act_walk
scene.frame_set(32)
for test_pitch_deg in [0, 15, 25, 35, 45, 55, 65]:
    for bname in ["Skirt_07", "Skirt_08", "Skirt_09", "Skirt_10"]:
        pb.get(bname).rotation_euler = Euler((math.radians(test_pitch_deg), 0, 0), "XYZ")
    bpy.context.view_layer.update()
    c = eval_frame_clearance()
    print(f"Right-front pitch = {test_pitch_deg:2d}° -> clearance = {c:6.2f} mm")
