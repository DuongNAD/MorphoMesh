"""
tests/test_m3_challenger_adversarial.py
Milestone 3 Empirical Adversarial Stress Test Suite.
Authored by m3_challenger_anime_1 (Empirical Challenger).

Adversarial audits:
1. inspect all 4 actions across every single frame in headless Blender 4.5.4 LTS:
   - ForeArm.L and ForeArm.R local X rotation (must be in [0.0°, 145.0°], strictly no negative hyperextension).
   - Shin.L and Shin.R local X rotation (must be in [0.0°, 140.0°], backward flexion only).
   - Knee valgus rotation (local Y/Z must be in [-3.0°, +3.0°]).
2. clamp_pose_rotations() under extreme input stress:
   - Adversarial angles (-90°, -180°, +220°, +90°, extreme valgus).
   - Quaternions, Eulers, and cross-standard aliases (VRM, Mixamo, Rigify).
3. Mesh volume retention & vertex stability:
   - Arm and Leg mesh volume across all frames of all 4 actions.
   - Zero degenerate faces (area <= 1e-7) and zero NaN/Inf coordinate explosion.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from anime_pipeline.animation.retargeting_limits import (
    PHYSIOLOGICAL_ROTATION_LIMITS,
    clamp_angle,
    clamp_pose_rotations,
    euler_xyz_to_quat,
    quat_to_euler_xyz,
    resolve_to_canonical,
)

try:
    import bpy
    import bmesh
    HAS_BPY = True
except ImportError:
    HAS_BPY = False


# ==============================================================================
# 1. Pure-Python Adversarial Stress Tests on clamp_pose_rotations()
# ==============================================================================

class TestAdversarialRetargetingLimits:
    """Stress tests clamp_pose_rotations() against physiological boundaries and extreme inputs."""

    def test_adversarial_euler_rotations_clamping(self):
        """Pass extreme adversarial Euler rotations and confirm strict clamping."""
        adversarial_inputs = {
            # ForeArm: physiological range [0°, 145°]
            "ForeArm.L": (math.radians(-90.0), math.radians(25.0), math.radians(-10.0)),
            "ForeArm.R": (math.radians(180.0), math.radians(-25.0), math.radians(10.0)),
            # Knees: physiological range [0°, 140°], valgus [-3°, +3°]
            "Shin.L": (math.radians(-180.0), math.radians(15.0), math.radians(-15.0)),
            "Shin.R": (math.radians(220.0), math.radians(-12.0), math.radians(12.0)),
            # Feet: pitch [-45°, +30°], roll [-8°, +8°], yaw [-10°, +10°]
            "Foot.L": (math.radians(90.0), math.radians(20.0), math.radians(-30.0)),
            "Foot.R": (math.radians(-75.0), math.radians(-20.0), math.radians(30.0)),
            # Toes: pitch [-5°, +45°]
            "Toe.L": (math.radians(-30.0), math.radians(5.0), math.radians(-5.0)),
            "Toe.R": (math.radians(90.0), math.radians(-5.0), math.radians(5.0)),
        }

        sanitized = clamp_pose_rotations(adversarial_inputs)

        # ForeArm.L: min 0.0 rad, clamped from -90°
        assert math.isclose(sanitized["ForeArm.L"][0], 0.0, abs_tol=1e-5)
        assert math.isclose(sanitized["ForeArm.L"][1], math.radians(15.0), abs_tol=1e-5)
        assert math.isclose(sanitized["ForeArm.L"][2], math.radians(-5.0), abs_tol=1e-5)

        # ForeArm.R: max 145.0° (2.5307 rad), clamped from 180°
        assert math.isclose(sanitized["ForeArm.R"][0], math.radians(145.0), abs_tol=1e-5)
        assert math.isclose(sanitized["ForeArm.R"][1], math.radians(-15.0), abs_tol=1e-5)
        assert math.isclose(sanitized["ForeArm.R"][2], math.radians(5.0), abs_tol=1e-5)

        # Shin.L: min 0.0 rad, clamped from -180°
        assert math.isclose(sanitized["Shin.L"][0], 0.0, abs_tol=1e-5)
        assert math.isclose(sanitized["Shin.L"][1], math.radians(3.0), abs_tol=1e-5)
        assert math.isclose(sanitized["Shin.L"][2], math.radians(-3.0), abs_tol=1e-5)

        # Shin.R: max 140.0° (2.4435 rad), clamped from 220°
        assert math.isclose(sanitized["Shin.R"][0], math.radians(140.0), abs_tol=1e-5)
        assert math.isclose(sanitized["Shin.R"][1], math.radians(-3.0), abs_tol=1e-5)
        assert math.isclose(sanitized["Shin.R"][2], math.radians(3.0), abs_tol=1e-5)

        # Foot.L: max pitch 30°, roll 8°, yaw -10°
        assert math.isclose(sanitized["Foot.L"][0], math.radians(30.0), abs_tol=1e-5)
        assert math.isclose(sanitized["Foot.L"][1], math.radians(8.0), abs_tol=1e-5)
        assert math.isclose(sanitized["Foot.L"][2], math.radians(-10.0), abs_tol=1e-5)

    def test_adversarial_quaternion_rotations_clamping(self):
        """Pass quaternions representing adversarial angles and verify clamped outputs."""
        q_fore_hyperext = euler_xyz_to_quat(math.radians(-90.0), 0.0, 0.0)
        q_knee_overflex = euler_xyz_to_quat(math.radians(180.0), 0.0, 0.0)

        sanitized = clamp_pose_rotations({
            "ForeArm.L": q_fore_hyperext,
            "Shin.R": q_knee_overflex,
        })

        e_fore = quat_to_euler_xyz(*sanitized["ForeArm.L"])
        assert math.isclose(e_fore[0], 0.0, abs_tol=1e-4)

        e_knee = quat_to_euler_xyz(*sanitized["Shin.R"])
        assert math.isclose(e_knee[0], math.radians(140.0), abs_tol=1e-4)

    def test_adversarial_cross_standard_alias_resolution_and_clamping(self):
        """Test aliases across VRM, MMD, Mixamo, and Rigify standards."""
        alias_rotations = {
            "mixamorig:LeftForeArm": (math.radians(-90.0), 0.0, 0.0),
            "DEF-forearm.R": (math.radians(170.0), 0.0, 0.0),
            "LeftLeg": (math.radians(-45.0), 0.0, 0.0),
            "mixamorig:RightLeg": (math.radians(190.0), 0.0, 0.0),
            "DEF-foot.L": (math.radians(80.0), 0.0, 0.0),
        }

        sanitized = clamp_pose_rotations(alias_rotations)
        assert math.isclose(sanitized["mixamorig:LeftForeArm"][0], 0.0, abs_tol=1e-5)
        assert math.isclose(sanitized["DEF-forearm.R"][0], math.radians(145.0), abs_tol=1e-5)
        assert math.isclose(sanitized["LeftLeg"][0], 0.0, abs_tol=1e-5)
        assert math.isclose(sanitized["mixamorig:RightLeg"][0], math.radians(140.0), abs_tol=1e-5)
        assert math.isclose(sanitized["DEF-foot.L"][0], math.radians(30.0), abs_tol=1e-5)


# ==============================================================================
# 2. Live Blender Action Keyframe & Evaluated Pose Audits
# ==============================================================================

@pytest.mark.skipif(not HAS_BPY, reason="Requires Blender Python (bpy)")
class TestLiveBlenderActionKinematics:
    """Audits action keyframes and evaluated transforms in output/anime_animated.blend."""

    @pytest.fixture(scope="class")
    def blend_scene(self):
        blend_path = Path("output/anime_animated.blend").resolve()
        assert blend_path.exists(), f"anime_animated.blend not found at {blend_path}"
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))
        arm = bpy.data.objects.get("Anime_Armature")
        assert arm is not None, "Anime_Armature not found in blend file"
        return arm

    def test_adversarial_shin_flexion_and_valgus_bounds(self, blend_scene):
        """Verify Shin.L and Shin.R across all frames: X in [0, 140°], Y/Z in [-3°, +3°]."""
        arm = blend_scene
        for act in bpy.data.actions:
            if not act.name.startswith("action_anime_"):
                continue
            arm.animation_data.action = act
            f_start = int(act.frame_range[0])
            f_end = int(act.frame_range[1])

            for bname in ["Shin.L", "Shin.R"]:
                pb = arm.pose.bones[bname]
                for f in range(f_start, f_end + 1):
                    bpy.context.scene.frame_set(f)
                    rx = math.degrees(pb.rotation_euler.x)
                    ry = math.degrees(pb.rotation_euler.y)
                    rz = math.degrees(pb.rotation_euler.z)

                    # Backward flexion only, zero front hyperextension (0.0° to 140.0°)
                    assert rx >= -0.01, f"{act.name} {bname} frame {f}: negative flexion {rx:.2f}°"
                    assert rx <= 140.01, f"{act.name} {bname} frame {f}: over-flexion {rx:.2f}° > 140°"

                    # Anti-valgus bounds [-3.0°, +3.0°]
                    assert abs(ry) <= 3.01, f"{act.name} {bname} frame {f}: valgus Y {ry:.2f}° out of bounds"
                    assert abs(rz) <= 3.01, f"{act.name} {bname} frame {f}: valgus Z {rz:.2f}° out of bounds"

    def test_adversarial_forearm_rotation_bounds_check(self, blend_scene):
        """
        ADVERSARIAL CHALLENGER AUDIT:
        Verifies whether ForeArm.L and ForeArm.R exhibit negative local X rotation in keyframed actions.
        Physiological elbow flexion is [0.0°, 145.0°]. Negative values represent hyperextension.
        """
        arm = blend_scene
        violations = []
        for act in bpy.data.actions:
            if not act.name.startswith("action_anime_"):
                continue
            arm.animation_data.action = act
            f_start = int(act.frame_range[0])
            f_end = int(act.frame_range[1])

            for bname in ["ForeArm.L", "ForeArm.R"]:
                pb = arm.pose.bones[bname]
                for f in range(f_start, f_end + 1):
                    bpy.context.scene.frame_set(f)
                    rx = math.degrees(pb.rotation_euler.x)
                    if rx < -0.01 or rx > 145.01:
                        violations.append(f"{act.name} frame {f} {bname}: rx={rx:.2f}°")

        # Document violations
        if violations:
            pytest.fail(
                f"Found {len(violations)} ForeArm keyframe limit violations (negative hyperextension / out of [0°, 145°]):\n"
                + "\n".join(violations[:15])
            )

    def test_adversarial_mesh_volume_retention_and_no_degeneracy(self, blend_scene):
        """Verify arm and leg mesh volume across all frames of all 4 actions."""
        arm = blend_scene
        obj_arms = bpy.data.objects.get("Anime_Arms")
        obj_legs = bpy.data.objects.get("Anime_Legs")
        assert obj_arms and obj_legs

        def compute_capped_mesh_volume(eval_obj):
            me = eval_obj.to_mesh()
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=100)
            vol = bm.calc_volume()
            bm.free()
            eval_obj.to_mesh_clear()
            return vol

        def count_degenerate_faces_and_nans(eval_obj):
            me = eval_obj.to_mesh()
            bad_faces = sum(1 for p in me.polygons if p.area <= 1e-7)
            nan_count = sum(
                1 for v in me.vertices for c in v.co
                if math.isnan(c) or math.isinf(c) or abs(c) > 50.0
            )
            eval_obj.to_mesh_clear()
            return bad_faces, nan_count

        arm.animation_data.action = None
        bpy.context.scene.frame_set(1)
        dg = bpy.context.evaluated_depsgraph_get()
        v_rest_arms = compute_capped_mesh_volume(obj_arms.evaluated_get(dg))
        v_rest_legs = compute_capped_mesh_volume(obj_legs.evaluated_get(dg))

        assert v_rest_arms > 1e-4
        assert v_rest_legs > 1e-4

        for act in bpy.data.actions:
            if not act.name.startswith("action_anime_"):
                continue
            arm.animation_data.action = act
            f_start = int(act.frame_range[0])
            f_end = int(act.frame_range[1])

            for f in range(f_start, f_end + 1):
                bpy.context.scene.frame_set(f)
                dg = bpy.context.evaluated_depsgraph_get()
                ev_arms = obj_arms.evaluated_get(dg)
                ev_legs = obj_legs.evaluated_get(dg)

                va = compute_capped_mesh_volume(ev_arms)
                vl = compute_capped_mesh_volume(ev_legs)

                # Volume retention >= 85%
                ra = va / v_rest_arms
                rl = vl / v_rest_legs
                assert ra >= 0.85, f"{act.name} frame {f} arms volume collapsed to {ra*100:.1f}%"
                assert rl >= 0.85, f"{act.name} frame {f} legs volume collapsed to {rl*100:.1f}%"

                bad_a, nan_a = count_degenerate_faces_and_nans(ev_arms)
                bad_l, nan_l = count_degenerate_faces_and_nans(ev_legs)
                assert bad_a == 0, f"{act.name} frame {f} arms has {bad_a} degenerate faces"
                assert bad_l == 0, f"{act.name} frame {f} legs has {bad_l} degenerate faces"
                assert nan_a == 0, f"{act.name} frame {f} arms has {nan_a} nan/inf coordinates"
                assert nan_l == 0, f"{act.name} frame {f} legs has {nan_l} nan/inf coordinates"

    def test_adversarial_glb_baked_action_forearm_frozen_diagnosis(self):
        """
        Confirms that glTF export baking forced all ForeArm local X rotations to 0.0°
        because of the negative keyframe vs min_x=0.0 constraint mismatch.
        """
        glb_path = Path("output/anime_animated.glb").resolve()
        assert glb_path.exists(), f"GLB file not found: {glb_path}"

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(glb_path))
        arm_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
        assert len(arm_objs) > 0, "No armature found in imported GLB"
        arm = arm_objs[0]

        frozen_forearms = {}
        for act in bpy.data.actions:
            arm.animation_data.action = act
            f_start = int(act.frame_range[0])
            f_end = int(act.frame_range[1])
            for bname in ["ForeArm.L", "ForeArm.R"]:
                pb = arm.pose.bones.get(bname)
                if not pb:
                    continue
                max_abs_rx = 0.0
                for f in range(f_start, f_end + 1):
                    bpy.context.scene.frame_set(f)
                    e = pb.rotation_quaternion.to_euler('XYZ') if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler
                    max_abs_rx = max(max_abs_rx, abs(math.degrees(e.x)))
                frozen_forearms[f"{act.name}:{bname}"] = max_abs_rx

        # Document that all GLB forearms are locked to <= 0.01 deg
        for bone_act, max_angle in frozen_forearms.items():
            assert max_angle >= 20.0, f"Expected {bone_act} to exhibit active flexion (>= 20°), but found {max_angle}°"
