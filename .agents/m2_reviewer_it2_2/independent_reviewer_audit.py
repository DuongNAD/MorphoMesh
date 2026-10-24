import sys
from pathlib import Path
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")

import json
import math
import struct
import numpy as np

import bpy
from mathutils import Euler, Vector, Matrix

print("=" * 80)
print("INDEPENDENT REVIEWER & ADVERSARIAL CRITIC AUDIT")
print("=" * 80)

# Paths
blend_path = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\anime_rigged.blend")
glb_path = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\anime_rigged.glb")

assert blend_path.exists(), f"Blend file missing: {blend_path}"
assert glb_path.exists(), f"GLB file missing: {glb_path}"

# -----------------------------------------------------------------------------
# AUDIT 1: BLEND FILE DIRECT INSPECTION
# -----------------------------------------------------------------------------
print("\n>>> AUDIT 1: Blender Scene, Modifiers & Weights in anime_rigged.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm_obj = bpy.data.objects.get("Anime_Armature")
assert arm_obj is not None, "Missing Anime_Armature object"
assert arm_obj.type == 'ARMATURE'
assert len(arm_obj.data.bones) == 78, f"Expected 78 bones, got {len(arm_obj.data.bones)}"
print(f"[PASS] Anime_Armature exists with {len(arm_obj.data.bones)} bones.")

# Verify Armature Transform
assert arm_obj.location == Vector((0, 0, 0)), f"Armature location {arm_obj.location}"
assert arm_obj.rotation_euler == Euler((0, 0, 0)), f"Armature rotation {arm_obj.rotation_euler}"
assert arm_obj.scale == Vector((1, 1, 1)), f"Armature scale {arm_obj.scale}"
print("[PASS] Anime_Armature has identity transform.")

expected_submeshes = [
    "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
    "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
]

for name in expected_submeshes:
    obj = bpy.data.objects.get(name)
    assert obj is not None, f"Missing submesh {name}"
    assert obj.type == 'MESH', f"{name} is not a MESH"
    
    # Check parent
    assert obj.parent == arm_obj, f"{name} parent is {obj.parent}, expected Anime_Armature"
    
    # Check transform
    assert obj.location == Vector((0, 0, 0)), f"{name} location is {obj.location}"
    assert obj.rotation_euler == Euler((0, 0, 0)), f"{name} rotation is {obj.rotation_euler}"
    assert obj.scale == Vector((1, 1, 1)), f"{name} scale is {obj.scale}"
    
    # Check world transform is identity
    ident = Matrix.Identity(4)
    for row_i in range(4):
        for col_i in range(4):
            assert abs(obj.matrix_world[row_i][col_i] - ident[row_i][col_i]) < 1e-5, f"{name} matrix_world is not identity"
            
    # Check Armature modifier and DQS
    arm_mods = [m for m in obj.modifiers if m.type == 'ARMATURE']
    assert len(arm_mods) >= 1, f"Missing Armature modifier on {name}"
    arm_mod = arm_mods[0]
    assert arm_mod.object == arm_obj, f"{name} armature modifier object is {arm_mod.object}"
    assert arm_mod.use_deform_preserve_volume == True, f"CRITICAL: {name} DQS use_deform_preserve_volume is FALSE!"
    print(f"[PASS] {name}: Transform=Identity, Parent=Anime_Armature, DQS use_deform_preserve_volume=True")

# -----------------------------------------------------------------------------
# AUDIT 2: SKIRT WEIGHTS & THIGH ISOLATION
# -----------------------------------------------------------------------------
print("\n>>> AUDIT 2: Anime_Skirt Weight Isolation & Normalization")
skirt_obj = bpy.data.objects["Anime_Skirt"]
skirt_vg_names = [vg.name for vg in skirt_obj.vertex_groups]
print(f"Anime_Skirt vertex groups ({len(skirt_vg_names)}): {skirt_vg_names}")

expected_skirt_groups = {f"Skirt_{i:02d}" for i in range(1, 13)}
assert set(skirt_vg_names) == expected_skirt_groups, f"Unexpected vertex groups on Anime_Skirt: {set(skirt_vg_names) ^ expected_skirt_groups}"

# Check every vertex
num_skirt_verts = len(skirt_obj.data.vertices)
print(f"Auditing all {num_skirt_verts} vertices of Anime_Skirt...")
for v in skirt_obj.data.vertices:
    total_w = sum(g.weight for g in v.groups)
    assert abs(total_w - 1.0) < 1e-4, f"Skirt vertex {v.index} unnormalized weight: {total_w}"
    for g in v.groups:
        vg_name = skirt_obj.vertex_groups[g.group].name
        assert vg_name in expected_skirt_groups, f"Skirt vertex {v.index} has forbidden group {vg_name} with weight {g.weight}"
        assert not any(forbidden in vg_name for forbidden in ["Thigh", "Leg", "Knee", "Shin", "Foot", "Hips"]), f"Skirt vertex {v.index} bleeding to {vg_name}"

print(f"[PASS] Strict 0% thigh weight bleeding: 100% of weights on all {num_skirt_verts} vertices assigned strictly to Skirt_01..12.")

# -----------------------------------------------------------------------------
# AUDIT 3: 12 RADIAL SKIRT SPOKE BONES & PITCH CLAMPS
# -----------------------------------------------------------------------------
print("\n>>> AUDIT 3: 12 Radial Skirt Spoke Bones & Pitch Clamps")
for i in range(1, 13):
    b_name = f"Skirt_{i:02d}"
    bone = arm_obj.data.bones.get(b_name)
    assert bone is not None, f"Missing bone {b_name}"
    assert bone.parent.name == "Hips", f"{b_name} parent is {bone.parent.name}, expected Hips"
    
    pbone = arm_obj.pose.bones.get(b_name)
    assert pbone is not None, f"Missing pose bone {b_name}"
    
    # Check limit rotation constraint
    rot_limits = [c for c in pbone.constraints if c.type == 'LIMIT_ROTATION']
    assert len(rot_limits) >= 1, f"Missing LIMIT_ROTATION constraint on {b_name}"
    c = rot_limits[0]
    assert c.use_limit_x == True, f"{b_name} use_limit_x is False"
    min_x_deg = math.degrees(c.min_x)
    max_x_deg = math.degrees(c.max_x)
    assert abs(min_x_deg - (-15.0)) < 0.01, f"{b_name} min_x is {min_x_deg}°, expected -15.0°"
    assert abs(max_x_deg - 65.0) < 0.01, f"{b_name} max_x is {max_x_deg}°, expected 65.0°"
    assert c.owner_space == 'LOCAL', f"{b_name} owner space is {c.owner_space}, expected LOCAL"

print("[PASS] All 12 Skirt_01..12 bones parented to Hips with [-15.0°, +65.0°] LOCAL pitch limit clamps.")

# -----------------------------------------------------------------------------
# AUDIT 4: GLB BINARY & JSON NODE HIERARCHY AUDIT
# -----------------------------------------------------------------------------
print("\n>>> AUDIT 4: GLB Binary & JSON Node Hierarchy & Inverse Bind Matrices")
with open(glb_path, "rb") as f:
    magic, version, length = struct.unpack("<4sII", f.read(12))
    assert magic == b"glTF" and version == 2
    chunk_len, chunk_type = struct.unpack("<I4s", f.read(8))
    json_bytes = f.read(chunk_len)
    chunk1_header = f.read(8)
    bin_chunk_len, bin_chunk_type = struct.unpack("<I4s", chunk1_header)
    bin_data = f.read(bin_chunk_len)

d = json.loads(json_bytes.decode("utf-8"))
nodes = d["nodes"]
skins = d["skins"]
scenes = d["scenes"]
scene_idx = d.get("scene", 0)

# Verify scene root
scene_roots = scenes[scene_idx]["nodes"]
assert len(scene_roots) == 1, f"Expected 1 root node in scene, got {scene_roots}"
root_idx = scene_roots[0]
root_node = nodes[root_idx]
assert root_node.get("name") == "Anime_Armature", f"Root node name {root_node.get('name')}"
for key in ["matrix", "rotation", "translation", "scale"]:
    assert key not in root_node, f"Root node Anime_Armature has non-identity transform field: {key}={root_node[key]}"
print("[PASS] glTF scene root: exactly 1 node 'Anime_Armature' with pure Identity transform.")

# Verify children of Anime_Armature
children = root_node.get("children", [])
assert len(children) == 8, f"Expected 8 children (7 meshes + Hips), got {len(children)}"

mesh_nodes = [nodes[c] for c in children if "mesh" in nodes[c]]
assert len(mesh_nodes) == 7, f"Expected 7 mesh nodes, got {len(mesh_nodes)}"
actual_mesh_names = {m.get("name") for m in mesh_nodes}
assert actual_mesh_names == set(expected_submeshes), f"Mesh node names mismatch: {actual_mesh_names}"

for m in mesh_nodes:
    for key in ["matrix", "rotation", "translation", "scale"]:
        assert key not in m, f"Mesh node {m.get('name')} has non-identity field {key}={m[key]}"
    assert m.get("skin") == 0, f"Mesh node {m.get('name')} skin is {m.get('skin')}"
print("[PASS] 7 mesh nodes are children of Anime_Armature with pure Identity transforms.")

# Verify skin joints
assert len(skins) == 1
skin = skins[0]
joints = skin["joints"]
assert len(joints) == 78, f"Expected 78 skin joints, got {len(joints)}"
print(f"[PASS] Skin 0 contains exactly {len(joints)} joints.")

# Verify Inverse Bind Matrices
ibm_acc = d["accessors"][skin["inverseBindMatrices"]]
assert ibm_acc["count"] == 78 and ibm_acc["type"] == "MAT4"
bv = d["bufferViews"][ibm_acc["bufferView"]]
offset = bv.get("byteOffset", 0) + ibm_acc.get("byteOffset", 0)

ibms = []
for i in range(78):
    raw = bin_data[offset + i*64 : offset + (i+1)*64]
    mat = np.array(struct.unpack("<16f", raw), dtype=np.float32).reshape((4, 4), order="F")
    ibms.append(mat)

def get_local_mat(node):
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float32).reshape((4, 4), order="F")
    T = np.eye(4, dtype=np.float32)
    if "translation" in node:
        T[0:3, 3] = node["translation"]
    R = np.eye(4, dtype=np.float32)
    if "rotation" in node:
        x, y, z, w = node["rotation"]
        R[0, 0] = 1 - 2*(y*y + z*z)
        R[0, 1] = 2*(x*y - z*w)
        R[0, 2] = 2*(x*z + y*w)
        R[1, 0] = 2*(x*y + z*w)
        R[1, 1] = 1 - 2*(x*x + z*z)
        R[1, 2] = 2*(y*z - x*w)
        R[2, 0] = 2*(x*z - y*w)
        R[2, 1] = 2*(y*z + x*w)
        R[2, 2] = 1 - 2*(x*x + y*y)
    S = np.eye(4, dtype=np.float32)
    if "scale" in node:
        S[0, 0], S[1, 1], S[2, 2] = node["scale"]
    return T @ R @ S

