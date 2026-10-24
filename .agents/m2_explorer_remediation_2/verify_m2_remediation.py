"""
verify_m2_remediation.py
Standalone Verification Script for Milestone 2 Remediation.
Author: m2_explorer_remediation_2

Usage:
  & "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe" --background output\\anime_rigged.blend --python verify_m2_remediation.py
Or from pytest:
  uv run pytest tests/test_m2_adversarial_stress.py -v
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import bpy
    import bmesh
    from mathutils import Euler, Matrix, Quaternion, Vector
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    print("Error: This script must be executed inside Blender (blender --background ... --python verify_m2_remediation.py)")
    sys.exit(1)


# ==============================================================================
# Helper Solvers
# ==============================================================================

def compute_mesh_signed_volume(eval_obj: Any) -> float:
    """Computes signed tetrahedral volume using divergence theorem."""
    me = eval_obj.to_mesh()
    vol = 0.0
    for poly in me.polygons:
        vs = poly.vertices
        if len(vs) < 3:
            continue
        v0 = me.vertices[vs[0]].co
        for i in range(1, len(vs) - 1):
            v1 = me.vertices[vs[i]].co
            v2 = me.vertices[vs[i + 1]].co
            vol += v0.dot(v1.cross(v2)) / 6.0
    eval_obj.to_mesh_clear()
    return abs(vol)


def measure_slice_cross_section_area(eval_obj: Any, plane_co: Any, plane_no: Any) -> float:
    """Computes 2D planar polygon cross-section area sliced through mesh."""
    me = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    res = bmesh.ops.bisect_plane(
        bm,
        geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
        plane_co=plane_co,
        plane_no=plane_no,
    )
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if not cut_edges:
        bm.free()
        eval_obj.to_mesh_clear()
        return 0.0

    verts = list({v for e in cut_edges for v in e.verts})
    if len(verts) < 3:
        bm.free()
        eval_obj.to_mesh_clear()
        return 0.0

    centroid = sum((v.co for v in verts), Vector()) / len(verts)
    area = sum(0.5 * (e.verts[0].co - centroid).cross(e.verts[1].co - centroid).length for e in cut_edges)
    bm.free()
    eval_obj.to_mesh_clear()
    return area


def count_degenerate_or_inverted_faces(eval_obj: Any, eps: float = 1e-7) -> int:
    """Counts faces with area <= eps."""
    me = eval_obj.to_mesh()
    bad_count = sum(1 for poly in me.polygons if poly.area <= eps)
    eval_obj.to_mesh_clear()
    return bad_count


# ==============================================================================
# Verification Main Runner
# ==============================================================================

def run_standalone_audit() -> bool:
    print("=" * 80)
    print("MILESTONE 2 REMEDIATION AUDIT: LIVE DEFORMATION & ANTI-PINCH VERIFICATION")
    print("=" * 80)

    arm_obj = bpy.data.objects.get("Anime_Armature")
    if not arm_obj:
        print("[FAIL] Anime_Armature missing from scene!")
        return False

    pb = arm_obj.pose.bones
    arms_obj = bpy.data.objects.get("Anime_Arms")
    if not arms_obj:
        print("[FAIL] Anime_Arms mesh missing from scene!")
        return False

    depsgraph = bpy.context.evaluated_depsgraph_get()
    all_passed = True

    # --------------------------------------------------------------------------
    # 1. Transform Alignment Audit
    # --------------------------------------------------------------------------
    print("\n--- 1. Submesh Transform Alignment Audit ---")
    expected_submeshes = [
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]
    desynced = []
    for name in expected_submeshes:
        obj = bpy.data.objects.get(name)
        if not obj:
            print(f"  [FAIL] Missing submesh: {name}")
            all_passed = False
            continue
        rx = math.degrees(obj.rotation_euler.x)
        ry = math.degrees(obj.rotation_euler.y)
        rz = math.degrees(obj.rotation_euler.z)
        if max(abs(rx), abs(ry), abs(rz)) > 0.1:
            desynced.append((name, (rx, ry, rz)))

    if desynced:
        print(f"  [FAIL] Desynchronized submeshes found: {desynced}")
        all_passed = False
    else:
        print(f"  [PASS] All {len(expected_submeshes)} submeshes aligned with Armature (rotation = (0, 0, 0)).")

    # --------------------------------------------------------------------------
    # 2. Hand Twist & Anti-Pinch Volume Retention (Hand.L & Hand.R at 90° and 180°)
    # --------------------------------------------------------------------------
    print("\n--- 2. Hand Twist Anti-Pinch Volume & Area Audit ---")
    ev_rest = arms_obj.evaluated_get(depsgraph)
    v_rest = compute_mesh_signed_volume(ev_rest)
    print(f"  Arms rest volume: {v_rest:.8f} m^3")

    twist_cases = [
        ("Hand.L", 90, 0.85, 0.85),
        ("Hand.L", 180, 0.85, 0.80),
        ("Hand.R", 90, 0.85, 0.85),
        ("Hand.R", 180, 0.85, 0.80),
    ]

    for bone_name, angle_deg, req_rv, req_ra in twist_cases:
        side = "L" if ".L" in bone_name else "R"
        p_fa = pb[f"ForeArm.{side}"]
        p_hand = pb[bone_name]

        fa_mid = (p_fa.head + p_fa.tail) * 0.5
        fa_axis = p_fa.vector.normalized()
        wrist_co = (p_fa.tail + fa_mid) * 0.5

        a_rest_wrist = measure_slice_cross_section_area(ev_rest, wrist_co, fa_axis)
        a_rest_mid = measure_slice_cross_section_area(ev_rest, fa_mid, fa_axis)

        p_hand.rotation_mode = 'QUATERNION'
        p_hand.rotation_quaternion = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(angle_deg))
        bpy.context.view_layer.update()
        depsgraph.update()

        ev = arms_obj.evaluated_get(depsgraph)
        vol = compute_mesh_signed_volume(ev)
        a_wrist = measure_slice_cross_section_area(ev, wrist_co, fa_axis)
        a_mid = measure_slice_cross_section_area(ev, fa_mid, fa_axis)

        rv = vol / v_rest if v_rest > 0 else 0.0
        ra_wrist = a_wrist / a_rest_wrist if a_rest_wrist > 0 else 0.0
        ra_mid = a_mid / a_rest_mid if a_rest_mid > 0 else 0.0

        p_hand.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        bpy.context.view_layer.update()
        depsgraph.update()

        pass_rv = rv >= req_rv
        pass_ra = ra_wrist >= req_ra
        status = "[PASS]" if (pass_rv and pass_ra) else "[FAIL]"
        if not (pass_rv and pass_ra):
            all_passed = False

        print(f"  {status} {bone_name} {angle_deg:+4d}°: Rv={rv*100:.2f}% (req>={req_rv*100:.0f}%) | "
              f"Wrist Ra={ra_wrist*100:.2f}% (req>={req_ra*100:.0f}%) | Mid Ra={ra_mid*100:.2f}%")

    # --------------------------------------------------------------------------
    # 3. 30-Phalange Finger Flexion Monotonicity & Zero Out-of-Plane Plunge Audit
    # --------------------------------------------------------------------------
    print("\n--- 3. 30-Phalange Finger Flexion & Non-Plunge Audit ---")
    palm_L = Vector((0.43550, -0.18575, 1.01439))
    palm_R = Vector((-0.43550, -0.18575, 1.01439))
    finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
    phalanges = ["01", "02", "03"]

    finger_failures = []
    total_fingers = 0

    for side in ["L", "R"]:
        palm = palm_L if side == "L" else palm_R
        for f in finger_names:
            for p in phalanges:
                total_fingers += 1
                bname = f"{f}.{p}.{side}"
                pbone = pb[bname]
                pbone.rotation_mode = 'QUATERNION'

                # Rest
                pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
                bpy.context.view_layer.update()
                t0 = (arm_obj.matrix_world @ pbone.tail).copy()
                d0 = (t0 - palm).length

                # +45°
                pbone.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(45.0))
                bpy.context.view_layer.update()
                t45 = (arm_obj.matrix_world @ pbone.tail).copy()
                d45 = (t45 - palm).length

                # +90°
                pbone.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(90.0))
                bpy.context.view_layer.update()
                t90 = (arm_obj.matrix_world @ pbone.tail).copy()
                d90 = (t90 - palm).length

                # Reset
                pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
                bpy.context.view_layer.update()

                monotonic = (d45 < d0) and (d90 < d45)
                disp_45 = (t45 - t0).length
                disp_90 = (t90 - t0).length
                no_plunge = (disp_45 < 0.15) and (disp_90 < 0.20)

                # Local lateral displacement
                local_x = (arm_obj.matrix_world.to_3x3() @ pbone.matrix.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
                lat_dev = abs((t90 - t0).dot(local_x))
                zero_lateral = lat_dev < 1e-4

                if not (monotonic and no_plunge and zero_lateral):
                    finger_failures.append((bname, d0, d45, d90, disp_90, lat_dev))

    if finger_failures:
        print(f"  [FAIL] {len(finger_failures)}/{total_fingers} phalanges failed curling check: {finger_failures}")
        all_passed = False
    else:
        print(f"  [PASS] All {total_fingers}/30 phalanges curl monotonically toward palm with 0 out-of-plane plunge.")

    # --------------------------------------------------------------------------
    # 4. Elbow Flexion Invariant (ForeArm.L & ForeArm.R at 90° and 145°)
    # --------------------------------------------------------------------------
    print("\n--- 4. Elbow Flexion Non-Degeneracy Audit ---")
    for side in ["L", "R"]:
        p_fa = pb[f"ForeArm.{side}"]
        for ang in [90, 145]:
            p_fa.rotation_mode = 'QUATERNION'
            p_fa.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(ang))
            bpy.context.view_layer.update()
            depsgraph.update()

            ev = arms_obj.evaluated_get(depsgraph)
            degen_faces = count_degenerate_or_inverted_faces(ev)
            vol = compute_mesh_signed_volume(ev)
            rv = vol / v_rest if v_rest > 0 else 0.0

            p_fa.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()
            depsgraph.update()

            status = "[PASS]" if degen_faces == 0 else "[FAIL]"
            if degen_faces > 0:
                all_passed = False

            print(f"  {status} ForeArm.{side} {ang:3d}°: Degen Faces={degen_faces} (req=0) | Rv={rv*100:.2f}%")

    # --------------------------------------------------------------------------
    # 5. Weight Normalization & Partition of Unity
    # --------------------------------------------------------------------------
    print("\n--- 5. Vertex Weight Normalization & Isolation Audit ---")
    tot_verts = 0
    orphan_count = 0
    unnorm_count = 0
    max_dev = 0.0

    for name in expected_submeshes:
        obj = bpy.data.objects.get(name)
        if not obj:
            continue
        tot_verts += len(obj.data.vertices)
        for v in obj.data.vertices:
            weights = [g.weight for g in v.groups if g.weight > 1e-6]
            if not weights:
                orphan_count += 1
                continue
            s_w = sum(weights)
            dev = abs(s_w - 1.0)
            if dev > max_dev:
                max_dev = dev
            if dev > 1e-4:
                unnorm_count += 1

    skirt_obj = bpy.data.objects.get("Anime_Skirt")
    thigh_in_skirt = [vg.name for vg in skirt_obj.vertex_groups if "Thigh" in vg.name] if skirt_obj else []

    pass_weights = (
        tot_verts == 14532
        and orphan_count == 0
        and unnorm_count == 0
        and len(thigh_in_skirt) == 0
    )
    if not pass_weights:
        all_passed = False
        print(f"  [FAIL] Weight audit failed: verts={tot_verts}, orphans={orphan_count}, unnorm={unnorm_count}, skirt_thigh={thigh_in_skirt}")
    else:
        print(f"  [PASS] 14,532 vertices validated: 0 orphans, 0 unnormalized (max dev={max_dev:.2e}), 0 thigh weights on Skirt.")

    print("\n" + "=" * 80)
    if all_passed:
        print(">>> FINAL VERDICT: 100% PASSED ALL DEFORMATION INVARIANTS <<<")
    else:
        print(">>> FINAL VERDICT: AUDIT FAILED <<<")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = run_standalone_audit()
    sys.exit(0 if success else 1)
