import bpy
import bmesh
import mathutils

obj = bpy.data.objects.get('Yu_Nian_An_Body')
assert obj is not None, 'Yu_Nian_An_Body not found!'

bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# Check manifoldness
is_manifold = True
for v in bm.verts:
    if not v.is_manifold:
        is_manifold = False
        break

# Check inverted normals / face areas
zero_area_faces = 0
min_face_area = 1e9
max_face_area = 0.0

for f in bm.faces:
    area = f.calc_area()
    if area < 1e-7:
        zero_area_faces += 1
    if area < min_face_area:
        min_face_area = area
    if area > max_face_area:
        max_face_area = area

# Check volume and bounding box
bbox_min = [min(v.co[i] for v in bm.verts) for i in range(3)]
bbox_max = [max(v.co[i] for v in bm.verts) for i in range(3)]
dim = [bbox_max[i] - bbox_min[i] for i in range(3)]

# Calculate mesh volume (if closed manifold, calc_volume is positive)
vol = bm.calc_volume()

print('=== BODY MESH FORENSIC VALIDATION ===')
print(f'Object: {obj.name}')
print(f'Is Strictly Manifold: {is_manifold}')
print(f'Zero Area Faces: {zero_area_faces}')
print(f'Min Face Area: {min_face_area:.8f} m^2')
print(f'Max Face Area: {max_face_area:.8f} m^2')
print(f'Mesh Volume: {vol:.6f} m^3 (Positive indicates outward-pointing normals)')
print(f'Bounding Box Min: {[round(x, 4) for x in bbox_min]}')
print(f'Bounding Box Max: {[round(x, 4) for x in bbox_max]}')
print(f'Dimensions (X, Y, Z): {[round(x, 4) for x in dim]}')

bm.free()
