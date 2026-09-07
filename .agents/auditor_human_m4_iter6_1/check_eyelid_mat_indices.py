import bpy

for name in ['Mesh_Eyelid_Left', 'Mesh_Eyelid_Right']:
    obj = bpy.data.objects.get(name)
    if obj:
        indices = [p.material_index for p in obj.data.polygons]
        print(f'{name} material indices: {indices}')
