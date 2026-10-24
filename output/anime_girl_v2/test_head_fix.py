import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
glb_path = r"E:\tool\mcp\MorphoMesh\output\anime_girl_v2\anime_girl_anim_28.glb"
bpy.ops.import_scene.gltf(filepath=glb_path)

mesh = bpy.data.objects['char1']

non_head_groups = [
    'RightHand', 'RightForeArm', 'RightArm', 'RightShoulder',
    'LeftHand', 'LeftForeArm', 'LeftArm', 'LeftShoulder',
    'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase',
    'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
    'Hips', 'Spine', 'Spine01'
]

removed_count = 0
reassigned_count = 0

head_vg = mesh.vertex_groups.get('Head')
neck_vg = mesh.vertex_groups.get('neck')

group_indices = {mesh.vertex_groups[name].index: name for name in non_head_groups if name in mesh.vertex_groups}

for v in mesh.data.vertices:
    # Any vertex in the skull and hair area (z >= 136.0 cm)
    if v.co.z >= 136.0:
        for g in list(v.groups):
            if g.group in group_indices:
                w = g.weight
                if w > 0:
                    mesh.vertex_groups[group_indices[g.group]].remove([v.index])
                    removed_count += 1
                    head_vg.add([v.index], w, 'ADD')
                    reassigned_count += 1

print(f"Cleaned {removed_count} rogue weight bindings from head vertices! Reassigned {reassigned_count} to Head bone.")
