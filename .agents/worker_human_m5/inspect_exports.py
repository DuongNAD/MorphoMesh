import struct
import json
import os

fbx_path = "output/yu_nian_an/Yu_Nian_An.fbx"
glb_path = "output/yu_nian_an/Yu_Nian_An.glb"

print("=== INSPECTING EXPORTED ASSETS ===")

# 1. FBX Inspection
print("\n--- FBX INSPECTION ---")
with open(fbx_path, "rb") as f:
    fbx_header = f.read(27)
print("FBX Header bytes:", fbx_header[:23])
assert fbx_header.startswith(b"Kaydara FBX Binary"), f"Invalid FBX header: {fbx_header}"
print("FBX Header magic valid: Kaydara FBX Binary")

# Read some strings or nodes in FBX to check for shape keys and deformers
with open(fbx_path, "rb") as f:
    fbx_content = f.read()

print(f"FBX Total bytes: {len(fbx_content)}")
# Check for ARKit shape keys in FBX
arkit_keys = [
    "eyeBlinkLeft", "eyeBlinkRight", "jawOpen", "mouthSmileLeft", "mouthSmileRight",
    "browDownLeft", "browDownRight", "browInnerUp", "cheekPuff"
]
found_fbx_keys = [k for k in arkit_keys if k.encode() in fbx_content]
print(f"Sample ARKit keys in FBX: {len(found_fbx_keys)}/{len(arkit_keys)} found")

# Check for DEF bones in FBX
found_def_bones = [b.encode() for b in ["DEF-spine", "DEF-head", "DEF-hand.L", "DEF-hand.R"] if b.encode() in fbx_content]
print(f"Sample DEF bones in FBX: {len(found_def_bones)} found")

# 2. GLB Inspection
print("\n--- GLB INSPECTION ---")
with open(glb_path, "rb") as f:
    magic = f.read(4)
    version, length = struct.unpack("<II", f.read(8))
    print(f"GLB Magic: {magic}, Version: {version}, Total Length: {length}")
    assert magic == b"glTF", f"Invalid GLB magic: {magic}"
    assert version == 2, f"Expected glTF version 2, got {version}"

    # Chunk 0: JSON
    chunk_len, chunk_type = struct.unpack("<II", f.read(8))
    assert chunk_type == 0x4E4F534A, f"Expected JSON chunk (0x4E4F534A), got {hex(chunk_type)}"
    json_bytes = f.read(chunk_len)
    gltf_json = json.loads(json_bytes.decode("utf-8"))

print("glTF JSON keys:", list(gltf_json.keys()))
print(f"Nodes: {len(gltf_json.get('nodes', []))}")
print(f"Meshes: {len(gltf_json.get('meshes', []))}")
print(f"Materials: {len(gltf_json.get('materials', []))}")
print(f"Skins: {len(gltf_json.get('skins', []))}")

# Check morph targets on body mesh
body_mesh = None
for m in gltf_json.get("meshes", []):
    name = m.get("name", "")
    if "Body" in name:
        body_mesh = m
        break

if body_mesh:
    print(f"\nFound Body Mesh: {body_mesh.get('name')}")
    target_names = body_mesh.get("extras", {}).get("targetNames", [])
    if not target_names:
        for prim in body_mesh.get("primitives", []):
            if "targets" in prim:
                print(f"Primitive targets count: {len(prim['targets'])}")
    print(f"Morph target names count: {len(target_names)}")
    if target_names:
        print("First 10 morph targets:", target_names[:10])
        print("Total 52 ARKit keys in morph targets:", len([k for k in target_names if k != "Basis"]))
else:
    print("Warning: Body mesh not found by name in glTF meshes")
    for m in gltf_json.get("meshes", []):
        t_names = m.get("extras", {}).get("targetNames", [])
        if t_names:
            print(f"Mesh '{m.get('name')}' has {len(t_names)} morph targets!")

# Check skinning
for s in gltf_json.get("skins", []):
    joints = s.get("joints", [])
    print(f"Skin '{s.get('name')}' has {len(joints)} joints")
