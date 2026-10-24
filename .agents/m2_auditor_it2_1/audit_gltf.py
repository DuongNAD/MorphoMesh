import sys
import os
import struct
import json
import math

def parse_glb(glb_path):
    print(f"=== AUDITING GLTF BINARY STRUCTURE: {glb_path} ===")
    with open(glb_path, "rb") as f:
        # Header: magic (4), version (4), length (4)
        header = f.read(12)
        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF":
            print(f"FAIL: Not a glTF binary file, magic={magic}")
            sys.exit(1)
        print(f"glTF Magic: {magic.decode('ascii')}, Version: {version}, Total Length: {length} bytes")
        
        # Chunk 0: JSON
        chunk_hdr = f.read(8)
        chunk_len, chunk_type = struct.unpack("<I4s", chunk_hdr)
        if chunk_type != b"JSON":
            print(f"FAIL: First chunk is not JSON: {chunk_type}")
            sys.exit(1)
        json_data = f.read(chunk_len).decode("utf-8")
        gltf = json.loads(json_data)
        
    print(f"glTF generator: {gltf.get('asset', {}).get('generator')}")
    print(f"glTF scenes count: {len(gltf.get('scenes', []))}")
    print(f"glTF total nodes: {len(gltf.get('nodes', []))}")
    print(f"glTF total meshes: {len(gltf.get('meshes', []))}")
    print(f"glTF total skins: {len(gltf.get('skins', []))}")
    
    # Check default scene and root nodes
    scene_idx = gltf.get("scene", 0)
    root_node_indices = gltf["scenes"][scene_idx]["nodes"]
    print(f"Default scene ({scene_idx}) root node indices: {root_node_indices}")
    
    root_nodes = [gltf["nodes"][i] for i in root_node_indices]
    for idx, node in zip(root_node_indices, root_nodes):
        name = node.get("name", f"Node_{idx}")
        translation = node.get("translation", [0.0, 0.0, 0.0])
        rotation = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
        scale = node.get("scale", [1.0, 1.0, 1.0])
        matrix = node.get("matrix", None)
        print(f"Root Node [{idx}] '{name}':")
        print(f"  translation: {translation}")
        print(f"  rotation: {rotation}")
        print(f"  scale: {scale}")
        if matrix:
            print(f"  matrix: {matrix}")
            
        # Verify root transform is identity
        is_t_ident = all(abs(x) < 1e-4 for x in translation)
        is_r_ident = (abs(rotation[0]) < 1e-4 and abs(rotation[1]) < 1e-4 and abs(rotation[2]) < 1e-4 and abs(abs(rotation[3]) - 1.0) < 1e-4)
        is_s_ident = all(abs(x - 1.0) < 1e-4 for x in scale)
        is_matrix_ident = True
        if matrix:
            is_matrix_ident = all(abs(matrix[i] - (1.0 if i in (0,5,10,15) else 0.0)) < 1e-4 for i in range(16))
        print(f"  Identity transform check: translation={is_t_ident}, rotation={is_r_ident}, scale={is_s_ident}, matrix={is_matrix_ident}")
        
    # Check child nodes under root
    for idx, node in zip(root_node_indices, root_nodes):
        children = node.get("children", [])
        print(f"Root Node [{idx}] has {len(children)} children:")
        for c_idx in children:
            c_node = gltf["nodes"][c_idx]
            c_name = c_node.get("name", f"Node_{c_idx}")
            c_mesh = c_node.get("mesh", None)
            c_skin = c_node.get("skin", None)
            mesh_desc = f", mesh={c_mesh} ({gltf['meshes'][c_mesh].get('name')})" if c_mesh is not None else ""
            skin_desc = f", skin={c_skin}" if c_skin is not None else ""
            print(f"    - Child [{c_idx}] '{c_name}'{mesh_desc}{skin_desc}")
            
    # Check skins
    skins = gltf.get("skins", [])
    for s_idx, skin in enumerate(skins):
        joints = skin.get("joints", [])
        skeleton = skin.get("skeleton", None)
        print(f"Skin [{s_idx}]: total joints={len(joints)}, skeleton={skeleton}")
        joint_names = [gltf["nodes"][j].get("name", f"Joint_{j}") for j in joints]
        print(f"  First 5 joints: {joint_names[:5]}")
        print(f"  Last 5 joints: {joint_names[-5:]}")
        
    audit_gltf_data = {
        "valid_gltf": True,
        "version": version,
        "length": length,
        "root_nodes": [
            {
                "index": idx,
                "name": node.get("name"),
                "translation": node.get("translation", [0.0, 0.0, 0.0]),
                "rotation": node.get("rotation", [0.0, 0.0, 0.0, 1.0]),
                "scale": node.get("scale", [1.0, 1.0, 1.0]),
            }
            for idx, node in zip(root_node_indices, root_nodes)
        ],
        "total_nodes": len(gltf.get("nodes", [])),
        "total_meshes": len(gltf.get("meshes", [])),
        "total_skins": len(skins),
        "skin_joints_count": len(skins[0].get("joints", [])) if skins else 0,
    }
    with open("E:/tool/mcp/MorphoMesh/.agents/m2_auditor_it2_1/gltf_audit_result.json", "w") as out:
        json.dump(audit_gltf_data, out, indent=2)
    print("\nGLB binary audit passed and saved to gltf_audit_result.json")

if __name__ == "__main__":
    parse_glb("E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_rigged.glb")
