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

for i, (x, y, z) in enumerate(verts):
    # -------------------------------------------------------------
    # 1. Teardrop Volumetric Bust (Ngực giọt nước chân thực)
    # -------------------------------------------------------------
    if 1.06 * s <= z <= 1.28 * s and abs(x) < 0.22 * s and y < -0.015 * s:
        dx_b = (abs(x) - 0.088 * s) / (0.078 * s)
        dz_b = (z - 1.165 * s) / (0.085 * s)
        r2_b = dx_b * dx_b + dz_b * dz_b
        if r2_b < 1.0:
            # Natural teardrop gravity sag: fuller in lower pole, gentle taper towards clavicle
            sag = 1.0 - 0.35 * dz_b
            w_bust = (math.cos(r2_b * math.pi * 0.5) ** 2) * sag
            verts[i][1] -= 0.038 * s * w_bust
            # Cleavage valley: smooth separation at midline
            if abs(x) < 0.032 * s:
                c_dip = (math.cos(abs(x) * math.pi / (0.032 * s)) + 1.0) * 0.5
                verts[i][1] += 0.014 * s * c_dip

    # -------------------------------------------------------------
    # 2. Rounded Feminine Gluteal Curves (Vòng mông nở nang tròn đầy)
    # -------------------------------------------------------------
    if 0.72 * s <= z <= 0.98 * s and abs(x) < 0.22 * s and y > 0.005 * s:
        dx_g = (abs(x) - 0.086 * s) / (0.086 * s)
        dz_g = (z - 0.855 * s) / (0.110 * s)
        r2_g = dx_g * dx_g + dz_g * dz_g
        if r2_g < 1.0:
            # Smooth spherical harmonic curve for perfectly rounded buttocks
            w_glute = math.cos(r2_g * math.pi * 0.5) ** 2
            verts[i][1] += 0.030 * s * w_glute
            # Smooth blend into upper posterior thigh
            if dz_g < -0.2:
                thigh_blend = (-0.2 - dz_g) / 0.8
                verts[i][1] += 0.008 * s * thigh_blend * (1.0 - dx_g * dx_g)

    # -------------------------------------------------------------
    # 3. Lumbar Lordosis (Độ cong cột sống thắt lưng tự nhiên)
    # -------------------------------------------------------------
    if 0.95 * s <= z <= 1.09 * s and abs(x) < 0.16 * s and y > 0.01 * s:
        w_lumbar = (math.cos((z - 1.02 * s) * math.pi / (0.14 * s)) ** 2)
        verts[i][1] -= 0.014 * s * w_lumbar

    # -------------------------------------------------------------
    # 4. Waist Cinch (Vòng eo thon gọn chuẩn WHR ~0.697)
    # -------------------------------------------------------------
    if 0.96 * s <= z <= 1.10 * s and abs(x) < 0.20 * s:
        w_waist = (math.cos((z - 1.025 * s) * math.pi / (0.14 * s)) ** 2)
        verts[i][0] *= (1.0 - 0.075 * w_waist)
        verts[i][1] *= (1.0 - 0.055 * w_waist)

    # -------------------------------------------------------------
    # 5. Clavicle & Neck Grace (Xương quai xanh & Cốt thế vai)
    # -------------------------------------------------------------
    if 1.28 * s <= z <= 1.34 * s and 0.02 * s < abs(x) < 0.14 * s and y < -0.01 * s:
        dx_c = (abs(x) - 0.08 * s) / (0.06 * s)
        dz_c = (z - 1.31 * s) / (0.03 * s)
        r2_c = dx_c * dx_c + dz_c * dz_c
        if r2_c < 1.0:
            w_clav = (math.cos(r2_c * math.pi * 0.5) ** 2)
            verts[i][1] -= 0.005 * s * w_clav

    # -------------------------------------------------------------
    # 6. Facial Refinement (Khuôn mặt thanh tú, cằm thon V-line)
    # -------------------------------------------------------------
    if z >= 1.38 * s:
        # Chin taper
        if z < 1.46 * s and y < -0.03 * s:
            t_chin = max(0.0, (1.46 * s - z) / (0.08 * s))
            w_chin = t_chin ** 1.5
            verts[i][0] *= (1.0 - 0.06 * w_chin)
            # Gentle feminine chin projection
            if abs(x) < 0.025 * s and 1.39 * s <= z <= 1.43 * s:
                verts[i][1] -= 0.003 * s * (1.0 - abs(x) / (0.025 * s))

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
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\perfect_mold_v2_front.png"
bpy.ops.render.render(write_still=True)

# 2. Side view
cam.location = (2.6, 0, 0.85)
cam.rotation_euler = (math.radians(90), 0, math.radians(90))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\perfect_mold_v2_side.png"
bpy.ops.render.render(write_still=True)

# 3. Three-quarter view
cam.location = (1.8, -2.0, 0.95)
cam.rotation_euler = (math.radians(85), 0, math.radians(42))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\perfect_mold_v2_threequarter.png"
bpy.ops.render.render(write_still=True)

# 4. Back view
cam.location = (0, 2.6, 0.85)
cam.rotation_euler = (math.radians(90), 0, math.radians(180))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\perfect_mold_v2_back.png"
bpy.ops.render.render(write_still=True)

print("Rendered all 4 angles of perfect mold v2!")
