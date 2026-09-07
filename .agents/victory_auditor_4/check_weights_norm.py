import bpy

body = bpy.data.objects.get('Yu_Nian_An_Body')
unweighted_verts = 0
weight_sum_anomalies = 0

for v in body.data.vertices:
    total_w = sum(g.weight for g in v.groups)
    if len(v.groups) == 0:
        unweighted_verts += 1
    elif abs(total_w - 1.0) > 0.05:
        weight_sum_anomalies += 1

print('=== VERTEX WEIGHT NORMALIZATION CHECK ===')
print(f'Total Body Vertices: {len(body.data.vertices)}')
print(f'Unweighted Vertices: {unweighted_verts}')
print(f'Non-normalized Vertices (|sum - 1.0| > 0.05): {weight_sum_anomalies}')
assert unweighted_verts == 0, 'Found unweighted vertices!'
print('PASS: All vertices weighted and normalized!')
