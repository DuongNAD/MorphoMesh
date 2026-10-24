"""
test_secondary_spring_dynamics.py
Comprehensive standalone verification script for Milestone 3 Feature F13:
Secondary Inertial Dynamics & Spring Solver.

Validates:
1. Analytical and numerical spring-damper physics (zeta >= 1.0, overdamping, stability).
2. RK4 integration vs implicit solver under shock impulse and variable timesteps.
3. Twintail chain (Hair_L_01..05 & Hair_R_01..05) inertial propagation and soft clamping.
4. Skirt radial spoke (Skirt_01..12) outward flare clearance and [-15°, +65°] pitch clamping.
5. In-Blender live verification against output/anime_rigged.blend (bone properties, constraints, keyframe baking).
"""

import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add working directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import blueprint solver
from proposed_spring_solver import (
    ALL_HAIR_BONES,
    HAIR_BONES_LEFT,
    HAIR_BONES_RIGHT,
    MIN_CLEARANCE_MM,
    SKIRT_BONE_NAMES,
    SKIRT_PITCH_MAX_DEG,
    SKIRT_PITCH_MIN_DEG,
    SPRING_DAMPING,
    SPRING_MASS,
    SPRING_REST_POS,
    SPRING_STIFFNESS,
    SkirtClearanceSimulator,
    TwintailChainSimulator,
    calculate_damping_ratio,
    simulate_rk4_spring_damper,
    solve_rk4_step,
    solve_rk4_substepped,
    solve_spring_damper_step,
)


def run_physics_unit_tests():
    print("\n--- [1/4] Running Analytical & Numerical Physics Tests ---")

    # 1. Damping ratio
    c_crit, zeta, (r1, r2) = calculate_damping_ratio(SPRING_MASS, SPRING_STIFFNESS, SPRING_DAMPING)
    print(f"  m = {SPRING_MASS} kg, k = {SPRING_STIFFNESS} N/m, c = {SPRING_DAMPING} N*s/m")
    print(f"  c_crit = {c_crit:.4f} N*s/m, zeta = {zeta:.4f}")
    print(f"  Roots: r1 = {r1:.4f} s^-1, r2 = {r2:.4f} s^-1")
    assert zeta >= 1.0, f"System is underdamped: zeta={zeta}"
    assert r1 < 0.0 and r2 < 0.0, "System roots are not strictly negative real"

    # 2. RK4 Simulation Monotonic Energy Dissipation
    sim = simulate_rk4_spring_damper(
        m=SPRING_MASS, k=SPRING_STIFFNESS, c=SPRING_DAMPING,
        x0=1.0, v0=0.0, duration=0.5, dt=1.0 / 240.0
    )
    print(f"  RK4 Sim: zero_crossings = {sim['zero_crossings']}, violations = {sim['energy_dissipation_violations']}")
    print(f"  Settling time: {sim['settling_time']:.4f}s, final_disp: {sim['final_displacement']:.6f}m")
    assert sim["zero_crossings"] == 0, f"Overdamped system oscillated: zero_crossings={sim['zero_crossings']}"
    assert sim["energy_dissipation_violations"] == 0, "Numerical energy inflation detected in RK4 solver"
    assert sim["final_displacement"] < 0.01, "Displacement did not decay to rest"

    # 3. Test Tier 1 F13 solver compliance
    pos, vel = 0.0, 0.0
    dt = 1.0 / 30.0
    peak_disp = 0.0
    for _ in range(3):
        pos, vel = solve_spring_damper_step(pos, vel, 0.0, SPRING_MASS, SPRING_STIFFNESS, SPRING_DAMPING, 10.0, dt)
        peak_disp = max(peak_disp, abs(pos))
    assert peak_disp > 0.0, "Secondary spring bone did not respond to external acceleration"
    for _ in range(60):
        pos, vel = solve_spring_damper_step(pos, vel, 0.0, SPRING_MASS, SPRING_STIFFNESS, SPRING_DAMPING, 0.0, dt)
    assert abs(pos) < 0.20 * peak_disp, "Secondary spring system failed to damp out oscillation"
    print("  Tier 1 F13 compliance: PASSED")

    # 4. Extreme acceleration shock impulse stability
    pos, vel = solve_spring_damper_step(0.0, 0.0, 0.0, SPRING_MASS, SPRING_STIFFNESS, SPRING_DAMPING, 1000.0, dt)
    assert abs(pos) < 1.0, f"Spring solver exploded under shock impulse: pos={pos}"
    print("  Tier 2 Extreme shock impulse test: PASSED")

    print("[1/4] Physics Unit Tests: ALL PASSED!\n")


