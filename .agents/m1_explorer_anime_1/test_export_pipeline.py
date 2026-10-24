"""
End-to-End Export Verification for M1 Feature F01:
Exports 7 discrete modular sub-meshes to:
1. Individual .obj files
2. Multi-object .obj file
3. Blender headless script generating master .blend and .glb
"""
import os
import subprocess
import sys
from test_modular_synthesis import test_synthesis

out_dir = r"E:\tool\mcp\MorphoMesh\.agents\m1_explorer_anime_1\test_output"
os.makedirs(out_dir, exist_ok=True)

# Build meshes
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human.mold_loader import load_anatomical_base_mold

verts, quads, uvs = load_anatomical_base_mold()

head_q, torso_q, arm_q, leg_q = [], [], [], []
for qi, q in enumerate(quads):
    cz = sum(verts[vi][2] for vi in q) / 4.0
    cx = sum(verts[vi][0] for vi in q) / 4.0
    if cz >= 1.385:
        head_q.append(qi)
    elif abs(cx) > 0.165 and cz >= 0.85:
        arm_q.append(qi)
    elif cz < 0.78:
        leg_q.append(qi)
    else:
        torso_q.append(qi)

def extract(q_list):
    sub_v, sub_q, v_map = [], [], {}
    for qi in q_list:
        q = quads[qi]
        new_f = []
        for vi in q:
            if vi not in v_map:
                v_map[vi] = len(sub_v)
                sub_v.append(verts[vi])
            new_f.append(v_map[vi])
        sub_q.append(tuple(new_f))
    return sub_v, sub_q

head_v, head_q = extract(head_q)
torso_v, torso_q = extract(torso_q)
arm_v, arm_q = extract(arm_q)
leg_v, leg_q = extract(leg_q)

# Skirt
import math
skirt_v, skirt_q = [], []
for ri in range(10):
    t = ri / 9.0
    z = 0.88 * (1.0 - t) + 0.54 * t
    rx = 0.155 * (1.0 - t) + 0.255 * t
    ry = 0.115 * (1.0 - t) + 0.205 * t
    amp = 0.006 * (1.0 - t) + 0.022 * t
    for si in range(48):
        th = 2.0 * math.pi * si / 48
        r_scale = 1.0 + (amp / rx) * math.sin(16 * th)
        skirt_v.append((rx * math.cos(th) * r_scale, ry * math.sin(th) * r_scale, z))
for ri in range(9):
    for si in range(48):
        sn = (si + 1) % 48
        skirt_q.append((ri*48 + si, ri*48 + sn, (ri+1)*48 + sn, (ri+1)*48 + si))

# Hair
hair_v, hair_q = [], []
for ri in range(6):
    phi = (math.pi * 0.45) * (ri / 5.0)
    z = 1.650 - 0.15 * (1.0 - math.cos(phi))
    r = 0.095 * math.sin(phi) + 0.006
    for si in range(24):
        th = 2.0 * math.pi * si / 24
        hair_v.append((r * math.cos(th), r * math.sin(th) * 1.15, z))
for ri in range(5):
    for si in range(24):
        sn = (si + 1) % 24
        hair_q.append((ri*24 + si, ri*24 + sn, (ri+1)*24 + sn, (ri+1)*24 + si))

for side in [1.0, -1.0]:
    bidx = len(hair_v)
    for ri in range(15):
        t = ri / 14.0
        P0 = (0.088 * side, -0.020, 1.530)
        P1 = (0.160 * side, -0.040, 1.480)
        P2 = (0.175 * side, -0.050, 1.320)
        P3 = (0.150 * side, -0.030, 1.150)
        cx = (1-t)**3 * P0[0] + 3*(1-t)**2 * t * P1[0] + 3*(1-t) * t**2 * P2[0] + t**3 * P3[0]
        cy = (1-t)**3 * P0[1] + 3*(1-t)**2 * t * P1[1] + 3*(1-t) * t**2 * P2[1] + t**3 * P3[1]
        cz = (1-t)**3 * P0[2] + 3*(1-t)**2 * t * P1[2] + 3*(1-t) * t**2 * P2[2] + t**3 * P3[2]
        rad = 0.025 * (1.0 - 0.75 * t)
        for si in range(6):
            th = 2.0 * math.pi * si / 6
            hair_v.append((cx + rad * math.cos(th), cy + rad * math.sin(th), cz))
    for ri in range(14):
        for si in range(6):
            sn = (si + 1) % 6
            hair_q.append((bidx + ri*6 + si, bidx + ri*6 + sn, bidx + (ri+1)*6 + sn, bidx + (ri+1)*6 + si))

