"""
Independent Empirical Adversarial Stress Test Suite — Milestone 4 Iteration 4
Target: Yu Nian An (余念安) Master Digital Human Asset (Blender 4.5.4 LTS)
Asset: output/yu_nian_an/Yu_Nian_An_Master.blend

Adversarial Audits:
1. Deep BVH Occlusion Audit:
   - Independent BVH raycasting from Camera_Portrait_85mm and normal-dot containment
     on all 6 hair layers (Hair_Hime_Bangs, Hair_Eyebrows, Hair_Eyelashes,
     Hair_Scalp_Crown, Hair_Hime_Sidelocks, Hair_Back_Cascade).
   - Verifies 0 vertices occluded / buried on bangs, eyebrows, eyelashes, crown, sidelocks!
2. Garment Signed Clearance:
   - Signed distance between body mesh and Mesh_Dress_Bodice, Mesh_Dress_WaistSash,
     Mesh_Dress_PleatedSkirt.
   - Verifies min clearance >= +4.0mm with 0 vertex penetrations and 0 BVH face overlaps.
3. Live Rigging & Props Kinematics:
   - Rotates all 10 finger DEF bones by 45° and 60°.
   - Verifies dynamic deformation of marionette strings (displacement > 3mm)
     and translation of butterflies (translation > 3mm).
   - Verifies string proximal roots snapped to finger bone tails (gap < 2mm).
   - Verifies butterfly 3D separation (pairwise >= 50mm, non-origin, Z > 0.8m).
4. Master Asset Integrity:
   - 163 DEF bones, 52 ARKit FACS blendshapes with active deltas, 10 PBR materials,
     100% pure quad body mesh.
"""

import sys
import os
import math
import subprocess

try:
    import bpy
    import bmesh
    import mathutils
    from bpy_extras.object_utils import world_to_camera_view
except ImportError:
    bpy = None
    bmesh = None
    mathutils = None
    world_to_camera_view = None

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
MASTER_BLEND = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"


