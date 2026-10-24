import sys
import bpy

print("=== BLENDER INFO ===")
print("Blender version:", bpy.app.version_string)
print("Python version:", sys.version)

print("\n=== RENDER ENGINES ===")
# List available render engines
scene = bpy.context.scene
print("Current engine:", scene.render.engine)
# Try setting different engines
for eng in ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH"]:
    try:
        scene.render.engine = eng
        print(f"Engine '{eng}' supported: YES (actual: {scene.render.engine})")
    except Exception as e:
        print(f"Engine '{eng}' supported: NO ({e})")

print("\n=== GLTF IMPORT OPERATOR ===")
print("has import_scene.gltf:", hasattr(bpy.ops.import_scene, "gltf"))
print("has wm.obj_import:", hasattr(bpy.ops.wm, "obj_import"))

print("\n=== MATERIAL / SHADING ATTRIBUTES (Blender 4.5) ===")
mat = bpy.data.materials.new(name="TestMat")
mat.use_nodes = True
print("Material attributes:", [attr for attr in dir(mat) if "blend" in attr or "shadow" in attr or "surface" in attr])
if hasattr(mat, "blend_method"):
    print("mat.blend_method values:", bpy.types.Material.bl_rna.properties['blend_method'].enum_items.keys() if 'blend_method' in bpy.types.Material.bl_rna.properties else "N/A")
else:
    print("mat.blend_method: NOT PRESENT in Blender 4.5 (EEVEE Next)")

# Check shadow catcher on object
obj = bpy.data.objects.new("TestObj", None)
print("Object shadow catcher attribute:", hasattr(obj, "is_shadow_catcher"))
if hasattr(obj, "is_shadow_catcher"):
    print("is_shadow_catcher default:", obj.is_shadow_catcher)

print("=== DONE ===")
