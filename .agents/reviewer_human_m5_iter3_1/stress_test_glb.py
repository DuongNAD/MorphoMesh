import json
import struct
import os
import numpy as np

GLB_PATH = "output/yu_nian_an/Yu_Nian_An.glb"

with open(GLB_PATH, "rb") as f:
    f.seek(12)
    chunk_len, _ = struct.unpack("<II", f.read(8))
    json_data = json.loads(f.read(chunk_len).decode("utf-8"))
    bin_len, _ = struct.unpack("<II", f.read(8))
    bin_data = f.read(bin_len)

print("=== MULTI-PRIMITIVE MESHES ===")
for m in json_data["meshes"]:
    if len(m["primitives"]) > 1:
        print(f"Mesh '{m['name']}' has {len(m['primitives'])} primitives:")
        for idx, p in enumerate(m["primitives"]):
            mat_idx = p.get("material")
            mat_name = json_data["materials"][mat_idx]["name"] if mat_idx is not None else "None"
            print(f"  prim {idx}: material={mat_name}, attrs={list(p.get('attributes', {}).keys())}")

print("\n=== GLB MORPH TARGET DELTA VERIFICATION ===")
body_mesh = next(m for m in json_data["meshes"] if "Body" in m.get("name", ""))
target_names = body_mesh.get("extras", {}).get("targetNames", [])
targets = body_mesh["primitives"][0].get("targets", [])
print(f"Target deltas count: {len(targets)} vs targetNames count: {len(target_names)}")

zero_delta_targets = []
delta_magnitudes = {}

for idx, t in enumerate(targets):
    t_name = target_names[idx] if idx < len(target_names) else f"target_{idx}"
    pos_acc_idx = t.get("POSITION")
    if pos_acc_idx is None:
        zero_delta_targets.append((t_name, "No POSITION accessor"))
        continue
    acc = json_data["accessors"][pos_acc_idx]
    if "bufferView" not in acc:
        if "sparse" in acc:
            # Sparse accessor
            sp = acc["sparse"]
            cnt = sp["count"]
            # Read indices
            idx_bv = json_data["bufferViews"][sp["indices"]["bufferView"]]
            idx_off = idx_bv.get("byteOffset", 0) + sp["indices"].get("byteOffset", 0)
            # Read values
            val_bv = json_data["bufferViews"][sp["values"]["bufferView"]]
            val_off = val_bv.get("byteOffset", 0) + sp["values"].get("byteOffset", 0)
            vals = np.frombuffer(bin_data, dtype=np.float32, count=cnt * 3, offset=val_off).reshape((cnt, 3))
            max_disp = float(np.max(np.linalg.norm(vals, axis=1)))
            delta_magnitudes[t_name] = max_disp
            print(f"  Sparse target '{t_name}': sparse count={cnt}, max_disp={max_disp:.6f}m")
        else:
            print(f"  Target '{t_name}' has no bufferView and no sparse! (all zeros)")
            zero_delta_targets.append((t_name, "No bufferView and no sparse"))
        continue
    bv = json_data["bufferViews"][acc["bufferView"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    cnt = acc["count"]
    deltas = np.frombuffer(bin_data, dtype=np.float32, count=cnt * 3, offset=off).reshape((cnt, 3))
    max_disp = float(np.max(np.linalg.norm(deltas, axis=1)))
    delta_magnitudes[t_name] = max_disp
    if max_disp < 1e-5:
        zero_delta_targets.append((t_name, f"Max disp {max_disp}"))

print(f"Total shape keys tested: {len(targets)}")
print(f"Zero delta targets: {len(zero_delta_targets)} {zero_delta_targets}")
print(f"Min non-zero target displacement: {min(delta_magnitudes.values()):.6f}m ({min(delta_magnitudes, key=delta_magnitudes.get)})")
print(f"Max non-zero target displacement: {max(delta_magnitudes.values()):.6f}m ({max(delta_magnitudes, key=delta_magnitudes.get)})")

print("\nSample displacements:")
for k in ["eyeBlinkLeft", "eyeBlinkRight", "jawOpen", "mouthSmileLeft", "mouthSmileRight", "browDownLeft"]:
    print(f"  {k}: {delta_magnitudes.get(k, 'N/A'):.6f}m")

print("\n=== GLB SKIN INVERSE BIND MATRICES & JOINTS ===")
skin = json_data["skins"][0]
ibm_acc_idx = skin.get("inverseBindMatrices")
acc_ibm = json_data["accessors"][ibm_acc_idx]
bv_ibm = json_data["bufferViews"][acc_ibm["bufferView"]]
off_ibm = bv_ibm.get("byteOffset", 0) + acc_ibm.get("byteOffset", 0)
cnt_ibm = acc_ibm["count"]
ibms = np.frombuffer(bin_data, dtype=np.float32, count=cnt_ibm * 16, offset=off_ibm).reshape((cnt_ibm, 4, 4))
print(f"IBM count: {cnt_ibm}, joints count: {len(skin['joints'])}")
assert cnt_ibm == len(skin["joints"]), "IBM count mismatch with joints count"

# Check if inverse bind matrices are degenerate / identity / valid
det_ibms = [np.linalg.det(m) for m in ibms]
singular_ibms = [i for i, d in enumerate(det_ibms) if abs(d) < 1e-6]
print(f"Singular / degenerate inverse bind matrices: {len(singular_ibms)}")
assert len(singular_ibms) == 0, f"Found singular IBMs at indices: {singular_ibms}"
print("All Inverse Bind Matrices are non-singular and valid!")
