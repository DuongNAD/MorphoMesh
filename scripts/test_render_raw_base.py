import bpy
import math

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

import sys
import os
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages")
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human_generator import load_anatomical_base_mold

raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()

mesh = bpy.data.meshes.new("Raw_Base_Mesh")
import bmesh
bm = bmesh.new()
for v in raw_verts:
    bm.verts.new(v)
bm.verts.ensure_lookup_table()
for q in raw_quads:
    bm.faces.new([bm.verts[i] for i in q])
bm.to_mesh(mesh)
bm.free()

obj = bpy.data.objects.new("Raw_Base_Obj", mesh)
scene.collection.objects.link(obj)

for p in mesh.polygons:
    p.use_smooth = True

mat = bpy.data.materials.new("ClaySkin")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.92, 0.82, 0.78, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.4
mesh.materials.append(mat)

# Studio Lights
bpy.ops.object.light_add(type='SUN', location=(2, -3, 3))
sun = bpy.context.active_object
sun.data.energy = 3.0

bpy.ops.object.light_add(type='AREA', location=(-2, -2, 2))
fill = bpy.context.active_object
fill.data.energy = 150.0
fill.data.size = 2.0

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

# Front view
cam.location = (0, -2.6, 0.85)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_raw_base_front.png"
bpy.ops.render.render(write_still=True)

# Side view
cam.location = (2.6, 0, 0.85)
cam.rotation_euler = (math.radians(90), 0, math.radians(90))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_raw_base_side.png"
bpy.ops.render.render(write_still=True)

print("Rendered raw base mold!")
