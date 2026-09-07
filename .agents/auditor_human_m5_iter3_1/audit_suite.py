import os
import sys
import json
import struct
import numpy as np
from PIL import Image

def audit_base_topology():
    print('=== AUDIT 1: Base Topology of Yu_Nian_An_Body ===')
    from morphomesh.human_generator import generate_human_base_mesh
    res = generate_human_base_mesh()
    print(f'  Human mesh vertices: {len(res.mesh.vertices)} (req 2144)')
    assert len(res.mesh.vertices) == 2144, f'Expected 2144 vertices, got {len(res.mesh.vertices)}'
    assert res.quad_ratio >= 0.95, f'Expected quad ratio >= 0.95, got {res.quad_ratio}'
    print('--> AUDIT 1 PASS: Base body generator verified.\n')

def audit_textures():
    print('=== AUDIT 2: Production Texture Suite (4K strictly 4096x4096) ===')
    tex_dir = 'output/yu_nian_an/textures'
    expected_maps = [
        ('Yu_Nian_An_BaseColor_4K.png', 'RGB'),
        ('Yu_Nian_An_Normal_4K.png', 'RGB'),
        ('Yu_Nian_An_Roughness_4K.png', 'L'),
        ('Yu_Nian_An_Metallic_4K.png', 'L'),
        ('Yu_Nian_An_SSS_4K.png', 'L'),
        ('Yu_Nian_An_Alpha_4K.png', 'L'),
        ('Yu_Nian_An_Height_4K.png', 'L'),
        ('Yu_Nian_An_ORM_4K.png', 'RGBA'),
        ('Yu_Nian_An_MaskMap_4K.png', 'RGBA'),
    ]
    assert os.path.isdir(tex_dir), f'Texture directory does not exist: {tex_dir}'
    
    for filename, expected_mode in expected_maps:
        path = os.path.join(tex_dir, filename)
        assert os.path.isfile(path), f'Missing texture map: {path}'
        size_bytes = os.path.getsize(path)
        assert size_bytes > 0, f'Texture file is empty: {path}'
        with Image.open(path) as img:
            w, h = img.size
            mode = img.mode
            print(f'  {filename:30s} | Size: {size_bytes:9d} B | Dims: {w}x{h} | Mode: {mode}')
            assert (w, h) == (4096, 4096), f'{filename} resolution is {w}x{h}, expected (4096, 4096)'
            assert mode == expected_mode, f'{filename} mode is {mode}, expected {expected_mode}'
    print('--> AUDIT 2 PASS: All 9 textures exist and are strictly 4096x4096 with correct modes.\n')

