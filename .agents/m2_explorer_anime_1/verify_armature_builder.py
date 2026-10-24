import sys
from pathlib import Path

# Add our working directory to sys.path
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\.agents\m2_explorer_anime_1")
from proposed_armature_builder import (
    ArmatureBuilder,
    ALL_REQUIRED_ARMATURE_BONES,
    ALL_30_FINGER_BONES,
    UNIVERSAL_SPINE_BONES,
    UNIVERSAL_LIMB_BONES,
    TWIST_BONES,
    SKIRT_BONES,
    HAIR_BONES,
    VRM_1_0_BONE_MAP,
    MMD_BONE_MAP,
    RIGIFY_DEF_BONE_MAP,
)

print("Testing pure-Python ArmatureBuilder...")
builder = ArmatureBuilder(height=1.650)
spec = builder.generate_armature_spec()

print(f"Total bones generated: {spec.total_bones}")
assert spec.total_bones == 78, f"Expected 78 bones, got {spec.total_bones}"

# Verify all required bones exist
for b in ALL_REQUIRED_ARMATURE_BONES:
    assert b in spec.bones, f"Missing bone: {b}"

# Verify spine hierarchy
assert spec.bones["Hips"].parent is None
assert spec.bones["Spine"].parent == "Hips"
assert spec.bones["Spine1"].parent == "Spine"
assert spec.bones["Spine2"].parent == "Spine1"
assert spec.bones["Neck"].parent == "Spine2"
assert spec.bones["Head"].parent == "Neck"

# Verify 30 fingers
assert len(ALL_30_FINGER_BONES) == 30
for b in ALL_30_FINGER_BONES:
    assert b in spec.bones

# Verify dynamic scaling at 1.45m, 1.58m, 1.75m
for h in [1.450, 1.580, 1.750]:
    b_scaled = ArmatureBuilder(height=h)
    s_spec = b_scaled.generate_armature_spec()
    assert s_spec.total_bones == 78
    head_z = s_spec.bones["Head"].tail[2]
    print(f"Height {h:.3f}m -> Head Top Z = {head_z:.4f}m")
    assert abs(head_z - (1.64139 * (h / 1.650))) < 1e-4

print("\nPure-Python ArmatureBuilder Verification: ALL CHECKS PASSED!")
