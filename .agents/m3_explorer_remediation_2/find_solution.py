import bpy
import math
import sys
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
SKIRT_BONE_NAMES = [f"Skirt_{i:02d}" for i in range(1, 13)]
pb = arm_obj.pose.bones

# Pre-sample actions kinematics
actions = [a for a in bpy.data.actions if a.name.startswith("action_anime_")]
act_kinematics = {}
for act in actions:
    arm_obj.animation_data.action = act
    f_start, f_end = int(act.frame_range[0]), int(act.frame_range[1])
    frames = list(range(f_start, f_end + 1))
    tl_list, tr_list, hb_list = [], [], []
    tl_bone = pb.get("Thigh.L")
    tr_bone = pb.get("Thigh.R")
    hips_bone = pb.get("Hips")
    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        tl_list.append(tl_bone.rotation_euler.x if tl_bone else 0.0)
        tr_list.append(tr_bone.rotation_euler.x if tr_bone else 0.0)
        hb_list.append(hips_bone.location.z if hips_bone else 0.0)
    act_kinematics[act.name] = (frames, tl_list, tr_list, hb_list)

def test_config(flare_mult, w10, w_main, w_flank, w_cross, w_side, rear_l_mult, rear_r_mult, bounce_mult=2.5):
    wl = {
        "Skirt_01": w_side,  "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
        "Skirt_05": 0.00,    "Skirt_06": 0.00, "Skirt_07": 0.00, "Skirt_08": 0.00,
        "Skirt_09": w_cross, "Skirt_10": w10,  "Skirt_11": w_main, "Skirt_12": w_flank,
    }
    wr = {
        "Skirt_01": 0.00,    "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
        "Skirt_05": 0.00,    "Skirt_06": 0.00, "Skirt_07": w_side, "Skirt_08": w_flank,
        "Skirt_09": w_main,  "Skirt_10": w10,  "Skirt_11": w_cross, "Skirt_12": 0.00,
    }

    # Re-bake
    for act in actions:
        arm_obj.animation_data.action = act
        frames, tl_list, tr_list, hb_list = act_kinematics[act.name]

        for idx, f in enumerate(frames):
            tl_fwd = max(0.0, -tl_list[idx])
            tr_fwd = max(0.0, -tr_list[idx])
            tl_back = max(0.0, tl_list[idx])
            tr_back = max(0.0, tr_list[idx])
            bounce = max(0.0, -hb_list[idx] * bounce_mult)

            for bname in SKIRT_BONE_NAMES:
                w_l = wl.get(bname, 0.0)
                w_r = wr.get(bname, 0.0)
                flare = (w_l * tl_fwd + w_r * tr_fwd) * flare_mult
                
                rear_push = 0.0
                if bname in ["Skirt_02", "Skirt_03", "Skirt_04"]:
                    rear_push += tl_back * rear_l_mult
                if bname in ["Skirt_04", "Skirt_05", "Skirt_06"]:
                    rear_push += tr_back * rear_r_mult

                tot = flare + rear_push + bounce
                deg = max(-15.0, min(65.0, math.degrees(tot)))
                rad = math.radians(deg)

                pb.get(bname).rotation_euler = Euler((rad, 0, 0), "XYZ")
                pb.get(bname).keyframe_insert(data_path="rotation_euler", frame=f)

    # Evaluate clearance and pitch
    report = {}
    for act in actions:
        arm_obj.animation_data.action = act
        frames, _, _, _ = act_kinematics[act.name]
        min_c = 9999.0
        min_p = 999.0
        max_p = -999.0
        worst_f = -1

        for f in frames:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()

            for bname in SKIRT_BONE_NAMES:
                p_deg = math.degrees(pb.get(bname).rotation_euler.x)
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

        report[act.name] = (min_c * 1000.0, worst_f, min_p, max_p)

    return report

print("Searching parameter grid...")
# Grid definition
grid = []
for fm in [0.85, 1.00, 1.15, 1.30]:
    for w10 in [0.70, 0.85, 1.00]:
        for w_flank in [0.75, 0.85]:
            for w_cross in [0.20, 0.35]:
                for w_side in [0.35, 0.50]:
                    for rm_l in [0.30, 0.40]:
                        for rm_r in [0.00, -0.20]:
                            grid.append((fm, w10, 1.00, w_flank, w_cross, w_side, rm_l, rm_r))

print(f"Total grid points: {len(grid)}")
best_overall = 0.0
best_params = None

for idx, params in enumerate(grid[:60]): # test first 60
    fm, w10, w_main, w_flank, w_cross, w_side, rm_l, rm_r = params
    rep = test_config(fm, w10, w_main, w_flank, w_cross, w_side, rm_l, rm_r)
    min_overall = min(r[0] for r in rep.values())
    if min_overall > best_overall:
        best_overall = min_overall
        best_params = params
        print(f"[{idx:2d}] New best min clearance = {min_overall:.2f}mm with fm={fm}, w10={w10}, cross={w_cross}, flank={w_flank}, rm_l={rm_l}, rm_r={rm_r}")
        for act_n, (c, wf, p0, p1) in sorted(rep.items()):
            print(f"     {act_n:28s}: {c:5.2f}mm (f{wf:2d}), pitch=[{p0:4.1f}°, {p1:4.1f}°]")
        if min_overall >= 15.0:
            print(">>> FOUND FULLY COMPLIANT SOLUTION! <<<")
            break
