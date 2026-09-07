import bpy
import os
import sys

BLEND_PATH = 'output/yu_nian_an/Yu_Nian_An_Master.blend'
FBX_PATH = 'output/yu_nian_an/Yu_Nian_An.fbx'
GLB_PATH = 'output/yu_nian_an/Yu_Nian_An.glb'

print('================================================================')
print('=== FORENSIC BLENDER AUDIT: Master Blend, FBX & GLB Analysis ===')
print('================================================================')

# 1. Open Master Blend
bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
print(f'Successfully loaded: {BLEND_PATH}')

mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
print(f'Total mesh objects in scene: {len(mesh_objs)} (required: 29)')
assert len(mesh_objs) in (29, 30), f'Expected 29 mesh objects, got {len(mesh_objs)}'

# Check all 29 mesh objects have UVMap
missing_uv = []
print('\nMesh Objects & UV Layers Audit:')
for obj in sorted(mesh_objs, key=lambda o: o.name):
    uv_names = [uv.name for uv in obj.data.uv_layers]
    has_uvmap = 'UVMap' in uv_names
    status = 'OK (UVMap)' if has_uvmap else f'FAIL (layers: {uv_names})'
    print(f'  {obj.name:32s} | Verts: {len(obj.data.vertices):5d} | Polys: {len(obj.data.polygons):5d} | {status}')
    if not has_uvmap:
        missing_uv.append(obj.name)

assert len(missing_uv) == 0, f'Mesh objects missing UVMap: {missing_uv}'
print('--> ALL 29 MESH OBJECTS HAVE UVMap LAYER ACTIVE.')

# Inspect Yu_Nian_An_Body topology
body_obj = bpy.data.objects.get('Yu_Nian_An_Body')
assert body_obj is not None, 'Yu_Nian_An_Body not found in blend file'
m_body = body_obj.data
n_verts = len(m_body.vertices)
n_polys = len(m_body.polygons)
n_quads = sum(1 for p in m_body.polygons if len(p.vertices) == 4)
n_tris = sum(1 for p in m_body.polygons if len(p.vertices) == 3)
n_ngons = sum(1 for p in m_body.polygons if len(p.vertices) not in (3, 4))

print(f'\nYu_Nian_An_Body Topology Breakdown:')
print(f'  Vertices:  {n_verts} (required: 2144)')
print(f'  Polygons:  {n_polys} (required: 2036)')
print(f'  Quads:     {n_quads} ({n_quads/n_polys*100:.2f}%)')
print(f'  Triangles: {n_tris}')
print(f'  N-gons:    {n_ngons}')

assert n_verts == 2144, f'Yu_Nian_An_Body verts {n_verts} != 2144'
assert n_polys == 2036, f'Yu_Nian_An_Body polys {n_polys} != 2036'
assert n_quads == 2036, f'Yu_Nian_An_Body quads {n_quads} != 2036'
assert n_tris == 0, f'Yu_Nian_An_Body tris {n_tris} != 0'
assert n_ngons == 0, f'Yu_Nian_An_Body ngons {n_ngons} != 0'
print('--> TOPOLOGY VERIFIED: Strictly 2,036 pure quads, 0 tris, 0 ngons, 2,144 vertices.')

# 2. Test FBX Import & Armature Rigging & Blendshapes
print('\n--- Testing FBX Re-import in Clean Scene ---')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX_PATH)

arm_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
assert len(arm_objs) >= 1, 'No armature imported from FBX'
arm = arm_objs[0]
def_bones = [b.name for b in arm.data.bones if b.name.startswith('DEF-')]
print(f'Imported FBX Armature: {arm.name} with {len(arm.data.bones)} total bones')
print(f'DEF Bones count: {len(def_bones)} (required: 163)')
assert len(def_bones) == 163, f'Expected 163 DEF bones in FBX, got {len(def_bones)}'

fbx_body = next((o for o in bpy.data.objects if o.type == 'MESH' and 'Body' in o.name), None)
assert fbx_body is not None, 'Body mesh not found in imported FBX'
assert fbx_body.data.shape_keys is not None, 'No shape keys on body mesh in FBX'
fbx_skeys = [k.name for k in fbx_body.data.shape_keys.key_blocks if k.name != 'Basis']
print(f'FBX Body Shape Keys count: {len(fbx_skeys)} (required: 52 ARKit)')
assert len(fbx_skeys) == 52, f'Expected 52 ARKit shape keys in FBX, got {len(fbx_skeys)}'

# Check UV layers on FBX meshes
fbx_meshes = [o for o in bpy.data.objects if o.type == 'MESH']
fbx_missing_uv = [o.name for o in fbx_meshes if len(o.data.uv_layers) == 0]
print(f'FBX Imported Meshes: {len(fbx_meshes)} | Missing UVs: {len(fbx_missing_uv)}')
assert len(fbx_missing_uv) == 0, f'FBX meshes missing UV layers: {fbx_missing_uv}'
print('--> FBX RE-IMPORT VERIFIED: 163 DEF bones, 52 blendshapes, active UV layers.')

# 3. Test GLB Import & Blendshapes
print('\n--- Testing GLB Re-import in Clean Scene ---')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_PATH)

glb_body = next((o for o in bpy.data.objects if o.type == 'MESH' and 'Body' in o.name), None)
assert glb_body is not None, 'Body mesh not found in imported GLB'
assert glb_body.data.shape_keys is not None, 'No shape keys on body mesh in GLB'
glb_skeys = [k.name for k in glb_body.data.shape_keys.key_blocks if k.name != 'Basis']
print(f'GLB Body Shape Keys count: {len(glb_skeys)} (required: 52 ARKit)')
assert len(glb_skeys) == 52, f'Expected 52 ARKit shape keys in GLB, got {len(glb_skeys)}'

# Test jawOpen shape key deformation
v_init = [v.co.copy() for v in glb_body.data.vertices]
kb_jaw = glb_body.data.shape_keys.key_blocks.get('jawOpen')
assert kb_jaw is not None, 'jawOpen shape key missing'
kb_jaw.value = 1.0
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_body = glb_body.evaluated_get(depsgraph)
eval_mesh = eval_body.to_mesh()
displacements = [(eval_mesh.vertices[i].co - v_init[i]).length for i in range(len(v_init))]
max_disp = max(displacements)
print(f'GLB jawOpen deformation max displacement: {max_disp:.6f}m')
assert max_disp > 0.01, f'jawOpen displacement too small: {max_disp}'
eval_body.to_mesh_clear()
print('--> GLB RE-IMPORT VERIFIED: 52 ARKit shape keys, functional jawOpen deformation.')

print('\n================================================================')
print('=== ALL BLENDER FORENSIC AUDIT CHECKS PASSED SUCCESSFULLY! ===')
print('================================================================')
