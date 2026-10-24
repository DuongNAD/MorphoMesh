"""
Milestone 3: Animation Pipeline, Action Library, Retargeting Limits & Secondary Dynamics Test Suite
File: tests/test_m3_animation_pipeline.py

Comprehensive validation of:
- Feature F11: Programmatic Anime Action Library & Keyframes (Idle Cute, Wave Hello, Walk Cycle, Jump Cheer)
- Feature F12: Joint Rotational Clamping & Retargeting Limits (Elbows, Knees, Feet, Toes, Cross-Standard Aliasing)
- Feature F13: Secondary Inertial Physics & Spring Solver (Overdamped RK4, Twintails, Skirt Clearance & Clamping)
- Milestone 3 Deliverable Assets: anime_animated.blend and anime_animated.glb
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Tuple

import pytest

import anime_pipeline.animation as anim
from anime_pipeline.animation import (
    ACTION_METADATA_REGISTRY,
    ACTION_NAMES,
    ALL_HAIR_BONES,
    BONE_MAPPING_TABLES,
    HAIR_BONES_LEFT,
    HAIR_BONES_RIGHT,
    HINGE_LIMITS,
    MIN_CLEARANCE_MM,
    PHYSIOLOGICAL_ROTATION_LIMITS,
    SKIRT_BONE_COUNT,
    SKIRT_BONE_NAMES,
    SKIRT_PITCH_MAX_DEG,
    SKIRT_PITCH_MIN_DEG,
    SPRING_DAMPING,
    SPRING_MASS,
    SPRING_REST_POS,
    SPRING_STIFFNESS,
    TWINTAIL_SEGMENT_COUNT,
    ActionDefinition,
    ActionMetadata,
    LimitSpec,
    SecondarySpringDynamicsSolver,
    SkirtClearanceSimulator,
    TwintailChainSimulator,
    calculate_damping_ratio,
    clamp_angle,
    clamp_joint_angle_deg,
    clamp_pose_rotations,
    clamp_single_bone_rotation,
    euler_xyz_to_quat,
    get_canonical_action_definitions,
    get_standard_bone_name,
    normalize_quaternion,
    quat_to_euler_xyz,
    resolve_to_canonical,
    simulate_rk4_spring_damper,
    solve_rk4_step,
    solve_rk4_substepped,
    solve_spring_damper_step,
)


# ==============================================================================
# 1. Feature F11: Action Library & Keyframe Integrity Tests
# ==============================================================================

class TestFeatureF11ActionLibrary:
    """Validates the 4 distinct anime actions, curves, timing, and aesthetic parameters."""

    def test_canonical_actions_presence_and_metadata(self):
        definitions = get_canonical_action_definitions()
        assert len(definitions) == 4

        for act_name in ACTION_NAMES:
            assert act_name in definitions, f"Missing action definition: {act_name}"
            act = definitions[act_name]
            assert act.name == act_name
            assert act.frame_end > act.frame_start
            assert act.fps == 30
            assert act.total_frames >= 32
            assert act.duration_seconds > 1.0
            assert len(act.curves) > 0

    def test_action_metadata_registry(self):
        for act_name in ACTION_NAMES:
            assert act_name in ACTION_METADATA_REGISTRY
            meta = ACTION_METADATA_REGISTRY[act_name]
            assert isinstance(meta, ActionMetadata)
            assert meta.name == act_name
            assert meta.fps == 30
            assert len(meta.description) > 10

        assert ACTION_METADATA_REGISTRY["action_anime_idle_cute"].is_looping is True
        assert ACTION_METADATA_REGISTRY["action_anime_idle_cute"].total_frames == 90

        assert ACTION_METADATA_REGISTRY["action_anime_wave_greeting"].is_looping is False
        assert ACTION_METADATA_REGISTRY["action_anime_wave_greeting"].total_frames == 120

        assert ACTION_METADATA_REGISTRY["action_anime_walk_cycle"].is_looping is True
        assert ACTION_METADATA_REGISTRY["action_anime_walk_cycle"].total_frames == 32

        assert ACTION_METADATA_REGISTRY["action_anime_jump_cheer"].is_looping is False
        assert ACTION_METADATA_REGISTRY["action_anime_jump_cheer"].total_frames == 75

    def test_idle_cute_contrapposto_and_bobbing(self):
        act = get_canonical_action_definitions()["action_anime_idle_cute"]
        assert "Hips.loc_x" in act.curves
        assert "Hips.loc_z" in act.curves
        assert "Spine1.rot_x" in act.curves
        assert "Head.rot_z" in act.curves

        # Contrapposto weight shift of +0.035m
        for f, val in act.curves["Hips.loc_x"]:
            assert abs(val - 0.035) < 1e-4

        # Micro-bob amplitude within +/-0.006m
        for f, val in act.curves["Hips.loc_z"]:
            assert abs(val) <= 0.006 + 1e-4

    def test_walk_cycle_timing_and_bounce(self):
        act = get_canonical_action_definitions()["action_anime_walk_cycle"]
        bounce_pts = {f: val for f, val in act.curves["Hips.loc_z"]}

        # Down phase at frames 4 & 20 should be -0.032m
        assert abs(bounce_pts[4] - (-0.032)) < 1e-3
        assert abs(bounce_pts[20] - (-0.032)) < 1e-3

        # Passing phase at frames 8 & 24 should be +0.025m
        assert abs(bounce_pts[8] - 0.025) < 1e-3
        assert abs(bounce_pts[24] - 0.025) < 1e-3

        # Forearm tuck angle (bent 35-45 deg)
        for f, val in act.curves["ForeArm.R.rot_x"]:
            assert val >= 35.0 and val <= 45.0

    def test_jump_cheer_kinematic_extremes(self):
        act = get_canonical_action_definitions()["action_anime_jump_cheer"]
        pts = {f: val for f, val in act.curves["Hips.loc_z"]}

        # Squash at frame 16: -0.14m
        assert abs(pts[16] - (-0.14)) < 1e-3
        # Apex leap at frame 35: +0.35m
        assert abs(pts[35] - 0.35) < 1e-3
        # Landing cushion at frame 50: -0.10m
        assert abs(pts[50] - (-0.10)) < 1e-3


# ==============================================================================
# 2. Feature F12: Retargeting Limits & Clamping Tests
# ==============================================================================

class TestFeatureF12RetargetingLimits:
    """Validates physiological angle bounds, mathematical clamping, and cross-standard aliasing."""

    def test_angle_clamping_math(self):
        assert clamp_angle(0.5, 0.0, 1.0) == 0.5
        assert clamp_angle(-0.2, 0.0, 1.0) == 0.0
        assert clamp_angle(1.5, 0.0, 1.0) == 1.0

        # Elbow hinge [0, 145 deg]
        assert clamp_joint_angle_deg(150.0, 0.0, 145.0) == 145.0
        assert clamp_joint_angle_deg(-10.0, 0.0, 145.0) == 0.0
        assert clamp_joint_angle_deg(90.0, 0.0, 145.0) == 90.0

        # Knee hinge [0, 140 deg]
        assert clamp_joint_angle_deg(160.0, 0.0, 140.0) == 140.0
        assert clamp_joint_angle_deg(-15.0, 0.0, 140.0) == 0.0
        assert clamp_joint_angle_deg(70.0, 0.0, 140.0) == 70.0

    def test_quaternion_euler_roundtrip(self):
        test_angles = [
            (0.0, 0.0, 0.0),
            (math.radians(30.0), 0.0, 0.0),
            (0.0, math.radians(-25.0), 0.0),
            (0.0, 0.0, math.radians(45.0)),
            (math.radians(45.0), math.radians(-20.0), math.radians(15.0)),
        ]
        for ex, ey, ez in test_angles:
            q = euler_xyz_to_quat(ex, ey, ez)
            rx, ry, rz = quat_to_euler_xyz(*q)
            assert abs(rx - ex) < 1e-4
            assert abs(ry - ey) < 1e-4
            assert abs(rz - ez) < 1e-4

    def test_cross_standard_bone_resolution(self):
        # VRM
        assert resolve_to_canonical("leftLowerArm") == "ForeArm.L"
        assert resolve_to_canonical("rightLowerArm") == "ForeArm.R"
        assert resolve_to_canonical("leftLowerLeg") == "Shin.L"
        assert resolve_to_canonical("rightLowerLeg") == "Shin.R"
        assert resolve_to_canonical("leftFoot") == "Foot.L"
        assert resolve_to_canonical("leftToes") == "Toe.L"

        # MMD
        assert resolve_to_canonical("左ひじ") == "ForeArm.L"
        assert resolve_to_canonical("右ひじ") == "ForeArm.R"
        assert resolve_to_canonical("左ひざ") == "Shin.L"
        assert resolve_to_canonical("右ひざ") == "Shin.R"
        assert resolve_to_canonical("左足首") == "Foot.L"
        assert resolve_to_canonical("左つま先") == "Toe.L"

        # Mixamo
        assert resolve_to_canonical("mixamorig:LeftForeArm") == "ForeArm.L"
        assert resolve_to_canonical("mixamorig:RightForeArm") == "ForeArm.R"
        assert resolve_to_canonical("mixamorig:LeftLeg") == "Shin.L"
        assert resolve_to_canonical("mixamorig:RightLeg") == "Shin.R"
        assert resolve_to_canonical("mixamorig:LeftFoot") == "Foot.L"
        assert resolve_to_canonical("mixamorig:LeftToeBase") == "Toe.L"

        # Rigify
        assert resolve_to_canonical("DEF-forearm.L") == "ForeArm.L"
        assert resolve_to_canonical("DEF-shin.L") == "Shin.L"
        assert resolve_to_canonical("DEF-foot.L") == "Foot.L"

    def test_clamp_pose_rotations(self):
        raw_rotations = {
            "ForeArm.L": (math.radians(-45.0), math.radians(30.0), math.radians(-10.0)),
            "Shin.L": (math.radians(-20.0), math.radians(10.0), math.radians(-15.0)),
            "Foot.L": (math.radians(-60.0), math.radians(20.0), math.radians(25.0)),
            "Toe.L": (math.radians(-10.0), math.radians(5.0), math.radians(-5.0)),
        }
        sanitized = clamp_pose_rotations(raw_rotations)

        # Elbow flexion clamped to [0, 145 deg]
        fa = sanitized["ForeArm.L"]
        assert abs(fa[0] - 0.0) < 1e-4
        assert abs(fa[1] - math.radians(15.0)) < 1e-4
        assert abs(fa[2] - math.radians(-5.0)) < 1e-4

        # Knee flexion clamped to [0, 140 deg], anti-valgus [-3, 3 deg]
        shin = sanitized["Shin.L"]
        assert abs(shin[0] - 0.0) < 1e-4
        assert abs(shin[1] - math.radians(3.0)) < 1e-4
        assert abs(shin[2] - math.radians(-3.0)) < 1e-4

        # Foot pitch clamped to [-45, 30 deg]
        foot = sanitized["Foot.L"]
        assert abs(foot[0] - math.radians(-45.0)) < 1e-4
        assert abs(foot[1] - math.radians(8.0)) < 1e-4
        assert abs(foot[2] - math.radians(10.0)) < 1e-4


# ==============================================================================
# 3. Feature F13: Secondary Inertial Dynamics & Spring Solver Tests
# ==============================================================================

class TestFeatureF13SecondaryDynamics:
    """Validates analytical damping ratio, RK4 integration, twintail chain, and skirt clearance."""

    def test_analytical_overdamping_parameters(self):
        c_crit, zeta, (r1, r2) = calculate_damping_ratio(SPRING_MASS, SPRING_STIFFNESS, SPRING_DAMPING)
        # m=0.20, k=150.0, c=12.0
        # c_crit = 2 * sqrt(30) ~ 10.9545 N*s/m
        # zeta ~ 1.0954 >= 1.0 (overdamped)
        assert abs(c_crit - 10.9545) < 0.01
        assert zeta >= 1.0, f"System is underdamped: zeta={zeta}"
        assert abs(zeta - 1.0954) < 0.01

        # Real strictly negative roots
        assert r1 < 0.0 and r2 < 0.0
        assert abs(r1 - (-17.75)) < 0.1
        assert abs(r2 - (-42.25)) < 0.1

    def test_rk4_simulation_energy_dissipation(self):
        res = simulate_rk4_spring_damper(
            m=SPRING_MASS,
            k=SPRING_STIFFNESS,
            c=SPRING_DAMPING,
            x0=0.05,
            v0=0.0,
            duration=1.0,
            dt=1.0 / 240.0,
        )
        assert res["energy_dissipation_violations"] == 0
        assert res["zero_crossings"] == 0  # Monotonic overdamped decay
        assert res["final_energy"] < 1e-6
        assert abs(res["final_displacement"]) < 1e-3

    def test_twintail_chain_simulator(self):
        sim = TwintailChainSimulator(n_substeps=4)
        frames = list(range(1, 11))
        # Pitch head forward at 10 deg at frame 5
        head_rots = [(0.0, 0.0, 0.0)] * 4 + [(math.radians(10.0), 0.0, 0.0)] * 3 + [(0.0, 0.0, 0.0)] * 3
        head_locs = [(0.0, 0.0, 1.5)] * 10

        res = sim.simulate_twintail_for_action(frames, head_rots, head_locs, fps=30.0)
        assert len(res) == 10  # 5 left + 5 right
        for bname in ALL_HAIR_BONES:
            assert bname in res
            assert len(res[bname]) == len(frames)

    def test_skirt_clearance_simulator(self):
        skirt_sim = SkirtClearanceSimulator()
        # Test extreme left high kick (-90 deg flexion in Anime_Armature)
        pitches = skirt_sim.evaluate_skirt_pitches_for_frame(
            thigh_l_pitch_rad=math.radians(-90.0),
            thigh_r_pitch_rad=0.0,
            hip_bounce_z=-0.05,
        )
        assert len(pitches) == 12

        # All skirt spoke pitches must remain strictly within [-15 deg, +65 deg]
        for bname, pitch_rad in pitches.items():
            pitch_deg = math.degrees(pitch_rad)
            assert pitch_deg >= SKIRT_PITCH_MIN_DEG - 1e-4, f"{bname} violated min pitch: {pitch_deg}"
            assert pitch_deg <= SKIRT_PITCH_MAX_DEG + 1e-4, f"{bname} violated max pitch: {pitch_deg}"

        # Front-left skirt bone Skirt_11 must flare outward significantly
        assert math.degrees(pitches["Skirt_11"]) > 20.0

    def test_secondary_spring_dynamics_solver_class(self):
        solver = SecondarySpringDynamicsSolver()
        assert solver.zeta >= 1.0
        assert solver.hair_sim is not None
        assert solver.skirt_sim is not None


# ==============================================================================
# 4. Master Deliverable Assets Verification Tests
# ==============================================================================

class TestMasterDeliverableAssets:
    """Verifies that the generated production deliverables satisfy size and integrity constraints."""

    def test_animated_blend_deliverable_exists_and_size(self):
        blend_path = Path("output/anime_animated.blend")
        if not blend_path.exists():
            pkg_root = Path(__file__).resolve().parent.parent
            blend_path = pkg_root / "output" / "anime_animated.blend"

        assert blend_path.exists(), f"output/anime_animated.blend not found at {blend_path}"
        size_mb = blend_path.stat().st_size / (1024 * 1024)
        assert size_mb > 3.5, f"anime_animated.blend too small: {size_mb:.2f} MB (required > 3.5 MB)"

    def test_animated_glb_deliverable_exists_and_size(self):
        glb_path = Path("output/anime_animated.glb")
        if not glb_path.exists():
            pkg_root = Path(__file__).resolve().parent.parent
            glb_path = pkg_root / "output" / "anime_animated.glb"

        assert glb_path.exists(), f"output/anime_animated.glb not found at {glb_path}"
        size_mb = glb_path.stat().st_size / (1024 * 1024)
        assert size_mb > 1.0, f"anime_animated.glb too small: {size_mb:.2f} MB (required > 1.0 MB)"
