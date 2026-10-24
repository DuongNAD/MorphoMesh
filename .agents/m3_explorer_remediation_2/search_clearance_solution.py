import bpy
import math
import sys
from pathlib import Path
from mathutils import Euler
from mathutils.kdtree import KDTree

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
SKIRT_BONE_NAMES = [f"Skirt_{i:02d}" for i in range(1, 13)]

def evaluate_solution(weights_l, weights_r, flare_mult, rear_mult=0.40, bounce_mult=2.5):
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

    actions = [a for a in bpy.data.actions if a.name.startswith("action_anime_")]
    pb = arm_obj.pose.bones

    # 1. Re-bake all actions
    for act in actions:
        arm_obj.animation_data.action = act
        f_start, f_end = int(act.frame_range[0]), int(act.frame_range[1])
        frames = list(range(f_start, f_end + 1))

        tl_pitches = []
        tr_pitches = []
        hb_z = []
        tl_bone = pb.get("Thigh.L")
        tr_bone = pb.get("Thigh.R")
        hips_bone = pb.get("Hips")

        for f in frames:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            tl_pitches.append(tl_bone.rotation_euler.x if tl_bone else 0.0)
            tr_pitches.append(tr_bone.rotation_euler.x if tr_bone else 0.0)
            hb_z.append(hips_bone.location.z if hips_bone else 0.0)

        for idx, f in enumerate(frames):
            tl_p = tl_pitches[idx]
            tr_p = tr_pitches[idx]
            hz = hb_z[idx]

            tl_fwd = max(0.0, -tl_p)
            tr_fwd = max(0.0, -tr_p)
            tl_back = max(0.0, tl_p)
            tr_back = max(0.0, tr_p)

            bounce = max(0.0, -hz * bounce_mult)

            for bname in SKIRT_BONE_NAMES:
                wl = weights_l.get(bname, 0.0)
                wr = weights_r.get(bname, 0.0)
                flare = (wl * tl_fwd + wr * tr_fwd) * flare_mult
                
                rear_push = 0.0
                if bname in ["Skirt_02", "Skirt_03", "Skirt_04"]:
                    rear_push += tl_back * rear_mult
                if bname in ["Skirt_04", "Skirt_05", "Skirt_06"]:
                    rear_push += tr_back * rear_mult

                tot = flare + rear_push + bounce
                deg = max(-15.0, min(65.0, math.degrees(tot)))
                rad = math.radians(deg)

                p_b = pb.get(bname)
                p_b.rotation_euler = Euler((rad, 0, 0), "XYZ")
                p_b.keyframe_insert(data_path="rotation_euler", frame=f)

    # 2. Audit all actions
    audit_results = {}
    for act in actions:
        arm_obj.animation_data.action = act
        f_start, f_end = int(act.frame_range[0]), int(act.frame_range[1])
        frames = list(range(f_start, f_end + 1))

        min_c = 9999.0
        worst_f = -1
        min_p = 999.0
        max_p = -999.0

        for f in frames:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()

            for bname in SKIRT_BONE_NAMES:
                pb_b = pb.get(bname)
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

        audit_results[act.name] = {
            "clearance_mm": min_c * 1000.0,
            "worst_frame": worst_f,
            "pitch_range": (min_p, max_p),
        }
    return audit_results

# Let's test combinations
candidates = [
    # (flare_mult, rear_mult, w_10, w_cross, w_flank, w_side)
    (0.70, 0.40, 0.70, 0.25, 0.80, 0.35),
    (0.80, 0.40, 0.80, 0.30, 0.85, 0.40),
    (0.90, 0.40, 0.85, 0.35, 0.90, 0.45),
    (1.00, 0.40, 0.90, 0.40, 0.90, 0.50),
    (1.10, 0.40, 0.90, 0.40, 0.95, 0.50),
]

for fm, rm, w10, w_cross, w_flank, w_side in candidates:
    wl = {
        "Skirt_01": w_side, "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
        "Skirt_05": 0.00, "Skirt_06": 0.00, "Skirt_07": 0.00, "Skirt_08": 0.00,
        "Skirt_09": w_cross, "Skirt_10": w10, "Skirt_11": 1.00, "Skirt_12": w_flank,
    }
    wr = {
        "Skirt_01": 0.00, "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
        "Skirt_05": 0.00, "Skirt_06": 0.00, "Skirt_07": w_side, "Skirt_08": w_flank,
        "Skirt_09": 1.00, "Skirt_10": w10, "Skirt_11": w_cross, "Skirt_12": 0.00,
    }
    print(f"\n--- Testing flare_mult={fm:.2f}, w10={w10:.2f}, w_cross={w_cross:.2f}, w_flank={w_flank:.2f} ---")
    res = evaluate_solution(wl, wr, flare_mult=fm, rear_mult=rm)
    all_pass = True
    for act, d in sorted(res.items()):
        c = d["clearance_mm"]
        p0, p1 = d["pitch_range"]
        ok = (c >= 15.0 and p0 >= -15.0 and p1 <= 65.0)
        if not ok: all_pass = False
        print(f"  {'PASS' if ok else 'FAIL'} {act:28s}: {c:6.2f}mm (frame {d['worst_frame']:2d}), pitch=[{p0:5.1f}°, {p1:5.1f}°]")
    print(f"Result: {'SUCCESS' if all_pass else 'FAILED'}")
