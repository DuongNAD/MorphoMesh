import bpy
import math
from pathlib import Path
from mathutils import Euler
from mathutils.kdtree import KDTree

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm_obj = bpy.data.objects['Anime_Armature']
skirt_obj = bpy.data.objects['Anime_Skirt']
legs_obj = bpy.data.objects['Anime_Legs']
scene = bpy.context.scene

thigh_vgroups = {g.index: g.name for g in legs_obj.vertex_groups if "Thigh" in g.name}
thigh_vert_indices = [
    v.index for v in legs_obj.data.vertices
    for g in v.groups if g.group in thigh_vgroups and g.weight > 0.05
]
skirt_rest_z_min = min(v.co.z for v in skirt_obj.data.vertices)
skirt_rest_z_max = max(v.co.z for v in skirt_obj.data.vertices)

def eval_frame():
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
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
    best_ti = -1
    best_si = -1
    for t_orig_idx, tc in thigh_cos:
        if (skirt_rest_z_min - 0.05) <= tc.z <= (skirt_rest_z_max + 0.05):
            sco, s_idx, dist = kd.find(tc)
            if dist < min_dist:
                min_dist = dist
                best_tc = tc
                best_ti = t_orig_idx
                best_si = s_idx
    eval_skirt.to_mesh_clear()
    eval_legs.to_mesh_clear()
    return min_dist * 1000.0, best_ti, best_si, best_tc

pb = arm_obj.pose.bones
act = bpy.data.actions['action_anime_jump_cheer']
arm_obj.animation_data.action = act

print("Searching for pitch profile on Jump Cheer frames 11 and 54...")

for p10 in [45, 50, 55, 60, 65]:
    for p_front in [45, 50, 55, 60, 65]: # Skirt_09 and Skirt_11
        for p_flank in [35, 45, 55, 65]: # Skirt_08 and Skirt_12
            for p_side in [15, 25, 35, 45]: # Skirt_07 and Skirt_01
                # Test frame 11
                scene.frame_set(11)
                for b in [f'Skirt_{i:02d}' for i in range(1, 13)]: pb[b].rotation_euler = (0, 0, 0)
                pb['Skirt_10'].rotation_euler = Euler((math.radians(p10), 0, 0), 'XYZ')
                pb['Skirt_09'].rotation_euler = Euler((math.radians(p_front), 0, 0), 'XYZ')
                pb['Skirt_11'].rotation_euler = Euler((math.radians(p_front), 0, 0), 'XYZ')
                pb['Skirt_08'].rotation_euler = Euler((math.radians(p_flank), 0, 0), 'XYZ')
                pb['Skirt_12'].rotation_euler = Euler((math.radians(p_flank), 0, 0), 'XYZ')
                pb['Skirt_07'].rotation_euler = Euler((math.radians(p_side), 0, 0), 'XYZ')
                pb['Skirt_01'].rotation_euler = Euler((math.radians(p_side), 0, 0), 'XYZ')
                c11, _, _, _ = eval_frame()

                if c11 >= 15.0:
                    # Test frame 54
                    scene.frame_set(54)
                    c54, _, _, _ = eval_frame()
                    if c54 >= 15.0:
                        # Test frame 8
                        scene.frame_set(8)
                        c8, _, _, _ = eval_frame()
                        if c8 >= 15.0:
                            print(f"FOUND PASSING SET: p10={p10}, p_front={p_front}, p_flank={p_flank}, p_side={p_side} -> f8={c8:.2f}mm, f11={c11:.2f}mm, f54={c54:.2f}mm")
