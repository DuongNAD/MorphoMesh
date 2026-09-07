import bpy

body = bpy.data.objects.get('Yu_Nian_An_Body')
verts = body.data.vertices
head_verts = [v.co for v in verts if v.co.z >= 1.44]

# Group by Z approx
z_buckets = {}
for v in head_verts:
    z_key = round(v.z, 3)
    if z_key not in z_buckets:
        z_buckets[z_key] = []
    z_buckets[z_key].append(v)

print(f"Total head verts: {len(head_verts)}")
for z_key in sorted(z_buckets.keys()):
    vs = z_buckets[z_key]
    min_y = min(v.y for v in vs)
    max_y = max(v.y for v in vs)
    min_x = min(v.x for v in vs)
    max_x = max(v.x for v in vs)
    print(f"Z={z_key:.3f}: count={len(vs)}, Y in [{min_y:.4f}, {max_y:.4f}], X in [{min_x:.4f}, {max_x:.4f}]")
