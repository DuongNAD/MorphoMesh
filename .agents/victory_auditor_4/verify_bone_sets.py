import sys
sys.path.insert(0, 'E:/tool/mcp/MorphoMesh/src')
import bpy
from morphomesh.human_rigging import BODY_DEF_BONES, FACIAL_DEF_BONES, ALL_163_DEF_BONES

arm = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')
blend_bones = set(b.name for b in arm.data.bones)

missing_body = set(BODY_DEF_BONES) - blend_bones
missing_face = set(FACIAL_DEF_BONES) - blend_bones
missing_all = set(ALL_163_DEF_BONES) - blend_bones

print('Missing body bones:', missing_body)
print('Missing facial bones:', missing_face)
print('Missing all bones:', missing_all)
assert len(missing_all) == 0, 'Bone mismatch!'
print('PASS: All 64 body and 99 face DEF bones (163 total) present in blend file!')
