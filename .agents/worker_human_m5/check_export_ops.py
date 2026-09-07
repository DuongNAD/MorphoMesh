import bpy

print("FBX operator doc:")
try:
    bpy.ops.export_scene.fbx.get_rna_type()
    props = bpy.ops.export_scene.fbx.get_rna_type().properties
    print("FBX props:", [p.identifier for p in props])
except Exception as e:
    print("FBX error:", e)

print("\nGLTF operator doc:")
try:
    props_gltf = bpy.ops.export_scene.gltf.get_rna_type().properties
    print("GLTF props:", [p.identifier for p in props_gltf])
except Exception as e:
    print("GLTF error:", e)
