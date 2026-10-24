import bpy

glb_path = r"E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\output\tropical\veg_tropical_palm_01\veg_tropical_palm_01.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)

print("All objects:", [o.name for o in bpy.data.objects])
print("All meshes:", [m.name for m in bpy.data.meshes])
print("All materials in blend file:", [m.name for m in bpy.data.materials])
print("All images in blend file:", [img.name for img in bpy.data.images])

for m in bpy.data.meshes:
    print(f"Mesh '{m.name}': materials={[mat.name if mat else 'None' for mat in m.materials]}")

