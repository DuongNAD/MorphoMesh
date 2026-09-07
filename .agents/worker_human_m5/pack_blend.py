import bpy

blend_path = "output/yu_nian_an/Yu_Nian_An_Master.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Pack all external images/assets
bpy.ops.file.pack_all()

# Ensure all 16 materials have use_fake_user = True
for m in bpy.data.materials:
    m.use_fake_user = True

# Save packed blend file
bpy.ops.wm.save_mainfile(filepath=blend_path)
print("Successfully packed and saved Yu_Nian_An_Master.blend")
