import bpy, os

# Clear existing objects
bpy.ops.wm.read_factory_settings(use_empty=True)

out_dir = r"E:\tool\mcp\MorphoMesh\.agents\m1_explorer_anime_1\test_output"
obj_names = ["Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs", "Anime_Hair", "Anime_Skirt", "Anime_Shoes"]

char_col = bpy.data.collections.new("Anime_Character_Meshes")
bpy.context.scene.collection.children.link(char_col)

imported_objs = []
for name in obj_names:
    path = os.path.join(out_dir, f"{name}.obj")
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
    print(f"[Blender] Imported {name}: {len(obj.data.vertices)} verts, {len(obj.data.polygons)} polys")

# Save master .blend
blend_path = os.path.join(out_dir, "anime_character_model.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"[Blender] Saved {blend_path}")

# Export .glb
glb_path = os.path.join(out_dir, "anime_character_model.glb")
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=False)
print(f"[Blender] Exported {glb_path}")
