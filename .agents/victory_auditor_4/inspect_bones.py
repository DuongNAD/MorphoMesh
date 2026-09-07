import bpy

obj = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')
assert obj is not None

def_bones = [b.name for b in obj.data.bones if b.name.startswith('DEF-')]
print(f'Total DEF bones: {len(def_bones)}')

for i, b in enumerate(sorted(def_bones)):
    print(f'{i+1:3d}: {b}')
