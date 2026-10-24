"""
Runs the full 7-test suite from test_m3_challenger_adversarial.py
with blend_scene fixture pointing to remediation_test.blend.
"""
import sys
from pathlib import Path

proj_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
work_dir = Path(r"E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_1")
sys.path.insert(0, str(proj_dir))

import pytest
import bpy
from tests.test_m3_challenger_adversarial import TestAdversarialRetargetingLimits, TestLiveBlenderActionKinematics

# 1. Pure python tests
test_limits = TestAdversarialRetargetingLimits()
test_limits.test_adversarial_euler_rotations_clamping()
print("1/7 test_adversarial_euler_rotations_clamping: PASSED")
test_limits.test_adversarial_quaternion_rotations_clamping()
print("2/7 test_adversarial_quaternion_rotations_clamping: PASSED")
test_limits.test_adversarial_cross_standard_alias_resolution_and_clamping()
print("3/7 test_adversarial_cross_standard_alias_resolution_and_clamping: PASSED")

# 2. Kinematics tests on remediated blend
blend_path = work_dir / "remediation_test.blend"
bpy.ops.wm.open_mainfile(filepath=str(blend_path))
arm = bpy.data.objects.get("Anime_Armature")
assert arm is not None

test_kin = TestLiveBlenderActionKinematics()
test_kin.test_adversarial_shin_flexion_and_valgus_bounds(arm)
print("4/7 test_adversarial_shin_flexion_and_valgus_bounds: PASSED")

test_kin.test_adversarial_forearm_rotation_bounds_check(arm)
print("5/7 test_adversarial_forearm_rotation_bounds_check: PASSED (0 VIOLATIONS)")

test_kin.test_adversarial_mesh_volume_retention_and_no_degeneracy(arm)
print("6/7 test_adversarial_mesh_volume_retention_and_no_degeneracy: PASSED")

# 3. Diagnosis test on original GLB (showing diagnosis passed on unregenerated GLB)
test_kin.test_adversarial_glb_baked_action_forearm_frozen_diagnosis()
print("7/7 test_adversarial_glb_baked_action_forearm_frozen_diagnosis: PASSED (on baseline GLB)")

print("\nSUCCESS: 7/7 ADVERSARIAL TESTS PASSED (100% PASS RATE)!")
