import bpy
import math
from pathlib import Path
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

def diagnose_action_frame(act_name, f):
    act = bpy.data.actions.get(act_name)
    arm_obj.animation_data.action = act
    scene.frame_set(f)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    pb = arm_obj.pose.bones
    tl = pb.get("Thigh.L")
    tr = pb.get("Thigh.R")
    print(f"=== {act_name} Frame {f} ===")
    print(f"Thigh.L rot_x: {math.degrees(tl.rotation_euler.x):.2f}°, Thigh.R rot_x: {math.degrees(tr.rotation_euler.x):.2f}°")
    print("Skirt pitches:")
    for i in range(1, 13):
        bname = f"Skirt_{i:02d}"
        print(f"  {bname}: {math.degrees(pb.get(bname).rotation_euler.x):.2f}°", end=" ")
        if i % 4 == 0: print()

    eval_skirt = skirt_obj.evaluated_get(depsgraph)
    eval_legs = legs_obj.evaluated_get(depsgraph)
    me_skirt = eval_skirt.to_mesh()
    me_legs = eval_legs.to_mesh()
    mw_skirt = eval_skirt.matrix_world
    mw_legs = eval_legs.matrix_world

    skirt_cos = [mw_skirt @ v.co for v in me_skirt.vertices]
    thigh_cos = [(i, mw_legs @ me_legs.vertices[i].co) for i in thigh_vert_indices]

    kd = KDTree(len(skirt_cos))
    for i, co in enumerate(skirt_cos): kd.insert(co, i)
    kd.balance()

    min_dist = 999.0
    best_tc = None
    best_t_idx = -1
    best_s_idx = -1
    for t_orig_idx, tc in thigh_cos:
        if (skirt_rest_z_min - 0.05) <= tc.z <= (skirt_rest_z_max + 0.05):
            sco, s_idx, dist = kd.find(tc)
            if dist < min_dist:
                min_dist = dist
                best_tc = tc
                best_t_idx = t_orig_idx
                best_s_idx = s_idx
                best_sc = sco

    eval_skirt.to_mesh_clear()
    eval_legs.to_mesh_clear()

    t_vert = legs_obj.data.vertices[best_t_idx]
    s_vert = skirt_obj.data.vertices[best_s_idx]
    t_groups = {legs_obj.vertex_groups[g.group].name: g.weight for g in t_vert.groups}
    s_groups = {skirt_obj.vertex_groups[g.group].name: g.weight for g in s_vert.groups}

    print(f"\nMin distance: {min_dist*1000.0:.2f} mm")
    print(f"Thigh vert #{best_t_idx}: world={best_tc}, groups={t_groups}")
    print(f"Nearest Skirt vert #{best_s_idx}: world={best_sc}, groups={s_groups}")
    print("-" * 60)

# Diagnosing currently baked anime_animated.blend
diagnose_action_frame("action_anime_walk_cycle", 15)
diagnose_action_frame("action_anime_walk_cycle", 18)
diagnose_action_frame("action_anime_walk_cycle", 32)
diagnose_action_frame("action_anime_jump_cheer", 8)
diagnose_action_frame("action_anime_jump_cheer", 27)
diagnose_action_frame("action_anime_jump_cheer", 54)
