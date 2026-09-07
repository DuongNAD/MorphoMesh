import json
import struct
import os
import numpy as np
from PIL import Image

GLB_PATH = "output/yu_nian_an/Yu_Nian_An.glb"
FBX_PATH = "output/yu_nian_an/Yu_Nian_An.fbx"
BLEND_PATH = "output/yu_nian_an/Yu_Nian_An_Master.blend"
TEXTURES_DIR = "output/yu_nian_an/textures"

print("=== 1. GLB CONTAINER INSPECTION ===")
with open(GLB_PATH, "rb") as f:
    magic = f.read(4)
    version, length = struct.unpack("<II", f.read(8))
    actual_len = os.path.getsize(GLB_PATH)
    print(f"GLB magic: {magic}, version: {version}, header_len: {length}, file_size: {actual_len}")
    assert magic == b"glTF", "GLB magic header mismatch"
    assert version == 2, "GLB version is not 2"
    assert length == actual_len, "GLB length mismatch"

    chunk_len, chunk_type = struct.unpack("<II", f.read(8))
    assert chunk_type == 0x4E4F534A, "Chunk type is not JSON"
    json_data = json.loads(f.read(chunk_len).decode("utf-8"))

    bin_len, bin_type = struct.unpack("<II", f.read(8))
    assert bin_type == 0x004E4942, "Chunk type is not BIN"
    bin_data = f.read(bin_len)

print(f"glTF generator: {json_data.get('asset', {}).get('generator')}")
print(f"Nodes count: {len(json_data.get('nodes', []))}")
print(f"Meshes count: {len(json_data.get('meshes', []))}")
print(f"Materials count: {len(json_data.get('materials', []))}")
print(f"Textures count: {len(json_data.get('textures', []))}")
print(f"Images count: {len(json_data.get('images', []))}")

skins = json_data.get("skins", [])
print(f"Skins count: {len(skins)}")
for i, s in enumerate(skins):
    joints = s.get("joints", [])
    print(f"  Skin {i} ({s.get('name')}): {len(joints)} joints")

total_prims = 0
prims_with_texcoord_0 = 0
prims_missing_texcoord_0 = []
all_uv_stats = {}