def run_empirical_challenger_audit():
    print("=" * 80)
    print("EMPIRICAL CHALLENGER ADVERSARIAL STRESS AUDIT — BLENDER 4.5.4 LTS")
    print(f"Target Blend: {MASTER_BLEND}")
    print("=" * 80)

    if not bpy:
        print("ERROR: bpy not loaded!")
        sys.exit(1)

    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    failures = []
    audit_stats = {}

    # --------------------------------------------------------------------------
    # 1. DEEP BVH OCCLUSION AUDIT (RAYCASTING & NORMAL-DOT CONTAINMENT)
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 1] DEEP BVH OCCLUSION & NORMAL-DOT CONTAINMENT AUDIT")
    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    assert body_obj is not None, "Yu_Nian_An_Body missing!"

    # Build BVH tree from body mesh in world space
    bm_body = bmesh.new()
    bm_body.from_mesh(body_obj.data)
    bm_body.transform(body_obj.matrix_world)
    body_bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

    cam_portrait = bpy.data.objects.get("Camera_Portrait_85mm")
    assert cam_portrait is not None, "Camera_Portrait_85mm missing!"
    cam_pos = cam_portrait.matrix_world.translation.copy()
    print(f"Portrait Camera Position: ({cam_pos.x:.4f}, {cam_pos.y:.4f}, {cam_pos.z:.4f})")

    hair_layers = [
        ("Hair_Hime_Bangs", True),
        ("Hair_Eyebrows", True),
        ("Hair_Eyelashes", True),
        ("Hair_Scalp_Crown", True),
        ("Hair_Hime_Sidelocks", True),
        ("Hair_Back_Cascade", False),  # Behind head; frontal camera raycast is occluded by head
    ]

    print(f"{'Hair Layer':<24} | {'Verts':<6} | {'Inside':<6} | {'RayOccluded':<11} | {'Outside %':<10} | {'Status'}")
    print("-" * 80)

    for h_name, require_zero_occlusion in hair_layers:
        h_obj = bpy.data.objects.get(h_name)
        if not h_obj or not h_obj.data or not hasattr(h_obj.data, "vertices"):
            failures.append(f"Hair object '{h_name}' missing or empty!")
            print(f"{h_name:<24} | MISSING OBJECT")
            continue

        verts = h_obj.data.vertices
        total = len(verts)
        inside_count = 0
        ray_occluded_count = 0

        for v in verts:
            v_world = h_obj.matrix_world @ v.co

            # Normal-dot containment check against body mesh
            nearest_co, normal, idx, dist = body_bvh.find_nearest(v_world)
            if nearest_co is not None and normal is not None:
                diff = v_world - nearest_co
                if diff.dot(normal) < -1e-5:
                    inside_count += 1

            # Independent BVH Raycasting from Camera_Portrait_85mm
            ray_dir = (v_world - cam_pos).normalized()
            ray_dist = (v_world - cam_pos).length
            # Cast ray from camera to vertex; check if body mesh blocks it
            hit_loc, hit_norm, hit_idx, hit_dist = body_bvh.ray_cast(cam_pos, ray_dir, ray_dist - 0.001)
            if hit_loc is not None and hit_dist < (ray_dist - 0.001):
                ray_occluded_count += 1

        pct_outside = ((total - inside_count) / total * 100.0) if total > 0 else 0.0
        status = "PASS"

        if require_zero_occlusion:
            if inside_count > 0:
                status = "FAIL (Buried)"
                failures.append(f"{h_name}: {inside_count}/{total} vertices buried inside body mesh (dot < 0)!")
            if ray_occluded_count > 0:
                status = "FAIL (Occluded)"
                failures.append(f"{h_name}: {ray_occluded_count}/{total} vertices occluded from Camera_Portrait_85mm!")
        else:
            # Back cascade: verify >= 95% exterior
            if pct_outside < 95.0:
                status = "FAIL (Low Outside %)"
                failures.append(f"{h_name}: Only {pct_outside:.1f}% outside skull (< 95.0%)!")

        print(f"{h_name:<24} | {total:<6} | {inside_count:<6} | {ray_occluded_count:<11} | {pct_outside:<9.1f}% | {status}")
        audit_stats[h_name] = {
            "total": total,
            "inside": inside_count,
            "ray_occluded": ray_occluded_count,
            "pct_outside": pct_outside,
        }

    # --------------------------------------------------------------------------
    # 2. GARMENT SIGNED CLEARANCE AUDIT
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 2] GARMENT SIGNED CLEARANCE AUDIT (>= +4.0mm, 0 PENETRATIONS)")
    garment_parts = [
        "Mesh_Dress_Bodice",
        "Mesh_Dress_WaistSash",
        "Mesh_Dress_PleatedSkirt",
    ]

    print(f"{'Garment Component':<24} | {'Verts':<6} | {'Min Dist':<11} | {'Avg Dist':<11} | {'Penetrations':<12} | {'Face Overlaps'}")
    print("-" * 80)

    for g_name in garment_parts:
        g_obj = bpy.data.objects.get(g_name)
        if not g_obj:
            failures.append(f"Garment object '{g_name}' missing!")
            print(f"{g_name:<24} | MISSING OBJECT")
            continue

        bm_g = bmesh.new()
        bm_g.from_mesh(g_obj.data)
        bm_g.transform(g_obj.matrix_world)
        g_bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_g)

        overlaps = body_bvh.overlap(g_bvh)
        bm_g.free()

        g_verts = [g_obj.matrix_world @ v.co for v in g_obj.data.vertices]
        signed_dists = []
        penetrations = 0
        min_clearance = float("inf")

        for v in g_verts:
            loc, normal, idx, dist = body_bvh.find_nearest(v)
            if loc is not None:
                offset = v - loc
                dot = offset.dot(normal)
                s_dist = dist if dot >= 0 else -dist
                signed_dists.append(s_dist)
                if s_dist < min_clearance:
                    min_clearance = s_dist
                if dot < -1e-6:
                    penetrations += 1

        avg_clearance = sum(signed_dists) / len(signed_dists) if signed_dists else 0.0
        min_mm = min_clearance * 1000.0
        avg_mm = avg_clearance * 1000.0
        overlap_count = len(overlaps)

        status_flag = "PASS"
        if min_mm < 4.0:
            status_flag = "FAIL (< 4.0mm)"
            failures.append(f"{g_name}: Min signed clearance {min_mm:+.2f}mm is less than +4.0mm requirement!")
        if penetrations > 0:
            status_flag = "FAIL (Penetrations)"
            failures.append(f"{g_name}: {penetrations} penetrating vertices detected!")
        if overlap_count > 0:
            status_flag = "FAIL (Overlaps)"
            failures.append(f"{g_name}: {overlap_count} BVH face overlaps detected with body mesh!")

        print(f"{g_name:<24} | {len(g_verts):<6} | {min_mm:+8.2f} mm | {avg_mm:+8.2f} mm | {penetrations:<12} | {overlap_count:<13} | {status_flag}")
        audit_stats[g_name] = {
            "min_clearance_mm": min_mm,
            "avg_clearance_mm": avg_mm,
            "penetrations": penetrations,
            "face_overlaps": overlap_count,
        }

    bm_body.free()

    # --------------------------------------------------------------------------
    # 3. LIVE RIGGING & PROPS KINEMATICS AUDIT (45° & 60° BONE ROTATIONS)
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 3] LIVE RIGGING & PROPS KINEMATICS AUDIT")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
    assert arm_obj is not None, "Armature missing!"
    assert strings_obj is not None, "Prop_Marionette_Strings missing!"

    butterflies = sorted(
        [o for o in bpy.data.objects if o.name.startswith("Prop_Butterfly_")],
        key=lambda x: x.name,
    )
    assert len(butterflies) == 10, f"Expected 10 butterflies, got {len(butterflies)}"

    finger_def_bones = [
        "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
        "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
    ]

    # Part 3a: String Proximal Root Snapping to Bone Tails
    print("\n  --- [3a] Proximal String Root to Bone Tail Alignment (< 2.0mm) ---")
    for i, b_name in enumerate(finger_def_bones):
        bone = arm_obj.data.bones.get(b_name)
        assert bone is not None, f"Bone {b_name} missing from armature data!"
        bone_tail_world = arm_obj.matrix_world @ bone.tail_local
        string_root_world = strings_obj.matrix_world @ strings_obj.data.vertices[i * 14].co
        gap_mm = (string_root_world - bone_tail_world).length * 1000.0
        print(f"  Cord {i:02d} -> {b_name:16}: root gap = {gap_mm:.4f} mm")
        if gap_mm >= 2.0:
            failures.append(f"Cord {i} proximal root gap {gap_mm:.2f}mm >= 2.0mm threshold from {b_name} tail!")

    # Part 3b: Butterfly 3D Spatial Separation & Non-Origin
    print("\n  --- [3b] Butterfly Spatial Separation (Non-Origin, Z > 0.8m, Separation >= 50mm) ---")
    bf_locs = [bf.matrix_world.translation.copy() for bf in butterflies]
    min_pair_dist = float("inf")
    closest_pair = None
    for i in range(len(bf_locs)):
        d_origin = bf_locs[i].length
        if d_origin < 0.1:
            failures.append(f"{butterflies[i].name} is at origin ({d_origin:.3f}m)!")
        if bf_locs[i].z <= 0.8:
            failures.append(f"{butterflies[i].name} Z={bf_locs[i].z:.3f}m <= 0.8m!")
        for j in range(i + 1, len(bf_locs)):
            d = (bf_locs[i] - bf_locs[j]).length
            if d < min_pair_dist:
                min_pair_dist = d
                closest_pair = (butterflies[i].name, butterflies[j].name)

    print(f"  Butterflies Count: {len(butterflies)} | Min Pairwise Separation: {min_pair_dist*1000.0:.2f} mm between {closest_pair[0]} & {closest_pair[1]}")
    if min_pair_dist < 0.050:
        failures.append(f"Butterflies minimum pairwise separation {min_pair_dist*1000.0:.2f}mm < 50.0mm!")

    # Part 3c: Live Kinematics Rotation Stress Test (45° and 60°)
    print("\n  --- [3c] Dynamic Deformation under 45° and 60° Finger DEF Rotations ---")
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()

    eval_s_base = strings_obj.evaluated_get(deps)
    m_s_base = eval_s_base.to_mesh()
    base_s_coords = [eval_s_base.matrix_world @ v.co for v in m_s_base.vertices]
    eval_s_base.to_mesh_clear()

    base_bf_locs = [bf.matrix_world.translation.copy() for bf in butterflies]

    for test_angle_deg in [45.0, 60.0]:
        print(f"\n  Testing Kinematic Rotations at {test_angle_deg}°:")
        print(f"  {'Bone':<18} | {'Angle':<6} | {'Max String Disp':<16} | {'Butterfly Disp':<16} | {'Status'}")
        print("  " + "-" * 70)

        for b_idx, b_name in enumerate(finger_def_bones):
            pb = arm_obj.pose.bones.get(b_name)
            assert pb is not None, f"Pose bone {b_name} missing!"

            orig_euler = pb.rotation_euler.copy()
            orig_mode = pb.rotation_mode

            # Apply test rotation in XYZ
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (
                math.radians(test_angle_deg),
                math.radians(test_angle_deg * 0.5),
                math.radians(test_angle_deg * 0.75),
            )
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()

            # Evaluate string mesh displacement
            eval_s_rot = strings_obj.evaluated_get(deps)
            m_s_rot = eval_s_rot.to_mesh()
            rot_s_coords = [eval_s_rot.matrix_world @ v.co for v in m_s_rot.vertices]
            eval_s_rot.to_mesh_clear()

            string_disp_mm = max((r - b).length for r, b in zip(rot_s_coords, base_s_coords)) * 1000.0

            # Evaluate butterfly translation
            target_bf = butterflies[b_idx % len(butterflies)]
            eval_bf = target_bf.evaluated_get(deps)
            m_bf = eval_bf.to_mesh()
            rot_bf_coords = [eval_bf.matrix_world @ v.co for v in m_bf.vertices]
            eval_bf.to_mesh_clear()

            # Measure butterfly vertex displacement
            bf_disp_mm = max((r - b).length for r, b in zip(rot_bf_coords, [target_bf.matrix_world @ v.co for v in target_bf.data.vertices])) * 1000.0

            # Restore original pose
            pb.rotation_euler = orig_euler
            pb.rotation_mode = orig_mode
            bpy.context.view_layer.update()

            status = "PASS"
            if string_disp_mm < 3.0:
                status = "FAIL (String Stiff)"
                failures.append(f"{b_name} at {test_angle_deg}° produced string displacement of only {string_disp_mm:.2f}mm (< 3.0mm)!")
            if bf_disp_mm < 3.0:
                status = "FAIL (Butterfly Fixed)"
                failures.append(f"{b_name} at {test_angle_deg}° produced butterfly displacement of only {bf_disp_mm:.2f}mm (< 3.0mm)!")

            print(f"  {b_name:<18} | {test_angle_deg:4.1f}° | {string_disp_mm:13.2f} mm | {bf_disp_mm:13.2f} mm | {status}")

    # --------------------------------------------------------------------------
    # 4. MASTER ASSET ESSENTIAL AUDIT
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 4] MASTER ASSET ESSENTIAL INTEGRITY AUDIT")
    def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")]
    print(f"  Armature DEF Bones Count: {len(def_bones)} / 163 required")
    if len(def_bones) != 163:
        failures.append(f"Armature has {len(def_bones)} DEF bones (expected 163)!")

    sk = body_obj.data.shape_keys
    arkit_keys = [k.name for k in sk.key_blocks if k.name != "Basis"] if sk else []
    print(f"  ARKit Shape Keys Count: {len(arkit_keys)} / 52 required")
    if len(arkit_keys) != 52:
        failures.append(f"Body has {len(arkit_keys)} ARKit shape keys (expected 52)!")

    # Check zero-delta shape keys
    basis_key = sk.key_blocks.get("Basis") if sk else None
    zero_delta_keys = []
    if basis_key:
        basis_cos = [v.co.copy() for v in basis_key.data]
        for kb_name in arkit_keys:
            kb = sk.key_blocks[kb_name]
            max_d = max((v.co - basis_cos[i]).length for i, v in enumerate(kb.data))
            if max_d < 1e-6:
                zero_delta_keys.append(kb_name)
    print(f"  Zero-Delta Shape Keys: {len(zero_delta_keys)}")
    if zero_delta_keys:
        failures.append(f"Found {len(zero_delta_keys)} zero-delta shape keys: {zero_delta_keys}")

    # Quads check
    quads = sum(1 for p in body_obj.data.polygons if len(p.vertices) == 4)
    quad_pct = quads / len(body_obj.data.polygons) * 100.0 if body_obj.data.polygons else 0.0
    print(f"  Body Topology: {quads}/{len(body_obj.data.polygons)} pure quads ({quad_pct:.1f}%)")
    if quad_pct < 100.0:
        failures.append(f"Body mesh quad ratio is {quad_pct:.2f}% (< 100.0%)!")

    # --------------------------------------------------------------------------
    # SUMMARY & FINAL VERDICT
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("EMPIRICAL CHALLENGER VERDICT & DEFECT LOG")
    print("=" * 80)
    if failures:
        print(f"FAILURES DETECTED ({len(failures)}):")
        for idx, f in enumerate(failures, 1):
            print(f"  [{idx}] {f}")
        print("\n>>> FINAL EMPIRICAL VERDICT: CHALLENGE <<<")
        return False
    else:
        print("ALL ADVERSARIAL STRESS TESTS PASSED WITH ZERO VIOLATIONS!")
        print(">>> FINAL EMPIRICAL VERDICT: CONFIRM (ROBUST) <<<")
        return True


# ==============================================================================
# Pytest Harness Wrapper
# ==============================================================================
def test_empirical_adversarial_audit_in_blender():
    """Execute the empirical challenger stress audit inside live Blender 4.5.4 LTS."""
    assert os.path.isfile(BLENDER_EXE), f"Blender 4.5 not found at {BLENDER_EXE}"
    assert os.path.isfile(MASTER_BLEND), f"Master blend not found at {MASTER_BLEND}"

    cmd = [
        BLENDER_EXE,
        "--background",
        MASTER_BLEND,
        "--python",
        os.path.abspath(__file__),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    print("\n[BLENDER AUDIT STDOUT]:\n" + proc.stdout)
    if proc.stderr:
        print("\n[BLENDER AUDIT STDERR]:\n" + proc.stderr)

    assert proc.returncode == 0, f"Blender audit exited with code {proc.returncode}"
    assert "FINAL EMPIRICAL VERDICT: CONFIRM (ROBUST)" in proc.stdout, "Audit did not yield CONFIRM (ROBUST) verdict!"


if __name__ == "__main__":
    success = run_empirical_challenger_audit()
    sys.exit(0 if success else 2)
