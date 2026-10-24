import json
import struct
import numpy as np
from pathlib import Path

def test_rest_pose_identity(glb_path):
    print("=== VERIFYING REST POSE INVERSE BIND MATRICES ===")
    with open(glb_path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        chunk_len, chunk_type = struct.unpack("<I4s", f.read(8))
        d = json.loads(f.read(chunk_len).decode("utf-8"))
        f.read(8) # bin header
        bin_data = f.read()

    nodes = d["nodes"]
    skin = d["skins"][0]
    joints = skin["joints"]
    ibm_acc = d["accessors"][skin["inverseBindMatrices"]]
    bv = d["bufferViews"][ibm_acc["bufferView"]]
    offset = bv.get("byteOffset", 0) + ibm_acc.get("byteOffset", 0)
    
    # Read IBMs
    ibms = []
    for i in range(len(joints)):
        raw = bin_data[offset + i*64 : offset + (i+1)*64]
        # Column-major in glTF!
        mat = np.array(struct.unpack("<16f", raw), dtype=np.float32).reshape((4, 4), order="F")
        ibms.append(mat)

    # Compute global transforms of all nodes in scene 0
    # Scene 0 root nodes
    roots = d["scenes"][d.get("scene", 0)]["nodes"]
    
    def get_local_mat(node):
        if "matrix" in node:
            return np.array(node["matrix"], dtype=np.float32).reshape((4, 4), order="F")
        T = np.eye(4, dtype=np.float32)
        if "translation" in node:
            T[0:3, 3] = node["translation"]
        R = np.eye(4, dtype=np.float32)
        if "rotation" in node:
            # glTF quat: [x, y, z, w]
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

    max_identity_err = 0.0
    bad_joints = []
    for i, j_idx in enumerate(joints):
        j_node = nodes[j_idx]
        j_name = j_node.get("name", f"joint_{i}")
        g_mat = global_mats[j_idx]
        ibm = ibms[i]
        prod = g_mat @ ibm
        err = np.max(np.abs(prod - np.eye(4, dtype=np.float32)))
        if err > max_identity_err:
            max_identity_err = err
        if err > 1e-4:
            bad_joints.append((j_name, err))

    print(f"Total skin joints: {len(joints)}")
    print(f"Maximum |GlobalJointTransform * IBM - Identity|: {max_identity_err:.6e}")
    if bad_joints:
        print(f"FAILED JOINTS ({len(bad_joints)}): {bad_joints[:5]}")
    else:
        print("ALL 78 JOINTS HAVE EXACT REST-POSE INVERSE BIND MATRIX IDENTITY!")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else r"E:\tool\mcp\MorphoMesh\.agents\m2_explorer_remediation_3\test_rigged.glb"
    test_rest_pose_identity(path)
