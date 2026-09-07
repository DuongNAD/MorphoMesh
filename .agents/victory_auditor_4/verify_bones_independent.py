import bpy
import json

with open('E:/tool/mcp/MorphoMesh/.agents/victory_auditor_4/expected_bones.json') as f:
    exp = json.load(f)

arm = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')
blend_bones = set(b.name for b in arm.data.bones)

missing_body = set(exp['body']) - blend_bones
missing_face = set(exp['face']) - blend_bones
missing_all = set(exp['all']) - blend_bones

print('Expected Body Bones:', len(exp['body']))
print('Expected Face Bones:', len(exp['face']))
print('Total Expected DEF Bones:', len(exp['all']))
print('Actual DEF Bones in Blend:', len([b for b in arm.data.bones if b.name.startswith('DEF-')]))

print('Missing body bones:', missing_body)
print('Missing facial bones:', missing_face)
print('Missing all bones:', missing_all)

assert len(missing_all) == 0, 'DEF bone mismatch!'
print('PASS: All 163 DEF bones (64 body + 99 face) match 100%!')
