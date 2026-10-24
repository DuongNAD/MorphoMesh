import bpy
import math

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Load base mold obj
mold_path = r"E:\tool\mcp\MorphoMesh\data\templates\anatomical_female_base_mold.obj"
bpy.ops.wm.obj_import(filepath=mold_path)

body = bpy.context.selected_objects[0]
body.name = "Base_Mold"

# Add smooth shading
for f in body.data.polygons:
    f.use_smooth = True

# Add subdivision surface level 1 for smooth curvature
sub = body.modifiers.new("Subsurf", 'SUBSURF')
sub.levels = 1

# Material
mat = bpy.data.materials.new("ClaySkin")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.92, 0.82, 0.78, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.4
body.data.materials.append(mat)

# Studio Lights
bpy.ops.object.light_add(type='SUN', location=(2, -3, 3))
sun = bpy.context.active_object
sun.data.energy = 3.0

bpy.ops.object.light_add(type='AREA', location=(-2, -2, 2))
fill = bpy.context.active_object
fill.data.energy = 150.0
fill.data.size = 2.0

bpy.ops.object.light_add(type='AREA', location=(0, 2, 2))
rim = bpy.context.active_object
rim.data.energy = 200.0
rim.data.size = 2.0

# Camera
cam_data = bpy.data.cameras.new("TestCam")
cam = bpy.data.objects.new("TestCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# Render settings
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.device = 'CPU'
scene.render.resolution_x = 720
scene.render.resolution_y = 1280

# 1. Front view
cam.location = (0, -2.8, 0.9)
cam.rotation_euler = (math.radians(88), 0, 0)
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_real_mold_front.png"
bpy.ops.render.render(write_still=True)

# 2. Side view
cam.location = (2.8, 0, 0.9)
cam.rotation_euler = (math.radians(88), 0, math.radians(90))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_real_mold_side.png"
bpy.ops.render.render(write_still=True)

# 3. Three-quarter view
cam.location = (2.0, -2.0, 1.0)
cam.rotation_euler = (math.radians(82), 0, math.radians(45))
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_real_mold_threequarter.png"
bpy.ops.render.render(write_still=True)

print("Render complete!")
