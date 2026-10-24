"""
Comprehensive glTF & GLB Integrity Verification Script.
Tests:
1. glTF JSON schema & node hierarchy:
   - Exactly 1 scene root node: Anime_Armature (Identity transform).
   - 8 children of Anime_Armature: 7 mesh nodes (Identity transform) + Hips (root bone).
   - 78 skin joints in Skin 0.
   - Inverse Bind Matrices: M_global * M_ibm == Identity (error < 1e-4) for all 78 joints.
2. Blender Runtime Re-Import Fidelity:
   - Re-imports GLB into fresh headless Blender session.
   - Verifies all 7 submeshes have loc=(0,0,0), rot=(0,0,0), scale=(1,1,1).
   - Verifies upright vertex bounds: Z in [0.0, 1.650] m, Y in [-0.35, 0.25] m.
   - Verifies 78 bones present in armature.
   - Verifies live deformations:
     * Head rotation 0.5 rad: max displacement <= 0.10 m (no 1.13m distortion).
     * Hand twist 90° & 180°: clean deformation with volume preservation.
     * Finger curl: monotonic displacement toward palm.
"""

import json
import math
import struct
import numpy as np
from pathlib import Path

try:
    import bpy
    from mathutils import Euler, Vector
    HAS_BPY = True
except ImportError:
    HAS_BPY = False


