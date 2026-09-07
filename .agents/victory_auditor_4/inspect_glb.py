import struct
import json
import os

glb_path = 'E:/tool/mcp/MorphoMesh/output/yu_nian_an/Yu_Nian_An.glb'
assert os.path.exists(glb_path), 'GLB file does not exist!'
file_size = os.path.getsize(glb_path)

with open(glb_path, 'rb') as f:
    magic, version, length = struct.unpack('<4sII', f.read(12))
    assert magic == b'glTF', f'Invalid magic: {magic}'
    assert length == file_size, f'Length mismatch: header {length} != file {file_size}'
    
    chunk0_len, chunk0_type = struct.unpack('<II', f.read(8))
    assert chunk0_type == 0x4E4F534A, f'Chunk 0 is not JSON: {chunk0_type}'
    json_bytes = f.read(chunk0_len)
    gltf = json.loads(json_bytes.decode('utf-8'))

meshes = gltf.get('meshes', [])
total_primitives = 0
primitives_with_texcoord0 = 0
missing_texcoord0 = []

for mesh_idx, mesh in enumerate(meshes):
    m_name = mesh.get('name', f'mesh_{mesh_idx}')
    for prim_idx, prim in enumerate(mesh.get('primitives', [])):
        total_primitives += 1
        attrs = prim.get('attributes', {})
        if 'TEXCOORD_0' in attrs:
            primitives_with_texcoord0 += 1
        else:
            missing_texcoord0.append(f'{m_name}[prim_{prim_idx}]')

skins = gltf.get('skins', [])
joints_count = len(skins[0].get('joints', [])) if skins else 0

morph_targets_count = 0
for mesh in meshes:
    for prim in mesh.get('primitives', []):
        targets = prim.get('targets', [])
        if targets:
            morph_targets_count = max(morph_targets_count, len(targets))

print('=== GLB FORENSIC INSPECTION ===')
print(f'File: {glb_path}')
print(f'Size: {file_size:,} bytes')
print(f'glTF Version: {version}')
print(f'Total Meshes: {len(meshes)}')
print(f'Total Primitives: {total_primitives}')
print(f'Primitives with TEXCOORD_0: {primitives_with_texcoord0} / {total_primitives}')
if missing_texcoord0:
    print(f'FAIL: Primitives MISSING TEXCOORD_0: {missing_texcoord0}')
else:
    print('PASS: 100% of GLB primitives have TEXCOORD_0!')

print(f'Skins count: {len(skins)}, Total Joints in Primary Skin: {joints_count}')
print(f'Max Morph Targets (Blendshapes) per primitive: {morph_targets_count}')

nodes = gltf.get('nodes', [])
print(f'Total Scene Nodes: {len(nodes)}')
materials = gltf.get('materials', [])
print(f'Total Materials: {len(materials)}')
for mat in materials:
    print('  - Material:', mat.get('name'))
