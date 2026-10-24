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

for f in [8, 27, 54]:
    scene.frame_set(f)
    tl = pb['Thigh.L'].rotation_euler.x
    tr = pb['Thigh.R'].rotation_euler.x
    hz = pb['Hips'].location.z

    tl_fwd = max(0.0, -tl)
    tr_fwd = max(0.0, -tr)
    bounce = max(0.0, -hz * 2.5)

    # Apply symmetric front flare
    for b in [f'Skirt_{i:02d}' for i in range(1, 13)]: pb[b].rotation_euler = (0, 0, 0)
    
    # Forward flare:
    # Skirt_09, 10, 11 receive full forward swing
    fwd_angle_deg = math.degrees((tl_fwd + tr_fwd) * 0.5) * 1.35
    pb['Skirt_10'].rotation_euler = Euler((math.radians(min(65.0, fwd_angle_deg)), 0, 0), 'XYZ')
    pb['Skirt_09'].rotation_euler = Euler((math.radians(min(65.0, fwd_angle_deg)), 0, 0), 'XYZ')
    pb['Skirt_11'].rotation_euler = Euler((math.radians(min(65.0, fwd_angle_deg)), 0, 0), 'XYZ')
    pb['Skirt_08'].rotation_euler = Euler((math.radians(min(65.0, fwd_angle_deg * 0.8)), 0, 0), 'XYZ')
    pb['Skirt_12'].rotation_euler = Euler((math.radians(min(65.0, fwd_angle_deg * 0.8)), 0, 0), 'XYZ')
    pb['Skirt_07'].rotation_euler = Euler((math.radians(min(65.0, fwd_angle_deg * 0.4)), 0, 0), 'XYZ')
    pb['Skirt_01'].rotation_euler = Euler((math.radians(min(65.0, fwd_angle_deg * 0.4)), 0, 0), 'XYZ')

    c, ti, si, tc = eval_frame()
    p10 = math.degrees(pb['Skirt_10'].rotation_euler.x)
    print(f"Jump cheer frame {f:2d}: pitch={p10:.1f}° -> clearance={c:6.2f}mm | Thigh #{ti} (Y={tc.y:+.3f})")