def get_prim_uvs(prim):
    acc = json_data["accessors"][prim["attributes"]["TEXCOORD_0"]]
    bv = json_data["bufferViews"][acc["bufferView"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    cnt = acc["count"]
    return np.frombuffer(bin_data, dtype=np.float32, count=cnt * 2, offset=off).reshape((cnt, 2))

for m_idx, m in enumerate(json_data.get("meshes", [])):
    m_name = m.get("name", f"mesh_{m_idx}")
    prims = m.get("primitives", [])
    target_names = m.get("extras", {}).get("targetNames", [])
    for p_idx, p in enumerate(prims):
        total_prims += 1
        attrs = p.get("attributes", {})
        if "TEXCOORD_0" in attrs:
            prims_with_texcoord_0 += 1
            uvs = get_prim_uvs(p)
            u_min, v_min = np.min(uvs, axis=0)
            u_max, v_max = np.max(uvs, axis=0)
            u_mean, v_mean = np.mean(uvs, axis=0)
            has_nan = np.isnan(uvs).any()
            all_uv_stats[f"{m_name}_prim{p_idx}"] = {
                "count": len(uvs),
                "u_range": (float(u_min), float(u_max)),
                "v_range": (float(v_min), float(v_max)),
                "mean": (float(u_mean), float(v_mean)),
                "has_nan": bool(has_nan)
            }
        else:
            prims_missing_texcoord_0.append(f"{m_name}[{p_idx}]")

print(f"\nTotal primitives: {total_prims}")
print(f"Primitives with TEXCOORD_0: {prims_with_texcoord_0} / {total_prims} ({prims_with_texcoord_0/total_prims*100:.1f}%)")
print(f"Missing TEXCOORD_0: {prims_missing_texcoord_0}")

# Check NaN or corrupt UVs
nan_uvs = [k for k, v in all_uv_stats.items() if v["has_nan"]]
print(f"Primitives with NaN UVs: {nan_uvs}")

print("\n=== 2. SEMANTIC TEXTURE SAMPLING CHECK ACROSS ATLAS ===")
base_color_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_BaseColor_4K.png")
base_img = np.array(Image.open(base_color_path))
h, w, c = base_img.shape
print(f"BaseColor resolution: {w}x{h}, channels: {c}")

sample_checks = [
    ("Mesh_Lips", "lips", lambda rgb: rgb[0] > rgb[1] + 30 and rgb[0] > rgb[2] + 30 and rgb[0] > 180, "Rose vermilion lips"),
    ("Mesh_Dress_Bodice", "bodice", lambda rgb: rgb[0] > 230 and rgb[1] > 230 and rgb[2] > 230, "Ivory silk bodice"),
    ("Mesh_Dress_PleatedSkirt", "skirt", lambda rgb: rgb[0] > 230 and rgb[1] > 230 and rgb[2] > 230, "Ivory silk skirt"),
    ("Mesh_Dress_WaistSash", "sash", lambda rgb: rgb[2] > rgb[0] and rgb[2] > 200, "Ice-blue satin sash"),
    ("Mesh_Sandal_L", "sandal", lambda rgb: rgb[0] > 200 and rgb[1] > 200, "Sandal leather/fabric"),
]

for name_pat, label, validator, desc in sample_checks:
    match_mesh = next((m for m in json_data.get("meshes", []) if name_pat in m.get("name", "")), None)
    if match_mesh:
        uvs = get_prim_uvs(match_mesh["primitives"][0])
        mean_u, mean_v = uvs.mean(axis=0)
        px = int(np.clip(mean_u * w, 0, w - 1))
        py = int(np.clip(mean_v * h, 0, h - 1))
        sampled = base_img[py, px, :3]
        is_valid = validator(sampled)
        print(f"  {label.upper()} ({match_mesh['name']}): UV mean=({mean_u:.4f}, {mean_v:.4f}), Pixel=({px}, {py}), RGB={sampled.tolist()}, Valid={is_valid} ({desc})")
    else:
        print(f"  {label.upper()}: Mesh not found!")

# Check body head and body torso
body_mesh = next((m for m in json_data.get("meshes", []) if "Body" in m.get("name", "")), None)
if body_mesh:
    uvs = get_prim_uvs(body_mesh["primitives"][0])
    head_mask = uvs[:, 0] < 0.5
    body_mask = uvs[:, 0] >= 0.5
    if np.any(head_mask):
        u_h, v_h = uvs[head_mask].mean(axis=0)
        px_h, py_h = int(np.clip(u_h * w, 0, w - 1)), int(np.clip(v_h * h, 0, h - 1))
        rgb_h = base_img[py_h, px_h, :3]
        print(f"  BODY HEAD: UV mean=({u_h:.4f}, {v_h:.4f}), Pixel=({px_h}, {py_h}), RGB={rgb_h.tolist()} (Porcelain skin)")
    if np.any(body_mask):
        u_b, v_b = uvs[body_mask].mean(axis=0)
        px_b, py_b = int(np.clip(u_b * w, 0, w - 1)), int(np.clip(v_b * h, 0, h - 1))
        rgb_b = base_img[py_b, px_b, :3]
        print(f"  BODY LIMBS: UV mean=({u_b:.4f}, {v_b:.4f}), Pixel=({px_b}, {py_b}), RGB={rgb_b.tolist()} (Body skin)")

print("\n=== 3. 52 ARKIT FACS BLENDSHAPES IN GLB ===")
if body_mesh:
    target_names = body_mesh.get("extras", {}).get("targetNames", [])
    print(f"Target names count: {len(target_names)}")
    from morphomesh.human_generator import ARKIT_52_BLENDSHAPES
    missing = [k for k in ARKIT_52_BLENDSHAPES if k not in target_names]
    extra = [k for k in target_names if k not in ARKIT_52_BLENDSHAPES]
    print(f"Missing from standard 52: {missing}")
    print(f"Extra targets: {extra}")
    assert len(missing) == 0, "Missing ARKit blendshapes in GLB!"
    print("All 52 ARKit FACS blendshapes strictly match standard names!")
