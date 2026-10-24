import bpy
import bmesh
import math
import sys
import os

sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages")
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human_generator import load_anatomical_base_mold

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()
s = 1.0  # 1.65m canonical height

verts = [list(v) for v in raw_verts]

# 1. Anatomical sculpting pass
for i, (x, y, z) in enumerate(verts):
    # --- Teardrop Bust ---
    # Center each breast at (±0.088, -0.065, 1.155)
    if 1.06 * s <= z <= 1.27 * s and abs(x) < 0.22 * s and y < -0.02 * s:
        dx_b = (abs(x) - 0.088 * s) / (0.078 * s)
        dz_b = (z - 1.155 * s) / (0.088 * s)
        r2_b = dx_b * dx_b + dz_b * dz_b
        if r2_b < 1.0:
            # Gravity sag: more projection in lower hemisphere
            sag = 1.0 - 0.40 * dz_b
            w_bust = ((1.0 - r2_b) ** 2) * sag
            # Project forward (-Y)
            verts[i][1] -= 0.038 * s * w_bust
            # Cleavage definition: slight separation near center
            if abs(x) < 0.035 * s:
                c_dip = (1.0 - abs(x) / (0.035 * s)) ** 2
                verts[i][1] += 0.012 * s * c_dip

    # --- Rounded Gluteal Curves (Vòng mông nở nang) ---
    # Center each gluteal cheek at (±0.088, 0.085, 0.855)
    if 0.74 * s <= z <= 0.96 * s and abs(x) < 0.22 * s and y > 0.01 * s:
        dx_g = (abs(x) - 0.088 * s) / (0.085 * s)
        dz_g = (z - 0.855 * s) / (0.095 * s)
        r2_g = dx_g * dx_g + dz_g * dz_g
        if r2_g < 1.0:
            w_glute = (1.0 - r2_g) ** 2
            # Project backward (+Y)
            verts[i][1] += 0.034 * s * w_glute
            # Gluteal fold / under-buttock shelf
            if dz_g < -0.3:
                under_fold = (-0.3 - dz_g) / 0.7
                verts[i][2] += 0.006 * s * under_fold * (1.0 - dx_g * dx_g)

    # --- Lumbar Lordosis (Độ cong thắt lưng thanh thoát) ---
    if 0.94 * s <= z <= 1.08 * s and abs(x) < 0.16 * s and y > 0.01 * s:
        w_lumbar = (math.cos((z - 1.01 * s) * math.pi / (0.14 * s)) ** 2)
        verts[i][1] -= 0.014 * s * w_lumbar

    # --- Waist Cinch (Tỷ lệ eo/hông chuẩn nữ tính WHR ~0.69) ---
    if 0.95 * s <= z <= 1.10 * s and abs(x) < 0.20 * s:
        w_waist = (math.cos((z - 1.025 * s) * math.pi / (0.15 * s)) ** 2)
        verts[i][0] *= (1.0 - 0.08 * w_waist)
        verts[i][1] *= (1.0 - 0.06 * w_waist)

    # --- Clavicle Definition (Xương quai xanh) ---
    if 1.28 * s <= z <= 1.34 * s and 0.02 * s < abs(x) < 0.14 * s and y < -0.01 * s:
        dx_c = (abs(x) - 0.08 * s) / (0.06 * s)
        dz_c = (z - 1.31 * s) / (0.03 * s)
        r2_c = dx_c * dx_c + dz_c * dz_c
        if r2_c < 1.0:
            w_clav = (1.0 - r2_c) ** 2
            verts[i][1] -= 0.005 * s * w_clav

# Build mesh in Blender
mesh = bpy.data.meshes.new("Perfect_Mold_Mesh")
bm = bmesh.new()
for v in verts:
    bm.verts.new(v)
bm.verts.ensure_lookup_table()
for q in raw_quads:
    bm.faces.new([bm.verts[vi] for vi in q])
bm.to_mesh(mesh)
bm.free()

obj = bpy.data.objects.new("Perfect_Mold_Obj", mesh)
scene.collection.objects.link(obj)

for p in mesh.polygons:
    p.use_smooth = True

# Add subdivision surface for silky smooth visual curves
sub = obj.modifiers.new("Subsurf", 'SUBSURF')
sub.levels = 1

# Material with SSS
mat = bpy.data.materials.new("ClaySkin")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.957, 0.894, 0.863, 1.0) # Porcelain #F4E4DC
    bsdf.inputs["Roughness"].default_value = 0.35
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.subsurface_method = 'RANDOM_WALK'
        bsdf.inputs["Subsurface Weight"].default_value = 0.3
        bsdf.inputs["Subsurface Radius"].default_value = (0.008, 0.004, 0.002)
        bsdf.inputs["Subsurface Scale"].default_value = 0.05
mesh.materials.append(mat)

# Studio Lights
bpy.ops.object.light_add(type='SUN', location=(2, -3, 3))
sun = bpy.context.active_object
sun.data.energy = 3.5

bpy.ops.object.light_add(type='AREA', location=(-2, -2, 2))
fill = bpy.context.active_object
fill.data.energy = 180.0
fill.data.size = 2.5

bpy.ops.object.light_add(type='AREA', location=(0, 2.5, 2))
rim = bpy.context.active_object
rim.data.energy = 220.0
rim.data.size = 2.0

# Camera
cam_data = bpy.data.cameras.new("TestCam")
cam = bpy.data.objects.new("TestCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.device = 'CPU'
scene.render.resolution_x = 720
scene.render.resolution_y = 1280

# 1. Front view
cam.location = (0, -2.6, 0.85)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_perfect_front.png"
bpy.ops.render.render(write_still=True)

# 2. Side view
cam.location = (2.6, 0, 0.85)
cam.rotation_euler = (math.radians(90), 0, math.radians(90))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_perfect_side.png"
bpy.ops.render.render(write_still=True)

# 3. Three-quarter view
cam.location = (1.8, -2.0, 0.95)
cam.rotation_euler = (math.radians(85), 0, math.radians(42))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_perfect_threequarter.png"
bpy.ops.render.render(write_still=True)

# 4. Back view
cam.location = (0, 2.6, 0.85)
cam.rotation_euler = (math.radians(90), 0, math.radians(180))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_perfect_back.png"
bpy.ops.render.render(write_still=True)

print("Rendered all 4 angles of perfect mold!")
