import bpy
import math

# Load the master blend file
blend_path = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)

scene = bpy.context.scene

# Hide all Beauty (Liva) objects
for o in bpy.data.objects:
    if "Beauty" in o.name:
        o.hide_render = True
        o.hide_viewport = True

# Unhide Yu_Nian_An_Body
body = bpy.data.objects.get("Yu_Nian_An_Body")
if body:
    body.hide_render = False
    body.hide_viewport = False
    print("Found Yu_Nian_An_Body with", len(body.data.vertices), "vertices")

# Check camera
cam = bpy.data.objects.get("Camera_Beauty_Front")
if not cam:
    cam = bpy.data.objects.get("Camera_Front")
scene.camera = cam

# Set render settings
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.device = 'CPU'
scene.render.resolution_x = 720
scene.render.resolution_y = 1280
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_render_unhidden_body.png"

bpy.ops.render.render(write_still=True)
print("Rendered unhidden body successfully!")
