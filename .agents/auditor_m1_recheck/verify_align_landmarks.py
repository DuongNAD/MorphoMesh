import bpy, mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.preferences.addon_enable(module='rigify')

with open('docs/RESEARCH_BENCHMARK.md') as f:
    text = f.read()

start_marker = 'def align_metarig_to_landmarks('
start_idx = text.find(start_marker)
end_idx = text.find('```', start_idx)
code = text[start_idx:end_idx]

bpy.ops.object.armature_wolf_metarig_add()
meta = bpy.context.active_object
meta.name = 'TestMetaRig'

exec_globals = {'bpy': bpy}
exec(code, exec_globals)
align_func = exec_globals['align_metarig_to_landmarks']

landmarks = {
    'spine.011': {'head': mathutils.Vector((0, 1.2, 0.8)), 'tail': mathutils.Vector((0, 1.4, 0.9))},
    'spine.004': {'head': mathutils.Vector((0, -0.5, 0.7)), 'tail': mathutils.Vector((0, -0.7, 0.75))}
}

align_func('TestMetaRig', landmarks)

bpy.ops.object.mode_set(mode='EDIT')
eb = meta.data.edit_bones
head_pos = eb['spine.011'].head
print('Updated head pos:', head_pos)
assert (head_pos - mathutils.Vector((0, 1.2, 0.8))).length < 1e-4, 'Head pos not aligned!'
bpy.ops.object.mode_set(mode='OBJECT')
print('SUCCESS: align_metarig_to_landmarks executed and snapped joints correctly!')
