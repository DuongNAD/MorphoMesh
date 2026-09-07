import bpy
import bmesh
import math
import sys

print('=== FORENSIC BLENDER AUDIT START ===')
blend_path = 'E:/tool/mcp/MorphoMesh/output/yu_nian_an/Yu_Nian_An_Master.blend'

# 1. Inspect Yu_Nian_An_Body
body = bpy.data.objects.get('Yu_Nian_An_Body')
if not body:
    print('FAIL: Yu_Nian_An_Body NOT FOUND')
    sys.exit(1)

bmesh_data = body.data
n_verts = len(bmesh_data.vertices)
n_polys = len(bmesh_data.polygons)
tri_count = sum(1 for p in bmesh_data.polygons if len(p.vertices) == 3)
quad_count = sum(1 for p in bmesh_data.polygons if len(p.vertices) == 4)
ngon_count = sum(1 for p in bmesh_data.polygons if len(p.vertices) > 4)

print(f'BODY_VERTS: {n_verts}')
print(f'BODY_POLYS: {n_polys}')
print(f'BODY_QUADS: {quad_count} ({(quad_count/n_polys)*100:.2f}%)')
print(f'BODY_TRIS: {tri_count}')
print(f'BODY_NGONS: {ngon_count}')

# Materials on Body
mat_names = [m.name if m else 'None' for m in bmesh_data.materials]
print(f'BODY_MATERIALS: {mat_names}')

# Check polygons 377 and 378
p377_mat_idx = bmesh_data.polygons[377].material_index
p378_mat_idx = bmesh_data.polygons[378].material_index
p377_mat_name = mat_names[p377_mat_idx] if p377_mat_idx < len(mat_names) else 'OOB'
p378_mat_name = mat_names[p378_mat_idx] if p378_mat_idx < len(mat_names) else 'OOB'
print(f'POLY_377_MAT: idx={p377_mat_idx}, name={p377_mat_name}')
print(f'POLY_378_MAT: idx={p378_mat_idx}, name={p378_mat_name}')

# Scalp polygons
scalp_polys = [p.index for p in bmesh_data.polygons if p.material_index < len(mat_names) and mat_names[p.material_index] == 'Mat_Human_Scalp']
print(f'SCALP_POLYS_COUNT: {len(scalp_polys)}')
if scalp_polys:
    z_min = min(min(bmesh_data.vertices[v].co.z for v in bmesh_data.polygons[i].vertices) for i in scalp_polys)
    z_max = max(max(bmesh_data.vertices[v].co.z for v in bmesh_data.polygons[i].vertices) for i in scalp_polys)
    print(f'SCALP_POLYS_Z_RANGE: [{z_min:.4f}m, {z_max:.4f}m]')

# Lip polys on body
lip_polys_on_body = [p.index for p in bmesh_data.polygons if p.material_index < len(mat_names) and mat_names[p.material_index] == 'Mat_Human_Lips']
print(f'LIP_POLYS_ON_BODY: {len(lip_polys_on_body)}')

# Shape keys
shape_keys = bmesh_data.shape_keys
if shape_keys and shape_keys.key_blocks:
    kb = shape_keys.key_blocks
    non_basis = [k for k in kb if k.name != 'Basis']
    print(f'SHAPE_KEYS_TOTAL: {len(kb)}')
    print(f'SHAPE_KEYS_NON_BASIS: {len(non_basis)}')
    zero_delta_keys = []
    for k in non_basis:
        delta_sum = sum((k.data[i].co - kb['Basis'].data[i].co).length for i in range(len(bmesh_data.vertices)))
        if delta_sum < 1e-6:
            zero_delta_keys.append(k.name)
    print(f'ZERO_DELTA_SHAPE_KEYS: {len(zero_delta_keys)}')
    if zero_delta_keys:
        print(f'ZERO_KEYS: {zero_delta_keys[:5]}')
else:
    print('FAIL: NO SHAPE KEYS FOUND')

# Vertex groups
vgs = [vg.name for vg in body.vertex_groups]
print(f'VERTEX_GROUPS_COUNT: {len(vgs)}')

# 2. Inspect Mesh_Lips
lips = bpy.data.objects.get('Mesh_Lips')
if lips:
    l_verts = len(lips.data.vertices)
    l_polys = len(lips.data.polygons)
    l_tris = sum(1 for p in lips.data.polygons if len(p.vertices) == 3)
    l_quads = sum(1 for p in lips.data.polygons if len(p.vertices) == 4)
    l_ngons = sum(1 for p in lips.data.polygons if len(p.vertices) > 4)
    l_mats = [m.name if m else 'None' for m in lips.data.materials]
    
    xs = [v.co.x for v in lips.data.vertices]
    ys = [v.co.y for v in lips.data.vertices]
    zs = [v.co.z for v in lips.data.vertices]
    dx = (max(xs) - min(xs)) * 1000
    dy = (max(ys) - min(ys)) * 1000
    dz = (max(zs) - min(zs)) * 1000

    vg_head = lips.vertex_groups.get('DEF-head')
    weights = []
    if vg_head:
        for v in lips.data.vertices:
            for g in v.groups:
                if g.group == vg_head.index:
                    weights.append(g.weight)
    
    print(f'LIPS_VERTS: {l_verts}')
    print(f'LIPS_POLYS: {l_polys}')
    print(f'LIPS_QUADS: {l_quads}')
    print(f'LIPS_TRIS: {l_tris}')
    print(f'LIPS_NGONS: {l_ngons}')
    print(f'LIPS_DIMS: dx={dx:.2f}mm, dy={dy:.2f}mm, dz={dz:.2f}mm')
    print(f'LIPS_MATERIALS: {l_mats}')
    print(f'LIPS_PARENT: {lips.parent.name if lips.parent else None}')
    print(f'LIPS_DEF_HEAD_WEIGHTS_COUNT: {len(weights)}, min={min(weights) if weights else None}, max={max(weights) if weights else None}')
    print(f'LIPS_COLLECTIONS: {[c.name for c in lips.users_collection]}')