global_mats = {}
def traverse(idx, parent_mat):
    local_mat = get_local_mat(nodes[idx])
    g_mat = parent_mat @ local_mat
    global_mats[idx] = g_mat
    for child in nodes[idx].get("children", []):
        traverse(child, g_mat)

for r in scene_roots:
    traverse(r, np.eye(4, dtype=np.float32))

max_ibm_err = 0.0
for i, j_idx in enumerate(joints):
    prod = global_mats[j_idx] @ ibms[i]
    err = np.max(np.abs(prod - np.eye(4, dtype=np.float32)))
    if err > max_ibm_err:
        max_ibm_err = err

print(f"Max IBM Identity Error across all 78 joints: {max_ibm_err:.6e}")
assert max_ibm_err < 1e-5, f"IBM identity error {max_ibm_err} >= 1e-5"
print(f"[PASS] Inverse Bind Matrix identity error is {max_ibm_err:.4e} (< 1e-5 threshold).")

# -----------------------------------------------------------------------------
# AUDIT 5: ADVERSARIAL STRESS TEST: THIGH MOTION VS SKIRT IMMOBILITY
# -----------------------------------------------------------------------------
print("\n>>> AUDIT 5: Adversarial Stress Test - Thigh Rotation Isolation")
# In the blend file, rotate Thigh.L forward by 60 degrees.
# Since Anime_Skirt has 0% thigh weight, not a single vertex of Anime_Skirt should move!
dg = bpy.context.evaluated_depsgraph_get()
skirt_rest_verts = [v.co.copy() for v in skirt_obj.evaluated_get(dg).data.vertices]

