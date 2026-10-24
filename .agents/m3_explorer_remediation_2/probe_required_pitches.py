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
SKIRT_BONE_NAMES = [f"Skirt_{i:02d}" for i in range(1, 13)]

def test_action_pitch_scale(act_name, scale_factors):
    act = bpy.data.actions.get(act_name)
    arm_obj.animation_data.action = act
    f_start, f_end = int(act.frame_range[0]), int(act.frame_range[1])
    frames = list(range(f_start, f_end + 1))

    # Read thigh angles
    tl_pitches = []
    tr_pitches = []
    hb_z = []
    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        tl_pitches.append(arm_obj.pose.bones["Thigh.L"].rotation_euler.x)
        tr_pitches.append(arm_obj.pose.bones["Thigh.R"].rotation_euler.x)
        hb_z.append(arm_obj.pose.bones["Hips"].location.z)

    min_overall_c = 9999.0
    worst_f = -1
    worst_ti = -1
    worst_si = -1

    for idx, f in enumerate(frames):
        scene.frame_set(f)
        tl_p = tl_pitches[idx]
        tr_p = tr_pitches[idx]
        hz = hb_z[idx]

        tl_fwd = max(0.0, -tl_p)
        tr_fwd = max(0.0, -tr_p)
        tl_back = max(0.0, tl_p)
        tr_back = max(0.0, tr_p)
        bounce = max(0.0, -hz * 2.5)

        for bname in SKIRT_BONE_NAMES:
            pitch_deg = scale_factors(bname, tl_fwd, tr_fwd, tl_back, tr_back, bounce)
            clamped = max(-15.0, min(65.0, pitch_deg))
            pb[bname].rotation_euler = Euler((math.radians(clamped), 0, 0), "XYZ")

        c, ti, si, tc = eval_frame()
        if c < min_overall_c:
            min_overall_c = c
            worst_f = f
            worst_ti = ti
            worst_si = si

    return min_overall_c, worst_f, worst_ti, worst_si

print("Testing scale functions on walk cycle and jump cheer...")