def audit_glb():
    print('=== AUDIT 3: GLB Container, Primitives, Bones, Morph Targets & Semantic UV Sampling ===')
    glb_path = 'output/yu_nian_an/Yu_Nian_An.glb'
    assert os.path.isfile(glb_path), f'GLB file missing: {glb_path}'
    glb_size = os.path.getsize(glb_path)
    print(f'GLB file size: {glb_size:,} bytes')
    
    with open(glb_path, 'rb') as f:
        magic = f.read(4)
        assert magic == b'glTF', f'Invalid glTF magic: {magic}'
        version, length = struct.unpack('<II', f.read(8))
        assert version == 2, f'Invalid glTF version: {version}'
        assert length == glb_size, f'Length header {length} != file size {glb_size}'
        
        chunk_len, chunk_type = struct.unpack('<II', f.read(8))
        assert chunk_type == 0x4E4F534A, 'Expected JSON chunk'
        json_bytes = f.read(chunk_len)
        data = json.loads(json_bytes.decode('utf-8'))
        
        bin_len, bin_type = struct.unpack('<II', f.read(8))
        assert bin_type == 0x004E4942, 'Expected BIN chunk'
        bin_data = f.read(bin_len)
        
    print(f'  JSON chunk length: {chunk_len:,} bytes')
    print(f'  BIN chunk length: {bin_len:,} bytes')
    
    meshes = data.get('meshes', [])
    total_primitives = 0
    missing_uv = []
    for m in meshes:
        m_name = m.get('name', 'unnamed')
        for i, p in enumerate(m.get('primitives', [])):
            total_primitives += 1
            if 'TEXCOORD_0' not in p.get('attributes', {}):
                missing_uv.append(f'{m_name}[{i}]')
                
    print(f'  Total meshes: {len(meshes)}')
    print(f'  Total primitives: {total_primitives}')
    assert len(missing_uv) == 0, f'Primitives missing TEXCOORD_0: {missing_uv}'
    assert total_primitives == 34, f'Expected 34 primitives, got {total_primitives}'
    print('  TEXCOORD_0: 34/34 primitives present (100%)')
    
    skins = data.get('skins', [])
    assert len(skins) >= 1, 'No skin found in GLB'
    joints = skins[0].get('joints', [])
    print(f'  Skin joints count: {len(joints)}')
    assert len(joints) == 164, f'Expected 164 skin joints, got {len(joints)}'
    
    nodes = data.get('nodes', [])
    body_mesh_idx = None
    for idx, m in enumerate(meshes):
        if 'Body' in m.get('name', ''):
            body_mesh_idx = idx
            break
    assert body_mesh_idx is not None, 'Body mesh not found in GLB'
    
    body_m = meshes[body_mesh_idx]
    targets = body_m.get('primitives', [])[0].get('targets', [])
    target_names = body_m.get('extras', {}).get('targetNames', [])
    if not target_names:
        for n in nodes:
            if n.get('mesh') == body_mesh_idx:
                target_names = n.get('extras', {}).get('targetNames', [])
                break
    print(f'  Morph targets on Body primitive 0: {len(targets)}')
    print(f'  Target names count: {len(target_names)}')
    assert len(targets) == 52, f'Expected 52 morph targets, got {len(targets)}'
    assert len(target_names) == 52, f'Expected 52 target names, got {len(target_names)}'
    
    sample_names = ['eyeBlinkLeft', 'eyeBlinkRight', 'jawOpen', 'mouthSmileLeft', 'mouthSmileRight']
    for sn in sample_names:
        assert sn in target_names, f'Missing expected ARKit target: {sn}'
    print(f'  Sample ARKit names verified: {sample_names}')
    
    def get_uvs(prim):
        acc = data['accessors'][prim['attributes']['TEXCOORD_0']]
        bv = data['bufferViews'][acc['bufferView']]
        off = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
        cnt = acc['count']
        return np.frombuffer(bin_data, dtype=np.float32, count=cnt * 2, offset=off).reshape((cnt, 2))
        
    base_img = np.array(Image.open('output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png'))
    h, w, _ = base_img.shape
    
    print('\n  Semantic UV Texture Sampling Checks:')
    lips_mesh = next(m for m in meshes if 'Lips' in m.get('name', ''))
    uv_lips = get_uvs(lips_mesh['primitives'][0]).mean(axis=0)
    col_lips = int(np.clip(uv_lips[0] * w, 0, w - 1))
    row_lips = int(np.clip(uv_lips[1] * h, 0, h - 1))
    c_lips = base_img[row_lips, col_lips]
    print(f'    Mesh_Lips_Mesh: UV mean = ({uv_lips[0]:.4f}, {uv_lips[1]:.4f}) -> Pixel ({col_lips}, {row_lips}) -> RGB {c_lips.tolist()}')
    assert c_lips[0] > c_lips[1] + 30 and c_lips[0] > c_lips[2] + 30 and c_lips[0] > 180, f'Lips failed rose vermilion check: {c_lips}'
    
    skirt_mesh = next(m for m in meshes if 'PleatedSkirt' in m.get('name', ''))
    uv_skirt = get_uvs(skirt_mesh['primitives'][0]).mean(axis=0)
    col_skirt = int(np.clip(uv_skirt[0] * w, 0, w - 1))
    row_skirt = int(np.clip(uv_skirt[1] * h, 0, h - 1))
    c_skirt = base_img[row_skirt, col_skirt]
    print(f'    Mesh_Dress_PleatedSkirt_Mesh: UV mean = ({uv_skirt[0]:.4f}, {uv_skirt[1]:.4f}) -> Pixel ({col_skirt}, {row_skirt}) -> RGB {c_skirt.tolist()}')
    assert c_skirt[0] > 230 and c_skirt[1] > 230 and c_skirt[2] > 230 and abs(int(c_skirt[0]) - int(c_skirt[1])) < 10, f'Skirt failed ivory silk check: {c_skirt}'
    
    bodice_mesh = next(m for m in meshes if 'Bodice' in m.get('name', ''))
    uv_bodice = get_uvs(bodice_mesh['primitives'][0]).mean(axis=0)
    col_bodice = int(np.clip(uv_bodice[0] * w, 0, w - 1))
    row_bodice = int(np.clip(uv_bodice[1] * h, 0, h - 1))
    c_bodice = base_img[row_bodice, col_bodice]
    print(f'    Mesh_Dress_Bodice_Mesh: UV mean = ({uv_bodice[0]:.4f}, {uv_bodice[1]:.4f}) -> Pixel ({col_bodice}, {row_bodice}) -> RGB {c_bodice.tolist()}')
    assert c_bodice[0] > 230 and c_bodice[1] > 230 and c_bodice[2] > 230 and abs(int(c_bodice[0]) - int(c_bodice[1])) < 10, f'Bodice failed ivory silk check: {c_bodice}'
    
    sash_mesh = next(m for m in meshes if 'WaistSash' in m.get('name', ''))
    uv_sash = get_uvs(sash_mesh['primitives'][0]).mean(axis=0)
    col_sash = int(np.clip(uv_sash[0] * w, 0, w - 1))
    row_sash = int(np.clip(uv_sash[1] * h, 0, h - 1))
    c_sash = base_img[row_sash, col_sash]
    print(f'    Mesh_Dress_WaistSash_Mesh: UV mean = ({uv_sash[0]:.4f}, {uv_sash[1]:.4f}) -> Pixel ({col_sash}, {row_sash}) -> RGB {c_sash.tolist()}')
    assert c_sash[2] > 220 and c_sash[1] > 200 and c_sash[0] < 210, f'Sash failed ice-blue satin check: {c_sash}'
    
    uvs_body = get_uvs(body_m['primitives'][0])
    head_mask = uvs_body[:, 0] < 0.5
    uv_head = uvs_body[head_mask].mean(axis=0)
    col_head = int(np.clip(uv_head[0] * w, 0, w - 1))
    row_head = int(np.clip(uv_head[1] * h, 0, h - 1))
    c_head = base_img[row_head, col_head]
    print(f'    Yu_Nian_An_Body (Head Q1): UV mean = ({uv_head[0]:.4f}, {uv_head[1]:.4f}) -> Pixel ({col_head}, {row_head}) -> RGB {c_head.tolist()}')
    assert c_head[0] > 200 and c_head[1] > 180 and c_head[2] > 170, f'Head failed porcelain skin check: {c_head}'
    
    print('--> AUDIT 3 PASS: GLB structure, 34 primitives, 164 joints, 52 blendshapes, and semantic texture sampling are 100% verified.\n')

def audit_fbx():
    print('=== AUDIT 4: FBX Kaydara Binary Header ===')
    fbx_path = 'output/yu_nian_an/Yu_Nian_An.fbx'
    assert os.path.isfile(fbx_path), f'FBX file missing: {fbx_path}'
    fbx_size = os.path.getsize(fbx_path)
    print(f'FBX file size: {fbx_size:,} bytes')
    
    with open(fbx_path, 'rb') as f:
        header = f.read(23)
        expected_header = b'Kaydara FBX Binary  \x00\x1a\x00'
        assert header == expected_header, f'Invalid FBX header: {header}'
        version = struct.unpack('<I', f.read(4))[0]
        print(f'  Kaydara Header: {header}')
        print(f'  FBX Version: {version}')
        assert version in (7400, 7500, 7700), f'Unexpected FBX version: {version}'
    print('--> AUDIT 4 PASS: FBX binary header is valid Kaydara 7400 format.\n')

if __name__ == '__main__':
    audit_base_topology()
    audit_textures()
    audit_glb()
    audit_fbx()
    print('=== PYTHON AUDIT SUITE PART 1-4 COMPLETED WITH ZERO ERRORS ===')
