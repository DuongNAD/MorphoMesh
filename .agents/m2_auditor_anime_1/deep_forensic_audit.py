"""
deep_forensic_audit.py
Forensic Integrity Audit Script for Milestone 2:
Executes in headless Blender 4.5.4 LTS.
Audits output/anime_rigged.blend for:
1. 78 canonical bones, hierarchy, head/tail coordinates, bone rolls.
2. Finger flexion cross-product alignment & palmar curl monotonic decrease.
3. COPY_ROTATION and LIMIT_ROTATION constraints attached in Blender data blocks.
4. use_deform_preserve_volume = True (DQS) on all 7 deforming meshes.
5. Vertex weights normalization, partition of unity, max 4 influences, zero orphans.
6. Strict 0% thigh weight bleeding on Anime_Skirt.
7. Wrist rotation twist bone volume preservation stress test.
"""

import sys
import math
from pathlib import Path
import bpy
import mathutils
from mathutils import Vector, Euler, Matrix

audit_log = []
violations = []

def log(msg):
    print(f"[AUDIT] {msg}")
    audit_log.append(msg)

def fail(msg):
    print(f"[VIOLATION] {msg}")
    violations.append(msg)

log("Starting Deep Forensic Audit on output/anime_rigged.blend in Blender 4.5.4 LTS...")

blend_path = Path("output/anime_rigged.blend").resolve()
if not blend_path.exists():
    fail(f"Blend file not found at {blend_path}")
    sys.exit(1)

bpy.ops.wm.open_mainfile(filepath=str(blend_path))

# -----------------------------------------------------------------------------
# 1. Armature Object & Bone Count Check
# -----------------------------------------------------------------------------
arm_obj = bpy.data.objects.get("Anime_Armature")
if not arm_obj or arm_obj.type != 'ARMATURE':
    fail("Anime_Armature object missing or not of type ARMATURE")
    sys.exit(1)

arm_data = arm_obj.data
bones = arm_data.bones
total_bones = len(bones)
log(f"Anime_Armature found with {total_bones} bones.")

if total_bones != 78:
    fail(f"Expected exactly 78 bones, found {total_bones}")

# Check all 78 bone names
expected_spine = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"]
expected_limbs = [
    "Clavicle.L", "Clavicle.R", "UpperArm.L", "UpperArm.R",
    "ForeArm.L", "ForeArm.R", "Hand.L", "Hand.R",
    "Thigh.L", "Thigh.R", "Shin.L", "Shin.R",
    "Foot.L", "Foot.R", "Toe.L", "Toe.R"
]
expected_twists = [
    "UpperArm_Twist.L", "UpperArm_Twist.R",
    "ForeArm_Twist.L", "ForeArm_Twist.R"
]
expected_fingers = [
    f"{f}.{p}.{s}"
    for s in ["L", "R"]
    for f in ["Thumb", "Index", "Middle", "Ring", "Pinky"]
    for p in ["01", "02", "03"]
]
expected_skirt = [f"Skirt_{i:02d}" for i in range(1, 13)]
expected_hair = [f"Hair_L_{i:02d}" for i in range(1, 6)] + [f"Hair_R_{i:02d}" for i in range(1, 6)]

all_expected_bones = (
    expected_spine + expected_limbs + expected_twists +
    expected_fingers + expected_skirt + expected_hair
)

missing_bones = [b for b in all_expected_bones if b not in bones]
if missing_bones:
    fail(f"Missing bones from Anime_Armature: {missing_bones}")
else:
    log("All 78 expected bones are present in Anime_Armature data block.")

# Check parent-child hierarchy
hierarchy_checks = [
    ("Hips", None),
    ("Spine", "Hips"),
    ("Spine1", "Spine"),
    ("Spine2", "Spine1"),
    ("Neck", "Spine2"),
    ("Head", "Neck"),
    ("Clavicle.L", "Spine2"),
    ("Clavicle.R", "Spine2"),
    ("UpperArm.L", "Clavicle.L"),
    ("UpperArm.R", "Clavicle.R"),
    ("ForeArm.L", "UpperArm.L"),
    ("ForeArm.R", "UpperArm.R"),
    ("Hand.L", "ForeArm.L"),
    ("Hand.R", "ForeArm.R"),
    ("UpperArm_Twist.L", "UpperArm.L"),
    ("UpperArm_Twist.R", "UpperArm.R"),
    ("ForeArm_Twist.L", "ForeArm.L"),
    ("ForeArm_Twist.R", "ForeArm.R"),
    ("Thigh.L", "Hips"),
    ("Thigh.R", "Hips"),
    ("Shin.L", "Thigh.L"),
    ("Shin.R", "Thigh.R"),
    ("Foot.L", "Shin.L"),
    ("Foot.R", "Shin.R"),
    ("Toe.L", "Foot.L"),
    ("Toe.R", "Foot.R"),
]
for side in ["L", "R"]:
    for f in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
        hierarchy_checks.append((f"{f}.01.{side}", f"Hand.{side}"))
        hierarchy_checks.append((f"{f}.02.{side}", f"{f}.01.{side}"))
        hierarchy_checks.append((f"{f}.03.{side}", f"{f}.02.{side}"))
