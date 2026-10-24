import bpy
import os
import json

print('=== BLENDER ANIMATED BLEND INSPECTION ===')
arm = bpy.data.objects.get('Anime_Armature')
print('Armature object:', arm.name if arm else None)
if arm and arm.animation_data:
    print('Active action:', arm.animation_data.action.name if arm.animation_data.action else None)
    print('NLA tracks count:', len(arm.animation_data.nla_tracks))
    for t in arm.animation_data.nla_tracks:
        print(f'  Track: {t.name}, muted={t.mute}, strips={len(t.strips)}')
        for s in t.strips:
            print(f'    Strip: {s.name}, action={s.action.name if s.action else None}, range=({s.frame_start}, {s.frame_end})')

print('\n=== ACTIONS AND SECONDARY BONES KEYFRAMES ===')
for act in bpy.data.actions:
    hair_fcurves = [fc for fc in act.fcurves if 'Hair_L_' in fc.data_path or 'Hair_R_' in fc.data_path]
    skirt_fcurves = [fc for fc in act.fcurves if 'Skirt_' in fc.data_path]
    total_hair_kfs = sum(len(fc.keyframe_points) for fc in hair_fcurves)
    total_skirt_kfs = sum(len(fc.keyframe_points) for fc in skirt_fcurves)
    print(f'Action: {act.name}, range={act.frame_range[:]}, total_fcurves={len(act.fcurves)}')
    print(f'  Hair fcurves={len(hair_fcurves)}, kfs={total_hair_kfs}')
    print(f'  Skirt fcurves={len(skirt_fcurves)}, kfs={total_skirt_kfs}')

print('\n=== MESHES AND MODIFIERS ===')
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        arm_mods = [m for m in obj.modifiers if m.type == 'ARMATURE']
        dqs = arm_mods[0].use_deform_preserve_volume if arm_mods else False
        print(f'Mesh: {obj.name}, verts={len(obj.data.vertices)}, DQS={dqs}')

print('\n=== DELIVERABLES FILE SIZES ===')
blend_file = 'output/anime_animated.blend'
glb_file = 'output/anime_animated.glb'
if os.path.exists(blend_file):
    print(f'{blend_file}: {os.path.getsize(blend_file)} bytes ({os.path.getsize(blend_file)/(1024*1024):.2f} MB)')
else:
    print(f'{blend_file}: MISSING')

if os.path.exists(glb_file):
    print(f'{glb_file}: {os.path.getsize(glb_file)} bytes ({os.path.getsize(glb_file)/(1024*1024):.2f} MB)')
else:
    print(f'{glb_file}: MISSING')
