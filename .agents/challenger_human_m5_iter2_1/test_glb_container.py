"""
Empirical GLB Container Parser and Stress Test
Tests Yu_Nian_An.glb for:
1. 100% of primitives having TEXCOORD_0
2. Exact UV coordinate bounds per mesh primitive directly extracted from binary buffer
3. 164 skin joints and valid inverse bind matrices
4. 52 ARKit morph targets in targets and extras.targetNames
"""
import json
import struct
import math
from pathlib import Path

glb_path = Path("output/yu_nian_an/Yu_Nian_An.glb")
assert glb_path.exists(), f"GLB file does not exist at {glb_path}"
file_size = glb_path.stat().st_size
print(f"GLB File: {glb_path} ({file_size} bytes)")

with open(glb_path, "rb") as f:
    magic, version, length = struct.unpack("<4sII", f.read(12))
    assert magic == b"glTF", f"Invalid magic: {magic}"
    assert version == 2, f"Expected glTF 2.0, got version {version}"
    assert length == file_size, f"Header length {length} != file size {file_size}"
    
    # Chunk 0: JSON
    c0_len, c0_type = struct.unpack("<II", f.read(8))
    assert c0_type == 0x4E4F534A, f"Expected JSON chunk (0x4E4F534A), got {hex(c0_type)}"
    json_bytes = f.read(c0_len)
    gltf = json.loads(json_bytes.decode("utf-8"))
    
    # Chunk 1: BIN
    c1_len, c1_type = struct.unpack("<II", f.read(8))
    assert c1_type == 0x004E4942, f"Expected BIN chunk (0x004E4942), got {hex(c1_type)}"
    bin_bytes = f.read(c1_len)

print(f"glTF JSON decoded: {len(gltf.get('meshes', []))} meshes, {len(gltf.get('accessors', []))} accessors, {len(gltf.get('bufferViews', []))} bufferViews")
print(f"glTF BIN buffer size: {len(bin_bytes)} bytes")

# Helper to read accessor data from bin
def read_accessor_floats(accessor_idx):
    acc = gltf["accessors"][accessor_idx]
    count = acc["count"]
    acc_type = acc["type"]
    comp_type = acc["componentType"] # 5126 = FLOAT
    bv_idx = acc["bufferView"]
    bv = gltf["bufferViews"][bv_idx]
    byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    byte_stride = bv.get("byteStride", 0)
    
    type_sizes = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    num_comp = type_sizes[acc_type]
    
    if comp_type != 5126:
        return None
        
    floats = []
    if byte_stride == 0 or byte_stride == num_comp * 4:
        # Contiguous
        fmt = f"<{count * num_comp}f"
        data = struct.unpack(fmt, bin_bytes[byte_offset:byte_offset + count * num_comp * 4])
        if num_comp == 1:
            return list(data)
        else:
            return [data[i*num_comp : (i+1)*num_comp] for i in range(count)]
    else:
        # Strided
        res = []
        for i in range(count):
            start = byte_offset + i * byte_stride
            fmt = f"<{num_comp}f"
            res.append(struct.unpack(fmt, bin_bytes[start:start + num_comp * 4]))
        return res

# 1. Inspect all primitives for TEXCOORD_0
total_primitives = 0
primitives_with_uv = 0
missing_uv_primitives = []
uv_stats_by_mesh = {}

for mesh_idx, mesh in enumerate(gltf.get("meshes", [])):
    m_name = mesh.get("name", f"mesh_{mesh_idx}")
    for p_idx, prim in enumerate(mesh.get("primitives", [])):
        total_primitives += 1
        attrs = prim.get("attributes", {})
        if "TEXCOORD_0" in attrs:
            primitives_with_uv += 1
            uv_acc_idx = attrs["TEXCOORD_0"]
            uv_acc = gltf["accessors"][uv_acc_idx]
            uv_min = uv_acc.get("min", [None, None])
            uv_max = uv_acc.get("max", [None, None])
            
            # Read actual data to double-check
            uv_data = read_accessor_floats(uv_acc_idx)
            u_vals = [uv[0] for uv in uv_data]
            v_vals = [uv[1] for uv in uv_data]
            actual_u_min, actual_u_max = min(u_vals), max(u_vals)
            actual_v_min, actual_v_max = min(v_vals), max(v_vals)
            
            # Check for NaN / Inf
            assert not any(math.isnan(u) or math.isinf(u) for u in u_vals), f"NaN/Inf U in {m_name} prim {p_idx}"
            assert not any(math.isnan(v) or math.isinf(v) for v in v_vals), f"NaN/Inf V in {m_name} prim {p_idx}"
            
            uv_stats_by_mesh[f"{m_name}_p{p_idx}"] = {
                "count": len(uv_data),
                "u_range": (actual_u_min, actual_u_max),
                "v_range": (actual_v_min, actual_v_max),
                "accessor_min": uv_min,
                "accessor_max": uv_max
            }
        else:
            missing_uv_primitives.append(f"{m_name}_p{p_idx}")

