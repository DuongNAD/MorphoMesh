"""
tests/challenger_it2_deep_empirical_audit.py
Milestone 3 Iteration 2 Challenger Deep Empirical Audit.
Executes deep forensic inspection on output/anime_animated.blend and output/anime_animated.glb.
"""

import sys
import math
from pathlib import Path

try:
    import bpy
    import bmesh
    from mathutils import Vector, Euler, Quaternion
    from mathutils.kdtree import KDTree
except ImportError as e:
    print(f"Error: Must be run inside Blender: {e}")
    sys.exit(1)


def audit_blend_file():
    print("\n" + "=" * 80)
    print("AUDIT 1: FORENSIC EVALUATION OF output/anime_animated.blend")
    print("=" * 80)

    blend_path = Path("output/anime_animated.blend").resolve()
    if not blend_path.exists():
        print(f"FAIL: {blend_path} not found")
        sys.exit(1)

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    arm = bpy.data.objects.get("Anime_Armature")
    if not arm:
        print("FAIL: Anime_Armature not found in blend file")
        sys.exit(1)

    actions = [a for a in bpy.data.actions if a.name.startswith("action_anime_")]
    print(f"Found {len(actions)} animation actions: {[a.name for a in actions]}")

    # Check 1: ForeArm Raw F-Curves
    print("\n--- 1.1 ForeArm Raw Keyframe F-Curves ---")
    fcurve_violations = []
    for act in actions:
        for fc in act.fcurves:
            if 'ForeArm' in fc.data_path and fc.array_index == 0:  # local X
                for kp in fc.keyframe_points:
                    val_deg = math.degrees(kp.co[1])
                    if val_deg < -0.01 or val_deg > 145.01:
                        fcurve_violations.append(f"{act.name} {fc.data_path} frame {kp.co[0]:.1f}: {val_deg:.2f}°")
    print(f"Raw ForeArm F-Curve keyframe limit violations: {len(fcurve_violations)}")
    if fcurve_violations:
        for v in fcurve_violations[:10]:
            print(f"  VIOLATION: {v}")

    # Check 1.2: Evaluated Pose Bone ForeArm Rotations
    print("\n--- 1.2 Pose Bone ForeArm Evaluated Rotations Across All Frames ---")
    forearm_violations = []
    forearm_stats = {}

    for act in actions:
        arm.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])
        num_frames = f_end - f_start + 1

        for bname in ["ForeArm.L", "ForeArm.R"]:
            pb = arm.pose.bones.get(bname)
            if not pb:
                print(f"FAIL: Pose bone {bname} not found")
                continue

            rx_vals = []
            ry_vals = []
            rz_vals = []
            for f in range(f_start, f_end + 1):
                bpy.context.scene.frame_set(f)
                rx = math.degrees(pb.rotation_euler.x)
                ry = math.degrees(pb.rotation_euler.y)
                rz = math.degrees(pb.rotation_euler.z)
                rx_vals.append(rx)
                ry_vals.append(ry)
                rz_vals.append(rz)

                if rx < -0.01 or rx > 145.01:
                    forearm_violations.append(f"{act.name} frame {f} {bname}: rx={rx:.2f}°")

            min_rx = min(rx_vals)
            max_rx = max(rx_vals)
            avg_rx = sum(rx_vals) / len(rx_vals)
            forearm_stats[f"{act.name}:{bname}"] = (min_rx, max_rx, avg_rx)
            print(f"  {act.name:<28} | {bname:<9} | Frames: {num_frames:3d} | rx: [{min_rx:6.2f}°, {max_rx:6.2f}°] (mean: {avg_rx:6.2f}°)")

    print(f"Total ForeArm Pose Bone Violations: {len(forearm_violations)}")

    # Check 1.3: Shin Flexion and Valgus Bounds
    print("\n--- 1.3 Shin Flexion [0°, 140°] & Valgus [-3°, +3°] Bounds ---")
    shin_violations = []
    for act in actions:
        arm.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])

        for bname in ["Shin.L", "Shin.R"]:
            pb = arm.pose.bones.get(bname)
            rx_vals, ry_vals, rz_vals = [], [], []
            for f in range(f_start, f_end + 1):
                bpy.context.scene.frame_set(f)
                rx = math.degrees(pb.rotation_euler.x)
                ry = math.degrees(pb.rotation_euler.y)
                rz = math.degrees(pb.rotation_euler.z)
                rx_vals.append(rx)
                ry_vals.append(ry)
                rz_vals.append(rz)

                if rx < -0.01 or rx > 140.01:
                    shin_violations.append(f"{act.name} frame {f} {bname} rx={rx:.2f}°")
                if abs(ry) > 3.01 or abs(rz) > 3.01:
                    shin_violations.append(f"{act.name} frame {f} {bname} valgus ry={ry:.2f}°, rz={rz:.2f}°")

            print(f"  {act.name:<28} | {bname:<9} | rx: [{min(rx_vals):6.2f}°, {max(rx_vals):6.2f}°] | ry: [{min(ry_vals):5.2f}°, {max(ry_vals):5.2f}°] | rz: [{min(rz_vals):5.2f}°, {max(rz_vals):5.2f}°]")

    print(f"Total Shin / Valgus Violations: {len(shin_violations)}")

    # Check 1.4: Dual Quaternion Skinning & Mesh Stability
    print("\n--- 1.4 DQS & Mesh Volume Retention & Degeneracy Audit ---")
    obj_arms = bpy.data.objects.get("Anime_Arms")
    obj_legs = bpy.data.objects.get("Anime_Legs")

    # Verify DQS settings
    for obj in [obj_arms, obj_legs]:
        arm_mods = [m for m in obj.modifiers if m.type == 'ARMATURE']
        assert len(arm_mods) > 0, f"No armature modifier on {obj.name}"
        assert arm_mods[0].use_deform_preserve_volume, f"DQS not enabled on {obj.name}"
        print(f"  {obj.name}: Armature modifier '{arm_mods[0].name}' use_deform_preserve_volume = {arm_mods[0].use_deform_preserve_volume}")

    def compute_capped_volume(eval_obj):
        me = eval_obj.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=100)
        vol = bm.calc_volume()
        bm.free()
        eval_obj.to_mesh_clear()
        return vol

    def check_mesh_stability(eval_obj):
        me = eval_obj.to_mesh()
        degen = sum(1 for p in me.polygons if p.area <= 1e-7)
        anomalies = sum(1 for v in me.vertices for c in v.co if math.isnan(c) or math.isinf(c) or abs(c) > 50.0)
        eval_obj.to_mesh_clear()
        return degen, anomalies

    arm.animation_data.action = None
    bpy.context.scene.frame_set(1)
    dg = bpy.context.evaluated_depsgraph_get()
    v_rest_arms = compute_capped_volume(obj_arms.evaluated_get(dg))
    v_rest_legs = compute_capped_volume(obj_legs.evaluated_get(dg))
    print(f"  Rest volume - Arms: {v_rest_arms*1e6:.1f} cm3, Legs: {v_rest_legs*1e6:.1f} cm3")

    min_arm_ret = 1.0
    max_arm_ret = 1.0
    min_leg_ret = 1.0
    max_leg_ret = 1.0
    total_degen_faces = 0
    total_coord_anomalies = 0

    for act in actions:
        arm.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])

        for f in range(f_start, f_end + 1):
            bpy.context.scene.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            ev_a = obj_arms.evaluated_get(dg)
            ev_l = obj_legs.evaluated_get(dg)

            va = compute_capped_volume(ev_a)
            vl = compute_capped_volume(ev_l)

            ra = va / v_rest_arms
            rl = vl / v_rest_legs

            min_arm_ret = min(min_arm_ret, ra)
            max_arm_ret = max(max_arm_ret, ra)
            min_leg_ret = min(min_leg_ret, rl)
            max_leg_ret = max(max_leg_ret, rl)

            d_a, an_a = check_mesh_stability(ev_a)
            d_l, an_l = check_mesh_stability(ev_l)
            total_degen_faces += (d_a + d_l)
            total_coord_anomalies += (an_a + an_l)

    print(f"  Arms Volume Retention: [{min_arm_ret*100:.2f}%, {max_arm_ret*100:.2f}%] (Threshold: >= 85%)")
    print(f"  Legs Volume Retention: [{min_leg_ret*100:.2f}%, {max_leg_ret*100:.2f}%] (Threshold: >= 85%)")
    print(f"  Total Degenerate Faces: {total_degen_faces}")
    print(f"  Total Coordinate Anomalies (NaN/Inf/>50m): {total_coord_anomalies}")

    # Check 1.5: Skirt Clearance
    print("\n--- 1.5 Skirt 3D Clearance and Pitch Limits Audit ---")
    obj_skirt = bpy.data.objects.get("Anime_Skirt")
    min_clearance_mm = 999.0
    pitch_violations = []

    # Thigh bone names
    thigh_bone_names = {"Thigh.L", "Thigh.R", "Thigh_Twist.L", "Thigh_Twist.R"}
    thigh_vg_indices = {obj_legs.vertex_groups[n].index for n in thigh_bone_names if n in obj_legs.vertex_groups}

    for act in actions:
        arm.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])

        for f in range(f_start, f_end + 1):
            bpy.context.scene.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            ev_skirt = obj_skirt.evaluated_get(dg)
            ev_legs = obj_legs.evaluated_get(dg)

            me_skirt = ev_skirt.to_mesh()
            me_legs = ev_legs.to_mesh()

            thigh_cos = [
                ev_legs.matrix_world @ v.co for v in me_legs.vertices
                if any(g.group in thigh_vg_indices and g.weight > 0.1 for g in v.groups)
            ]
            if thigh_cos:
                kd = KDTree(len(thigh_cos))
                for i, co in enumerate(thigh_cos):
                    kd.insert(co, i)
                kd.balance()

                for v in me_skirt.vertices:
                    wco = ev_skirt.matrix_world @ v.co
                    _, _, dist = kd.find(wco)
                    dist_mm = dist * 1000.0
                    if dist_mm < min_clearance_mm:
                        min_clearance_mm = dist_mm

            ev_skirt.to_mesh_clear()
            ev_legs.to_mesh_clear()

            # Check skirt spoke bone pitch [-15°, 65°]
            for i in range(1, 13):
                bname = f"Skirt_{i:02d}"
                pb = arm.pose.bones.get(bname)
                if pb:
                    rx = math.degrees(pb.rotation_euler.x)
                    if rx < -15.01 or rx > 65.01:
                        pitch_violations.append(f"{act.name} f{f} {bname}: {rx:.2f}°")

    print(f"  Minimum Skirt-to-Thigh Clearance: {min_clearance_mm:.2f} mm (Threshold: >= 15.0 mm)")
    print(f"  Skirt Spoke Pitch Violations: {len(pitch_violations)}")

    return {
        "fcurve_violations": len(fcurve_violations),
        "forearm_violations": len(forearm_violations),
        "forearm_stats": forearm_stats,
        "shin_violations": len(shin_violations),
        "min_arm_ret": min_arm_ret,
        "max_arm_ret": max_arm_ret,
        "min_leg_ret": min_leg_ret,
        "max_leg_ret": max_leg_ret,
        "degenerate_faces": total_degen_faces,
        "coordinate_anomalies": total_coord_anomalies,
        "min_clearance_mm": min_clearance_mm,
        "pitch_violations": len(pitch_violations),
    }