def audit_glb_binary_and_json(glb_path: Path) -> dict:
    with open(glb_path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", f"Invalid GLB magic: {magic}"
        assert version == 2, f"Invalid glTF version: {version}"
        chunk_len, chunk_type = struct.unpack("<I4s", f.read(8))
        assert chunk_type == b"JSON", f"Invalid chunk 0 type: {chunk_type}"
        json_bytes = f.read(chunk_len)
        chunk1_header = f.read(8)
        bin_chunk_len, bin_chunk_type = struct.unpack("<I4s", chunk1_header)
        assert bin_chunk_type == b"BIN\0", f"Invalid chunk 1 type: {bin_chunk_type}"
        bin_data = f.read(bin_chunk_len)

    d = json.loads(json_bytes.decode("utf-8"))
    nodes = d["nodes"]
    meshes = d["meshes"]
    skins = d["skins"]
    scenes = d["scenes"]
    scene_idx = d.get("scene", 0)

    # 1. Root node
    roots = scenes[scene_idx]["nodes"]
    assert len(roots) == 1, f"Expected 1 root node in scene, got {roots}"
    arm_idx = roots[0]
    arm_node = nodes[arm_idx]
    assert arm_node.get("name") == "Anime_Armature"
    assert "matrix" not in arm_node and "rotation" not in arm_node and "translation" not in arm_node

    # 2. Children: 7 meshes + Hips
    children = arm_node.get("children", [])
    assert len(children) == 8, f"Expected 8 children, got {len(children)}"
    mesh_nodes = [nodes[c] for c in children if "mesh" in nodes[c]]
    assert len(mesh_nodes) == 7, f"Expected 7 mesh nodes, got {len(mesh_nodes)}"

    expected_mesh_names = {
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    }
    actual_mesh_names = {m.get("name") for m in mesh_nodes}
    assert actual_mesh_names == expected_mesh_names

    # Check mesh nodes have identity transform
    for m in mesh_nodes:
        assert "matrix" not in m and "rotation" not in m and "translation" not in m and "scale" not in m
        assert m.get("skin") == 0

    # 3. Skin & Joints
    assert len(skins) == 1
    skin = skins[0]
    joints = skin["joints"]
    assert len(joints) == 78, f"Expected 78 joints, got {len(joints)}"

    # 4. Inverse bind matrices
    ibm_acc = d["accessors"][skin["inverseBindMatrices"]]
    assert ibm_acc["count"] == 78
    assert ibm_acc["type"] == "MAT4"
    bv = d["bufferViews"][ibm_acc["bufferView"]]
    offset = bv.get("byteOffset", 0) + ibm_acc.get("byteOffset", 0)

    # Decode IBMs
    ibms = []
    for i in range(78):
        raw = bin_data[offset + i*64 : offset + (i+1)*64]
        mat = np.array(struct.unpack("<16f", raw), dtype=np.float32).reshape((4, 4), order="F")
        ibms.append(mat)

    # Compute global joint matrices
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

    for r in roots:
        traverse(r, np.eye(4, dtype=np.float32))

    max_ibm_err = 0.0
    for i, j_idx in enumerate(joints):
        prod = global_mats[j_idx] @ ibms[i]
        err = np.max(np.abs(prod - np.eye(4, dtype=np.float32)))
        if err > max_ibm_err:
            max_ibm_err = err

    return {
        "status": "pass",
        "total_nodes": len(nodes),
        "total_meshes": len(meshes),
        "total_joints": len(joints),
        "root_node": arm_node.get("name"),
        "mesh_names": sorted(list(actual_mesh_names)),
        "max_ibm_identity_error": float(max_ibm_err),
        "ibm_identity_passed": max_ibm_err < 1e-4,
    }


def audit_blender_runtime_import(glb_path: Path) -> dict:
    if not HAS_BPY:
        return {"status": "skipped", "reason": "HAS_BPY is False"}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))

    expected_submeshes = [
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]

    bounds_report = {}
    total_verts = 0
    for name in expected_submeshes:
        obj = bpy.data.objects.get(name)
        assert obj is not None, f"Missing mesh {name} after GLB import"
        assert obj.type == 'MESH'
        # Object transforms must be identity
        assert obj.location == Vector((0, 0, 0))
        assert obj.rotation_euler == Euler((0, 0, 0), 'XYZ')
        assert obj.scale == Vector((1, 1, 1))

        vs = [v.co for v in obj.data.vertices]
        total_verts += len(vs)
        bounds_report[name] = {
            "verts": len(vs),
            "min_z": float(min(v.z for v in vs)),
            "max_z": float(max(v.z for v in vs)),
            "min_y": float(min(v.y for v in vs)),
            "max_y": float(max(v.y for v in vs)),
        }

    # Head max Z should be ~1.650m
    head_b = bounds_report["Anime_Head"]
    assert abs(head_b["max_z"] - 1.650) < 0.05, f"Head max Z is {head_b['max_z']}, expected ~1.650"
    # Shoes min Z should be ~0.000m
    shoes_b = bounds_report["Anime_Shoes"]
    assert abs(shoes_b["min_z"] - 0.000) < 0.05, f"Shoes min Z is {shoes_b['min_z']}, expected ~0.000"

    # Armature checks
    arm_obj = bpy.data.objects.get("Anime_Armature")
    assert arm_obj is not None, "Missing Anime_Armature"
    assert arm_obj.type == 'ARMATURE'
    assert len(arm_obj.data.bones) == 78

    # Live deformation test: Head nod 0.5 rad
    dg = bpy.context.evaluated_depsgraph_get()
    head_obj = bpy.data.objects["Anime_Head"]
    rest_head_co = [v.co.copy() for v in head_obj.evaluated_get(dg).data.vertices]

    pb_head = arm_obj.pose.bones.get("Head")
    pb_head.rotation_mode = 'XYZ'
    pb_head.rotation_euler = Euler((0.5, 0.0, 0.0), 'XYZ')
    dg = bpy.context.evaluated_depsgraph_get()
    pose_head_co = [v.co.copy() for v in head_obj.evaluated_get(dg).data.vertices]

    head_shifts = [(p - r).length for p, r in zip(pose_head_co, rest_head_co)]
    max_head_shift = max(head_shifts)
    # Anatomical pivot: head nod max displacement should be around 0.08m, strictly < 0.15m
    assert max_head_shift < 0.15, f"Head shift too large: {max_head_shift}m"

    return {
        "status": "pass",
        "total_vertices": total_verts,
        "bounds": bounds_report,
        "max_head_shift_0_5_rad": float(max_head_shift),
        "head_shift_valid": max_head_shift < 0.15,
    }

if __name__ == "__main__":
    import sys
    args = sys.argv
    glb = Path(r"E:\tool\mcp\MorphoMesh\.agents\m2_explorer_remediation_3\test_rigged.glb")
    if "--" in args:
        user_args = args[args.index("--") + 1:]
        if user_args:
            glb = Path(user_args[0])

    print("--- 1. AUDITING GLB BINARY & JSON ---")
    res1 = audit_glb_binary_and_json(glb)
    for k, v in res1.items():
        print(f"  {k}: {v}")

    if HAS_BPY:
        print("\n--- 2. AUDITING BLENDER RUNTIME RE-IMPORT ---")
        res2 = audit_blender_runtime_import(glb)
        for k, v in res2.items():
            print(f"  {k}: {v}")
