"""
Forensic asset inspector for Milestone 5 deliverables.
"""
import os
import sys
import json
import struct
import numpy as np
from PIL import Image

print("=== 1. MASTER BLEND INSPECTION ===")
blend_path = "output/yu_nian_an/Yu_Nian_An_Master.blend"
with open(blend_path, "rb") as f:
    blend_header = f.read(12)
print(f"Blend header: {blend_header}, size: {os.path.getsize(blend_path)} bytes")

print("\n=== 2. FBX INSPECTION ===")
fbx_path = "output/yu_nian_an/Yu_Nian_An.fbx"
with open(fbx_path, "rb") as f:
    fbx_header = f.read(27)
    fbx_content = f.read()
print(f"FBX header: {fbx_header}")
print(f"FBX size: {os.path.getsize(fbx_path)} bytes")

from morphomesh.human_rigging import ALL_163_DEF_BONES
from morphomesh.human_generator import ARKIT_52_BLENDSHAPES

fbx_bones_found = [b for b in ALL_163_DEF_BONES if b.encode("utf-8") in fbx_content]
print(f"DEF bones found in FBX: {len(fbx_bones_found)} / {len(ALL_163_DEF_BONES)}")

fbx_arkit_found = [k for k in ARKIT_52_BLENDSHAPES if k.encode("utf-8") in fbx_content]
print(f"ARKit blendshapes found in FBX: {len(fbx_arkit_found)} / {len(ARKIT_52_BLENDSHAPES)}")

print("\n=== 3. GLB INSPECTION ===")
glb_path = "output/yu_nian_an/Yu_Nian_An.glb"
with open(glb_path, "rb") as f:
    magic = f.read(4)
    version, length = struct.unpack("<II", f.read(8))
    chunk_len, chunk_type = struct.unpack("<II", f.read(8))
    json_bytes = f.read(chunk_len)
    bin_chunk_header = f.read(8)
    if bin_chunk_header:
        bin_len, bin_type = struct.unpack("<II", bin_chunk_header)
    else:
        bin_len, bin_type = 0, 0

print(f"GLB Magic: {magic}, Version: {version}, Total Header Length: {length}, File Size: {os.path.getsize(glb_path)}")
print(f"JSON Chunk Len: {chunk_len}, Bin Chunk Len: {bin_len}")

gltf_json = json.loads(json_bytes.decode("utf-8"))
print("GLB Top-Level Keys:", list(gltf_json.keys()))
print(f"Nodes count: {len(gltf_json.get('nodes', []))}")
print(f"Meshes count: {len(gltf_json.get('meshes', []))}")
print(f"Skins count: {len(gltf_json.get('skins', []))}")
print(f"Materials count: {len(gltf_json.get('materials', []))}")

if gltf_json.get("skins"):
    skin0 = gltf_json["skins"][0]
    joints = skin0.get("joints", [])
    print(f"Skin 0 name: {skin0.get('name')}, joints count: {len(joints)}")

body_meshes = [m for m in gltf_json.get("meshes", []) if "Body" in m.get("name", "")]
if body_meshes:
    bm = body_meshes[0]
    targets = bm.get("extras", {}).get("targetNames", [])
    print(f"Body Mesh Name: {bm.get('name')}, morph targets count: {len(targets)}")
    matched_targets = [k for k in ARKIT_52_BLENDSHAPES if k in targets]
    print(f"ARKit FACS matched in GLB: {len(matched_targets)} / 52")

print("\n=== 4. TEXTURE SUITE EMPIRICAL STATS ===")
tex_dir = "output/yu_nian_an/textures"
for fname in sorted(os.listdir(tex_dir)):
    p = os.path.join(tex_dir, fname)
    if not fname.endswith(".png"):
        continue
    with Image.open(p) as img:
        w, h = img.size
        mode = img.mode
        arr = np.array(img)
    val_min = float(arr.min())
    val_max = float(arr.max())
    val_mean = float(arr.mean())
    val_std = float(arr.std())
    unique_count = len(np.unique(arr))
    print(f"{fname:32s} | Size: {w}x{h} | Mode: {mode:4s} | Min: {val_min:6.1f} | Max: {val_max:6.1f} | Mean: {val_mean:6.2f} | Std: {val_std:6.2f} | Unique: {unique_count}")