# Shoes
shoes_v, shoes_q = [], []
for side in [1.0, -1.0]:
    bidx = len(shoes_v)
    cx = 0.088 * side
    for ri in range(4):
        t = ri / 3.0
        z = 0.000 + 0.035 * t
        rx = 0.045 + 0.005 * t
        ry = 0.090 + 0.010 * t
        for si in range(20):
            th = 2.0 * math.pi * si / 20
            shoes_v.append((cx + rx * math.cos(th), -0.035 + ry * math.sin(th), z))
    for ri in range(3):
        for si in range(20):
            sn = (si + 1) % 20
            shoes_q.append((bidx + ri*20 + si, bidx + ri*20 + sn, bidx + (ri+1)*20 + sn, bidx + (ri+1)*20 + si))

submeshes = {
    "Anime_Head": (head_v, head_q),
    "Anime_Torso": (torso_v, torso_q),
    "Anime_Arms": (arm_v, arm_q),
    "Anime_Legs": (leg_v, leg_q),
    "Anime_Hair": (hair_v, hair_q),
    "Anime_Skirt": (skirt_v, skirt_q),
    "Anime_Shoes": (shoes_v, shoes_q),
}

# 1. Export Individual OBJs
for name, (sv, sq) in submeshes.items():
    filepath = os.path.join(out_dir, f"{name}.obj")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {name} Wavefront OBJ\n")
        f.write(f"o {name}\n")
        for v in sv:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for q in sq:
            f.write(f"f {q[0]+1} {q[1]+1} {q[2]+1} {q[3]+1}\n")
    print(f"Exported {name}.obj ({len(sv)} verts, {len(sq)} quads)")

# 2. Export Multi-Object Master OBJ
master_obj = os.path.join(out_dir, "anime_character_modular.obj")
with open(master_obj, "w", encoding="utf-8") as f:
    f.write("# Anime Character Modular Master OBJ\n")
    v_offset = 0
    for name, (sv, sq) in submeshes.items():
        f.write(f"o {name}\n")
        f.write(f"g {name}\n")
        for v in sv:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for q in sq:
            f.write(f"f {q[0]+1+v_offset} {q[1]+1+v_offset} {q[2]+1+v_offset} {q[3]+1+v_offset}\n")
        v_offset += len(sv)
print(f"Exported {master_obj} (total {v_offset} vertices)")

# 3. Test Blender headless scene generation and .blend / .glb export
blender_py = os.path.join(out_dir, "blender_build_scene.py")
with open(blender_py, "w", encoding="utf-8") as f:
    f.write(f"""import bpy, os

# Clear existing objects
bpy.ops.wm.read_factory_settings(use_empty=True)

out_dir = r"{out_dir}"
obj_names = ["Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs", "Anime_Hair", "Anime_Skirt", "Anime_Shoes"]

char_col = bpy.data.collections.new("Anime_Character_Meshes")
bpy.context.scene.collection.children.link(char_col)

imported_objs = []
for name in obj_names:
    path = os.path.join(out_dir, f"{{name}}.obj")
    bpy.ops.wm.obj_import(filepath=path)
    # The newly imported object is selected
    obj = bpy.context.selected_objects[0]
    obj.name = name
    # Move to character collection
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    char_col.objects.link(obj)
    # Set smooth shading
    for poly in obj.data.polygons:
        poly.use_smooth = True
    imported_objs.append(obj)
    print(f"[Blender] Imported {{name}}: {{len(obj.data.vertices)}} verts, {{len(obj.data.polygons)}} polys")

# Save master .blend
blend_path = os.path.join(out_dir, "anime_character_model.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"[Blender] Saved {{blend_path}}")

# Export .glb
glb_path = os.path.join(out_dir, "anime_character_model.glb")
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=False)
print(f"[Blender] Exported {{glb_path}}")
""")

# Run blender headless
blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
cmd = [blender_exe, "--background", "--python", blender_py]
res = subprocess.run(cmd, capture_output=True, text=True)
print("\n--- BLENDER HEADLESS EXECUTION OUTPUT ---")
print(res.stdout)
if res.returncode != 0:
    print("Blender STDERR:", res.stderr)
else:
    print("Blender headless execution completed successfully with return code 0!")