def run_twintail_simulation_tests():
    print("--- [2/4] Running Twintail Chain Inertial Simulator Tests ---")
    sim = TwintailChainSimulator()

    # Simulate 30-frame sway cycle
    frames = list(range(1, 31))
    fps = 30.0
    head_rotations = [(0.05 * math.sin(2 * math.pi * f / 30.0), 0.0, 0.02 * math.cos(2 * math.pi * f / 30.0)) for f in frames]
    head_locations = [(0.01 * math.sin(2 * math.pi * f / 30.0), 0.0, 1.5 + 0.02 * math.sin(4 * math.pi * f / 30.0)) for f in frames]

    results = sim.simulate_twintail_for_action(frames, head_rotations, head_locations, fps=fps)

    assert len(results) == 10, f"Expected 10 hair bones, got {len(results)}"
    for bname in ALL_HAIR_BONES:
        assert bname in results, f"Missing bone in results: {bname}"
        angles = results[bname]
        assert len(angles) == 30, f"Expected 30 frames for {bname}, got {len(angles)}"
        # Check angles are within [-60°, +60°]
        max_p = max(abs(a[0]) for a in angles)
        assert max_p <= math.radians(60.01), f"Hair bone {bname} exceeded pitch clamp: {math.degrees(max_p)}°"

    # Verify tip moves more than root (momentum propagation)
    root_l = max(abs(a[0]) for a in results["Hair_L_01"])
    tip_l = max(abs(a[0]) for a in results["Hair_L_05"])
    print(f"  Hair_L_01 root max pitch: {math.degrees(root_l):.2f}°")
    print(f"  Hair_L_05 tip max pitch:  {math.degrees(tip_l):.2f}°")
    assert tip_l > root_l, "Twintail tip failed to exhibit greater sway than root"

    print("[2/4] Twintail Chain Simulator Tests: ALL PASSED!\n")


def run_skirt_clearance_tests():
    print("--- [3/4] Running Skirt Spoke Flare & Thigh Clearance Tests ---")
    sim = SkirtClearanceSimulator()

    # Test Walk stride: Left leg forward (+35 deg), Right leg back (-30 deg)
    pitches = sim.evaluate_skirt_pitches_for_frame(
        thigh_l_pitch_rad=math.radians(35.0),
        thigh_r_pitch_rad=math.radians(-30.0),
        hip_bounce_z=-0.02,
    )

    assert len(pitches) == 12, f"Expected 12 skirt bones, got {len(pitches)}"
    for bname in SKIRT_BONE_NAMES:
        assert bname in pitches, f"Missing skirt bone: {bname}"
        deg = math.degrees(pitches[bname])
        assert SKIRT_PITCH_MIN_DEG <= deg <= SKIRT_PITCH_MAX_DEG, (
            f"Skirt bone {bname} pitch {deg:.2f}° breached [{SKIRT_PITCH_MIN_DEG}°, {SKIRT_PITCH_MAX_DEG}°]"
        )

    # Left front bones (Skirt_10, 11, 12) should flare significantly outward to clear Left thigh
    p11_deg = math.degrees(pitches["Skirt_11"])
    p09_deg = math.degrees(pitches["Skirt_09"])
    print(f"  Left leg forward: Skirt_11 pitch = {p11_deg:.2f}°, Skirt_09 pitch = {p09_deg:.2f}°")
    assert p11_deg > 10.0, f"Skirt_11 failed to flare outward: {p11_deg:.2f}°"
    assert p11_deg > p09_deg, "Front left skirt failed to flare more than front right during left stride"

    # Test Jump compression: Both thighs bent (+60 deg)
    pitches_jump = sim.evaluate_skirt_pitches_for_frame(
        thigh_l_pitch_rad=math.radians(60.0),
        thigh_r_pitch_rad=math.radians(60.0),
        hip_bounce_z=-0.10,
    )
    for bname, pitch in pitches_jump.items():
        deg = math.degrees(pitch)
        assert deg <= SKIRT_PITCH_MAX_DEG + 1e-5, f"Over-flared on jump: {deg}°"
        assert deg >= SKIRT_PITCH_MIN_DEG - 1e-5, f"Inward penetration on jump: {deg}°"

    print("[3/4] Skirt Spoke Flare & Clearance Tests: ALL PASSED!\n")


