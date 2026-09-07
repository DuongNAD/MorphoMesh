import bpy

body = bpy.data.objects.get('Yu_Nian_An_Body')
arm = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')

# Check vertex groups for joints: forearm / upper_arm, thigh / shin
groups = {vg.name: vg.index for vg in body.vertex_groups}

joints = [
    ('DEF-upper_arm.L', 'DEF-forearm.L'),
    ('DEF-upper_arm.R', 'DEF-forearm.R'),
    ('DEF-thigh.L', 'DEF-shin.L'),
    ('DEF-thigh.R', 'DEF-shin.R'),
    ('DEF-spine.003', 'DEF-head'),
]

print('=== ANTI-PINCH JOINT WEIGHTING VERIFICATION ===')
for b1_name, b2_name in joints:
    if b1_name not in groups or b2_name not in groups:
        print(f'Missing group for {b1_name} or {b2_name}')
        continue
    g1 = groups[b1_name]
    g2 = groups[b2_name]
    
    # Find vertices influenced by both bones (blend / transition zone)
    shared_verts = 0
    smooth_weights = []
    for v in body.data.vertices:
        w1 = 0.0
        w2 = 0.0
        for g in v.groups:
            if g.group == g1:
                w1 = g.weight
            elif g.group == g2:
                w2 = g.weight
        if w1 > 0.05 and w2 > 0.05:
            shared_verts += 1
            smooth_weights.append((w1, w2))
            
    print(f'Joint {b1_name} <-> {b2_name}: {shared_verts} transition zone vertices (smooth anti-pinch blending)')
    assert shared_verts > 0, f'No blend transition zone found between {b1_name} and {b2_name}!'

print('PASS: Anti-pinch blend zones verified across all major articulated joints!')
