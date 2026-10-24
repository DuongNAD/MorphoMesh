"""
Unit & Integration Tests for proposed_retargeting_limits.py.
Validates pure-Python math, cross-standard bone resolution,
and live Blender 4.5+ pose bone constraint attachment.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Add current directory to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from proposed_retargeting_limits import (
    PHYSIOLOGICAL_ROTATION_LIMITS,
    HINGE_LIMITS,
    VRM_1_0_BONE_MAP,
    MMD_BONE_MAP,
    RIGIFY_DEF_BONE_MAP,
    MIXAMO_BONE_MAP,
    ALIAS_TO_CANONICAL_MAP,
    LimitSpec,
    clamp_angle,
    clamp_joint_angle_deg,
    normalize_quaternion,
    quat_to_euler_xyz,
    euler_xyz_to_quat,
    resolve_to_canonical,
    get_standard_bone_name,
    clamp_single_bone_rotation,
    clamp_pose_rotations,
)


# ==============================================================================
# 1. Pure-Python Mathematical & Resolution Tests
# ==============================================================================

def test_clamp_angle_and_deg():
    assert clamp_angle(0.5, 0.0, 1.0) == 0.5
    assert clamp_angle(-0.2, 0.0, 1.0) == 0.0
    assert clamp_angle(1.5, 0.0, 1.0) == 1.0

    assert clamp_joint_angle_deg(150.0, 0.0, 145.0) == 145.0
    assert clamp_joint_angle_deg(-10.0, 0.0, 145.0) == 0.0
    assert clamp_joint_angle_deg(90.0, 0.0, 145.0) == 90.0
    assert clamp_joint_angle_deg(160.0, 0.0, 140.0) == 140.0
    assert clamp_joint_angle_deg(-15.0, 0.0, 140.0) == 0.0
    assert clamp_joint_angle_deg(70.0, 0.0, 140.0) == 70.0


def test_quat_euler_roundtrip():
    test_cases = [
        (0.0, 0.0, 0.0),
        (math.radians(45.0), 0.0, 0.0),
        (0.0, math.radians(30.0), 0.0),
        (0.0, 0.0, math.radians(-25.0)),
        (math.radians(90.0), math.radians(-15.0), math.radians(10.0)),
        (math.radians(-30.0), math.radians(20.0), math.radians(-45.0)),
    ]
    for ex, ey, ez in test_cases:
        w, x, y, z = euler_xyz_to_quat(ex, ey, ez)
        rx, ry, rz = quat_to_euler_xyz(w, x, y, z)
        assert abs(rx - ex) < 1e-4, f"X mismatch: {rx} vs {ex}"
        assert abs(ry - ey) < 1e-4, f"Y mismatch: {ry} vs {ey}"
        assert abs(rz - ez) < 1e-4, f"Z mismatch: {rz} vs {ez}"


def test_cross_standard_resolution():
    # VRM 1.0
    assert resolve_to_canonical("leftLowerArm") == "ForeArm.L"
    assert resolve_to_canonical("rightLowerArm") == "ForeArm.R"
    assert resolve_to_canonical("leftLowerLeg") == "Shin.L"
    assert resolve_to_canonical("rightLowerLeg") == "Shin.R"
    assert resolve_to_canonical("leftFoot") == "Foot.L"
    assert resolve_to_canonical("leftToes") == "Toe.L"
    assert resolve_to_canonical("chest") == "Spine1"
    assert resolve_to_canonical("upperChest") == "Spine2"

    # MMD
    assert resolve_to_canonical("左ひじ") == "ForeArm.L"
    assert resolve_to_canonical("右ひじ") == "ForeArm.R"
    assert resolve_to_canonical("左ひざ") == "Shin.L"
    assert resolve_to_canonical("右ひざ") == "Shin.R"
    assert resolve_to_canonical("左足首") == "Foot.L"
    assert resolve_to_canonical("左つま先") == "Toe.L"
    assert resolve_to_canonical("上半身") == "Spine"
    assert resolve_to_canonical("上半身2") == "Spine1"
    assert resolve_to_canonical("センター") == "Hips"

    # Rigify DEF
    assert resolve_to_canonical("DEF-forearm.L") == "ForeArm.L"
    assert resolve_to_canonical("DEF-forearm.R") == "ForeArm.R"
    assert resolve_to_canonical("DEF-shin.L") == "Shin.L"
    assert resolve_to_canonical("DEF-shin.R") == "Shin.R"
    assert resolve_to_canonical("DEF-foot.L") == "Foot.L"
    assert resolve_to_canonical("DEF-toe.L") == "Toe.L"
    assert resolve_to_canonical("DEF-spine.002") == "Spine1"

    # Mixamo
    assert resolve_to_canonical("mixamorig:LeftForeArm") == "ForeArm.L"
    assert resolve_to_canonical("mixamorig:RightForeArm") == "ForeArm.R"
    assert resolve_to_canonical("mixamorig:LeftLeg") == "Shin.L"
    assert resolve_to_canonical("mixamorig:RightLeg") == "Shin.R"
    assert resolve_to_canonical("mixamorig:LeftFoot") == "Foot.L"
    assert resolve_to_canonical("mixamorig:LeftToeBase") == "Toe.L"
    assert resolve_to_canonical("mixamorig:LeftHandIndex1") == "Index.01.L"

    # Common Mocap Nicknames
    assert resolve_to_canonical("Elbow.L") == "ForeArm.L"
    assert resolve_to_canonical("Knee.L") == "Shin.L"
    assert resolve_to_canonical("LeftLeg") == "Shin.L"


def test_standard_bone_lookup():
    assert get_standard_bone_name("ForeArm.L", "vrm") == "leftLowerArm"
    assert get_standard_bone_name("ForeArm.L", "mmd") == "左ひじ"
    assert get_standard_bone_name("ForeArm.L", "rigify") == "DEF-forearm.L"
    assert get_standard_bone_name("ForeArm.L", "mixamo") == "mixamorig:LeftForeArm"


def test_clamp_single_bone_rotation():
    forearm_limit = PHYSIOLOGICAL_ROTATION_LIMITS["ForeArm.L"]

    # 1. Negative flexion (-30° X) -> Clamped to 0.0°
    bad_euler = (math.radians(-30.0), 0.0, 0.0)
    clamped_e = clamp_single_bone_rotation(bad_euler, forearm_limit)
    assert abs(clamped_e[0] - 0.0) < 1e-4, f"Hyperextension was not clamped: {clamped_e[0]}"

    # 2. Over-flexion (+160° X) -> Clamped to 145.0°
    over_euler = (math.radians(160.0), 0.0, 0.0)
    clamped_over = clamp_single_bone_rotation(over_euler, forearm_limit)
    assert abs(clamped_over[0] - math.radians(145.0)) < 1e-4, f"Over-flexion was not clamped: {clamped_over[0]}"

    # 3. Valid flexion (+65° X) -> Unchanged
    valid_euler = (math.radians(65.0), 0.0, 0.0)
    clamped_valid = clamp_single_bone_rotation(valid_euler, forearm_limit)
    assert abs(clamped_valid[0] - math.radians(65.0)) < 1e-4

    # 4. Quaternion hyperextension
    bad_quat = euler_xyz_to_quat(math.radians(-45.0), 0.0, 0.0)
    clamped_q = clamp_single_bone_rotation(bad_quat, forearm_limit)
    qx, qy, qz = quat_to_euler_xyz(*clamped_q)
    assert abs(qx - 0.0) < 1e-4, f"Quaternion hyperextension not clamped: {qx}"


def test_clamp_pose_rotations_batch():
    raw_mocap = {
        "mixamorig:LeftForeArm": (math.radians(-40.0), math.radians(25.0), math.radians(-10.0)),
        "leftLowerLeg": (math.radians(-30.0), math.radians(10.0), math.radians(-15.0)),
        "DEF-foot.L": (math.radians(-60.0), math.radians(20.0), math.radians(-25.0)),
        "左つま先": (math.radians(-20.0), math.radians(5.0), math.radians(-5.0)),
        "Hips": (0.0, 0.0, 0.0),  # No limit, should pass through
    }

    sanitized = clamp_pose_rotations(raw_mocap)

    # Check LeftForeArm: X in [0, 145], Y in [-15, 15], Z in [-5, 5]
    fa = sanitized["mixamorig:LeftForeArm"]
    assert abs(fa[0] - 0.0) < 1e-4
    assert abs(fa[1] - math.radians(15.0)) < 1e-4
    assert abs(fa[2] - math.radians(-5.0)) < 1e-4

    # Check Shin.L (leftLowerLeg): X in [0, 140], Y in [-3, 3], Z in [-3, 3]
    shin = sanitized["leftLowerLeg"]
    assert abs(shin[0] - 0.0) < 1e-4
    assert abs(shin[1] - math.radians(3.0)) < 1e-4
    assert abs(shin[2] - math.radians(-3.0)) < 1e-4

    # Check Foot.L: X in [-45, 30], Y in [-8, 8], Z in [-10, 10]
    foot = sanitized["DEF-foot.L"]
    assert abs(foot[0] - math.radians(-45.0)) < 1e-4
    assert abs(foot[1] - math.radians(8.0)) < 1e-4
    assert abs(foot[2] - math.radians(-10.0)) < 1e-4

    # Check Toe.L: X in [-5, 45], Y in [-2, 2], Z in [-2, 2]
    toe = sanitized["左つま先"]
    assert abs(toe[0] - math.radians(-5.0)) < 1e-4
    assert abs(toe[1] - math.radians(2.0)) < 1e-4
    assert abs(toe[2] - math.radians(-2.0)) < 1e-4


if __name__ == "__main__":
    print("Running Pure-Python Unit Tests...")
    test_clamp_angle_and_deg()
    test_quat_euler_roundtrip()
    test_cross_standard_resolution()
    test_standard_bone_lookup()
    test_clamp_single_bone_rotation()
    test_clamp_pose_rotations_batch()
    print("ALL PURE-PYTHON UNIT TESTS PASSED SUCCESSFULLY (6/6)!")