print(f"\n--- PRIMITIVE UV SUMMARY ---")
print(f"Total Mesh Primitives: {total_primitives}")
print(f"Primitives with TEXCOORD_0: {primitives_with_uv}")
print(f"Missing TEXCOORD_0 count: {len(missing_uv_primitives)}")
if missing_uv_primitives:
    print(f"MISSING: {missing_uv_primitives}")
else:
    print("VERIFIED: 100% of primitives have TEXCOORD_0!")

print("\n--- KEY MESH UV BOUNDS ---")
key_patterns = ["Yu_Nian_An_Body", "Mesh_Dress_Bodice", "Mesh_Dress_PleatedSkirt", "Mesh_Dress_WaistSash", "Mesh_Sandal_L", "Mesh_Sandal_R", "Mesh_Lips"]
for k, stats in uv_stats_by_mesh.items():
    if any(pat in k for pat in key_patterns):
        u_min, u_max = stats["u_range"]
        v_min, v_max = stats["v_range"]
        print(f"  {k} ({stats['count']} UVs): U=[{u_min:.4f}, {u_max:.4f}], V=[{v_min:.4f}, {v_max:.4f}]")
        # Assert within reasonable range [0, 1] (or slightly toleranced for clamping)
        assert -0.01 <= u_min and u_max <= 1.01, f"U out of [0, 1] in {k}: {u_min}, {u_max}"
        assert -0.01 <= v_min and v_max <= 1.01, f"V out of [0, 1] in {k}: {v_min}, {v_max}"

# 2. Inspect Skin Joints
print("\n--- SKIN JOINT SUMMARY ---")
skins = gltf.get("skins", [])
print(f"Total skins: {len(skins)}")
assert len(skins) > 0, "No skins found in GLB"
skin = skins[0]
joints = skin.get("joints", [])
print(f"Skin joints count: {len(joints)}")
assert len(joints) == 164, f"Expected 164 joints, got {len(joints)}"

# Check inverse bind matrices
ibm_idx = skin.get("inverseBindMatrices")
assert ibm_idx is not None, "Missing inverseBindMatrices in skin"
ibm_acc = gltf["accessors"][ibm_idx]
assert ibm_acc["count"] == 164, f"Expected 164 inverse bind matrices, got {ibm_acc['count']}"
assert ibm_acc["type"] == "MAT4", f"Expected MAT4, got {ibm_acc['type']}"
print(f"Inverse bind matrices confirmed: {ibm_acc['count']} MAT4 matrices")

# 3. Inspect Morph Targets (ARKit Blendshapes)
print("\n--- MORPH TARGET SUMMARY ---")
body_mesh = None
for mesh in gltf.get("meshes", []):
    if "Yu_Nian_An_Body" in mesh.get("name", ""):
        body_mesh = mesh
        break

assert body_mesh is not None, "Yu_Nian_An_Body mesh not found in GLB"
extras = body_mesh.get("extras", {})
target_names = extras.get("targetNames", [])
print(f"Yu_Nian_An_Body extras.targetNames count: {len(target_names)}")
assert len(target_names) == 52, f"Expected 52 target names, got {len(target_names)}"

# Check that primitives also have 52 targets
for p_idx, prim in enumerate(body_mesh.get("primitives", [])):
    targets = prim.get("targets", [])
    print(f"  Body prim {p_idx} targets count: {len(targets)}")
    assert len(targets) == 52, f"Expected 52 primitive targets, got {len(targets)}"

# Verify canonical ARKit names presence
arkit_samples = [
    "eyeBlinkLeft", "eyeBlinkRight", "jawOpen", "mouthSmileLeft", 
    "mouthSmileRight", "browInnerUp", "browDownLeft", "browDownRight",
    "cheekPuff", "noseSneerLeft", "tongueOut"
]
for s in arkit_samples:
    assert s in target_names, f"Missing expected ARKit blendshape: {s}"
print("ARKit 52 blendshape names verified in GLB!")

print("\n=== GLB CONTAINER PARSER: ALL CHECKS PASSED SUCCESSFULLY ===")
