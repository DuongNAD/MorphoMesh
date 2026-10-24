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

SKIRT_BONE_NAMES = [f"Skirt_{i:02d}" for i in range(1, 13)]

# Re-bake walk cycle and jump cheer with fixed sign convention and flare_mult = 0.55
thigh_l_weights = {
    "Skirt_01": 0.35, "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
    "Skirt_05": 0.00, "Skirt_06": 0.00, "Skirt_07": 0.00, "Skirt_08": 0.00,
    "Skirt_09": 0.15, "Skirt_10": 0.50, "Skirt_11": 1.00, "Skirt_12": 0.80,
}
thigh_r_weights = {
    "Skirt_01": 0.00, "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
    "Skirt_05": 0.00, "Skirt_06": 0.00, "Skirt_07": 0.35, "Skirt_08": 0.80,
    "Skirt_09": 1.00, "Skirt_10": 0.50, "Skirt_11": 0.15, "Skirt_12": 0.00,
}

pb = arm_obj.pose.bones
actions = [a for a in bpy.data.actions if a.name.startswith("action_anime_")]

for act in actions:
    arm_obj.animation_data.action = act
    f_start = int(act.frame_range[0])
    f_end = int(act.frame_range[1])
    frames = list(range(f_start, f_end + 1))

    tl_pitches = []
    tr_pitches = []
    hip_bounces = []
    tl_bone = pb.get("Thigh.L")
    tr_bone = pb.get("Thigh.R")
    hips_bone = pb.get("Hips")

    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        hip_bounces.append(hips_bone.location.z if hips_bone else 0.0)
        tl_pitches.append(tl_bone.rotation_euler.x if tl_bone else 0.0)
        tr_pitches.append(tr_bone.rotation_euler.x if tr_bone else 0.0)

    for idx, f in enumerate(frames):
        tl_p = tl_pitches[idx]
        tr_p = tr_pitches[idx]
        hb_z = hip_bounces[idx]

        thigh_l_fwd = max(0.0, -tl_p)
        thigh_r_fwd = max(0.0, -tr_p)
        thigh_l_back = max(0.0, tl_p)
        thigh_r_back = max(0.0, tr_p)

        bounce_flare_rad = max(0.0, -hb_z * 2.5)

        for bname in SKIRT_BONE_NAMES:
            wl = thigh_l_weights.get(bname, 0.0)
            wr = thigh_r_weights.get(bname, 0.0)
            flare_forward = (wl * thigh_l_fwd + wr * thigh_r_fwd) * 0.55
            rear_push = 0.0
            if bname in ["Skirt_02", "Skirt_03", "Skirt_04"]:
                rear_push += thigh_l_back * 0.40
            if bname in ["Skirt_04", "Skirt_05", "Skirt_06"]:
                rear_push += thigh_r_back * 0.40

            total_pitch_rad = flare_forward + rear_push + bounce_flare_rad
            total_pitch_deg = math.degrees(total_pitch_rad)
            clamped_deg = max(-15.0, min(65.0, total_pitch_deg))
            p_rad = math.radians(clamped_deg)

            p_bone = pb.get(bname)
            p_bone.rotation_euler = Euler((p_rad, 0.0, 0.0), "XYZ")
            p_bone.keyframe_insert(data_path="rotation_euler", frame=f)

thigh_vgroups = {g.index: g.name for g in legs_obj.vertex_groups if "Thigh" in g.name}
thigh_vert_indices = [
    v.index for v in legs_obj.data.vertices
    for g in v.groups if g.group in thigh_vgroups and g.weight > 0.05
]
skirt_rest_z_min = min(v.co.z for v in skirt_obj.data.vertices)
skirt_rest_z_max = max(v.co.z for v in skirt_obj.data.vertices)

def diagnose(act_name, f):
    act = bpy.data.actions.get(act_name)
    arm_obj.animation_data.action = act
    scene.frame_set(f)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    pb = arm_obj.pose.bones
    tl = pb.get("Thigh.L")
    tr = pb.get("Thigh.R")
    print(f"\n=== AFTER RE-BAKE: {act_name} Frame {f} ===")
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

    print(f"Min distance: {min_dist*1000.0:.2f} mm")
    print(f"Thigh vert #{best_t_idx}: world={best_tc}, groups={t_groups}")
    print(f"Nearest Skirt vert #{best_s_idx}: world={best_sc}, groups={s_groups}")

diagnose("action_anime_walk_cycle", 15)
diagnose("action_anime_walk_cycle", 32)
diagnose("action_anime_jump_cheer", 27)
diagnose("action_anime_jump_cheer", 54)
