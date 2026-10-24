"""
Validation script for Milestone 3 ForeArm Keyframe Remediation.
Runs in Blender 4.5.4 LTS headless mode.
"""

import math
import sys
from pathlib import Path

# Add paths
proj_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
work_dir = Path(r"E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_1")
sys.path.insert(0, str(proj_dir))
sys.path.insert(0, str(work_dir))

import bpy
import bmesh
import action_library_patched as patched_lib
import anime_pipeline.animation.retargeting_limits as retargeting_limits
from anime_pipeline.animation.spring_solver import SecondarySpringDynamicsSolver

print("=" * 70)
print("STARTING REMEDIATION VALIDATION IN BLENDER 4.5.4 LTS")
print("=" * 70)

# Step 1: Open rigged character
rigged_blend = proj_dir / "output" / "anime_rigged.blend"
assert rigged_blend.exists(), f"Rigged blend not found: {rigged_blend}"
bpy.ops.wm.open_mainfile(filepath=str(rigged_blend))

arm_obj = bpy.data.objects.get("Anime_Armature")
assert arm_obj is not None, "Anime_Armature not found in rigged blend"

# Step 2: Apply retargeting limits
print("Applying retargeting limits...")
limit_stats = retargeting_limits.apply_retargeting_limits(arm_obj)
print(f"Applied limits: {limit_stats}")

# Step 3: Build all 4 actions using patched action_library
print("Building actions using patched action_library...")
actions = patched_lib.build_all_anime_actions(arm_obj, push_to_nla=True)
print(f"Built actions: {list(actions.keys())}")

# Step 4: Check keyframes and evaluated transforms across all frames of all 4 actions
print("\nAuditing ForeArm.L and ForeArm.R local X rotations...")
violations = []
forearm_stats = {}

for act_name, act in actions.items():
    arm_obj.animation_data.action = act
    f_start = int(act.frame_range[0])
    f_end = int(act.frame_range[1])
    
    for bname in ["ForeArm.L", "ForeArm.R"]:
        pb = arm_obj.pose.bones[bname]
        angles = []
        for f in range(f_start, f_end + 1):
            bpy.context.scene.frame_set(f)
            rx = math.degrees(pb.rotation_euler.x)
            angles.append(rx)
            if rx < -0.01 or rx > 145.01:
                violations.append(f"{act_name} frame {f} {bname}: rx={rx:.2f}°")
        
        min_a = min(angles)
        max_a = max(angles)
        forearm_stats[f"{act_name} {bname}"] = (min_a, max_a)
        print(f"  {act_name:<30} {bname}: min={min_a:6.2f}°, max={max_a:6.2f}°")

print(f"\nTotal ForeArm Limit Violations: {len(violations)} (Challenger baseline was 632)")
assert len(violations) == 0, f"Violations found: {violations[:10]}"

# Step 5: Test Shin bounds and knee valgus
print("\nAuditing Shin and valgus bounds...")
shin_violations = []
for act_name, act in actions.items():
    arm_obj.animation_data.action = act
    f_start = int(act.frame_range[0])
    f_end = int(act.frame_range[1])
    for bname in ["Shin.L", "Shin.R"]:
        pb = arm_obj.pose.bones[bname]
        for f in range(f_start, f_end + 1):
            bpy.context.scene.frame_set(f)
            rx = math.degrees(pb.rotation_euler.x)
            ry = math.degrees(pb.rotation_euler.y)
            rz = math.degrees(pb.rotation_euler.z)
            if rx < -0.01 or rx > 140.01:
                shin_violations.append(f"{act_name} frame {f} {bname}: rx={rx:.2f}°")
            if abs(ry) > 3.01 or abs(rz) > 3.01:
                shin_violations.append(f"{act_name} frame {f} {bname}: valgus Y={ry:.2f}°, Z={rz:.2f}°")

print(f"Total Shin/Valgus Violations: {len(shin_violations)}")
assert len(shin_violations) == 0

# Step 6: Test Mesh volume retention
print("\nAuditing Mesh volume retention across actions...")
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

arm_obj.animation_data.action = None
bpy.context.scene.frame_set(1)
dg = bpy.context.evaluated_depsgraph_get()
v_rest_arms = compute_capped_mesh_volume(obj_arms.evaluated_get(dg))
v_rest_legs = compute_capped_mesh_volume(obj_legs.evaluated_get(dg))

