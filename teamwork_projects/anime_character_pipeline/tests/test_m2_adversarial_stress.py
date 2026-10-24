"""
tests/test_m2_adversarial_stress.py
Milestone 2 Empirical Adversarial Stress Test Suite.
Authored by m2_challenger_anime_1 (Empirical Challenger).

Tests against output/anime_rigged.blend and the rigging codebase:
1. Anti-pinch & DQS volume retention stress test (Hand.L/Hand.R at 90? and 180? local Y twist).
2. Elbow flexion stress test (ForeArm.L/ForeArm.R flexed to 90? and 145?).
3. 30-Phalange finger curling & non-skew stress test (+45? and +90? local X curl).
4. 14,532-Vertex weight normalization & modular isolation stress test (zero NaN/Inf, zero orphans, sum=1.000000).
5. Submesh-Armature transform alignment audit (exposes 90? X rotation desynchronization).
"""

from __future__ import annotations

import math
import subprocess
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
    import pytest


# ==============================================================================
# Helper Geometric & Volumetric Solvers (Blender Runtime)
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


def count_degenerate_or_inverted_faces(eval_obj: Any) -> int:
    """Counts faces with area <= 1e-7."""
    me = eval_obj.to_mesh()
    bad_count = sum(1 for poly in me.polygons if poly.area <= 1e-7)
    eval_obj.to_mesh_clear()
    return bad_count


# ==============================================================================
# Live Headless Blender Adversarial Test Suite
# ==============================================================================

