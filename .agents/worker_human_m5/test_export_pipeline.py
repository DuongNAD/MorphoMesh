import bpy
import os
import sys

blend_path = "output/yu_nian_an/Yu_Nian_An_Master.blend"
output_fbx = "output/yu_nian_an/Yu_Nian_An.fbx"
output_glb = "output/yu_nian_an/Yu_Nian_An.glb"

print(f"Loading {blend_path}...")
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Collections to export
export_collections = ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature"]

# Deselect all objects first
bpy.ops.object.select_all(action='DESELECT')

export_objects = []
for c_name in export_collections:
    col = bpy.data.collections.get(c_name)
    if col:
        for obj in col.objects:
            obj.select_set(True)
            export_objects.append(obj)

print(f"Selected {len(export_objects)} objects for export: {[o.name for o in export_objects]}")

# Ensure active object is set (e.g. to Armature or Body)
arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
if arm_obj:
    bpy.context.view_layer.objects.active = arm_obj

# 1. EXPORT FBX
print("Exporting FBX...")
os.makedirs(os.path.dirname(output_fbx), exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=output_fbx,
    use_selection=True,
    object_types={'ARMATURE', 'MESH'},
    mesh_smooth_type='FACE',
    add_leaf_bones=False,
    primary_bone_axis='Y',
    secondary_bone_axis='X',
    bake_anim=False,
)
fbx_size = os.path.getsize(output_fbx) if os.path.exists(output_fbx) else 0
print(f"FBX exported successfully: size = {fbx_size} bytes ({fbx_size / 1024 / 1024:.2f} MB)")

# 2. EXPORT GLB
print("Exporting GLB...")
os.makedirs(os.path.dirname(output_glb), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    use_selection=True,
    export_skins=True,
    export_morph=True,
    export_morph_normal=True,
    export_morph_tangent=False,
    export_materials='EXPORT',
    export_cameras=False,
    export_lights=False,
)
glb_size = os.path.getsize(output_glb) if os.path.exists(output_glb) else 0
print(f"GLB exported successfully: size = {glb_size} bytes ({glb_size / 1024 / 1024:.2f} MB)")
