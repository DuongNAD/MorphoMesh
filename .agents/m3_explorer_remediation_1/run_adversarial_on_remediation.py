"""
Run test_m3_challenger_adversarial.py against remediation_test.blend
"""
import sys
from pathlib import Path

proj_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
work_dir = Path(r"E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_1")
sys.path.insert(0, str(proj_dir))
sys.path.insert(0, str(work_dir))

import pytest
import bpy

# Open remediation_test.blend
blend_path = work_dir / "remediation_test.blend"
print(f"Opening {blend_path}...")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

from tests.test_m3_challenger_adversarial import (
    TestAdversarialRetargetingLimits,
    TestLiveBlenderActionKinematics,
)

# Run pure python tests
retarget_tester = TestAdversarialRetargetingLimits()
retarget_tester.test_adversarial_euler_rotations_clamping()
retarget_tester.test_adversarial_quaternion_rotations_clamping()
retarget_tester.test_adversarial_cross_standard_alias_resolution_and_clamping()
print("TestAdversarialRetargetingLimits: 3/3 passed")

# Run live blender kinematics tests
kinematics_tester = TestLiveBlenderActionKinematics()
arm = bpy.data.objects["Anime_Armature"]

kinematics_tester.test_adversarial_shin_flexion_and_valgus_bounds(arm)
print("test_adversarial_shin_flexion_and_valgus_bounds: PASSED")

kinematics_tester.test_adversarial_forearm_rotation_bounds_check(arm)
print("test_adversarial_forearm_rotation_bounds_check: PASSED (0 violations!)")

kinematics_tester.test_adversarial_mesh_volume_retention_and_no_degeneracy(arm)
print("test_adversarial_mesh_volume_retention_and_no_degeneracy: PASSED")

print("\nALL 6 ADVERSARIAL INTEGRITY AUDITS PASSED 100% ON REMEDIATED BLEND!")
