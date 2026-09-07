import traceback
from morphomesh.blender_bridge import BlenderBridge

bridge = BlenderBridge()

# 1. create_human_asset
print('1. Testing create_human_asset...')
r1 = bridge.create_human_asset(character_name='Adversarial_Yu', height=1.65, head_ratio=7.41)
assert r1['status'] == 'success'
print('  r1 status:', r1['status'], 'mesh:', r1.get('mesh_path'))
assert r1.get('def_bone_count') is None or 'asset_id' in r1

# 2. auto_rig_human
print('2. Testing auto_rig_human...')
r2 = bridge.auto_rig_human(mesh_object_name='Adversarial_Yu_Base_Mesh')
assert r2['status'] == 'success'
print('  r2 status:', r2['status'], 'def_bones:', r2.get('def_bone_count'), 'armature:', r2.get('armature_name'))
assert r2.get('def_bone_count') == 163

# 3. setup_human_materials
print('3. Testing setup_human_materials...')
r3 = bridge.setup_human_materials(mesh_object_name='Adversarial_Yu_Base_Mesh', material_preset='yu_nian_an')
assert r3['status'] == 'success'
print('  r3 status:', r3['status'], 'materials:', len(r3.get('materials_created', [])))
assert len(r3.get('materials_created', [])) >= 5

# 4. groom_human
print('4. Testing groom_human...')
r4 = bridge.groom_human(mesh_object_name='Adversarial_Yu_Base_Mesh', hair_style='hime_cut_long')
assert r4['status'] == 'success'
print('  r4 status:', r4['status'], 'layers:', len(r4.get('layers', [])))
assert len(r4.get('layers', [])) >= 5

# 5. dress_human
print('5. Testing dress_human...')
r5 = bridge.dress_human(human_object_name='Adversarial_Yu_Base_Mesh', outfit='yu_nian_an_dress', butterfly_count=10)
assert r5['status'] == 'success'
print('  r5 status:', r5['status'], 'garments:', len(r5.get('garments', [])), 'props:', r5.get('prop_count'))
assert r5.get('prop_count') == 20

print('ALL 5 BLENDER BRIDGE DISPATCH METHODS TESTED SUCCESSFULLY!')
