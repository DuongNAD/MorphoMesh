import json
import struct
import numpy as np
from pathlib import Path

def test_node_integrity(glb_path):
    print(f"=== GLTF NODE INTEGRITY AUDIT: {glb_path} ===")
    with open(glb_path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        chunk_len, chunk_type = struct.unpack("<I4s", f.read(8))
        d = json.loads(f.read(chunk_len).decode("utf-8"))

    nodes = d.get("nodes", [])
    meshes = d.get("meshes", [])
    skins = d.get("skins", [])
    scenes = d.get("scenes", [])
    scene_idx = d.get("scene", 0)
    root_nodes = scenes[scene_idx]["nodes"]

    print(f"Scene root nodes: {root_nodes}")
    assert len(root_nodes) == 1, f"Expected 1 scene root node, got {len(root_nodes)}"
    arm_node_idx = root_nodes[0]
    arm_node = nodes[arm_node_idx]
    print(f"Root node [{arm_node_idx}] name: '{arm_node.get('name')}'")
    assert arm_node.get("name") == "Anime_Armature", f"Root node should be Anime_Armature"

    # Verify Armature root transform is Identity
    assert "translation" not in arm_node, f"Armature has non-identity translation: {arm_node.get('translation')}"
    assert "rotation" not in arm_node, f"Armature has non-identity rotation: {arm_node.get('rotation')}"
    assert "scale" not in arm_node, f"Armature has non-identity scale: {arm_node.get('scale')}"
    assert "matrix" not in arm_node, f"Armature has non-identity matrix: {arm_node.get('matrix')}"
    print("PASS: Anime_Armature root has pure Identity transform.")

    # Check children of Anime_Armature
    children = arm_node.get("children", [])
    print(f"Anime_Armature children count: {len(children)}")
    # Expected: 7 submesh nodes + 1 Hips root bone node = 8 children
    assert len(children) == 8, f"Expected 8 children (7 meshes + 1 Hips), got {len(children)}"

    mesh_nodes = []
    bone_root_nodes = []
    for c_idx in children:
        c_node = nodes[c_idx]
        if "mesh" in c_node:
            mesh_nodes.append((c_idx, c_node))
        else:
            bone_root_nodes.append((c_idx, c_node))

    print(f"Mesh nodes attached to Armature: {len(mesh_nodes)}")
    assert len(mesh_nodes) == 7, f"Expected 7 mesh nodes, got {len(mesh_nodes)}"

    expected_mesh_names = {
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    }
    found_mesh_names = {c_node.get("name") for _, c_node in mesh_nodes}
    assert found_mesh_names == expected_mesh_names, f"Mesh names mismatch: {found_mesh_names} != {expected_mesh_names}"
    print(f"PASS: All 7 expected meshes found: {sorted(list(found_mesh_names))}")

    # Verify all 7 mesh nodes have pure Identity transforms
    for c_idx, c_node in mesh_nodes:
        m_name = c_node.get("name")
        assert "translation" not in c_node, f"Mesh {m_name} has translation: {c_node.get('translation')}"
        assert "rotation" not in c_node, f"Mesh {m_name} has rotation: {c_node.get('rotation')}"
        assert "scale" not in c_node, f"Mesh {m_name} has scale: {c_node.get('scale')}"
        assert "matrix" not in c_node, f"Mesh {m_name} has matrix: {c_node.get('matrix')}"
        assert c_node.get("skin") == 0, f"Mesh {m_name} skin index is {c_node.get('skin')}, expected 0"
    print("PASS: All 7 mesh nodes have pure Identity transforms and reference skin 0.")

    # Check Skin
    assert len(skins) == 1, f"Expected 1 skin, got {len(skins)}"
    skin = skins[0]
    joints = skin.get("joints", [])
    print(f"Skin joints count: {len(joints)}")
    assert len(joints) == 78, f"Expected 78 joints in skin, got {len(joints)}"

    # Check bone node quaternion normalization and scales
    max_quat_norm_err = 0.0
    max_scale_err = 0.0
    for j_idx in joints:
        j_node = nodes[j_idx]
        j_name = j_node.get("name")
        if "rotation" in j_node:
            q = np.array(j_node["rotation"], dtype=np.float64)
            norm = np.linalg.norm(q)
            err = abs(norm - 1.0)
            if err > max_quat_norm_err:
                max_quat_norm_err = err
            assert err < 1e-4, f"Bone {j_name} has non-unit quaternion norm {norm}"
        if "scale" in j_node:
            s = np.array(j_node["scale"], dtype=np.float64)
            err = np.max(np.abs(s - 1.0))
            if err > max_scale_err:
                max_scale_err = err
            assert err < 1e-3, f"Bone {j_name} has non-unit scale {s}"

    print(f"PASS: All 78 bone quaternions normalized (max error = {max_quat_norm_err:.6e}).")
    print(f"PASS: All 78 bone scales uniform unit (max deviation = {max_scale_err:.6e}).")
    print("=== GLTF NODE INTEGRITY: 100% PASS ===")

if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else r"E:\tool\mcp\MorphoMesh\.agents\m2_explorer_remediation_3\test_rigged.glb"
    test_node_integrity(p)