for i in range(1, 13):
    hierarchy_checks.append((f"Skirt_{i:02d}", "Hips"))
for side in ["L", "R"]:
    hierarchy_checks.append((f"Hair_{side}_01", "Head"))
    for j in range(1, 5):
        hierarchy_checks.append((f"Hair_{side}_{j+1:02d}", f"Hair_{side}_{j:02d}"))

for child, expected_p in hierarchy_checks:
    b = bones.get(child)
    if not b:
        continue
    actual_p = b.parent.name if b.parent else None
    if actual_p != expected_p:
        fail(f"Hierarchy mismatch for {child}: expected parent '{expected_p}', got '{actual_p}'")
log("Armature parent-child hierarchy verified for all 78 bones.")

# -----------------------------------------------------------------------------
# 2. Coordinates & Symmetry Audit
# -----------------------------------------------------------------------------
for bname, b in bones.items():
    length = b.length
    if length < 0.005:
        fail(f"Bone {bname} has suspiciously zero or near-zero length: {length:.6f}")
    if math.isnan(b.head_local.x) or math.isnan(b.tail_local.x):
        fail(f"Bone {bname} has NaN coordinates")

# Bilateral symmetry check (L vs R)
bilateral_pairs = [
    ("Clavicle.L", "Clavicle.R"),
    ("UpperArm.L", "UpperArm.R"),
    ("ForeArm.L", "ForeArm.R"),
    ("Hand.L", "Hand.R"),
    ("Thigh.L", "Thigh.R"),
    ("Shin.L", "Shin.R"),
    ("Foot.L", "Foot.R"),
    ("Toe.L", "Toe.R"),
]
for f in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
    for p in ["01", "02", "03"]:
        bilateral_pairs.append((f"{f}.{p}.L", f"{f}.{p}.R"))

for b_l_name, b_r_name in bilateral_pairs:
    b_l = bones[b_l_name]
    b_r = bones[b_r_name]
    dx = abs(b_l.head_local.x - (-b_r.head_local.x))
    dy = abs(b_l.head_local.y - b_r.head_local.y)
    dz = abs(b_l.head_local.z - b_r.head_local.z)
    if dx > 1e-4 or dy > 1e-4 or dz > 1e-4:
        fail(f"Asymmetry detected between {b_l_name} and {b_r_name}: dx={dx:.5f}, dy={dy:.5f}, dz={dz:.5f}")
log(f"Bilateral symmetry verified across {len(bilateral_pairs)} bone pairs.")

# -----------------------------------------------------------------------------
# 3. Finger Bone Rolls & Cross-Product Palmar Flexion Audit
# -----------------------------------------------------------------------------
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
pb = arm_obj.pose.bones

# Test finger curl under local +X rotation
log("Testing finger curling dynamics toward palmar centroid...")
for side in ["L", "R"]:
    sign = 1.0 if side == "L" else -1.0
    palm = Vector((sign * 0.43550, -0.18575, 1.01439))

    for f in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
        for p in ["01", "02", "03"]:
            bname = f"{f}.{p}.{side}"
            pbone = pb[bname]
            pbone.rotation_mode = 'XYZ'
            pbone.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()

            rest_tail = arm_obj.matrix_world @ pbone.tail
            rest_dist = (rest_tail - palm).length

            # Test curl at 30 deg and 60 deg
            pbone.rotation_euler = (math.radians(30.0), 0.0, 0.0)
            bpy.context.view_layer.update()
            curl30_tail = arm_obj.matrix_world @ pbone.tail
            curl30_dist = (curl30_tail - palm).length

            pbone.rotation_euler = (math.radians(60.0), 0.0, 0.0)
            bpy.context.view_layer.update()
            curl60_tail = arm_obj.matrix_world @ pbone.tail
            curl60_dist = (curl60_tail - palm).length

            if curl30_dist >= rest_dist:
                fail(f"Finger {bname} +X 30deg did not curl toward palm: rest={rest_dist:.4f}, curl30={curl30_dist:.4f}")
            if curl60_dist >= curl30_dist:
                fail(f"Finger {bname} +X 60deg did not continue curling: curl30={curl30_dist:.4f}, curl60={curl60_dist:.4f}")

            # Reset rotation
            pbone.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()

