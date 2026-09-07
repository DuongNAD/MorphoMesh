import bpy

bpy.ops.wm.open_mainfile(filepath="output/yu_nian_an/Yu_Nian_An_Master.blend")
print("Scene res X:", bpy.context.scene.render.resolution_x)
print("Scene res Y:", bpy.context.scene.render.resolution_y)
print("Scene engine:", bpy.context.scene.render.engine)
print("Active camera:", bpy.context.scene.camera.name)
