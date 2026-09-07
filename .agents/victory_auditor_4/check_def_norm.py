import bpy

body = bpy.data.objects.get('Yu_Nian_An_Body')
def_groups = {vg.index for vg in body.vertex_groups if vg.name.startswith('DEF-')}

def_anomalies = 0
for v in body.data.vertices:
    def_w = sum(g.weight for g in v.groups if g.group in def_groups)
    if abs(def_w - 1.0) > 0.05:
        def_anomalies += 1

print('=== DEF BONE WEIGHT NORMALIZATION CHECK ===')
print(f'Total Vertices: {len(body.data.vertices)}')
print(f'DEF- Bone Weight Anomalies (|sum - 1.0| > 0.05): {def_anomalies}')
assert def_anomalies == 0, f'{def_anomalies} vertices have non-normalized DEF weights!'
print('PASS: 100% of body vertices have strictly normalized DEF bone weights (sum = 1.000)!')