def run_live_adversarial_suite(blend_path: Path) -> Dict[str, Any]:
    """Executes all adversarial stress audits against the live blend file."""
    assert blend_path.exists(), f"Target blend file does not exist: {blend_path}"
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    arm_obj = bpy.data.objects.get("Anime_Armature")
    assert arm_obj is not None, "Anime_Armature object missing from scene"
    pb = arm_obj.pose.bones

    report: Dict[str, Any] = {
        "transform_audit": {},
        "weight_audit": {},
        "finger_audit": {},
        "wrist_twist_audit": {},
        "elbow_flexion_audit": {},
    }

    # --------------------------------------------------------------------------
    # Audit 1: Transform Alignment & Synchronization Audit
    # --------------------------------------------------------------------------
    expected_submeshes = [
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]
    desynced_meshes = []
    for name in expected_submeshes:
        obj = bpy.data.objects.get(name)
        assert obj is not None, f"Submesh {name} missing"
        # Check if mesh object has non-zero rotation relative to Armature (which has (0, 0, 0))
        rot_x_deg = math.degrees(obj.rotation_euler.x)
        if abs(rot_x_deg) > 1.0:
            desynced_meshes.append((name, rot_x_deg))

    report["transform_audit"] = {
        "armature_rotation": tuple(round(math.degrees(a), 2) for a in arm_obj.rotation_euler),
        "desynced_meshes": desynced_meshes,
        "is_aligned": len(desynced_meshes) == 0,
    }

    # --------------------------------------------------------------------------
    # Audit 2: Vertex Weight Normalization across all 14,532 vertices
    # --------------------------------------------------------------------------
    total_verts = 0
    nan_inf_count = 0
    orphan_count = 0
    unnormalized_count = 0
    max_influence_violations = 0
    max_weight_dev = 0.0

    for name in expected_submeshes:
        obj = bpy.data.objects[name]
        verts = obj.data.vertices
        total_verts += len(verts)
        for v in verts:
            weights = [g.weight for g in v.groups if g.weight > 1e-6]
            for w in weights:
                if math.isnan(w) or math.isinf(w):
                    nan_inf_count += 1
            if len(weights) == 0:
                orphan_count += 1
                continue
            tot_w = sum(weights)
            dev = abs(tot_w - 1.0)
            if dev > max_weight_dev:
                max_weight_dev = dev
            if dev > 1e-4:
                unnormalized_count += 1
            if len(weights) > 4:
                max_influence_violations += 1

    # Check Anime_Skirt zero thigh weights invariant
    skirt_obj = bpy.data.objects["Anime_Skirt"]
    prohibited_skirt_groups = [vg.name for vg in skirt_obj.vertex_groups if "Thigh" in vg.name]

    report["weight_audit"] = {
        "total_vertices": total_verts,
        "expected_vertices": 14532,
        "nan_inf_count": nan_inf_count,
        "orphan_count": orphan_count,
        "unnormalized_count": unnormalized_count,
        "max_influence_violations": max_influence_violations,
        "max_weight_deviation": max_weight_dev,
        "prohibited_skirt_groups": prohibited_skirt_groups,
        "passed": (
            total_verts == 14532
            and nan_inf_count == 0
            and orphan_count == 0
            and unnormalized_count == 0
            and max_influence_violations == 0
            and len(prohibited_skirt_groups) == 0
        ),
    }

    # --------------------------------------------------------------------------
    # Audit 3: 30-Phalange Finger Curling Stress Test
    # --------------------------------------------------------------------------
    finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
    phalanges = ["01", "02", "03"]
    palm_L = Vector((0.43550, -0.18575, 1.01439))
    palm_R = Vector((-0.43550, -0.18575, 1.01439))

    finger_results = []
    for side in ["L", "R"]:
        palm = palm_L if side == "L" else palm_R
        for f in finger_names:
            for p in phalanges:
                bname = f"{f}.{p}.{side}"
                pbone = pb[bname]
                pbone.rotation_mode = 'QUATERNION'
                pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
                bpy.context.view_layer.update()
                d_rest = (arm_obj.matrix_world @ pbone.tail - palm).length

                pbone.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(45.0))
                bpy.context.view_layer.update()
                d_45 = (arm_obj.matrix_world @ pbone.tail - palm).length

                pbone.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(90.0))
                bpy.context.view_layer.update()
                d_90 = (arm_obj.matrix_world @ pbone.tail - palm).length

                pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
                bpy.context.view_layer.update()

                monotonic = (d_45 < d_rest) and (d_90 < d_45)
                finger_results.append({
                    "bone": bname,
                    "d_rest": d_rest,
                    "d_45": d_45,
                    "d_90": d_90,
                    "curls_toward_palm": monotonic,
                })

    report["finger_audit"] = {
        "total_fingers": len(finger_results),
        "passing_fingers": sum(1 for r in finger_results if r["curls_toward_palm"]),
        "failed_fingers": [r["bone"] for r in finger_results if not r["curls_toward_palm"]],
        "passed": all(r["curls_toward_palm"] for r in finger_results),
    }

    # --------------------------------------------------------------------------
    # Audit 4: Anti-Pinch & DQS Volume Retention Stress Test
    # --------------------------------------------------------------------------
    arms_mesh = bpy.data.objects["Anime_Arms"]
    arm_mod = [m for m in arms_mesh.modifiers if m.type == 'ARMATURE'][0]
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # Step A: Measure in AS-DELIVERED state
    ev_rest_asis = arms_mesh.evaluated_get(depsgraph)
    v_rest_asis = compute_mesh_signed_volume(ev_rest_asis)

    pb["Hand.L"].rotation_mode = 'QUATERNION'
    pb["Hand.L"].rotation_quaternion = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(180.0))
    bpy.context.view_layer.update()
    depsgraph.update()

    ev_180_asis = arms_mesh.evaluated_get(depsgraph)
    v_180_asis = compute_mesh_signed_volume(ev_180_asis)
    rv_180_asis = v_180_asis / v_rest_asis if v_rest_asis > 0 else 0.0

    pb["Hand.L"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
    bpy.context.view_layer.update()

    # Step B: Measure with SYNCHRONIZED transforms (obj.rotation_euler = (0, 0, 0))
    arms_mesh.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    depsgraph.update()

    ev_rest_sync = arms_mesh.evaluated_get(depsgraph)
    v_rest_sync = compute_mesh_signed_volume(ev_rest_sync)

    fa_mid = (pb["ForeArm.L"].head + pb["ForeArm.L"].tail) * 0.5
    fa_axis = pb["ForeArm.L"].vector.normalized()
    wrist_co = (pb["ForeArm.L"].tail + fa_mid) * 0.5

    a_rest_mid = measure_slice_cross_section_area(ev_rest_sync, fa_mid, fa_axis)
    a_rest_wrist = measure_slice_cross_section_area(ev_rest_sync, wrist_co, fa_axis)

    dqs_angles_results = []
    for ang in [90, 180, -90, -180]:
        pb["Hand.L"].rotation_mode = 'QUATERNION'
        pb["Hand.L"].rotation_quaternion = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(ang))
        bpy.context.view_layer.update()
        depsgraph.update()

        ev = arms_mesh.evaluated_get(depsgraph)
        vol = compute_mesh_signed_volume(ev)
        a_mid = measure_slice_cross_section_area(ev, fa_mid, fa_axis)
        a_wrist = measure_slice_cross_section_area(ev, wrist_co, fa_axis)

        rv = vol / v_rest_sync if v_rest_sync > 0 else 0.0
        ra_mid = a_mid / a_rest_mid if a_rest_mid > 0 else 0.0
        ra_wrist = a_wrist / a_rest_wrist if a_rest_wrist > 0 else 0.0

        dqs_angles_results.append({
            "angle": ang,
            "volume_retention_rv": rv,
            "mid_area_retention_ra": ra_mid,
            "wrist_area_retention_ra": ra_wrist,
            "meets_85_pct_volume": rv >= 0.85,
        })

    # Step C: Contrast Oracle against LBS (Linear Blend Skinning without twist)
    arm_mod.use_deform_preserve_volume = False
    c_twist = pb["ForeArm_Twist.L"].constraints[0]
    orig_inf = c_twist.influence
    c_twist.influence = 0.0

    pb["Hand.L"].rotation_quaternion = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(90.0))
    bpy.context.view_layer.update()
    depsgraph.update()
    ev_lbs_90 = arms_mesh.evaluated_get(depsgraph)
    a_lbs_90 = measure_slice_cross_section_area(ev_lbs_90, wrist_co, fa_axis)

    pb["Hand.L"].rotation_quaternion = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(180.0))
    bpy.context.view_layer.update()
    depsgraph.update()
    ev_lbs_180 = arms_mesh.evaluated_get(depsgraph)
    a_lbs_180 = measure_slice_cross_section_area(ev_lbs_180, wrist_co, fa_axis)

    # Restore
    arm_mod.use_deform_preserve_volume = True
    c_twist.influence = orig_inf
    pb["Hand.L"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
    bpy.context.view_layer.update()

    report["wrist_twist_audit"] = {
        "as_delivered": {
            "v_rest": v_rest_asis,
            "v_180": v_180_asis,
            "rv_180": rv_180_asis,
            "passed_85_pct": rv_180_asis >= 0.85,
        },
        "synchronized_transforms": {
            "v_rest": v_rest_sync,
            "a_rest_mid": a_rest_mid,
            "a_rest_wrist": a_rest_wrist,
            "angles": dqs_angles_results,
            "passed_85_pct": all(r["meets_85_pct_volume"] for r in dqs_angles_results),
        },
        "lbs_contrast": {
            "a_lbs_90_pct": (a_lbs_90 / a_rest_wrist) * 100 if a_rest_wrist > 0 else 0,
            "a_lbs_180_pct": (a_lbs_180 / a_rest_wrist) * 100 if a_rest_wrist > 0 else 0,
        },
    }

    # --------------------------------------------------------------------------
    # Audit 5: Elbow Flexion Stress Test
    # --------------------------------------------------------------------------
    elbow_results = []
    for side in ["L", "R"]:
        pb_fa = pb[f"ForeArm.{side}"]
        for ang in [90, 145]:
            pb_fa.rotation_mode = 'QUATERNION'
            pb_fa.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(ang))
            bpy.context.view_layer.update()
            depsgraph.update()

            ev = arms_mesh.evaluated_get(depsgraph)
            bad_faces = count_degenerate_or_inverted_faces(ev)
            vol = compute_mesh_signed_volume(ev)

            pb_fa.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()

            elbow_results.append({
                "joint": f"ForeArm.{side}",
                "flexion_angle": ang,
                "volume": vol,
                "degenerate_faces": bad_faces,
                "passed": bad_faces == 0,
            })

    report["elbow_flexion_audit"] = {
        "trials": elbow_results,
        "passed": all(r["passed"] for r in elbow_results),
    }

    return report


