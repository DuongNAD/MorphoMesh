import bpy

lips = bpy.data.objects.get('Mesh_Lips')
mesh = lips.data

print(f'Mesh_Lips vertices: {len(mesh.vertices)}')
print(f'Mesh_Lips polygons: {len(mesh.polygons)}')

slot0_count = sum(1 for p in mesh.polygons if p.material_index == 0)
slot1_count = sum(1 for p in mesh.polygons if p.material_index == 1)
print(f'Slot 0 (Mat_Human_Lips): {slot0_count} quads')
print(f'Slot 1 (Mat_Human_Oral_Slit): {slot1_count} quads')

center_verts = [v for v in mesh.vertices if abs(v.co.x) < 0.0015]
center_verts.sort(key=lambda v: v.co.z)
print('Centerline profile (X ~ 0):')
for v in center_verts:
    print(f'  z={v.co.z:.4f}m, y={v.co.y:.4f}m, x={v.co.x:.4f}m')

row5_verts = [v for v in mesh.vertices if v.co.z > 1.468]
row5_verts.sort(key=lambda v: v.co.x)
print('Cupids bow upper margin (Row 5):')
for v in row5_verts:
    print(f'  x={v.co.x*1000:6.2f}mm, z={v.co.z*1000:6.2f}mm, y={v.co.y*1000:6.2f}mm')

print(f'Parent: {lips.parent.name if lips.parent else None}')
print(f'Modifiers: {[m.name for m in lips.modifiers]}')
