import sys
sys.path.insert(0, 'src')
import json
import math
import os
import subprocess
import tempfile

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

blender_code = """
import sys
sys.path.insert(0, r'E:\\tool\\mcp\\MorphoMesh\\src')
sys.path.append(r'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages')

import bpy, math, json
from morphomesh.human_generator import get_human_generation_script
from morphomesh.human_rigging import get_rigging_script, ARKIT_52_BLENDSHAPES

mesh_name = 'Human_Base_Mesh'
exec(get_human_generation_script(mesh_name))
exec(get_rigging_script(mesh_name))

obj = bpy.data.objects[mesh_name]
arm = bpy.data.objects['Armature_Yu_Nian_An_Rigify']
rest_coords = [list(v.co) for v in obj.data.vertices]

# 1. Bone deformation metrics
bone_tests = [
    ('DEF-forearm.L', (math.radians(45), 0, 0)),
    ('DEF-forearm.R', (math.radians(45), 0, 0)),
    ('DEF-shin.L', (math.radians(-45), 0, 0)),
    ('DEF-shin.R', (math.radians(-45), 0, 0)),
    ('DEF-upper_arm.L', (0, 0, math.radians(45))),
    ('DEF-thigh.L', (math.radians(45), 0, 0)),
]

bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')

bone_res = {}
for b_name, rot in bone_tests:
    pb = arm.pose.bones[b_name]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = rot
    bpy.context.view_layer.update()
    eval_mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    disps = [math.sqrt(sum((a - b)**2 for a, b in zip(p0, p1))) for p0, p1 in zip(rest_coords, [list(v.co) for v in eval_mesh.vertices])]
    bone_res[b_name] = {'max_disp': max(disps), 'moving_verts': sum(1 for d in disps if d > 0.001)}
    # Reset
    pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

# 2. Blendshape metrics
key_blocks = obj.data.shape_keys.key_blocks
basis = key_blocks['Basis']
shape_res = {}
for k in ARKIT_52_BLENDSHAPES:
    kb = key_blocks[k]
    disps = [math.sqrt(sum((a - b)**2 for a, b in zip(kb.data[i].co, basis.data[i].co))) for i in range(len(kb.data))]
    shape_res[k] = {'max_disp': max(disps), 'displaced_verts': sum(1 for d in disps if d > 1e-5)}

print('REPORT_START')
print(json.dumps({'bones': bone_res, 'shapes': shape_res}))
print('REPORT_END')
"""

with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
    f.write(blender_code)
    sp = f.name

p = subprocess.run([BLENDER_EXE, '--background', '--factory-startup', '--python', sp], capture_output=True, text=True)
if os.path.exists(sp):
    os.remove(sp)

if p.returncode != 0 or 'REPORT_START' not in p.stdout:
    print("STDOUT:\n", p.stdout)
    print("STDERR:\n", p.stderr)
    sys.exit(1)

lines = p.stdout.splitlines()
idx1 = [i for i, l in enumerate(lines) if 'REPORT_START' in l][0]
idx2 = [i for i, l in enumerate(lines) if 'REPORT_END' in l][0]
data = json.loads(lines[idx1+1])

print('=== BONE ROTATION METRICS IN BLENDER ===')
for b, s in data['bones'].items():
    print(f"{b}: max_disp = {s['max_disp']:.6f}m, moving_verts = {s['moving_verts']}")

print('\n=== ARKIT 52 BLENDSHAPES IN BLENDER ===')
disps = [s['max_disp'] for s in data['shapes'].values()]
displaced_counts = [s['displaced_verts'] for s in data['shapes'].values()]
print(f"Total keys: {len(data['shapes'])} / 52")
min_d = min(disps)
max_d = max(disps)
min_k = [k for k, v in data['shapes'].items() if v['max_disp'] == min_d][0]
max_k = [k for k, v in data['shapes'].items() if v['max_disp'] == max_d][0]
print(f"Min displacement: {min_d:.6f}m ({min_k})")
print(f"Max displacement: {max_d:.6f}m ({max_k})")
print(f"Average displacement: {sum(disps)/len(disps):.6f}m")
min_c = min(displaced_counts)
max_c = max(displaced_counts)
min_ck = [k for k, v in data['shapes'].items() if v['displaced_verts'] == min_c][0]
max_ck = [k for k, v in data['shapes'].items() if v['displaced_verts'] == max_c][0]
print(f"Min displaced verts count: {min_c} ({min_ck})")
print(f"Max displaced verts count: {max_c} ({max_ck})")
