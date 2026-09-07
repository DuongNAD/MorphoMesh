"""
Milestone 4 Iteration 7: Master Character Regeneration and Verification Renders.
Regenerates output/yu_nian_an/Yu_Nian_An_Master.blend from updated character_assembler.py,
validates zero lip penetration, material slot preservation, and 0.00mm shear detachment,
and renders portrait, fullbody, and face closeup plates.
"""

import sys
import os
import math
import subprocess

sys.path.insert(0, os.path.abspath("src"))
from morphomesh.character_assembler import MasterAssemblyConfig, get_master_assembly_script

blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
master_blend = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")

cfg = MasterAssemblyConfig(
    character_name="Yu_Nian_An",
    height=1.65,
    head_ratio=7.41,
    hair_strand_count=15000,
    render_engine="CYCLES",
    cycles_samples=128,
    save_blend=True,
    output_blend_path=master_blend,
)

script = get_master_assembly_script(cfg, output_blend_path=master_blend)

gen_script_path = os.path.abspath(".agents/worker_human_m4_iter7/run_assembly.py")
with open(gen_script_path, "w", encoding="utf-8") as f:
    f.write(script)

print("Step 1: Running master assembly script inside Blender 4.5.4 LTS...")
proc = subprocess.run([blender_exe, "--background", "--python", gen_script_path], capture_output=True, text=True)
print("Assembly stdout tail:")
print("\n".join(proc.stdout.splitlines()[-30:]))
if proc.returncode != 0:
    print("Assembly stderr:")
    print(proc.stderr)
    sys.exit(proc.returncode)

