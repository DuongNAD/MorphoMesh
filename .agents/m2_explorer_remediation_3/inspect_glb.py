import json
import struct
import sys
from pathlib import Path

def inspect_glb(glb_path):
    print("=== INSPECTING GLB:", glb_path)
    with open(glb_path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        chunk_len, chunk_type = struct.unpack("<I4s", f.read(8))
        json_data = f.read(chunk_len).decode("utf-8")
        bin_chunk_header = f.read(8)
        bin_data = f.read()

    data = json.loads(json_data)
    print(f"GLB Version: {version}, Total Length: {length}, Bin length: {len(bin_data)}")
    
    nodes = data.get("nodes", [])
    meshes = data.get("meshes", [])
    skins = data.get("skins", [])
    scenes = data.get("scenes", [])
    accessors = data.get("accessors", [])

    print(f"Total nodes: {len(nodes)}")
    print(f"Total meshes: {len(meshes)}")
    print(f"Total skins: {len(skins)}")
    print(f"Scenes: {scenes}")

    print("\n--- NODES SUMMARY ---")
    for idx, node in enumerate(nodes):
        name = node.get("name", f"Node_{idx}")
        mesh_idx = node.get("mesh")
        skin_idx = node.get("skin")
        children = node.get("children", [])
        trans = node.get("translation")
        rot = node.get("rotation")
        scale = node.get("scale")
        matrix = node.get("matrix")
        
        # Only print details if it has mesh, skin, non-default transform, or is a root
        extra = []
        if mesh_idx is not None:
            extra.append(f"mesh={mesh_idx} ({meshes[mesh_idx].get('name', '')})")
        if skin_idx is not None:
            extra.append(f"skin={skin_idx}")
        if children:
            extra.append(f"children_count={len(children)}")
        if trans:
            extra.append(f"T={trans}")
        if rot:
            extra.append(f"R={rot}")
        if scale:
            extra.append(f"S={scale}")
        if matrix:
            extra.append(f"M={matrix}")
            
        print(f"Node[{idx}] '{name}': {', '.join(extra)}")

    print("\n--- SKINS SUMMARY ---")
    for s_idx, skin in enumerate(skins):
        joints = skin.get("joints", [])
        skeleton = skin.get("skeleton")
        ibm_accessor = skin.get("inverseBindMatrices")
        print(f"Skin[{s_idx}] '{skin.get('name', '')}': joints={len(joints)}, skeleton_root={skeleton}, ibm_accessor={ibm_accessor}")
        joint_names = [nodes[j].get("name", f"node_{j}") for j in joints]
        print(f"Joint sample (first 10): {joint_names[:10]}")
        print(f"Joint sample (last 10): {joint_names[-10:]}")

        # Check inverse bind matrices
        if ibm_accessor is not None:
            acc = accessors[ibm_accessor]
            print(f"IBM Accessor[{ibm_accessor}]: count={acc.get('count')}, type={acc.get('type')}, componentType={acc.get('componentType')}")
            # read first 2 matrices
            buffer_view = data["bufferViews"][acc["bufferView"]]
            byte_offset = buffer_view.get("byteOffset", 0) + acc.get("byteOffset", 0)
            print(f"IBM byteOffset={byte_offset}")
            for m_i in range(min(3, acc["count"])):
                m_bytes = bin_data[byte_offset + m_i * 64 : byte_offset + (m_i + 1) * 64]
                floats = struct.unpack("<16f", m_bytes)
                print(f"  IBM[{m_i}] ({joint_names[m_i]}): {[round(x, 4) for x in floats[:4]]} ...")

if __name__ == "__main__":
    glb = sys.argv[1] if len(sys.argv) > 1 else "output/anime_rigged.glb"
    inspect_glb(glb)
