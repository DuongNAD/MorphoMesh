import bpy, mathutils, os, tempfile

bpy.ops.wm.read_factory_settings(use_empty=True)

with open('docs/RESEARCH_BENCHMARK.md') as f:
    text = f.read()

start_marker = 'def bake_high_to_low_poly('
start_idx = text.find(start_marker)
end_idx = text.find('```', start_idx)
code = text[start_idx:end_idx]

exec_globals = {'bpy': bpy, 'mathutils': mathutils}
exec(code, exec_globals)
bake_func = exec_globals['bake_high_to_low_poly']

# 1. Create high-poly detailed mesh
bpy.ops.mesh.primitive_monkey_add(size=2.0)
high_obj = bpy.context.active_object
high_obj.name = 'HighPolyDragon'
sub = high_obj.modifiers.new('Subsurf', 'SUBSURF')
sub.levels = 2
bpy.ops.object.modifier_apply(modifier='Subsurf')

# 2. Create low-poly mesh (e.g. icosphere) with NO material and NO UVs
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
low_obj = bpy.context.active_object
low_obj.name = 'LowPolyDragon'

# Explicitly remove any UV layers and materials to stress-test defensiveness
while low_obj.data.uv_layers:
    low_obj.data.uv_layers.remove(low_obj.data.uv_layers[0])
low_obj.data.materials.clear()

assert len(low_obj.data.uv_layers) == 0, 'UV layers still exist!'
assert low_obj.active_material is None, 'Material still exists!'

tmp_out = os.path.join(tempfile.gettempdir(), 'test_forensic_bake_normal.png')
if os.path.exists(tmp_out):
    os.remove(tmp_out)

print('Executing bake_high_to_low_poly with active_material=None and 0 UV layers...')
res = bake_func('HighPolyDragon', 'LowPolyDragon', tmp_out)
print(f'Bake output path: {res}')

assert os.path.exists(tmp_out), 'Output normal map file was not created!'
size_bytes = os.path.getsize(tmp_out)
print(f'Normal map file size: {size_bytes} bytes')
assert size_bytes > 0, 'Normal map file is empty!'
print('SUCCESS: bake_high_to_low_poly executed with 0 errors and generated valid normal map!')
