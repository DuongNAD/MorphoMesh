import bpy

body = bpy.data.objects.get('Yu_Nian_An_Body')
for i in range(10):
    v = body.data.vertices[i]
    weights = [(body.vertex_groups[g.group].name, g.weight) for g in v.groups]
    total_w = sum(w for _, w in weights)
    print(f'Vert {i:2d}: total_w={total_w:.4f}, groups={weights}')
