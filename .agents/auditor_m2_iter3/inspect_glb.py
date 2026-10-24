import struct, json, os

path = 'output/yu_nian_an/Yu_Nian_An.glb'
print(f'Inspecting GLB: {path} ({os.path.getsize(path)} bytes)')
with open(path, 'rb') as f_in:
    magic, version, length = struct.unpack('<4sII', f_in.read(12))
    assert magic == b'glTF', f'Invalid magic {magic}'
    print(f'glTF version: {version}, header length: {length}')
    chunk_len, chunk_type = struct.unpack('<II', f_in.read(8))
    assert chunk_type == 0x4E4F534A, 'Expected JSON chunk'
    json_bytes = f_in.read(chunk_len)
    data = json.loads(json_bytes.decode('utf-8'))

nodes = data.get('nodes', [])
print(f'Total nodes: {len(nodes)}')

skins = data.get('skins', [])
print(f'Total skins: {len(skins)}')
for i, skin in enumerate(skins):
    joints = skin.get('joints', [])
    joint_names = [nodes[j]['name'] for j in joints if 'name' in nodes[j]]
    def_joints = [name for name in joint_names if name.startswith('DEF-')]
    print(f'Skin {i}: {len(joints)} joints, {len(def_joints)} DEF joints')

meshes = data.get('meshes', [])
print(f'Total meshes: {len(meshes)}')
all_prims_have_texcoord0 = True
total_prims = 0
prims_with_texcoord0 = 0
target_names_found = set()
for m_idx, m in enumerate(meshes):
    name = m.get('name', f'mesh_{m_idx}')
    extras = m.get('extras', {})
    t_names = extras.get('targetNames', [])
    if t_names:
        print(f'Mesh "{name}" extras.targetNames: {len(t_names)} targets')
        target_names_found.update(t_names)
    prims = m.get('primitives', [])
    total_prims += len(prims)
    for p in prims:
        attrs = p.get('attributes', {})
        if 'TEXCOORD_0' in attrs:
            prims_with_texcoord0 += 1
        else:
            all_prims_have_texcoord0 = False
            print(f'WARNING: primitive in mesh {name} missing TEXCOORD_0: {list(attrs.keys())}')

print(f'Primitives check: {prims_with_texcoord0}/{total_prims} have TEXCOORD_0')
print(f'All primitives have TEXCOORD_0: {all_prims_have_texcoord0}')
print(f'Total distinct target names across meshes: {len(target_names_found)}')
assert len(target_names_found) == 52, f'Expected 52 ARKit target names, got {len(target_names_found)}'
print('52 ARKit FACS targets verified in GLB!')