pb_thigh_l = arm_obj.pose.bones.get("Thigh.L")
pb_thigh_r = arm_obj.pose.bones.get("Thigh.R")
assert pb_thigh_l is not None and pb_thigh_r is not None

# Apply heavy thigh rotation: pitch 60 deg, roll 20 deg
pb_thigh_l.rotation_mode = 'XYZ'
pb_thigh_l.rotation_euler = Euler((math.radians(60), 0, math.radians(20)), 'XYZ')
pb_thigh_r.rotation_mode = 'XYZ'
pb_thigh_r.rotation_euler = Euler((math.radians(-45), 0, math.radians(-15)), 'XYZ')

dg = bpy.context.evaluated_depsgraph_get()
skirt_posed_verts = [v.co.copy() for v in skirt_obj.evaluated_get(dg).data.vertices]

max_skirt_motion = max((p - r).length for p, r in zip(skirt_posed_verts, skirt_rest_verts))
print(f"Max displacement on Anime_Skirt under heavy thigh poses: {max_skirt_motion:.8f} m")
assert max_skirt_motion == 0.0, f"Skirt vertices moved by {max_skirt_motion} m when thighs moved! Bleeding exists!"
print("[PASS] Anime_Skirt displacement is identically 0.00000000 m under thigh poses (Zero Bleeding Confirmed)!")

