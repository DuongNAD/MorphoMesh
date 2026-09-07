import bpy

body = bpy.data.objects.get('Yu_Nian_An_Body')
groups = {vg.name: vg.index for vg in body.vertex_groups}

joints = [
    ('DEF-upper_arm.L', 'DEF-upper_arm.L.001'),
    ('DEF-upper_arm.L.001', 'DEF-forearm.L'),
    ('DEF-forearm.L', 'DEF-forearm.L.001'),
    ('DEF-thigh.L', 'DEF-thigh.L.001'),
    ('DEF-thigh.L.001', 'DEF-shin.L'),
    ('DEF-shin.L', 'DEF-shin.L.001'),
    ('DEF-shin.L.001', 'DEF-foot.L'),
    ('DEF-thigh.R.001', 'DEF-shin.R'),
    ('DEF-upper_arm.R.001', 'DEF-forearm.R'),
]

print('=== RIGIFY TWO-BONE SEGMENT JOINT WEIGHTING VERIFICATION ===')
for b1_name, b2_name in joints:
    if b1_name not in groups or b2_name not in groups:
        print(f'Missing group: {b1_name} or {b2_name}')
        continue
    g1 = groups[b1_name]
    g2 = groups[b2_name]
    
    shared = 0
    for v in body.data.vertices:
        w1 = 0.0
        w2 = 0.0
        for g in v.groups:
            if g.group == g1:
                w1 = g.weight
            elif g.group == g2:
                w2 = g.weight
        if w1 > 0.01 and w2 > 0.01:
            shared += 1
    print(f'Joint {b1_name} <-> {b2_name}: {shared} shared blend vertices')
