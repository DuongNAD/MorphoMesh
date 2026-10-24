import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
from anime_pipeline.mesh.generator import AnimeMeshGenerator, AnimeModelResult
from anime_pipeline.mesh.topology_cleaner import NormalHarmonizer

def compute_area_weighted_normals(verts, quads):
    acc = [[0.0, 0.0, 0.0] for _ in range(len(verts))]
    for q in quads:
        p0, p1, p2 = verts[q[0]], verts[q[1]], verts[q[2]]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        for vi in q:
            acc[vi][0] += cx
            acc[vi][1] += cy
            acc[vi][2] += cz
    res_n = []
    for nx, ny, nz in acc:
        nl = math.sqrt(nx * nx + ny * ny + nz * nz)
        if nl < 1e-12:
            res_n.append((0.0, 0.0, 1.0))
        else:
            res_n.append((nx / nl, ny / nl, nz / nl))
    return res_n

# 1. Generate mesh result
gen = AnimeMeshGenerator()
res = gen.generate()

# 2. Populate normals and harmonize seams
for name, sm in res.submeshes.items():
    sm.normals = compute_area_weighted_normals(sm.vertices, sm.quads)

overrides = NormalHarmonizer.harmonize_all_modular_seams(res.submeshes)
for name, sm in res.submeshes.items():
    if name in overrides:
        for vi, unified_n in overrides[name].items():
            sm.normals[vi] = unified_n

# 3. Export to temp output dir
td = Path(tempfile.mkdtemp())
t_blend = td / "anime_mesh_clean.blend"
t_glb = td / "anime_mesh_clean.glb"
temp_objs = td / "_temp_objs"
temp_objs.mkdir(parents=True, exist_ok=True)

# Export individual objs
res.export_all_obj(temp_objs)

# Write normals data for Blender script
normals_dict = {name: sm.normals for name, sm in res.submeshes.items() if sm.normals}
with open(temp_objs / "_normals.json", "w", encoding="utf-8") as nf:
    json.dump(normals_dict, nf)

builder_script = temp_objs / "_build_scene.py"
submesh_materials = {
    "Anime_Head": ["M_Anime_Skin", "M_Anime_Outline"],
    "Anime_Torso": ["M_Anime_Skin", "M_Anime_Outline"],
    "Anime_Arms": ["M_Anime_Skin", "M_Anime_Outline"],
    "Anime_Legs": ["M_Anime_Skin", "M_Anime_Outline"],
    "Anime_Hair": ["M_Anime_Hair", "M_Anime_Outline"],
    "Anime_Skirt": ["M_Anime_Clothes", "M_Anime_Outline"],
    "Anime_Shoes": ["M_Anime_Clothes", "M_Anime_Outline"],
}

temp_dir_esc = str(temp_objs).replace("\\", "\\\\")
blend_path_esc = str(t_blend).replace("\\", "\\\\")
glb_path_esc = str(t_glb).replace("\\", "\\\\")

with open(builder_script, "w", encoding="utf-8") as f:
    f.write(f"""import bpy, os, json

bpy.ops.wm.read_factory_settings(use_empty=True)

temp_dir = r"{temp_dir_esc}"
obj_names = {list(res.submeshes.keys())}
submesh_mats = {submesh_materials}

char_col = bpy.data.collections.new("Anime_Character_Meshes")
bpy.context.scene.collection.children.link(char_col)

created_mats = {{}}
for mat_name in ["M_Anime_Skin", "M_Anime_Hair", "M_Anime_Clothes", "M_Anime_Outline"]:
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    created_mats[mat_name] = mat

with open(os.path.join(temp_dir, "_normals.json"), "r", encoding="utf-8") as nf:
    normals_dict = json.load(nf)

imported_objs = []
for name in obj_names:
    path = os.path.join(temp_dir, f"{{name}}.obj")
    bpy.ops.wm.obj_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    obj.name = name

    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    char_col.objects.link(obj)

    for poly in obj.data.polygons:
        poly.use_smooth = True

    if name in normals_dict and normals_dict[name]:
        obj.data.normals_split_custom_set_from_vertices(normals_dict[name])

    for mname in submesh_mats.get(name, []):
        if mname in created_mats:
            obj.data.materials.append(created_mats[mname])

    imported_objs.append(obj)
    print(f"[Blender] Successfully imported {{name}}: {{len(obj.data.vertices)}} verts, {{len(obj.data.polygons)}} quads")

bpy.ops.wm.save_as_mainfile(filepath=r"{blend_path_esc}")
print(f"[Blender] Saved mainfile: {blend_path_esc}")

bpy.ops.export_scene.gltf(filepath=r"{glb_path_esc}", export_format='GLB', use_selection=False)
print(f"[Blender] Exported binary GLB: {glb_path_esc}")
""")

blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
cmd = [blender_exe, "--background", "--python", str(builder_script)]
res_build = subprocess.run(cmd, capture_output=True, text=True)
assert res_build.returncode == 0, f"Build scene failed:\n{res_build.stderr}\n{res_build.stdout}"