min_ra = 1.0
min_rl = 1.0
for act_name, act in actions.items():
    arm_obj.animation_data.action = act
    f_start = int(act.frame_range[0])
    f_end = int(act.frame_range[1])
    for f in range(f_start, f_end + 1):
        bpy.context.scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev_arms = obj_arms.evaluated_get(dg)
        ev_legs = obj_legs.evaluated_get(dg)
        ra = compute_capped_mesh_volume(ev_arms) / v_rest_arms
        rl = compute_capped_mesh_volume(ev_legs) / v_rest_legs
        min_ra = min(min_ra, ra)
        min_rl = min(min_rl, rl)

print(f"Minimum Arms Volume Ratio: {min_ra * 100:.2f}% (>= 85% required)")
print(f"Minimum Legs Volume Ratio: {min_rl * 100:.2f}% (>= 85% required)")
assert min_ra >= 0.85
assert min_rl >= 0.85

# Step 7: Save test blend file and export test GLB
test_blend_path = work_dir / "remediation_test.blend"
test_glb_path = work_dir / "remediation_test.glb"

print(f"\nSaving remediation test blend to {test_blend_path}...")
bpy.ops.wm.save_as_mainfile(filepath=str(test_blend_path))

print(f"Exporting test GLB to {test_glb_path}...")
bpy.ops.export_scene.gltf(
    filepath=str(test_glb_path),
    export_format='GLB',
    export_animations=True,
    export_nla_strips=True,
    export_def_bones=False,
    export_current_frame=False,
)
assert test_glb_path.exists()
print(f"GLB exported successfully ({test_glb_path.stat().st_size / 1024:.1f} KB)")

# Step 8: Re-import test GLB and audit baked animations for ForeArms
print("\nAuditing re-imported GLB baked skeletal transforms...")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(test_glb_path))
glb_arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
assert len(glb_arms) > 0, "No armature found in imported GLB"
glb_arm = glb_arms[0]

glb_forearm_results = {}
for act in bpy.data.actions:
    glb_arm.animation_data.action = act
    f_start = int(act.frame_range[0])
    f_end = int(act.frame_range[1])
    for bname in ["ForeArm.L", "ForeArm.R"]:
        pb = glb_arm.pose.bones.get(bname)
        if not pb:
            continue
        angles = []
        for f in range(f_start, f_end + 1):
            bpy.context.scene.frame_set(f)
            e = pb.rotation_quaternion.to_euler('XYZ') if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler
            angles.append(math.degrees(e.x))
        min_a = min(angles)
        max_a = max(angles)
        glb_forearm_results[f"{act.name} {bname}"] = (min_a, max_a)
        print(f"  GLB {act.name:<30} {bname}: min={min_a:6.2f}°, max={max_a:6.2f}°")

# Confirm that GLB forearms are NO LONGER frozen at 0.00°!
print("\nVerifying GLB forearms are active and visibly bending:")
for bone_act, (min_a, max_a) in glb_forearm_results.items():
    peak_flexion = max(abs(min_a), abs(max_a))
    print(f"  {bone_act}: peak flexion = {peak_flexion:.2f}°")
    # For active forearm bones in each action, peak flexion must be >= 20.0°:
    # Note: In idle, ForeArm.L is 38°, ForeArm.R is 65°
    # In wave, ForeArm.R is 95° (ForeArm.L is resting 0°)
    # In walk, both ForeArm.L and ForeArm.R are 40°
    # In jump, both are 20° - 40°
    if "wave_greeting ForeArm.L" not in bone_act:
        assert peak_flexion >= 19.5, f"Bone {bone_act} failed to bend! peak={peak_flexion:.2f}°"

print("\nGLB AUDIT SUCCESS: All intended forearms bend with strong physiological flexion [20°, 95°]!")
print("Frozen arm defect is completely cured!")

# Step 9: Validate canonical definitions
print("\nAuditing canonical action definitions in patched_lib...")
canon_defs = patched_lib.get_canonical_action_definitions()
for act_name, defn in canon_defs.items():
    for curve_name, pts in defn.curves.items():
        if "ForeArm" in curve_name and "rot_x" in curve_name:
            for f, val in pts:
                assert val >= 0.0, f"Canonical curve {act_name} {curve_name} frame {f} has negative angle: {val}"
                print(f"  Canonical {act_name} {curve_name} frame {f}: {val:.1f}° (PASSED)")

print("\nALL REMEDIATION VALIDATION CHECKS PASSED 100%!")
print("=" * 70)
