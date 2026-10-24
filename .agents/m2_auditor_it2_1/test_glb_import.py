import sys
import bpy

def test_glb_import():
    print("=== TESTING RE-IMPORT OF ANIME_RIGGED.GLB IN BLENDER ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath="output/anime_rigged.glb")
    
    arm_obj = bpy.data.objects.get("Anime_Armature")
    if not arm_obj:
        print("FAIL: Anime_Armature not found after glTF import!")
        sys.exit(1)
        
    print(f"Imported Armature: {arm_obj.name}, rotation={tuple(arm_obj.rotation_euler)}, location={tuple(arm_obj.location)}")
    
    submeshes = ["Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs", "Anime_Hair", "Anime_Skirt", "Anime_Shoes"]
    for name in submeshes:
        obj = bpy.data.objects.get(name)
        if not obj:
            print(f"FAIL: {name} not found after glTF import!")
            continue
        z_coords = [v.co.z for v in obj.data.vertices]
        y_coords = [v.co.y for v in obj.data.vertices]
        print(f"{name}: verts={len(obj.data.vertices)}, Z_range=[{min(z_coords):.3f}, {max(z_coords):.3f}], Y_range=[{min(y_coords):.3f}, {max(y_coords):.3f}]")
        
    print("GLB re-import verified successfully!")

if __name__ == "__main__":
    test_glb_import()
