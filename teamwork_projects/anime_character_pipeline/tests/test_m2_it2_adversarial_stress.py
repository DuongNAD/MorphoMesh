"""
tests/test_m2_it2_adversarial_stress.py
Milestone 2 Iteration 2 Adversarial Stress Test Suite.
Authored by m2_challenger_it2_2 (Empirical Challenger).

Empirical verification suite for:
1. 0% Thigh Weight Bleeding Audit: All 480 skirt vertices have exactly 0.000000 weight for Thigh.L & Thigh.R.
2. Leg High Kick Pose Test: Rotate Thigh.L by 90° (and bilateral extremes), verify skirt vertices experience exactly 0.000000m displacement (no sagittal tearing).
3. Skirt Pitch Clamping Limit Test: All 12 skirt radial spoke bones clamp evaluated rotation strictly within [-15.0°, +65.0°] across extreme rotation inputs.
4. Twintail Spring Chain Dynamic Stability Test: Unbroken bone chains to Head, calibrated parameters (m=0.2kg, k=150N/m, c=12N*s/m), and overdamped stability (zeta >= 1.0).
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import bpy
    from mathutils import Euler, Matrix, Quaternion, Vector
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    import pytest


# ==============================================================================
# 1. Pure Python Analytical & Numerical Dynamics Solvers
# ==============================================================================

def calculate_damping_ratio(m: float, k: float, c: float) -> Tuple[float, float, Tuple[float, float]]:
    """
    Computes critical damping coefficient, damping ratio, and characteristic roots.
    Returns: (c_critical, zeta, (r1, r2))
    """
    assert m > 0, "Mass must be positive"
    assert k > 0, "Stiffness must be positive"
    assert c >= 0, "Damping must be non-negative"

    c_critical = 2.0 * math.sqrt(m * k)
    zeta = c / c_critical

    discriminant = c * c - 4.0 * m * k
    if discriminant >= 0.0:
        sqrt_disc = math.sqrt(discriminant)
        r1 = (-c + sqrt_disc) / (2.0 * m)
        r2 = (-c - sqrt_disc) / (2.0 * m)
    else:
        alpha = -c / (2.0 * m)
        beta = math.sqrt(-discriminant) / (2.0 * m)
        r1 = alpha
        r2 = beta

    return c_critical, zeta, (r1, r2)


def simulate_rk4_spring_damper(
    m: float,
    k: float,
    c: float,
    x0: float,
    v0: float,
    duration: float = 1.0,
    dt: float = 1.0 / 240.0,
) -> Dict[str, Any]:
    """
    Simulates m*x'' + c*x' + k*x = 0 using 4th-order Runge-Kutta.
    Returns trajectory, energy history, and stability metrics.
    """
    def derivatives(x: float, v: float) -> Tuple[float, float]:
        dxdt = v
        dvdt = (-c * v - k * x) / m
        return dxdt, dvdt

    t = 0.0
    x = x0
    v = v0
    times = [t]
    positions = [x]
    velocities = [v]
    energies = [0.5 * m * v * v + 0.5 * k * x * x]

    steps = int(duration / dt)
    energy_dissipation_violations = 0
    zero_crossings = 0

    for _ in range(steps):
        k1_x, k1_v = derivatives(x, v)
        k2_x, k2_v = derivatives(x + 0.5 * dt * k1_x, v + 0.5 * dt * k1_v)
        k3_x, k3_v = derivatives(x + 0.5 * dt * k2_x, v + 0.5 * dt * k2_v)
        k4_x, k4_v = derivatives(x + dt * k3_x, v + dt * k3_v)

        new_x = x + (dt / 6.0) * (k1_x + 2.0 * k2_x + 2.0 * k3_x + k4_x)
        new_v = v + (dt / 6.0) * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v)

        t += dt
        new_e = 0.5 * m * new_v * new_v + 0.5 * k * new_x * new_x

        # Check for non-physical energy creation (numerical violation of dE/dt <= 0)
        if new_e > energies[-1] + 1e-9:
            energy_dissipation_violations += 1

        # Check for zero crossing if started from rest displacement
        if (x > 0.0 and new_x < -1e-6) or (x < 0.0 and new_x > 1e-6):
            zero_crossings += 1

        x = new_x
        v = new_v
        times.append(t)
        positions.append(x)
        velocities.append(v)
        energies.append(new_e)

    # Settling time (time after which |x(t)| <= 0.01 * |x0| or 1% max displacement)
    threshold = 0.01 * max(abs(p) for p in positions)
    settling_time = duration
    for ti, pi in reversed(list(zip(times, positions))):
        if abs(pi) > threshold:
            settling_time = ti
            break

    return {
        "final_position": positions[-1],
        "final_velocity": velocities[-1],
        "final_energy": energies[-1],
        "max_displacement": max(abs(p) for p in positions),
        "zero_crossings": zero_crossings,
        "energy_violations": energy_dissipation_violations,
        "settling_time": settling_time,
        "is_stable": (energy_dissipation_violations == 0) and (abs(positions[-1]) < threshold),
    }


# ==============================================================================
# 2. Live Blender Adversarial Audit Suite
# ==============================================================================

def run_live_it2_adversarial_suite(blend_path: Path) -> Dict[str, Any]:
    """
    Executes the complete adversarial stress suite on output/anime_rigged.blend:
    1. 0% Thigh Weight Bleeding Audit
    2. Leg High Kick Pose Displacement Test
    3. Skirt Pitch Clamping Limit Test
    4. Twintail Spring Chain Dynamic Stability Test
    """
    assert blend_path.exists(), f"Target blend file does not exist: {blend_path}"
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    arm_obj = bpy.data.objects.get("Anime_Armature")
    assert arm_obj is not None, "Anime_Armature object missing from scene"

    skirt_obj = bpy.data.objects.get("Anime_Skirt")
    assert skirt_obj is not None, "Anime_Skirt object missing from scene"

    pb = arm_obj.pose.bones
    depsgraph = bpy.context.evaluated_depsgraph_get()

    results: Dict[str, Any] = {}

    # --------------------------------------------------------------------------
    # AUDIT 1: 0% Thigh Weight Bleeding Audit
    # --------------------------------------------------------------------------
    num_skirt_verts = len(skirt_obj.data.vertices)
    skirt_vg_names = [vg.name for vg in skirt_obj.vertex_groups]
    prohibited_groups = [
        "Thigh.L", "Thigh.R", "Thigh_Twist.L", "Thigh_Twist.R",
        "Shin.L", "Shin.R", "Shin_Twist.L", "Shin_Twist.R",
        "Foot.L", "Foot.R", "Toe.L", "Toe.R", "Hips", "Spine", "Head"
    ]
    leaked_groups = [g for g in prohibited_groups if g in skirt_vg_names]

    verts_with_thigh_l_weight = 0
    verts_with_thigh_r_weight = 0
    verts_with_prohibited_weight = 0
    max_thigh_l_weight = 0.0
    max_thigh_r_weight = 0.0
    unnormalized_verts = 0
    max_norm_deviation = 0.0
    orphaned_verts = 0
    influence_counts: Dict[int, int] = {}

    for v in skirt_obj.data.vertices:
        w_map: Dict[str, float] = {}
        for g in v.groups:
            gname = skirt_obj.vertex_groups[g.group].name
            w_map[gname] = g.weight

        w_tl = w_map.get("Thigh.L", 0.0)
        w_tr = w_map.get("Thigh.R", 0.0)
        if w_tl > 1e-7:
            verts_with_thigh_l_weight += 1
            max_thigh_l_weight = max(max_thigh_l_weight, w_tl)
        if w_tr > 1e-7:
            verts_with_thigh_r_weight += 1
            max_thigh_r_weight = max(max_thigh_r_weight, w_tr)

        for pg in prohibited_groups:
            if w_map.get(pg, 0.0) > 1e-7:
                verts_with_prohibited_weight += 1

        active_weights = [w for w in w_map.values() if w > 1e-6]
        n_inf = len(active_weights)
        influence_counts[n_inf] = influence_counts.get(n_inf, 0) + 1

        if n_inf == 0:
            orphaned_verts += 1
        else:
            tot_w = sum(active_weights)
            dev = abs(tot_w - 1.0)
            max_norm_deviation = max(max_norm_deviation, dev)
            if dev > 1e-4:
                unnormalized_verts += 1

    expected_skirt_groups = [f"Skirt_{i:02d}" for i in range(1, 13)]
    skirt_groups_correct = sorted(skirt_vg_names) == sorted(expected_skirt_groups)

    audit_1_passed = (
        num_skirt_verts == 480
        and len(leaked_groups) == 0
        and verts_with_thigh_l_weight == 0
        and verts_with_thigh_r_weight == 0
        and verts_with_prohibited_weight == 0
        and max_thigh_l_weight == 0.0
        and max_thigh_r_weight == 0.0
        and orphaned_verts == 0
        and unnormalized_verts == 0
        and max_norm_deviation < 1e-5
        and skirt_groups_correct
    )

    results["thigh_weight_bleeding_audit"] = {
        "passed": audit_1_passed,
        "total_skirt_vertices": num_skirt_verts,
        "expected_vertices": 480,
        "skirt_vertex_groups": skirt_vg_names,
        "leaked_prohibited_groups": leaked_groups,
        "verts_with_thigh_l_weight": verts_with_thigh_l_weight,
        "verts_with_thigh_r_weight": verts_with_thigh_r_weight,
        "max_thigh_l_weight": max_thigh_l_weight,
        "max_thigh_r_weight": max_thigh_r_weight,
        "orphaned_vertices": orphaned_verts,
        "unnormalized_vertices": unnormalized_verts,
        "max_norm_deviation": max_norm_deviation,
        "influence_distribution": influence_counts,
    }

    # --------------------------------------------------------------------------
    # AUDIT 2: Leg High Kick Pose Test (Zero Sagittal Tearing)
    # --------------------------------------------------------------------------
    for pbone in pb:
        pbone.rotation_mode = 'QUATERNION'
        pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        pbone.location = Vector((0.0, 0.0, 0.0))
        pbone.scale = Vector((1.0, 1.0, 1.0))
    bpy.context.view_layer.update()
    depsgraph.update()

    eval_skirt_rest = skirt_obj.evaluated_get(depsgraph).to_mesh()
    rest_world_coords = [skirt_obj.matrix_world @ v.co.copy() for v in eval_skirt_rest.vertices]
    skirt_obj.to_mesh_clear()

    leg_pose_trials: List[Dict[str, Any]] = []

    adversarial_poses = [
        ("Thigh.L Forward Sagittal High Kick +90°", [("Thigh.L", Vector((1.0, 0.0, 0.0)), 90.0)]),
        ("Thigh.L Sagittal Backward Kick -90°", [("Thigh.L", Vector((1.0, 0.0, 0.0)), -90.0)]),
        ("Thigh.L Extreme Sagittal Flexion +120°", [("Thigh.L", Vector((1.0, 0.0, 0.0)), 120.0)]),
        ("Thigh.L Lateral Abduction / Side Split +90°", [("Thigh.L", Vector((0.0, 0.0, 1.0)), 90.0)]),
        ("Thigh.R Forward Sagittal High Kick +90°", [("Thigh.R", Vector((1.0, 0.0, 0.0)), 90.0)]),
        ("Thigh.R Sagittal Backward Kick -90°", [("Thigh.R", Vector((1.0, 0.0, 0.0)), -90.0)]),
        (
            "Bilateral Sagittal Split & Knee Flexion",
            [
                ("Thigh.L", Vector((1.0, 0.0, 0.0)), 90.0),
                ("Thigh.R", Vector((1.0, 0.0, 0.0)), -90.0),
                ("Shin.L", Vector((1.0, 0.0, 0.0)), 120.0),
                ("Shin.R", Vector((1.0, 0.0, 0.0)), 120.0),
            ],
        ),
        (
            "Thigh Twist Extreme Rotation 180°",
            [
                ("Thigh_Twist.L", Vector((0.0, 1.0, 0.0)), 180.0),
                ("Thigh_Twist.R", Vector((0.0, 1.0, 0.0)), 180.0),
            ],
        ),
    ]

    for pose_name, rotations in adversarial_poses:
        for pbone in pb:
            pbone.rotation_mode = 'QUATERNION'
            pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))

        for bname, axis, deg in rotations:
            pbone = pb.get(bname)
            if pbone:
                pbone.rotation_quaternion = Quaternion(axis, math.radians(deg))

        bpy.context.view_layer.update()
        depsgraph.update()

        eval_skirt = skirt_obj.evaluated_get(depsgraph).to_mesh()
        posed_world_coords = [skirt_obj.matrix_world @ v.co.copy() for v in eval_skirt.vertices]
        skirt_obj.to_mesh_clear()

        displacements = [
            (p - r).length for p, r in zip(posed_world_coords, rest_world_coords)
        ]
        max_disp = max(displacements)
        avg_disp = sum(displacements) / len(displacements)
        torn_verts = sum(1 for d in displacements if d > 1e-6)

        passed_trial = (max_disp < 1e-6) and (torn_verts == 0)
        leg_pose_trials.append({
            "pose_name": pose_name,
            "max_displacement_m": max_disp,
            "avg_displacement_m": avg_disp,
            "torn_vertices": torn_verts,
            "passed": passed_trial,
        })

    for pbone in pb:
        pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
    bpy.context.view_layer.update()
    depsgraph.update()

    audit_2_passed = all(t["passed"] for t in leg_pose_trials)
    results["leg_high_kick_pose_test"] = {
        "passed": audit_2_passed,
        "trials": leg_pose_trials,
        "zero_displacement_confirmed": audit_2_passed,
    }

    # --------------------------------------------------------------------------
    # AUDIT 3: Skirt Pitch Clamping Limit Test
    # --------------------------------------------------------------------------
    skirt_bone_names = [f"Skirt_{i:02d}" for i in range(1, 13)]
    skirt_clamping_results: Dict[str, Any] = {}
    all_bones_clamped = True

    test_input_pitch_angles = [
        -180.0, -120.0, -90.0, -45.0, -30.0, -20.0, -15.1, -15.0, -14.9,
        0.0, 30.0, 45.0, 64.9, 65.0, 65.1, 90.0, 120.0, 180.0
    ]

    for bname in skirt_bone_names:
        pbone = pb.get(bname)
        assert pbone is not None, f"Missing skirt spoke bone: {bname}"
        data_bone = arm_obj.data.bones.get(bname)
        assert data_bone is not None, f"Missing data bone: {bname}"
        rest_mat = data_bone.matrix_local.copy()

        c = pbone.constraints.get("Skirt_Pitch_Clamp")
        assert c is not None, f"Missing Skirt_Pitch_Clamp on {bname}"
        assert c.type == 'LIMIT_ROTATION', f"Invalid constraint type on {bname}: {c.type}"
        assert c.owner_space == 'LOCAL', f"Invalid owner space on {bname}: {c.owner_space}"
        assert c.use_limit_x, f"use_limit_x is False on {bname}"
        assert abs(math.degrees(c.min_x) - (-15.0)) < 1e-4, f"Invalid min_x on {bname}: {math.degrees(c.min_x)}"
        assert abs(math.degrees(c.max_x) - 65.0) < 1e-4, f"Invalid max_x on {bname}: {math.degrees(c.max_x)}"

        pbone.rotation_mode = 'XYZ'
        bone_angle_evals = []
        bone_pass = True

        for angle_deg in test_input_pitch_angles:
            pbone.rotation_euler = Euler((math.radians(angle_deg), 0.0, 0.0), 'XYZ')
            bpy.context.view_layer.update()
            depsgraph.update()

            eval_arm = arm_obj.evaluated_get(depsgraph)
            eval_pb = eval_arm.pose.bones.get(bname)

            delta_mat = rest_mat.inverted() @ eval_pb.matrix
            eval_pitch_deg = math.degrees(delta_mat.to_euler().x)

            is_clamped = (-15.0001 <= eval_pitch_deg <= 65.0001)
            if abs(abs(angle_deg) - 180.0) < 1e-4:
                matches_expected = (abs(eval_pitch_deg - 65.0) < 0.01 or abs(eval_pitch_deg - (-15.0)) < 0.01)
                expected_pitch_deg = 65.0 if abs(eval_pitch_deg - 65.0) < 0.01 else -15.0
            else:
                expected_pitch_deg = max(-15.0, min(65.0, angle_deg))
                matches_expected = abs(eval_pitch_deg - expected_pitch_deg) < 0.01

            if not (is_clamped and matches_expected):
                bone_pass = False
                all_bones_clamped = False

            bone_angle_evals.append({
                "input_deg": angle_deg,
                "eval_deg": eval_pitch_deg,
                "expected_deg": expected_pitch_deg,
                "clamped": is_clamped,
            })

        pbone.rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
        bpy.context.view_layer.update()

        skirt_clamping_results[bname] = {
            "passed": bone_pass,
            "min_eval_deg": min(a["eval_deg"] for a in bone_angle_evals),
            "max_eval_deg": max(a["eval_deg"] for a in bone_angle_evals),
            "sample_sweeps": bone_angle_evals,
        }

    # Collective Skirt Rotation Extreme Test (All 12 simultaneously flexed to +90° and -60°)
    for bname in skirt_bone_names:
        pb[bname].rotation_mode = 'XYZ'
        pb[bname].rotation_euler = Euler((math.radians(90.0), 0.0, 0.0), 'XYZ')
    bpy.context.view_layer.update()
    depsgraph.update()

    eval_arm = arm_obj.evaluated_get(depsgraph)
    collective_90_clamped = all(
        abs(math.degrees((arm_obj.data.bones[bn].matrix_local.inverted() @ eval_arm.pose.bones[bn].matrix).to_euler().x) - 65.0) < 0.01
        for bn in skirt_bone_names
    )

    for bname in skirt_bone_names:
        pb[bname].rotation_euler = Euler((math.radians(-60.0), 0.0, 0.0), 'XYZ')
    bpy.context.view_layer.update()
    depsgraph.update()

    eval_arm = arm_obj.evaluated_get(depsgraph)
    collective_neg60_clamped = all(
        abs(math.degrees((arm_obj.data.bones[bn].matrix_local.inverted() @ eval_arm.pose.bones[bn].matrix).to_euler().x) - (-15.0)) < 0.01
        for bn in skirt_bone_names
    )

    for bname in skirt_bone_names:
        pb[bname].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
    bpy.context.view_layer.update()
    depsgraph.update()

    audit_3_passed = all_bones_clamped and collective_90_clamped and collective_neg60_clamped

    results["skirt_pitch_clamping_test"] = {
        "passed": audit_3_passed,
        "collective_plus90_clamped_to_65": collective_90_clamped,
        "collective_neg60_clamped_to_neg15": collective_neg60_clamped,
        "bone_results": skirt_clamping_results,
    }

    # --------------------------------------------------------------------------
    # AUDIT 4: Twintail Spring Chain Dynamic Stability Test
    # --------------------------------------------------------------------------
    left_hair_bones = [f"Hair_L_{i:02d}" for i in range(1, 6)]
    right_hair_bones = [f"Hair_R_{i:02d}" for i in range(1, 6)]
    all_10_hair = left_hair_bones + right_hair_bones

    head_data_bone = arm_obj.data.bones.get("Head")
    assert head_data_bone is not None, "Head bone missing from armature"

    chain_topology_valid = True
    hierarchy_map: Dict[str, str] = {}

    expected_left_parents = ["Head"] + left_hair_bones[:-1]
    for bname, exp_parent in zip(left_hair_bones, expected_left_parents):
        b = arm_obj.data.bones.get(bname)
        assert b is not None, f"Missing bone {bname}"
        actual_parent = b.parent.name if b.parent else None
        hierarchy_map[bname] = str(actual_parent)
        if actual_parent != exp_parent:
            chain_topology_valid = False

    expected_right_parents = ["Head"] + right_hair_bones[:-1]
    for bname, exp_parent in zip(right_hair_bones, expected_right_parents):
        b = arm_obj.data.bones.get(bname)
        assert b is not None, f"Missing bone {bname}"
        actual_parent = b.parent.name if b.parent else None
        hierarchy_map[bname] = str(actual_parent)
        if actual_parent != exp_parent:
            chain_topology_valid = False

    param_checks: Dict[str, Dict[str, Any]] = {}
    all_params_calibrated = True

    for bname in all_10_hair:
        pbone = pb.get(bname)
        assert pbone is not None, f"Missing pose bone: {bname}"

        m_val = pbone.get("spring_mass")
        k_val = pbone.get("spring_stiffness")
        c_val = pbone.get("spring_damping")
        x_rest = pbone.get("spring_rest_pos")
        is_sec = pbone.get("is_secondary_hair")

        valid_m = (m_val is not None) and (abs(float(m_val) - 0.20) < 1e-5)
        valid_k = (k_val is not None) and (abs(float(k_val) - 150.0) < 1e-5)
        valid_c = (c_val is not None) and (abs(float(c_val) - 12.0) < 1e-5)
        valid_rest = (x_rest is not None) and (abs(float(x_rest) - 0.0) < 1e-5)
        valid_flag = (is_sec is True)

        bone_valid = valid_m and valid_k and valid_c and valid_rest and valid_flag
        if not bone_valid:
            all_params_calibrated = False

        param_checks[bname] = {
            "mass": m_val,
            "stiffness": k_val,
            "damping": c_val,
            "rest_pos": x_rest,
            "is_secondary": is_sec,
            "calibrated": bone_valid,
        }

    m_phys = 0.20
    k_phys = 150.0
    c_phys = 12.0
    c_crit, zeta, (r1, r2) = calculate_damping_ratio(m_phys, k_phys, c_phys)
    is_overdamped = (zeta >= 1.0) and (r1 < 0.0) and (r2 < 0.0)

    sim_results = simulate_rk4_spring_damper(
        m=m_phys, k=k_phys, c=c_phys, x0=1.0, v0=0.0, duration=0.6
    )

    audit_4_passed = (
        chain_topology_valid
        and all_params_calibrated
        and is_overdamped
        and sim_results["is_stable"]
        and sim_results["zero_crossings"] == 0
    )

    results["twintail_spring_chain_test"] = {
        "passed": audit_4_passed,
        "chain_topology_valid": chain_topology_valid,
        "hierarchy_map": hierarchy_map,
        "all_params_calibrated": all_params_calibrated,
        "parameters": {
            "mass_kg": m_phys,
            "stiffness_npm": k_phys,
            "damping_ns_per_m": c_phys,
            "critical_damping": c_crit,
            "damping_ratio_zeta": zeta,
            "roots": (r1, r2),
            "is_overdamped": is_overdamped,
        },
        "rk4_simulation": sim_results,
    }

    # --------------------------------------------------------------------------
    # OVERALL VERDICT
    # --------------------------------------------------------------------------
    overall_pass = (
        results["thigh_weight_bleeding_audit"]["passed"]
        and results["leg_high_kick_pose_test"]["passed"]
        and results["skirt_pitch_clamping_test"]["passed"]
        and results["twintail_spring_chain_test"]["passed"]
    )
    results["overall_verdict"] = "APPROVE" if overall_pass else "REQUEST_CHANGES"

    return results


# ==============================================================================
# 3. Pytest Integration Test Cases
# ==============================================================================

def test_pure_python_damping_ratio_and_roots():
    """Unit test: analytical proof that m=0.2, k=150, c=12 is overdamped (zeta >= 1.0)."""
    c_crit, zeta, (r1, r2) = calculate_damping_ratio(m=0.20, k=150.0, c=12.0)
    assert abs(c_crit - 10.954451) < 1e-4
    assert abs(zeta - 1.095445) < 1e-4
    assert zeta >= 1.0, "Damping ratio must be >= 1.0 (overdamped)"
    assert r1 < 0.0 and r2 < 0.0, "Real roots must be strictly negative"
    assert abs(r1 - (-17.752551)) < 1e-4
    assert abs(r2 - (-42.247449)) < 1e-4


def test_pure_python_rk4_shock_stability():
    """Unit test: numerical proof that system experiences monotonic energy dissipation and 0 overshoot."""
    sim = simulate_rk4_spring_damper(m=0.20, k=150.0, c=12.0, x0=1.0, v0=0.0, duration=0.5)
    assert sim["is_stable"], "Spring damper system must be numerically stable"
    assert sim["zero_crossings"] == 0, "Overdamped system must exhibit zero zero-crossings"
    assert sim["energy_violations"] == 0, "Damping must strictly dissipate energy"
    assert sim["settling_time"] <= 0.35, f"Settling time {sim['settling_time']}s must be <= 0.35s"


def test_pure_python_skirt_pitch_clamp_formula():
    """Unit test: skirt pitch clamping boundary values [-15.0°, +65.0°]."""
    from anime_pipeline.rigging.secondary_bones import clamp_skirt_pitch
    assert clamp_skirt_pitch(-45.0) == -15.0
    assert clamp_skirt_pitch(-15.0) == -15.0
    assert clamp_skirt_pitch(0.0) == 0.0
    assert clamp_skirt_pitch(30.0) == 30.0
    assert clamp_skirt_pitch(65.0) == 65.0
    assert clamp_skirt_pitch(90.0) == 65.0
    assert clamp_skirt_pitch(180.0) == 65.0


def test_live_blender_m2_it2_adversarial_stress_suite():
    """
    Live Blender adversarial test runner.
    Spawns headless Blender 4.5 against output/anime_rigged.blend.
    """
    blend_path = Path("output/anime_rigged.blend").resolve()
    assert blend_path.exists(), f"Missing output/anime_rigged.blend at {blend_path}"

    if HAS_BPY:
        results = run_live_it2_adversarial_suite(blend_path)
        assert results["overall_verdict"] == "APPROVE"
    else:
        blender_exe = Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")
        assert blender_exe.exists(), f"Blender executable not found at {blender_exe}"

        cmd = [
            str(blender_exe),
            "--background",
            "--python-expr",
            f"import sys; sys.path.insert(0, '.'); from tests.test_m2_it2_adversarial_stress import run_live_it2_adversarial_suite; from pathlib import Path; res = run_live_it2_adversarial_suite(Path('{blend_path.as_posix()}')); import pprint; pprint.pprint(res); v = res['overall_verdict']; assert v == 'APPROVE', 'Adversarial test failed with verdict: ' + str(v)",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        print(proc.stdout)
        print(proc.stderr)
        assert proc.returncode == 0, f"Blender test failed with returncode {proc.returncode}:\n{proc.stderr}"


if __name__ == "__main__":
    if HAS_BPY:
        blend_path = Path("output/anime_rigged.blend").resolve()
        res = run_live_it2_adversarial_suite(blend_path)
        import pprint
        print("=" * 80)
        print("MILESTONE 2 ITERATION 2 ADVERSARIAL STRESS AUDIT REPORT")
        print("=" * 80)
        pprint.pprint(res)
        print("=" * 80)
        print("OVERALL VERDICT:", res["overall_verdict"])
        print("=" * 80)
    else:
        print("Run using Blender: blender.exe --background output/anime_rigged.blend --python tests/test_m2_it2_adversarial_stress.py")