# Now run all 4 challenger tests against t_blend and t_glb!
test_script = td / "run_challenger_tests.py"
with open(test_script, "w", encoding="utf-8") as f:
    f.write(f"""import bpy, math

# 1. Blend integrity
mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
assert len(mesh_objs) == 7, f'Expected 7 mesh objects, got {{len(mesh_objs)}}'
char_col = bpy.data.collections.get('Anime_Character_Meshes')
assert char_col is not None, 'Collection Anime_Character_Meshes not found'
col_mesh_objs = [obj for obj in char_col.objects if obj.type == 'MESH']
assert len(col_mesh_objs) == 7, f'Expected 7 mesh objects in collection, got {{len(col_mesh_objs)}}'
for obj in mesh_objs:
    v_cnt = len(obj.data.vertices)
    p_cnt = len(obj.data.polygons)
    assert v_cnt > 0
    assert p_cnt > 0
    deg = [p.index for p in obj.data.polygons if p.area < 1e-8]
    assert len(deg) == 0
print("PASS_TEST_1_BLEND_INTEGRITY")

# 2. Seam normal alignment blend
head = bpy.data.objects.get('Anime_Head')
torso = bpy.data.objects.get('Anime_Torso')
assert head is not None and torso is not None
head_verts = {{i: (head.matrix_world @ v.co, (head.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(head.data.vertices)}}
torso_verts = {{i: (torso.matrix_world @ v.co, (torso.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(torso.data.vertices)}}
coincident = []
for hi, (hco, hno) in head_verts.items():
    for ti, (tco, tno) in torso_verts.items():
        if (hco - tco).length < 1e-4:
            dot = max(-1.0, min(1.0, hno.dot(tno)))
            ang = math.acos(dot)
            coincident.append((hi, ti, ang))
assert len(coincident) == 46
max_dev = max(c[2] for c in coincident)
avg_dev = sum(c[2] for c in coincident) / len(coincident)
violating = [c for c in coincident if c[2] >= 0.01]
print(f'MAX_ANGULAR_DEVIATION_RAD:{{max_dev:.6f}}')
print(f'AVG_ANGULAR_DEVIATION_RAD:{{avg_dev:.6f}}')
print(f'VIOLATIONS_COUNT:{{len(violating)}}/{{len(coincident)}}')
assert max_dev < 0.01, f'Seam normal angular deviation {{max_dev:.6f}} rad exceeds 0.01 rad'
assert max_dev < 0.005, f'Seam normal angular deviation {{max_dev:.6f}} rad exceeds 0.005 rad remediation threshold'
print("PASS_TEST_2_SEAM_NORMAL_ALIGNMENT")

# 3. GLB integrity
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{glb_path_esc}")
glb_mesh_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
assert len(glb_mesh_objs) == 7
for obj in glb_mesh_objs:
    assert len(obj.data.vertices) > 0
    assert len(obj.data.polygons) > 0
    deg = [p.index for p in obj.data.polygons if p.area < 1e-8]
    assert len(deg) == 0
print("PASS_TEST_3_GLB_INTEGRITY")

# 4. GLB seam normal alignment
objs = {{o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}}
head = objs.get('Anime_Head')
torso = objs.get('Anime_Torso')
assert head is not None and torso is not None
head_verts = {{i: (head.matrix_world @ v.co, (head.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(head.data.vertices)}}
torso_verts = {{i: (torso.matrix_world @ v.co, (torso.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(torso.data.vertices)}}
coincident_glb = []
for hi, (hco, hno) in head_verts.items():
    for ti, (tco, tno) in torso_verts.items():
        if (hco - tco).length < 1e-4:
            dot = max(-1.0, min(1.0, hno.dot(tno)))
            coincident_glb.append(math.acos(dot))
assert len(coincident_glb) == 46
max_dev_glb = max(coincident_glb)
violating_glb = [c for c in coincident_glb if c >= 0.01]
print(f'GLB_MAX_ANGULAR_DEVIATION_RAD:{{max_dev_glb:.6f}}')
print(f'GLB_VIOLATIONS_COUNT:{{len(violating_glb)}}/{{len(coincident_glb)}}')
assert max_dev_glb < 0.01, f'GLB deviation {{max_dev_glb:.6f}} rad exceeds 0.01 rad'
assert max_dev_glb < 0.005, f'GLB deviation {{max_dev_glb:.6f}} rad exceeds 0.005 rad remediation threshold'
print("PASS_TEST_4_GLB_SEAM_NORMAL_ALIGNMENT")
""")

cmd = [blender_exe, "--background", str(t_blend), "--python", str(test_script)]
res_test = subprocess.run(cmd, capture_output=True, text=True)
print(res_test.stdout)
if res_test.stderr:
    print("STDERR:", res_test.stderr)
assert res_test.returncode == 0, "Adversarial test verification failed!"
print("=== ALL 4 CHALLENGER 2 TESTS VERIFIED WITH 100% SUCCESS ===")
