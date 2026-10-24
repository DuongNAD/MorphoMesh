"""
tests/test_live_blender_rig.py
Live headless Blender verification script for output/anime_rigged.blend.
Inspects the live Blender data blocks, bones, constraints, and vertex weights.
"""

import math
import sys
from pathlib import Path

try:
    import bpy
    import mathutils
    from mathutils import Vector
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    import pytest
    pytest.skip("bpy is not available outside Blender runtime", allow_module_level=True)

blend_path = Path("output/anime_rigged.blend").resolve()
if not blend_path.exists():
    print(f"FAIL: {blend_path} not found")
    sys.exit(1)

bpy.ops.wm.open_mainfile(filepath=str(blend_path))

# 1. Check Armature
assert "Anime_Armature" in bpy.data.objects, "Anime_Armature object not found in scene"
arm_obj = bpy.data.objects["Anime_Armature"]
bones = arm_obj.data.bones
assert len(bones) == 78, f"Expected 78 bones, found {len(bones)}"

# Check spine hierarchy
assert bones["Hips"].parent is None
assert bones["Spine"].parent.name == "Hips"
assert bones["Spine1"].parent.name == "Spine"
assert bones["Spine2"].parent.name == "Spine1"
assert bones["Neck"].parent.name == "Spine2"
assert bones["Head"].parent.name == "Neck"

# Check all 30 fingers
finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
phalanges = ["01", "02", "03"]
for side in ["L", "R"]:
    for f in finger_names:
        for p in phalanges:
            bname = f"{f}.{p}.{side}"
            assert bname in bones, f"Missing finger bone: {bname}"

# Check finger curl toward palm on +local X
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
pb = arm_obj.pose.bones

for side in ["L", "R"]:
    sign = 1.0 if side == "L" else -1.0
    palm = Vector((sign * 0.43550, -0.18575, 1.01439))
    for f in finger_names:
        for p in phalanges:
            bname = f"{f}.{p}.{side}"
            pbone = pb[bname]
            pbone.rotation_mode = 'XYZ'
            pbone.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
            rest_dist = (arm_obj.matrix_world @ pbone.tail - palm).length

            pbone.rotation_euler = (math.radians(30.0), 0.0, 0.0)
            bpy.context.view_layer.update()
            curl_dist = (arm_obj.matrix_world @ pbone.tail - palm).length

            assert curl_dist < rest_dist, f"Finger {bname} did not curl toward palm under +X rotation"
            pbone.rotation_euler = (0.0, 0.0, 0.0)

# Check twist bone constraints
for twist_name, target in [
    ("UpperArm_Twist.L", "ForeArm.L"), ("UpperArm_Twist.R", "ForeArm.R"),
    ("ForeArm_Twist.L", "Hand.L"), ("ForeArm_Twist.R", "Hand.R")
]:
    pbone = pb[twist_name]
    assert len(pbone.constraints) > 0, f"Twist bone {twist_name} has no constraints"
    c = pbone.constraints[0]
    assert c.type == 'COPY_ROTATION'
    assert c.subtarget == target
    assert c.use_y is True
    assert c.use_x is False and c.use_z is False
    assert abs(c.influence - 0.5) < 1e-4

# Check skirt radial rig constraints
for i in range(1, 13):
    bname = f"Skirt_{i:02d}"
    pbone = pb[bname]
    assert len(pbone.constraints) > 0, f"Skirt bone {bname} has no constraints"
    c = pbone.constraints[0]
    assert c.type == 'LIMIT_ROTATION'
    assert c.use_limit_x is True
    assert abs(math.degrees(c.min_x) - (-15.0)) < 0.1
    assert abs(math.degrees(c.max_x) - 65.0) < 0.1
    assert pbone.get("is_secondary_skirt") is True

# Check twintail spring properties
for side in ["L", "R"]:
    for i in range(1, 6):
        bname = f"Hair_{side}_{i:02d}"
        pbone = pb[bname]
        assert pbone.get("is_secondary_hair") is True
        assert abs(pbone.get("spring_mass") - 0.20) < 1e-4
        assert abs(pbone.get("spring_stiffness") - 150.0) < 1e-4
        assert abs(pbone.get("spring_damping") - 12.0) < 1e-4

bpy.ops.object.mode_set(mode='OBJECT')

# 2. Check Submeshes, DQS Modifiers, and Skin Weights
expected_submeshes = [
    "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
    "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
]

for name in expected_submeshes:
    assert name in bpy.data.objects, f"Submesh {name} missing"
    obj = bpy.data.objects[name]
    assert obj.type == 'MESH'

    # Check Armature modifier with DQS
    arm_mod = None
    for m in obj.modifiers:
        if m.type == 'ARMATURE':
            arm_mod = m
            break
    assert arm_mod is not None, f"Submesh {name} has no Armature modifier"
    assert arm_mod.use_deform_preserve_volume is True, f"Submesh {name} DQS preserve volume not enabled"
    assert arm_mod.object == arm_obj

    # Check weight normalization & zero orphans
    verts = obj.data.vertices
    for v in verts:
        tot_w = sum(g.weight for g in v.groups)
        assert tot_w > 0.0, f"Vertex {v.index} in {name} is orphaned"
        assert abs(tot_w - 1.0) < 1e-3, f"Vertex {v.index} in {name} unnormalized: {tot_w}"

# 3. Check CRITICAL INVARIANT: 0% Thigh Weight Bleeding on Anime_Skirt
skirt_obj = bpy.data.objects["Anime_Skirt"]
for vg in skirt_obj.vertex_groups:
    assert not vg.name.startswith("Thigh"), f"CRITICAL INVARIANT VIOLATION: {vg.name} present on Anime_Skirt"
    assert vg.name.startswith("Skirt_"), f"Unexpected non-skirt vertex group on Anime_Skirt: {vg.name}"

print("=" * 70)
print("ALL LIVE BLENDER RIGGING AUDITS PASSED PERFECTLY (100%)")
print("=" * 70)
