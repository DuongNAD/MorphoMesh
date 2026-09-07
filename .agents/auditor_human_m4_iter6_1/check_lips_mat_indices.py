import bpy

lips = bpy.data.objects.get('Mesh_Lips')
mesh = lips.data

print('LIPS MATERIALS IN OBJECT:', [m.name if m else 'None' for m in lips.data.materials])
for i, p in enumerate(mesh.polygons):
    if p.material_index != 0:
        print(f'Poly {i}: mat_index={p.material_index}')