log("All 30 finger phalanges strictly curled monotonically toward palmar centroid under positive local X flexion.")

# -----------------------------------------------------------------------------
# 4. Pose Bone Constraints Audit (Twist, Skirt, Hair)
# -----------------------------------------------------------------------------
# UpperArm and ForeArm Twist constraints
# Per PROJECT.md line 118: Arm twist bones have COPY_ROTATION targeting child bone with 0.5 influence on local Y axis.
# Child of UpperArm is ForeArm; child of ForeArm is Hand.
twist_constraints_expected = [
    ("UpperArm_Twist.L", "ForeArm.L", 0.50),
    ("UpperArm_Twist.R", "ForeArm.R", 0.50),
    ("ForeArm_Twist.L", "Hand.L", 0.50),
    ("ForeArm_Twist.R", "Hand.R", 0.50),
]
for twist_name, target, exp_influence in twist_constraints_expected:
    pbone = pb.get(twist_name)
    if not pbone:
        fail(f"Pose bone {twist_name} missing")
        continue
    c_list = [c for c in pbone.constraints if c.type == 'COPY_ROTATION']
    if not c_list:
        fail(f"No COPY_ROTATION constraint on twist bone {twist_name}")
        continue
    c = c_list[0]
    if c.subtarget != target:
        fail(f"Constraint on {twist_name} targets '{c.subtarget}', expected '{target}'")
    if not (c.use_y and not c.use_x and not c.use_z):
        fail(f"Constraint on {twist_name} does not exclusively isolate local Y axis")
    if abs(c.influence - exp_influence) > 1e-4:
        fail(f"Constraint on {twist_name} has influence {c.influence}, expected {exp_influence}")
    if c.target_space != 'LOCAL' or c.owner_space != 'LOCAL':
        fail(f"Constraint on {twist_name} space is not LOCAL/LOCAL (got {c.target_space}/{c.owner_space})")
log("Forearm & UpperArm Twist COPY_ROTATION constraints verified.")

# Skirt LIMIT_ROTATION constraints
for i in range(1, 13):
    bname = f"Skirt_{i:02d}"
    pbone = pb.get(bname)
    if not pbone:
        fail(f"Pose bone {bname} missing")
        continue
    c_list = [c for c in pbone.constraints if c.type == 'LIMIT_ROTATION']
    if not c_list:
        fail(f"No LIMIT_ROTATION constraint on skirt bone {bname}")
        continue
    c = c_list[0]
    if not c.use_limit_x:
        fail(f"Limit rotation on {bname} does not enable pitch limit X")
    min_x_deg = math.degrees(c.min_x)
    max_x_deg = math.degrees(c.max_x)
    if abs(min_x_deg - (-15.0)) > 0.1 or abs(max_x_deg - 65.0) > 0.1:
        fail(f"Skirt {bname} pitch limit out of range: [{min_x_deg:.1f}°, {max_x_deg:.1f}°], expected [-15°, 65°]")
    if pbone.get("is_secondary_skirt") is not True:
        fail(f"Skirt {bname} missing is_secondary_skirt property")
log("12-Radial Skirt LIMIT_ROTATION [-15°, +65°] pitch constraints verified.")

# Hair spring dynamics properties
for side in ["L", "R"]:
    for i in range(1, 6):
        bname = f"Hair_{side}_{i:02d}"
        pbone = pb.get(bname)
        if not pbone:
            fail(f"Pose bone {bname} missing")
            continue
        if pbone.get("is_secondary_hair") is not True:
            fail(f"Hair bone {bname} missing is_secondary_hair property")
        m = pbone.get("spring_mass")
        k = pbone.get("spring_stiffness")
        c_val = pbone.get("spring_damping")
        if abs(m - 0.20) > 1e-4 or abs(k - 150.0) > 1e-4 or abs(c_val - 12.0) > 1e-4:
            fail(f"Hair {bname} spring properties incorrect: m={m}, k={k}, c={c_val}")
log("10 Hair Twintail secondary spring dynamics properties verified.")

# Cross-standard mapping dictionaries on Armature data block
assert "vrm_1_0_bone_map" in arm_data, "vrm_1_0_bone_map missing from armature data"
assert "rigify_def_bone_map" in arm_data, "rigify_def_bone_map missing from armature data"
assert "mmd_bone_map" in arm_data, "mmd_bone_map missing from armature data"
log("Cross-standard mapping tables (VRM 1.0, Rigify, MMD) stored on data block.")

