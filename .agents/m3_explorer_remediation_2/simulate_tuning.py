import bpy
import math
import sys
from pathlib import Path
from mathutils import Euler
from mathutils.kdtree import KDTree

SKIRT_BONE_NAMES = [f"Skirt_{i:02d}" for i in range(1, 13)]

def test_skirt_tuning(flare_mult=0.55, w_center=0.50, w_cross=0.15, w_flank=0.80, rear_mult=0.40):
    thigh_l_weights = {
        "Skirt_01": 0.35, "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
        "Skirt_05": 0.00, "Skirt_06": 0.00, "Skirt_07": 0.00, "Skirt_08": 0.00,
        "Skirt_09": w_cross, "Skirt_10": w_center, "Skirt_11": 1.00, "Skirt_12": w_flank,
    }
    thigh_r_weights = {
        "Skirt_01": 0.00, "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
        "Skirt_05": 0.00, "Skirt_06": 0.00, "Skirt_07": 0.35, "Skirt_08": w_flank,
        "Skirt_09": 1.00, "Skirt_10": w_center, "Skirt_11": w_cross, "Skirt_12": 0.00,
    }

    arm_obj = bpy.data.objects.get("Anime_Armature")
    skirt_obj = bpy.data.objects.get("Anime_Skirt")
    legs_obj = bpy.data.objects.get("Anime_Legs")
    scene = bpy.context.scene

    thigh_vgroups = [g.index for g in legs_obj.vertex_groups if "Thigh" in g.name]
    thigh_vert_indices = [
        v.index for v in legs_obj.data.vertices
        for g in v.groups if g.group in thigh_vgroups and g.weight > 0.05
    ]
    skirt_rest_z_min = min(v.co.z for v in skirt_obj.data.vertices)
    skirt_rest_z_max = max(v.co.z for v in skirt_obj.data.vertices)

    actions = [a for a in bpy.data.actions if a.name.startswith("action_anime_")]
    
    # 1. Re-bake skirt keyframes
    pb = arm_obj.pose.bones
    for act in actions:
        arm_obj.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])
        frames = list(range(f_start, f_end + 1))

        thigh_l_pitches = []
        thigh_r_pitches = []
        hip_bounces = []
        thigh_l_bone = pb.get("Thigh.L")
        thigh_r_bone = pb.get("Thigh.R")
        hips_bone = pb.get("Hips")

        for f in frames:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            hip_bounces.append(hips_bone.location.z if hips_bone else 0.0)
            thigh_l_pitches.append(thigh_l_bone.rotation_euler.x if thigh_l_bone else 0.0)
            thigh_r_pitches.append(thigh_r_bone.rotation_euler.x if thigh_r_bone else 0.0)

        for idx, f in enumerate(frames):
            tl_p = thigh_l_pitches[idx]
            tr_p = thigh_r_pitches[idx]
            hb_z = hip_bounces[idx]

            # CORRECTED SIGN CONVENTION
            thigh_l_fwd = max(0.0, -tl_p)
            thigh_r_fwd = max(0.0, -tr_p)
            thigh_l_back = max(0.0, tl_p)
            thigh_r_back = max(0.0, tr_p)

            bounce_flare_rad = max(0.0, -hb_z * 2.5)

            for bname in SKIRT_BONE_NAMES:
                wl = thigh_l_weights.get(bname, 0.0)
                wr = thigh_r_weights.get(bname, 0.0)
                flare_forward = (wl * thigh_l_fwd + wr * thigh_r_fwd) * flare_mult
                rear_push = 0.0
                if bname in ["Skirt_02", "Skirt_03", "Skirt_04"]:
                    rear_push += thigh_l_back * rear_mult
                if bname in ["Skirt_04", "Skirt_05", "Skirt_06"]:
                    rear_push += thigh_r_back * rear_mult

                total_pitch_rad = flare_forward + rear_push + bounce_flare_rad
                total_pitch_deg = math.degrees(total_pitch_rad)
                clamped_deg = max(-15.0, min(65.0, total_pitch_deg))
                p_rad = math.radians(clamped_deg)

                p_bone = pb.get(bname)
                euler_rot = Euler((p_rad, 0.0, 0.0), "XYZ")
                p_bone.rotation_euler = euler_rot
                p_bone.keyframe_insert(data_path="rotation_euler", frame=f)

    # 2. Audit clearance and pitch
    res = {}
    for act in actions:
        arm_obj.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])
        min_c = 9999.0
        min_p = 999.0
        max_p = -999.0
        worst_f = -1
        for f in range(f_start, f_end + 1):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()

            for bname in SKIRT_BONE_NAMES:
                pb_b = arm_obj.pose.bones.get(bname)
                p_deg = math.degrees(pb_b.rotation_euler.x)
                min_p = min(min_p, p_deg)
                max_p = max(max_p, p_deg)

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

            for tc in thigh_cos:
                if (skirt_rest_z_min - 0.05) <= tc.z <= (skirt_rest_z_max + 0.05):
                    _, _, dist = kd.find(tc)
                    if dist < min_c:
                        min_c = dist
                        worst_f = f
            eval_skirt.to_mesh_clear()
            eval_legs.to_mesh_clear()

        res[act.name] = {"min_clearance_mm": min_c * 1000.0, "worst_frame": worst_f, "pitch_range": (min_p, max_p)}
    return res

print("STARTING TUNING SWEEP...")
configs = [
    {"flare_mult": 0.55, "w_center": 0.50, "w_cross": 0.15, "w_flank": 0.80, "desc": "mult 0.55 (default weights)"},
    {"flare_mult": 0.70, "w_center": 0.50, "w_cross": 0.15, "w_flank": 0.80, "desc": "mult 0.70 (default weights)"},
    {"flare_mult": 0.85, "w_center": 0.50, "w_cross": 0.15, "w_flank": 0.80, "desc": "mult 0.85 (default weights)"},
    {"flare_mult": 0.90, "w_center": 0.50, "w_cross": 0.15, "w_flank": 0.80, "desc": "mult 0.90 (default weights)"},
    {"flare_mult": 0.85, "w_center": 0.65, "w_cross": 0.25, "w_flank": 0.85, "desc": "mult 0.85 (boosted front weights)"},
    {"flare_mult": 0.95, "w_center": 0.65, "w_cross": 0.25, "w_flank": 0.85, "desc": "mult 0.95 (boosted front weights)"},
]

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")

for cfg in configs:
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    r = test_skirt_tuning(
        flare_mult=cfg["flare_mult"],
        w_center=cfg["w_center"],
        w_cross=cfg["w_cross"],
        w_flank=cfg["w_flank"],
    )
    print("=" * 60)
    print(f"CONFIG: {cfg['desc']} (mult={cfg['flare_mult']}, w_center={cfg['w_center']})")
    all_pass = True
    for act, data in sorted(r.items()):
        c_mm = data["min_clearance_mm"]
        wf = data["worst_frame"]
        p_min, p_max = data["pitch_range"]
        passed = c_mm >= 15.0 and p_min >= -15.0 and p_max <= 65.0
        status = "PASS" if passed else "FAIL"
        if not passed: all_pass = False
        print(f"  [{status}] {act:28s}: clearance={c_mm:6.2f}mm (frame {wf:3d}), pitch=[{p_min:5.1f} deg, {p_max:5.1f} deg]")
    print(f"OVERALL: {'ALL PASS' if all_pass else 'FAIL'}")