else:
    print('FAIL: Mesh_Lips NOT FOUND')

# 3. Inspect Eyelids
for el_name in ['Mesh_Eyelid_Left', 'Mesh_Eyelid_Right']:
    el = bpy.data.objects.get(el_name)
    if el:
        el_mats = [m.name if m else 'None' for m in el.data.materials]
        el_quads = sum(1 for p in el.data.polygons if len(p.vertices) == 4)
        print(f'{el_name}: verts={len(el.data.vertices)}, polys={len(el.data.polygons)}, quads={el_quads}, mats={el_mats}, parent={el.parent.name if el.parent else None}')
    else:
        print(f'FAIL: {el_name} NOT FOUND')

# 4. Inspect Eye Spheres and Iris UV/Material
for eye_name in ['Mesh_Eye_Left_IrisPupil', 'Mesh_Eye_Right_IrisPupil']:
    eye = bpy.data.objects.get(eye_name)
    if eye:
        has_uv = len(eye.data.uv_layers) > 0
        uv_name = eye.data.uv_layers.active.name if has_uv else 'None'
        eye_mats = [m.name if m else 'None' for m in eye.data.materials]
        print(f'{eye_name}: has_uv={has_uv}, uv_name={uv_name}, mats={eye_mats}')
    else:
        print(f'FAIL: {eye_name} NOT FOUND')

mat_iris = bpy.data.materials.get('Mat_Human_Eye_Inner_Iris')
if mat_iris and mat_iris.use_nodes:
    ramp_nodes = [n for n in mat_iris.node_tree.nodes if n.type == 'VALTORGB']
    print(f'IRIS_COLOR_RAMPS_COUNT: {len(ramp_nodes)}')
    if ramp_nodes:
        cr = ramp_nodes[0].color_ramp
        print(f'IRIS_COLOR_RAMP_STOPS: {len(cr.elements)}')
        for idx, el in enumerate(cr.elements):
            col = [round(c, 3) for c in el.color]
            print(f'  Stop {idx}: pos={el.position:.3f}, col={col}')

# 5. Inspect Bangs Ribbons
bangs = bpy.data.objects.get('Hair_Hime_Bangs')
if bangs:
    b_verts = len(bangs.data.vertices)
    b_polys = len(bangs.data.polygons)
    # Consecutive vertex pairs (left, right) form the ribbon width
    # In convert_curves_to_ribbon_mesh: (2*i, 2*i+1)
    ribbon_widths = []
    for i in range(b_verts // 2):
        v_left = bangs.data.vertices[2*i].co
        v_right = bangs.data.vertices[2*i+1].co
        dist = (v_left - v_right).length
        ribbon_widths.append(dist)
    
    # Quad X-widths
    quad_x_widths = [max(bangs.data.vertices[v].co.x for v in p.vertices) - min(bangs.data.vertices[v].co.x for v in p.vertices) for p in bangs.data.polygons]
    print(f'BANGS_VERTS: {b_verts}, BANGS_QUADS: {b_polys}')
    print(f'BANGS_3D_RIBBON_WIDTHS: min={min(ribbon_widths)*1000:.2f}mm, max={max(ribbon_widths)*1000:.2f}mm, avg={sum(ribbon_widths)/len(ribbon_widths)*1000:.2f}mm')
    print(f'BANGS_QUAD_X_WIDTHS: min={min(quad_x_widths)*1000:.2f}mm, max={max(quad_x_widths)*1000:.2f}mm, avg={sum(quad_x_widths)/len(quad_x_widths)*1000:.2f}mm')
else:
    print('FAIL: Hair_Hime_Bangs NOT FOUND')

# 6. Inspect Scalp Crown Ribbons
crown = bpy.data.objects.get('Hair_Scalp_Crown')
if crown:
    print(f'CROWN_VERTS: {len(crown.data.vertices)}, CROWN_QUADS: {len(crown.data.polygons)}')
else:
    print('FAIL: Hair_Scalp_Crown NOT FOUND')

# 7. Inspect Mat_Human_Hair
mat_hair = bpy.data.materials.get('Mat_Human_Hair')
if mat_hair and mat_hair.use_nodes:
    p_bsdf = next((n for n in mat_hair.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if p_bsdf:
        rough = p_bsdf.inputs['Roughness'].default_value if 'Roughness' in p_bsdf.inputs else None
        spec = p_bsdf.inputs['Specular IOR Level'].default_value if 'Specular IOR Level' in p_bsdf.inputs else None
        coat = p_bsdf.inputs['Coat Weight'].default_value if 'Coat Weight' in p_bsdf.inputs else None
        coat_r = p_bsdf.inputs['Coat Roughness'].default_value if 'Coat Roughness' in p_bsdf.inputs else None
        print(f'MAT_HUMAN_HAIR: Roughness={rough}, Specular={spec}, Coat={coat}, CoatRough={coat_r}')

# 8. Inspect Light_Rim_HairLight
rim = bpy.data.objects.get('Light_Rim_HairLight')
if rim and rim.type == 'LIGHT':
    print(f'RIM_LIGHT: type={rim.data.type}, energy={rim.data.energy}W, size={rim.data.size}m')
else:
    print('FAIL: Light_Rim_HairLight NOT FOUND or not light')

# 9. Inspect Collections
cols = [c.name for c in bpy.data.collections]
print(f'COLLECTIONS: {cols}')

print('=== FORENSIC BLENDER AUDIT END ===')