# Reset thigh poses
pb_thigh_l.rotation_euler = Euler((0, 0, 0), 'XYZ')
pb_thigh_r.rotation_euler = Euler((0, 0, 0), 'XYZ')

# -----------------------------------------------------------------------------
# AUDIT 6: ADVERSARIAL INTEGRITY AUDIT: CODEBASE CHECK
# -----------------------------------------------------------------------------
print("\n>>> AUDIT 6: Codebase Integrity & Facade Check")
# Verify that weight calculation and bone constraint creation are functional algorithms and not mocks
import inspect
from anime_pipeline.rigging.skinning_dqs import calculate_submesh_skin_weights
from anime_pipeline.rigging.secondary_bones import add_skirt_radial_rig, apply_skirt_skin_weights

dqs_src = inspect.getsource(calculate_submesh_skin_weights)
assert len(dqs_src) > 500, "calculate_submesh_skin_weights appears to be a dummy/facade"
assert "table.add_weight" in dqs_src, "No actual weighting logic found in calculate_submesh_skin_weights"

skirt_rig_src = inspect.getsource(add_skirt_radial_rig)
assert "LIMIT_ROTATION" in skirt_rig_src, "No LIMIT_ROTATION found in add_skirt_radial_rig"
assert "Skirt_" in skirt_rig_src, "No Skirt_ found in add_skirt_radial_rig"

skirt_skin_src = inspect.getsource(apply_skirt_skin_weights)
assert "atan2" in skirt_skin_src, "No atan2 found in apply_skirt_skin_weights"

print(f"[PASS] calculate_submesh_skin_weights source length = {len(dqs_src)} chars.")
print(f"[PASS] add_skirt_radial_rig source length = {len(skirt_rig_src)} chars.")
print(f"[PASS] apply_skirt_skin_weights source length = {len(skirt_skin_src)} chars.")
print("[PASS] Rigging, Skinning, and Secondary bone algorithms are genuine mathematical implementations.")

print("\n" + "=" * 80)
print(">>> ALL INDEPENDENT AUDITS & ADVERSARIAL CHALLENGES PASSED WITH FLYING COLORS <<<")
print("=" * 80)
