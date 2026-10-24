import bpy
import math
from pathlib import Path
from mathutils import Euler
from mathutils.kdtree import KDTree

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")

SKIRT_BONE_NAMES = [f"Skirt_{i:02d}" for i in range(1, 13)]

def run_full_audit(weights_l, weights_r, flare_mult, rear_l_mult, rear_r_mult, bounce_mult=2.5):
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
                    rear_push += tl_back * rear_l_mult
                if bname in ["Skirt_04", "Skirt_05", "Skirt_06"]:
                    rear_push += tr_back * rear_r_mult

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

# Define candidate weight mappings
w_l_default = {
    "Skirt_01": 0.35, "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
    "Skirt_05": 0.00, "Skirt_06": 0.00, "Skirt_07": 0.00, "Skirt_08": 0.00,
    "Skirt_09": 0.15, "Skirt_10": 0.50, "Skirt_11": 1.00, "Skirt_12": 0.80,
}
w_r_default = {
    "Skirt_01": 0.00, "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
    "Skirt_05": 0.00, "Skirt_06": 0.00, "Skirt_07": 0.35, "Skirt_08": 0.80,
    "Skirt_09": 1.00, "Skirt_10": 0.50, "Skirt_11": 0.15, "Skirt_12": 0.00,
}

print("RUNNING CANDIDATE AUDITS...")
res = run_full_audit(w_l_default, w_r_default, flare_mult=0.75, rear_l_mult=0.40, rear_r_mult=0.00)
for act, d in sorted(res.items()):
    print(f"{act:28s}: clearance={d['clearance_mm']:6.2f}mm (frame {d['worst_frame']:3d}), pitch=[{d['pitch_range'][0]:.1f}°, {d['pitch_range'][1]:.1f}°]")