print("\nStep 2: Auditing regenerated master blend and executing verification renders...")
render_script = f"""
import bpy
import bmesh
import math
import os
from mathutils.bvhtree import BVHTree
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=r"{master_blend}")
scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()

print("=== LIVE MASTER BLEND VERIFICATION AUDIT ===")

# 1. Audit Body Mesh
body = bpy.data.objects.get('Yu_Nian_An_Body')
assert body is not None, "Yu_Nian_An_Body missing!"
n_verts = len(body.data.vertices)
n_quads = sum(1 for p in body.data.polygons if len(p.vertices) == 4)
n_tris = sum(1 for p in body.data.polygons if len(p.vertices) == 3)
print(f"Body vertices: {{n_verts}} (2144 req), quads: {{n_quads}} (2036 req, 100%), tris: {{n_tris}} (0 req)")
assert n_verts == 2144, f"Body verts {{n_verts}} != 2144"
assert n_quads == 2036, f"Body quads {{n_quads}} != 2036"
assert n_tris == 0, f"Body tris {{n_tris}} != 0"

# 2. Audit Mouth Polygons on Body
skin_mat_idx = [i for i, m in enumerate(body.data.materials) if m.name == 'Mat_Human_Skin_SSS'][0]
p377 = body.data.polygons[377]
p378 = body.data.polygons[378]
print(f"Poly 377: slot {{p377.material_index}} (skin={{skin_mat_idx}}), Poly 378: slot {{p378.material_index}}")
assert p377.material_index == skin_mat_idx, "Poly 377 is not skin!"
assert p378.material_index == skin_mat_idx, "Poly 378 is not skin!"

# 3. Audit Scalp Material
scalp_mat_idx = [i for i, m in enumerate(body.data.materials) if m.name == 'Mat_Human_Scalp'][0]
scalp_polys = [p for p in body.data.polygons if p.material_index == scalp_mat_idx]
print(f"Scalp polygons count: {{len(scalp_polys)}} (73 req)")
assert len(scalp_polys) == 73, f"Expected 73 scalp polygons, got {{len(scalp_polys)}}"

# 4. Audit Mesh_Lips Geometry and Penetration
lips = bpy.data.objects.get('Mesh_Lips')
assert lips is not None, "Mesh_Lips missing!"
l_verts = len(lips.data.vertices)
l_quads = sum(1 for p in lips.data.polygons if len(p.vertices) == 4)
print(f"Mesh_Lips verts: {{l_verts}} (66 req), quads: {{l_quads}} (50 req)")
assert l_verts == 66, f"Mesh_Lips verts {{l_verts}} != 66"
assert l_quads == 50, f"Mesh_Lips quads {{l_quads}} != 50"

bvh_body = BVHTree.FromObject(body, depsgraph)
signed_dists = []
penetrations = 0
for v in lips.data.vertices:
    vw = lips.matrix_world @ v.co
    loc, norm, _, dist = bvh_body.find_nearest(vw)
    if loc is not None:
        dot = (vw - loc).dot(norm)
        sd = dist if dot >= 0 else -dist
        signed_dists.append(sd * 1000.0)
        if dot < -0.0001:
            penetrations += 1

min_clearance = min(signed_dists)
avg_clearance = sum(signed_dists) / len(signed_dists)
max_clearance = max(signed_dists)
print(f"Mesh_Lips Signed Clearance: min={{min_clearance:+.2f}}mm, avg={{avg_clearance:+.2f}}mm, max={{max_clearance:+.2f}}mm | Penetrations: {{penetrations}}/66")
assert penetrations == 0, f"Mesh_Lips has {{penetrations}} penetrating vertices inside body!"
assert min_clearance >= 0.1, f"Mesh_Lips min clearance {{min_clearance:.2f}}mm < 0.1mm!"

# 5. Audit Material Slots and Index Distribution on Lips and Eyelids
lips_dist = {{}}
for p in lips.data.polygons:
    lips_dist[p.material_index] = lips_dist.get(p.material_index, 0) + 1
print(f"Mesh_Lips material distribution: {{lips_dist}} (materials: {{[m.name for m in lips.data.materials]}})")
assert lips_dist.get(0, 0) == 41, f"Expected 41 quads on slot 0 (lips), got {{lips_dist.get(0, 0)}}"
assert lips_dist.get(1, 0) == 9, f"Expected 9 quads on slot 1 (oral slit), got {{lips_dist.get(1, 0)}}"

for el_name in ['Mesh_Eyelid_Left', 'Mesh_Eyelid_Right']:
    el = bpy.data.objects.get(el_name)
    assert el is not None, f"{{el_name}} missing!"
    el_dist = {{}}
    for p in el.data.polygons:
        el_dist[p.material_index] = el_dist.get(p.material_index, 0) + 1
    print(f"{{el_name}} material distribution: {{el_dist}} (materials: {{[m.name for m in el.data.materials]}})")
    assert el_dist.get(0, 0) == 8, f"{{el_name}} expected 8 eyeliner quads, got {{el_dist.get(0, 0)}}"
    assert el_dist.get(1, 0) == 8, f"{{el_name}} expected 8 skin SSS quads, got {{el_dist.get(1, 0)}}"

# 6. Audit Armature Binding & 30° Head Rotation Kinematics
arm_obj = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')
assert arm_obj is not None, "Armature missing!"
pb_head = arm_obj.pose.bones.get('DEF-head')
assert pb_head is not None, "DEF-head pose bone missing!"

eye_sphere_names = [
    'Mesh_Eye_Left_CorneaSclera', 'Mesh_Eye_Left_IrisPupil',
    'Mesh_Eye_Right_CorneaSclera', 'Mesh_Eye_Right_IrisPupil'
]
hair_names = [
    'Hair_Hime_Bangs', 'Hair_Eyebrows', 'Hair_Eyelashes',
    'Hair_Scalp_Crown', 'Hair_Hime_Sidelocks', 'Hair_Back_Cascade'
]

# Verify modifiers and vertex groups present
for name in ['Mesh_Lips', 'Mesh_Eyelid_Left', 'Mesh_Eyelid_Right'] + eye_sphere_names + hair_names:
    o = bpy.data.objects.get(name)
    assert o is not None, f"Object {{name}} missing!"
    has_arm = any(m.type == 'ARMATURE' and m.object == arm_obj for m in o.modifiers)
    assert has_arm, f"{{name}} lacks Armature modifier targeting {{arm_obj.name}}!"
    assert 'DEF-head' in o.vertex_groups, f"{{name}} lacks 'DEF-head' vertex group!"

def get_eval_center(obj_name, deps):
    o = bpy.data.objects.get(obj_name)
    if not o or not hasattr(o.data, 'vertices') or len(o.data.vertices) == 0:
        return None
    e = o.evaluated_get(deps)
    me = e.to_mesh()
    cos = [e.matrix_world @ v.co for v in me.vertices]
    e.to_mesh_clear()
    return sum(cos, Vector((0, 0, 0))) / len(cos) if cos else None

# Reset pose
pb_head.rotation_mode = 'XYZ'
pb_head.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
deps_rest = bpy.context.evaluated_depsgraph_get()

all_eval_names = ['Mesh_Lips', 'Mesh_Eyelid_Left', 'Mesh_Eyelid_Right'] + eye_sphere_names + hair_names
base_centers = {{n: get_eval_center(n, deps_rest) for n in all_eval_names}}

# Rotate 30 degrees
pb_head.rotation_euler = (math.radians(30.0), 0.0, 0.0)
bpy.context.view_layer.update()
deps_rot = bpy.context.evaluated_depsgraph_get()

print("--- EVALUATED DISPLACEMENTS UNDER 30° DEF-head ROTATION ---")
for n in all_eval_names:
    c_base = base_centers[n]
    c_rot = get_eval_center(n, deps_rot)
    disp = (c_rot - c_base).length * 1000.0 if c_rot and c_base else 0.0
    print(f"  {{n:<32}}: {{disp:.2f}} mm")
    assert disp >= 20.0, f"{{n}} failed kinematics: displacement {{disp:.2f}}mm < 20.0mm!"

# Eyelid-to-eyeball shear
c_lid_base = base_centers['Mesh_Eyelid_Left']
c_eye_base = base_centers['Mesh_Eye_Left_CorneaSclera']
c_lid_rot = get_eval_center('Mesh_Eyelid_Left', deps_rot)
c_eye_rot = get_eval_center('Mesh_Eye_Left_CorneaSclera', deps_rot)
dist_base = (c_lid_base - c_eye_base).length * 1000.0
dist_rot = (c_lid_rot - c_eye_rot).length * 1000.0
shear = abs(dist_rot - dist_base)
print(f"Eyelid-to-Eyeball Rest Dist: {{dist_base:.2f}}mm, Rotated Dist: {{dist_rot:.2f}}mm, Shear: {{shear:.4f}}mm")
assert shear < 0.01, f"Separation shear {{shear:.4f}}mm > 0.01mm!"

# Reset head rotation before rendering
pb_head.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()

print("ALL GEOMETRIC AND KINEMATIC AUDITS PASSED! PROCEEDING TO BEAUTY RENDERS...")

# 7. Render Settings
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.engine = 'CYCLES'
scene.cycles.samples = 128
scene.cycles.device = 'CPU'

# Render 1: Portrait (85mm)
cam_portrait = bpy.data.objects.get('Camera_Portrait_85mm')
assert cam_portrait is not None, "Camera_Portrait_85mm missing!"
scene.camera = cam_portrait
portrait_path = os.path.abspath("output/yu_nian_an/master_portrait_clean.png")
scene.render.filepath = portrait_path
print("Rendering portrait to:", portrait_path)
bpy.ops.render.render(write_still=True)
print("Portrait rendered! File size:", os.path.getsize(portrait_path))

# Render 2: Fullbody (50mm)
cam_fullbody = bpy.data.objects.get('Camera_FullBody')
assert cam_fullbody is not None, "Camera_FullBody missing!"
scene.camera = cam_fullbody
fullbody_path = os.path.abspath("output/yu_nian_an/master_fullbody_clean.png")
scene.render.filepath = fullbody_path
print("Rendering fullbody to:", fullbody_path)
bpy.ops.render.render(write_still=True)
print("Fullbody rendered! File size:", os.path.getsize(fullbody_path))

# Render 3: Close-up Face Plate (135mm camera, distance 1.2m, centered on lips/eyes Z=1.50m)
cam_closeup_data = bpy.data.cameras.get("Camera_Face_Closeup_135mm") or bpy.data.cameras.new(name="Camera_Face_Closeup_135mm")
cam_closeup_data.lens = 135.0
cam_closeup_data.sensor_width = 36.0
cam_closeup_data.sensor_height = 24.0

cam_closeup_obj = bpy.data.objects.get("Camera_Face_Closeup_135mm") or bpy.data.objects.new(name="Camera_Face_Closeup_135mm", object_data=cam_closeup_data)
s = {cfg.height} / 1.65
cam_closeup_obj.location = (0.0, -1.25 * s, 1.505 * s)
cam_closeup_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
if "06_Lights_Camera" in bpy.data.collections:
    if cam_closeup_obj.name not in bpy.data.collections["06_Lights_Camera"].objects:
        bpy.data.collections["06_Lights_Camera"].objects.link(cam_closeup_obj)

scene.camera = cam_closeup_obj
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
closeup_path = os.path.abspath("output/yu_nian_an/audit_face_closeup.png")
scene.render.filepath = closeup_path
print("Rendering face close-up to:", closeup_path)
bpy.ops.render.render(write_still=True)
print("Face close-up rendered! File size:", os.path.getsize(closeup_path))

# Save the master mainfile with the closeup camera
bpy.ops.wm.save_mainfile(filepath=r"{master_blend}")

print("=== ALL BEAUTY RENDERS AND VERIFICATIONS COMPLETE ===")
"""

render_script_path = os.path.abspath(".agents/worker_human_m4_iter7/run_render.py")
with open(render_script_path, "w", encoding="utf-8") as f:
    f.write(render_script)

print("\nStep 3: Executing live Blender audit and rendering...")
proc2 = subprocess.run([blender_exe, "--background", "--python", render_script_path], capture_output=True, text=True)
print(proc2.stdout)
if proc2.returncode != 0:
    print("Render stderr:")
    print(proc2.stderr)
    sys.exit(proc2.returncode)

print("\nStep 4: Copying close-up face plate to agent folder for reporting...")
import shutil
shutil.copy2(os.path.abspath("output/yu_nian_an/audit_face_closeup.png"), os.path.abspath(".agents/worker_human_m4_iter7/audit_face_closeup.png"))
print("Done!")