# ==============================================================================
# Pytest Integration Test Cases
# ==============================================================================

def test_pure_python_weight_normalization_algorithm():
    """Unit test for VertexWeightTable normalization and isolation in pure Python."""
    from anime_pipeline.rigging.skinning_dqs import VertexWeightTable

    table = VertexWeightTable("Anime_Skirt", num_vertices=3)
    table.add_weight(0, "Skirt_01", 0.6)
    table.add_weight(0, "Skirt_02", 0.4)
    # Attempt prohibited thigh weight
    table.add_weight(0, "Thigh.L", 0.8)
    table.prune_and_normalize()

    # Thigh.L must be purged
    assert "Thigh.L" not in table.weights[0]
    # Sum must be 1.000000
    assert abs(sum(table.weights[0].values()) - 1.0) < 1e-5


def test_pure_python_c1_harmonic_cosine_falloff():
    """Unit test for C1 harmonic cosine falloff continuity and boundaries."""
    from anime_pipeline.rigging.skinning_dqs import harmonic_cosine_falloff

    assert abs(harmonic_cosine_falloff(0.0) - 1.0) < 1e-9
    assert abs(harmonic_cosine_falloff(1.0) - 0.0) < 1e-9
    assert abs(harmonic_cosine_falloff(0.5) - 0.5) < 1e-9