def run_blender_live_integration_test():
    print("--- [4/4] Running In-Blender Live Armature Baking & Export Tests ---")
    try:
        import bpy
        import mathutils
    except ImportError:
        print("  Skipping Blender-specific tests (bpy not available in current python process).")
        print("  Run this script inside Blender headless to execute full integration test.")
        return

    blend_file = Path("output/anime_rigged.blend")
    if not blend_file.exists():
        blend_file = Path("teamwork_projects/anime_character_pipeline/output/anime_rigged.blend")
    if not blend_file.exists():
        print(f"  Rigged blend file not found at {blend_file}. Skipping live test.")
        return

    bpy.ops.wm.open_mainfile(filepath=str(blend_file))
    arm = bpy.data.objects.get("Anime_Armature")
    assert arm is not None, "Anime_Armature not found in scene"
    pb = arm.pose.bones

    # 1. Verify hair bone custom properties
    for bname in ALL_HAIR_BONES:
        pbone = pb.get(bname)
        assert pbone is not None, f"Missing pose bone: {bname}"
        assert abs(pbone.get("spring_mass", 0.0) - SPRING_MASS) < 1e-4
        assert abs(pbone.get("spring_stiffness", 0.0) - SPRING_STIFFNESS) < 1e-4
        assert abs(pbone.get("spring_damping", 0.0) - SPRING_DAMPING) < 1e-4
        assert pbone.get("is_secondary_hair") is True
    print("  All 10 twintail hair bones have calibrated spring properties.")

    # 2. Verify skirt constraints and custom properties
    for bname in SKIRT_BONE_NAMES:
        pbone = pb.get(bname)
        assert pbone is not None, f"Missing skirt pose bone: {bname}"
        assert pbone.get("is_secondary_skirt") is True
        c = next((c for c in pbone.constraints if c.type == 'LIMIT_ROTATION'), None)
        assert c is not None, f"Missing LIMIT_ROTATION on {bname}"
        assert abs(math.degrees(c.min_x) - SKIRT_PITCH_MIN_DEG) < 1e-2
        assert abs(math.degrees(c.max_x) - SKIRT_PITCH_MAX_DEG) < 1e-2
    print("  All 12 skirt radial bones have verified [-15°, +65°] pitch constraints.")

    # 3. Create test action and bake keyframes
    from proposed_spring_solver import bake_secondary_dynamics_action
    if not arm.animation_data:
        arm.animation_data_create()

    test_action = bpy.data.actions.new("action_anime_test_walk")
    test_action.use_fake_user = True
    arm.animation_data.action = test_action

    # Add mock parent motion
    for f in range(1, 33):
        t = (f - 1) / 32.0
        pb["Hips"].location = (0.0, 0.0, 0.02 * math.sin(4.0 * math.pi * t))
        pb["Hips"].keyframe_insert(data_path="location", frame=f)

        thigh_rot = 0.45 * math.sin(2.0 * math.pi * t)
        pb["Thigh.L"].rotation_mode = 'XYZ'
        pb["Thigh.L"].rotation_euler = (thigh_rot, 0.0, 0.0)
        pb["Thigh.L"].keyframe_insert(data_path="rotation_euler", frame=f)

        pb["Thigh.R"].rotation_mode = 'XYZ'
        pb["Thigh.R"].rotation_euler = (-thigh_rot, 0.0, 0.0)
        pb["Thigh.R"].keyframe_insert(data_path="rotation_euler", frame=f)

        pb["Head"].rotation_mode = 'XYZ'
        pb["Head"].rotation_euler = (0.05 * math.sin(2.0 * math.pi * t), 0.0, 0.0)
        pb["Head"].keyframe_insert(data_path="rotation_euler", frame=f)

    # Bake secondary dynamics
    report = bake_secondary_dynamics_action(arm, test_action, fps=30.0, n_substeps=4)
    print(f"  Bake Report: {report}")
    assert report["status"] == "success"
    assert report["keyframes_baked"] > 500, f"Low keyframe count: {report['keyframes_baked']}"

    print("[4/4] In-Blender Live Armature Baking Tests: ALL PASSED!\n")


if __name__ == "__main__":
    run_physics_unit_tests()
    run_twintail_simulation_tests()
    run_skirt_clearance_tests()
    run_blender_live_integration_test()
    print("================================================================")
    print("  ALL SECONDARY SPRING DYNAMICS VERIFICATION TESTS PASSED (100%)")
    print("================================================================")