def audit_glb_file():
    print("\n" + "=" * 80)
    print("AUDIT 2: FORENSIC EVALUATION OF output/anime_animated.glb")
    print("=" * 80)

    glb_path = Path("output/anime_animated.glb").resolve()
    if not glb_path.exists():
        print(f"FAIL: {glb_path} not found")
        sys.exit(1)

    print(f"Loading GLB file: {glb_path} (Size: {glb_path.stat().st_size:,} bytes)")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))

    arm_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if not arm_objs:
        print("FAIL: No armature in imported GLB")
        sys.exit(1)
    arm = arm_objs[0]

    actions = list(bpy.data.actions)
    print(f"Imported GLB Actions ({len(actions)}): {[a.name for a in actions]}")

    forearm_channels_stats = {}
    frozen_channels = []

    print("\n--- 2.1 Baked ForeArm Animation Channels Inspection ---")
    for act in actions:
        arm.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])
        num_frames = f_end - f_start + 1

        for bname in ["ForeArm.L", "ForeArm.R"]:
            pb = arm.pose.bones.get(bname)
            if not pb:
                print(f"FAIL: Pose bone {bname} not found in GLB")
                continue

            rx_vals = []
            angular_devs = []

            for f in range(f_start, f_end + 1):
                bpy.context.scene.frame_set(f)
                if pb.rotation_mode == 'QUATERNION':
                    q = pb.rotation_quaternion
                    e = q.to_euler('XYZ')
                    # Angle from neutral (w=1, x=0, y=0, z=0)
                    dev_deg = 2.0 * math.acos(max(-1.0, min(1.0, abs(q.w)))) * 180.0 / math.pi
                else:
                    e = pb.rotation_euler
                    dev_deg = math.degrees(math.sqrt(e.x**2 + e.y**2 + e.z**2))

                rx_deg = math.degrees(e.x)
                rx_vals.append(rx_deg)
                angular_devs.append(dev_deg)

            min_rx = min(rx_vals)
            max_rx = max(rx_vals)
            max_dev = max(angular_devs)
            forearm_channels_stats[f"{act.name}:{bname}"] = {
                "min_rx": min_rx,
                "max_rx": max_rx,
                "max_dev": max_dev,
                "frames": num_frames,
            }

            is_frozen = max_dev < 20.0
            status_str = "ACTIVE (PASSED)" if not is_frozen else "FROZEN (FAILED)"
            if is_frozen:
                frozen_channels.append(f"{act.name}:{bname} (max_dev={max_dev:.2f}°)")

            print(f"  {act.name:<28} | {bname:<9} | rx: [{min_rx:6.2f}°, {max_rx:6.2f}°] | Max Flexion: {max_dev:6.2f}° | {status_str}")

    print(f"\nTotal Frozen Channels (max flexion < 20.0°): {len(frozen_channels)}")
    if frozen_channels:
        for fc in frozen_channels:
            print(f"  FROZEN CHANNEL: {fc}")

    return {
        "num_actions": len(actions),
        "forearm_channels": forearm_channels_stats,
        "frozen_channels": len(frozen_channels),
    }


