import json
import struct
import numpy as np

GLB_PATH = "output/yu_nian_an/Yu_Nian_An.glb"

with open(GLB_PATH, "rb") as f:
    f.seek(12)
    chunk_len, _ = struct.unpack("<II", f.read(8))
    json_data = json.loads(f.read(chunk_len).decode("utf-8"))
    bin_len, _ = struct.unpack("<II", f.read(8))
    bin_data = f.read(bin_len)

print("=== SKINNING WEIGHTS AUDIT ACROSS GLB PRIMITIVES ===")
skinned_prims = 0
unskinned_prims = 0
invalid_weight_prims = []

for m_idx, m in enumerate(json_data["meshes"]):
    m_name = m.get("name", f"mesh_{m_idx}")
    for p_idx, p in enumerate(m["primitives"]):
        attrs = p.get("attributes", {})
        if "WEIGHTS_0" in attrs and "JOINTS_0" in attrs:
            skinned_prims += 1
            w_acc = json_data["accessors"][attrs["WEIGHTS_0"]]
            w_bv = json_data["bufferViews"][w_acc["bufferView"]]
            w_off = w_bv.get("byteOffset", 0) + w_acc.get("byteOffset", 0)
            w_cnt = w_acc["count"]
            weights = np.frombuffer(bin_data, dtype=np.float32, count=w_cnt * 4, offset=w_off).reshape((w_cnt, 4))

            j_acc = json_data["accessors"][attrs["JOINTS_0"]]
            j_bv = json_data["bufferViews"][j_acc["bufferView"]]
            j_off = j_bv.get("byteOffset", 0) + j_acc.get("byteOffset", 0)
            j_cnt = j_acc["count"]
            # Check joints component type (5121=ubyte, 5123=ushort)
            j_dtype = np.uint8 if j_acc["componentType"] == 5121 else np.uint16
            joints = np.frombuffer(bin_data, dtype=j_dtype, count=j_cnt * 4, offset=j_off).reshape((j_cnt, 4))

            # Validate weights
            w_sum = np.sum(weights, axis=1)
            bad_sum = np.where(np.abs(w_sum - 1.0) > 0.05)[0]
            bad_neg = np.where(weights < -1e-6)[0]
            bad_nan = np.where(np.isnan(weights))[0]
            bad_joints = np.where(joints >= 164)[0]

            if len(bad_sum) > 0 or len(bad_neg) > 0 or len(bad_nan) > 0 or len(bad_joints) > 0:
                invalid_weight_prims.append((f"{m_name}[{p_idx}]", {
                    "bad_sum": len(bad_sum),
                    "bad_neg": len(bad_neg),
                    "bad_nan": len(bad_nan),
                    "bad_joints": len(bad_joints)
                }))
        else:
            unskinned_prims += 1

print(f"Skinned primitives: {skinned_prims}")
print(f"Unskinned primitives: {unskinned_prims}")
print(f"Invalid weight primitives: {len(invalid_weight_prims)} {invalid_weight_prims}")
assert len(invalid_weight_prims) == 0, "Found invalid skin weights in GLB!"
print("All skinned primitives have valid normalized weights (sum=1.0, non-negative, joints < 164)!")