def test_live_blender_rig_adversarial_stress_suite():
    """
    Empirical adversarial stress test running inside or spawning headless Blender.
    Executes all 5 adversarial audits against output/anime_rigged.blend.
    """
    blend_path = Path("output/anime_rigged.blend").resolve()
    assert blend_path.exists(), f"Missing output/anime_rigged.blend at {blend_path}"

    if HAS_BPY:
        results = run_live_adversarial_suite(blend_path)
    else:
        blender_exe = Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")
        assert blender_exe.exists(), f"Blender executable not found at {blender_exe}"

        cmd = [
            str(blender_exe),
            "--background",
            "--python-expr",
            f"import sys; sys.path.insert(0, '.'); from tests.test_m2_adversarial_stress import run_live_adversarial_suite; from pathlib import Path; res = run_live_adversarial_suite(Path('{blend_path.as_posix()}')); import pprint; pprint.pprint(res); assert res['weight_audit']['passed']; assert res['finger_audit']['passed']; assert res['elbow_flexion_audit']['passed']; assert res['wrist_twist_audit']['synchronized_transforms']['passed_85_pct']",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        print(proc.stdout)
        print(proc.stderr)
        assert proc.returncode == 0, f"Blender adversarial test failed with code {proc.returncode}:\n{proc.stderr}"


if __name__ == "__main__":
    if HAS_BPY:
        blend_path = Path("output/anime_rigged.blend").resolve()
        res = run_live_adversarial_suite(blend_path)
        import pprint
        print("=" * 80)
        print("M2 ADVERSARIAL STRESS TEST AUDIT REPORT")
        print("=" * 80)
        pprint.pprint(res)
    else:
        print("Run this script using Blender: blender.exe --background output/anime_rigged.blend --python tests/test_m2_adversarial_stress.py")
