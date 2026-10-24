import os
import struct
import json
import re
from PIL import Image
import subprocess

print("=== INDEPENDENT DELIVERABLE EMPIRICAL AUDIT ===")

# 1. Blend file
blend_path = "output/yu_nian_an/Yu_Nian_An_Master.blend"
blend_size = os.path.getsize(blend_path)
print(f"1. Master blend size: {blend_size} bytes ({blend_size / (1024*1024):.2f} MB)")
assert blend_size > 5_000_000, f"Blend size {blend_size} <= 5 MB"

# 2. GLB file
glb_path = "output/yu_nian_an/Yu_Nian_An.glb"
glb_size = os.path.getsize(glb_path)
print(f"2. GLB size: {glb_size} bytes ({glb_size / (1024*1024):.2f} MB)")
assert glb_size > 2_000_000, f"GLB size {glb_size} <= 2 MB"

with open(glb_path, "rb") as f:
    magic, version, length = struct.unpack("<4sII", f.read(12))
    assert magic == b"glTF", f"Invalid magic: {magic}"
    assert version == 2, f"Invalid version: {version}"
    chunk_len, chunk_type = struct.unpack("<II", f.read(8))
    assert chunk_type == 0x4E4F534A  # JSON
    json_bytes = f.read(chunk_len)
    gltf = json.loads(json_bytes.decode("utf-8"))

meshes = gltf.get("meshes", [])
nodes = gltf.get("nodes", [])
print(f"   GLB total meshes: {len(meshes)}, total nodes: {len(nodes)}")

# Check 100% TEXCOORD_0
prims_checked = 0
for m in meshes:
    for p in m.get("primitives", []):
        prims_checked += 1
        assert "TEXCOORD_0" in p.get("attributes", {}), f"Primitive in mesh {m.get('name')} missing TEXCOORD_0"
print(f"   GLB primitives with TEXCOORD_0: {prims_checked}/{prims_checked} (100%)")

# Check 52 morph targets in extras.targetNames
body_mesh = next((m for m in meshes if m.get("name") == "Yu_Nian_An_Body"), None)
assert body_mesh is not None, "Body mesh not found in GLB"
target_names = body_mesh.get("extras", {}).get("targetNames", [])
print(f"   GLB Yu_Nian_An_Body morph targets in extras.targetNames: {len(target_names)}")
assert len(target_names) == 52, f"Expected 52 morph targets, found {len(target_names)}"

# 3. FBX file
fbx_path = "output/yu_nian_an/Yu_Nian_An.fbx"
fbx_size = os.path.getsize(fbx_path)
print(f"3. FBX size: {fbx_size} bytes ({fbx_size / (1024*1024):.2f} MB)")
assert fbx_size > 5_000_000, f"FBX size {fbx_size} <= 5 MB"

with open(fbx_path, "rb") as f:
    header = f.read(27)
    magic = header[:23]
    version = struct.unpack("<I", header[23:27])[0]
    print(f"   FBX header: {magic}, version: {version}")
    assert b"Kaydara FBX Binary" in magic, f"Invalid FBX magic: {magic}"
    assert version == 7400, f"Expected FBX version 7400, got {version}"
    f.seek(0)
    fbx_content = f.read()

def_matches = set(re.findall(rb"DEF-[a-zA-Z0-9_\.]+", fbx_content))
print(f"   FBX unique DEF bones matched: {len(def_matches)}")
assert len(def_matches) == 163, f"Expected 163 unique DEF bones in FBX, found {len(def_matches)}"

# 4. Textures
tex_dir = "output/yu_nian_an/textures"
expected_tex = [
    "Yu_Nian_An_BaseColor_4K.png",
    "Yu_Nian_An_Normal_4K.png",
    "Yu_Nian_An_Roughness_4K.png",
    "Yu_Nian_An_Metallic_4K.png",
    "Yu_Nian_An_SSS_4K.png",
    "Yu_Nian_An_Alpha_4K.png",
    "Yu_Nian_An_Height_4K.png",
    "Yu_Nian_An_ORM_4K.png",
    "Yu_Nian_An_MaskMap_4K.png",
]
print(f"4. Inspecting {len(expected_tex)} PBR textures...")
for t in expected_tex:
    p = os.path.join(tex_dir, t)
    assert os.path.isfile(p), f"Missing texture: {t}"
    with Image.open(p) as img:
        print(f"   {t:30} | size: {img.size} | mode: {img.mode} | bytes: {os.path.getsize(p)}")
        assert img.size == (4096, 4096), f"{t} size is {img.size}, expected (4096, 4096)"

