import struct
import json
from pathlib import Path

def inspect_glb():
    glb_path = Path("output/anime_rigged.glb")
    assert glb_path.exists(), "GLB does not exist"
    data = glb_path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", f"Invalid magic: {magic}"
    assert version == 2, f"Invalid glTF version: {version}"
    assert length == len(data), f"Length mismatch: {length} vs {len(data)}"

    # Read JSON chunk
    chunk_len, chunk_type = struct.unpack_from("<II", data, 12)
    assert chunk_type == 0x4E4F534A, f"First chunk is not JSON: {chunk_type:x}"
    json_bytes = data[20:20 + chunk_len]
    gltf = json.loads(json_bytes.decode('utf-8'))

    print(f"glTF Version: {gltf.get('asset', {}).get('version')}")
    print(f"Nodes count: {len(gltf.get('nodes', []))}")
    print(f"Meshes count: {len(gltf.get('meshes', []))}")
    print(f"Skins count: {len(gltf.get('skins', []))}")

    # Check that skins exist
    skins = gltf.get("skins", [])
    assert len(skins) > 0, "No skins found in exported GLB!"
    skin = skins[0]
    joints = skin.get("joints", [])
    print(f"Joints in skin: {len(joints)}")
    # Collect node names
    nodes = gltf.get("nodes", [])
    joint_names = [nodes[j]["name"] for j in joints if "name" in nodes[j]]
    print(f"First 10 joints: {joint_names[:10]}")
    assert "Hips" in joint_names, "Hips root bone missing from GLB joints"
    assert "Spine" in joint_names, "Spine bone missing from GLB joints"
    assert "Head" in joint_names, "Head bone missing from GLB joints"
    assert "Index.01.L" in joint_names, "Finger bone missing from GLB joints"
    assert "Skirt_01" in joint_names, "Skirt bone missing from GLB joints"
    assert "Hair_L_01" in joint_names, "Hair bone missing from GLB joints"

    print("ALL GLB EXPORT INTEGRITY CHECKS PASSED!")

if __name__ == "__main__":
    inspect_glb()