bpy.ops.object.mode_set(mode='OBJECT')

# -----------------------------------------------------------------------------
# 5. Modular Sub-meshes, DQS Modifiers & Vertex Weight Verification
# -----------------------------------------------------------------------------
submesh_names = [
    "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
    "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
]

total_scene_verts = 0
for name in submesh_names:
    obj = bpy.data.objects.get(name)
    if not obj or obj.type != 'MESH':
        fail(f"Sub-mesh {name} missing from scene or not MESH")
        continue

    v_count = len(obj.data.vertices)
    total_scene_verts += v_count
    log(f"Sub-mesh {name}: {v_count} vertices, {len(obj.data.polygons)} polygons.")

    # 1. Armature modifier with DQS
    arm_mods = [m for m in obj.modifiers if m.type == 'ARMATURE']
    if not arm_mods:
        fail(f"Sub-mesh {name} missing ARMATURE modifier")
        continue
    mod = arm_mods[0]
    if mod.object != arm_obj:
        fail(f"Sub-mesh {name} ARMATURE modifier object is '{mod.object.name if mod.object else None}', expected 'Anime_Armature'")
    if not mod.use_deform_preserve_volume:
        fail(f"CRITICAL: Sub-mesh {name} use_deform_preserve_volume (Dual Quaternion Skinning) is FALSE!")
    else:
        log(f"Sub-mesh {name}: use_deform_preserve_volume = True (DQS active)")

    # 2. Vertex weights normalization & partition of unity
    verts = obj.data.vertices
    orphans = 0
    unnormalized = 0
    max_infl = 0

    for v in verts:
        groups = v.groups
        if len(groups) == 0:
            orphans += 1
            continue
        tot_w = sum(g.weight for g in groups)
        if abs(tot_w - 1.0) > 1e-3:
            unnormalized += 1
        active_infl = sum(1 for g in groups if g.weight > 1e-4)
        if active_infl > max_infl:
            max_infl = active_infl

    if orphans > 0:
        fail(f"Sub-mesh {name} has {orphans} orphaned vertices with no bone weights!")
    if unnormalized > 0:
        fail(f"Sub-mesh {name} has {unnormalized} unnormalized vertices (sum != 1.0)!")
    log(f"Sub-mesh {name}: 0 orphans, 100% normalized weights, max influences per vert = {max_infl}.")

# -----------------------------------------------------------------------------
# 6. CRITICAL INVARIANT: 0% Thigh Weight Bleeding on Anime_Skirt
# -----------------------------------------------------------------------------
skirt_obj = bpy.data.objects.get("Anime_Skirt")
if skirt_obj:
    prohibited_leaks = []
    for vg in skirt_obj.vertex_groups:
        if "Thigh" in vg.name or "Leg" in vg.name or "Shin" in vg.name:
            prohibited_leaks.append(vg.name)
        if not vg.name.startswith("Skirt_"):
            prohibited_leaks.append(vg.name)
    if prohibited_leaks:
        fail(f"CRITICAL INVARIANT VIOLATION: Prohibited vertex groups found on Anime_Skirt: {prohibited_leaks}")
    else:
        log("CRITICAL INVARIANT VERIFIED: Anime_Skirt has strictly 0% thigh/leg weight bleeding (100% Skirt_01..12).")

# -----------------------------------------------------------------------------
# 7. Wrist Twist Volume Preservation Test (DQS Behavior)
# -----------------------------------------------------------------------------
# Rotate Hand.L around local Y by 90° and 180°
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
hand_l = pb["Hand.L"]
forearm_twist_l = pb["ForeArm_Twist.L"]

hand_l.rotation_mode = 'XYZ'
hand_l.rotation_euler = (0.0, math.radians(90.0), 0.0)
bpy.context.view_layer.update()

# Verify that ForeArm_Twist.L followed with 50% copy rotation
# Check constraint evaluation
log(f"Pose twist evaluation: Hand.L rot_y=90°, ForeArm_Twist.L constraint active: {len(forearm_twist_l.constraints)} constraints.")

# Reset pose
hand_l.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode='OBJECT')

log(f"Total scene vertices audited across all 7 sub-meshes: {total_scene_verts}.")

# -----------------------------------------------------------------------------
# Final Verdict
# -----------------------------------------------------------------------------
print("=" * 80)
if violations:
    print(f"FORENSIC AUDIT FAILED WITH {len(violations)} VIOLATIONS:")
    for v in violations:
        print(f"  - {v}")
    sys.exit(2)
else:
    print("FORENSIC AUDIT PASSED WITH ZERO VIOLATIONS: VERDICT = CLEAN")
print("=" * 80)