def main():
    res_blend = audit_blend_file()
    res_glb = audit_glb_file()

    print("\n" + "=" * 80)
    print("FINAL CHALLENGER EMPIRICAL AUDIT SUMMARY")
    print("=" * 80)
    print(f"1. ForeArm Keyframe Bounds Violations (Blend):       {res_blend['forearm_violations']}")
    print(f"2. ForeArm Raw F-Curve Violations (Blend):           {res_blend['fcurve_violations']}")
    print(f"3. Shin Flexion / Anti-Valgus Violations (Blend):    {res_blend['shin_violations']}")
    print(f"4. GLB Frozen ForeArm Channels (< 20.0°):            {res_glb['frozen_channels']} / 8")
    print(f"5. Arm Volume Retention:                             [{res_blend['min_arm_ret']*100:.2f}%, {res_blend['max_arm_ret']*100:.2f}%] (>= 85%)")
    print(f"6. Leg Volume Retention:                             [{res_blend['min_leg_ret']*100:.2f}%, {res_blend['max_leg_ret']*100:.2f}%] (>= 85%)")
    print(f"7. Degenerate Faces:                                 {res_blend['degenerate_faces']}")
    print(f"8. Coordinate Anomalies:                             {res_blend['coordinate_anomalies']}")
    print(f"9. Minimum Skirt Clearance:                          {res_blend['min_clearance_mm']:.2f} mm (>= 15.0 mm)")
    print(f"10. Skirt Pitch Violations:                          {res_blend['pitch_violations']}")

    all_passed = (
        res_blend['forearm_violations'] == 0 and
        res_blend['fcurve_violations'] == 0 and
        res_blend['shin_violations'] == 0 and
        res_glb['frozen_channels'] == 0 and
        res_blend['min_arm_ret'] >= 0.85 and
        res_blend['min_leg_ret'] >= 0.85 and
        res_blend['degenerate_faces'] == 0 and
        res_blend['coordinate_anomalies'] == 0 and
        res_blend['min_clearance_mm'] >= 15.0 and
        res_blend['pitch_violations'] == 0
    )

    if all_passed:
        print("\n>>> EMPIRICAL VERDICT: ALL ADVERSARIAL CHECKS PASSED [VERDICT: APPROVE] <<<")
        sys.exit(0)
    else:
        print("\n>>> EMPIRICAL VERDICT: VIOLATIONS DETECTED [VERDICT: REQUEST_CHANGES] <<<")
        sys.exit(1)


if __name__ == "__main__":
    main()
