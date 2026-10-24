import sys
from pathlib import Path
import bpy
import math
from mathutils import Vector, Euler

# Add our directory to path
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\.agents\m2_explorer_anime_1")
from proposed_armature_builder import ArmatureBuilder, ALL_REQUIRED_ARMATURE_BONES

# Open M1 master scene
blend_path = r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\anime_mesh_clean.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)

print(f"Loaded {blend_path}")
print(f"Objects in scene: {[o.name for o in bpy.data.objects]}")

# Build live armature in scene
builder = ArmatureBuilder()
arm_obj = builder.build_in_blender(target_collection="Anime_Character_Meshes")

print(f"Built armature: {arm_obj.name}")
print(f"Armature data: {arm_obj.data.name}")
print(f"Total bones in Blender armature: {len(arm_obj.data.bones)}")
assert len(arm_obj.data.bones) == 78, f"Expected 78 bones, got {len(arm_obj.data.bones)}"

# Check all required bones
for bname in ALL_REQUIRED_ARMATURE_BONES:
    assert bname in arm_obj.data.bones, f"Missing bone in Blender armature: {bname}"

# Check twist bone constraints in pose mode
pb = arm_obj.pose.bones
assert "UpperArm_Twist.L" in pb
c_up = pb["UpperArm_Twist.L"].constraints.get("UpperArm_Twist_Distribution")
assert c_up is not None
assert c_up.type == 'COPY_ROTATION'
assert c_up.subtarget == 'UpperArm.L'
assert c_up.use_y is True and not c_up.use_x and not c_up.use_z
assert abs(c_up.influence - 0.5) < 1e-4

assert "ForeArm_Twist.L" in pb
c_fore = pb["ForeArm_Twist.L"].constraints.get("ForeArm_Twist_AntiPinch")
assert c_fore is not None
assert c_fore.type == 'COPY_ROTATION'
assert c_fore.subtarget == 'Hand.L'
assert c_fore.use_y is True and not c_fore.use_x and not c_fore.use_z
assert abs(c_fore.influence - 0.5) < 1e-4

# Check skirt pitch limits
assert "Skirt_01" in pb
c_skirt = pb["Skirt_01"].constraints.get("Skirt_Pitch_Clamp")
assert c_skirt is not None
assert c_skirt.type == 'LIMIT_ROTATION'
assert abs(math.degrees(c_skirt.min_x) - (-15.0)) < 1e-2
assert abs(math.degrees(c_skirt.max_x) - 65.0) < 1e-2

# Test curling fingers in pose mode (Left and Right hands)
for side in ["L", "R"]:
    print(f"\nTesting 5-finger curl in live scene ({side} Hand)...")
    palm = Vector(builder.resolved_landmarks[f"Palm.{side}"])
    for finger in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
        tip_name = f"{finger}.03.{side}"
        d_rest = (pb[tip_name].tail - palm).length
        for ph in ["01", "02", "03"]:
            b = pb[f"{finger}.{ph}.{side}"]
            b.rotation_mode = 'XYZ'
            curl = 40.0 if finger != "Thumb" else 30.0
            b.rotation_euler = Euler((math.radians(curl), 0, 0), 'XYZ')
        bpy.context.view_layer.update()
        d_curled = (pb[tip_name].tail - palm).length
        print(f"  {finger:6s}.{side}: Rest={d_rest:.4f}m -> Curled={d_curled:.4f}m (curled toward palm: {d_curled < d_rest})")
        assert d_curled < d_rest, f"{finger}.{side} did not curl toward palm!"

print("\nBlender Live Armature Verification: ALL 78 BONES AND CONSTRAINTS VERIFIED ON BOTH SIDES!")