# 5. Live Blender verification of Master .blend
blender_bin = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
inspect_script = """
import bpy
import json
import numpy as np

bpy.ops.wm.open_mainfile(filepath=r"__BLEND_PATH__")

# 1. Check collections
collections = [c.name for c in bpy.data.collections]
root_col = bpy.data.collections.get("Yu_Nian_An_Master")
child_cols = [c.name for c in root_col.children] if root_col else []

# 2. Check DEF bones
rig = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
def_bones = [b.name for b in rig.data.bones if b.name.startswith("DEF-")] if rig else []

# 3. Check shape keys on Yu_Nian_An_Body
body = bpy.data.objects.get("Yu_Nian_An_Body")
shape_keys = []
if body and body.data.shape_keys:
    shape_keys = [k.name for k in body.data.shape_keys.key_blocks if k.name != "Basis"]

# 4. Check marionette strings snapping to finger bone tails
strings = bpy.data.objects.get("Prop_Marionette_Strings")
strings_snap_errors = []
finger_tail_bones = [
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
]
if strings and rig:
    verts_per_cord = 14
    for cord_i, b_name in enumerate(finger_tail_bones):
        bone = rig.data.bones.get(b_name)
        if bone:
            tail_world = rig.matrix_world @ bone.tail_local
            v0_idx = cord_i * verts_per_cord
            v1_idx = v0_idx + 1
            v0 = strings.matrix_world @ strings.data.vertices[v0_idx].co
            v1 = strings.matrix_world @ strings.data.vertices[v1_idx].co
            center = (v0 + v1) * 0.5
            dist = (center - tail_world).length
            strings_snap_errors.append(dist)

# 5. Check wardrobe clearance
import bmesh
import mathutils
body = bpy.data.objects.get("Yu_Nian_An_Body")
bm_body = bmesh.new()
bm_body.from_mesh(body.data)
bm_body.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

wardrobe_stats = {}
wardrobe_parts = ["Mesh_Dress_Bodice", "Mesh_Dress_WaistSash", "Mesh_Dress_PleatedSkirt"]
for part_name in wardrobe_parts:
    obj = bpy.data.objects.get(part_name)
    if obj:
        verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
        min_signed = float("inf")
        penetrations = 0
        for v in verts:
            loc, normal, _, dist = bvh.find_nearest(v)
            if loc is not None:
                diff = v - loc
                signed_dist = dist if diff.dot(normal) >= 0 else -dist
                if signed_dist < 0:
                    penetrations += 1
                if signed_dist < min_signed:
                    min_signed = signed_dist
        wardrobe_stats[part_name] = {
            "min_clearance_mm": min_signed * 1000.0,
            "penetrations": penetrations,
        }

print("===BLENDER_INSPECT_RESULT===")
print(json.dumps({
    "root_col": root_col.name if root_col else None,
    "child_cols": child_cols,
    "def_bones_count": len(def_bones),
    "shape_keys_count": len(shape_keys),
    "strings_snap_max_err_mm": max(strings_snap_errors) * 1000.0 if strings_snap_errors else None,
    "strings_cords_count": len(strings_snap_errors),
    "wardrobe_stats": wardrobe_stats,
}))
print("===BLENDER_INSPECT_END===")

""".replace("__BLEND_PATH__", os.path.abspath(blend_path))


proc = subprocess.run([blender_bin, "--background", "--python-expr", inspect_script], capture_output=True, text=True, timeout=60)
assert proc.returncode == 0, f"Blender inspection failed: {proc.stderr}"
out = proc.stdout
assert "===BLENDER_INSPECT_RESULT===" in out, f"No result marker in output: {out}"
json_text = out.split("===BLENDER_INSPECT_RESULT===")[1].split("===BLENDER_INSPECT_END===")[0].strip()
result_json = json.loads(json_text)
print("5. Live Blender inspection results:")

print(f"   Root collection: {result_json['root_col']}")
print(f"   Child collections: {result_json['child_cols']}")
print(f"   DEF bones count: {result_json['def_bones_count']}")
assert result_json['def_bones_count'] == 163, f"Expected 163 DEF bones, got {result_json['def_bones_count']}"
print(f"   ARKit shape keys count: {result_json['shape_keys_count']}")
assert result_json['shape_keys_count'] == 52, f"Expected 52 shape keys, got {result_json['shape_keys_count']}"
print(f"   Marionette strings max snap error: {result_json['strings_snap_max_err_mm']:.4f} mm")
assert result_json['strings_snap_max_err_mm'] < 0.1, f"Strings snap error too large: {result_json['strings_snap_max_err_mm']}"
print(f"   Wardrobe stats: {json.dumps(result_json['wardrobe_stats'], indent=2)}")
for part, st in result_json['wardrobe_stats'].items():
    assert st['penetrations'] == 0, f"Penetrations in {part}: {st['penetrations']}"
    assert st['min_clearance_mm'] >= 5.0, f"Clearance in {part} < 5.0mm: {st['min_clearance_mm']}"

print("=== ALL 5 DELIVERABLES AUDIT CHECKS CONFIRMED EMPIRICALLY! ===")

